# tests/test_integration.py
import json
import pytest
from unittest.mock import patch
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def valid_payload():
    return {
        "first_name": "Test",
        "last_name": "User",
        "mrn": "777777",
        "date_of_birth": "1990-01-01",
        "provider_name": "Dr. Test",
        "provider_npi": "1111111111",
        "medication_name": "TestDrug",
        "primary_diagnosis": "I10",
    }


@pytest.mark.django_db
def test_create_order_success(client, valid_payload):
    with patch("careplan.tasks.generate_careplan_task.delay") as mock_delay:
        mock_delay.return_value = None
        response = client.post(
            "/api/orders/",
            data=json.dumps(valid_payload),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"


@pytest.mark.django_db
def test_create_order_invalid_npi_returns_400(client, valid_payload):
    valid_payload["provider_npi"] = "123"

    response = client.post(
        "/api/orders/",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert data["type"] == "validation"
    assert "provider_npi" in data["detail"]


@pytest.mark.django_db
def test_create_order_invalid_mrn_returns_400(client, valid_payload):
    valid_payload["mrn"] = "12"

    response = client.post(
        "/api/orders/",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert data["type"] == "validation"


@pytest.mark.django_db
def test_create_order_npi_conflict_returns_409(client, valid_payload):
    from careplan.models import Provider
    Provider.objects.create(name="Dr. Original", npi="1111111111")
    valid_payload["provider_name"] = "Dr. Different"

    response = client.post(
        "/api/orders/",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )

    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "block"
    assert data["code"] == "NPI_NAME_MISMATCH"


@pytest.mark.django_db
def test_create_order_mrn_mismatch_returns_warning(client, valid_payload):
    from careplan.models import Patient
    Patient.objects.create(
        first_name="Test",
        last_name="User",
        mrn="777777",
        date_of_birth="1990-01-01",
    )
    valid_payload["last_name"] = "Different"

    response = client.post(
        "/api/orders/",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "warning"
    assert data["code"] == "MRN_INFO_MISMATCH"


@pytest.mark.django_db
def test_duplicate_order_same_day_returns_409(client, valid_payload):
    with patch("careplan.tasks.generate_careplan_task.delay") as mock_delay:
        mock_delay.return_value = None

        client.post(
            "/api/orders/",
            data=json.dumps(valid_payload),
            content_type="application/json",
        )

        response = client.post(
            "/api/orders/",
            data=json.dumps(valid_payload),
            content_type="application/json",
        )

    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "block"
    assert data["code"] == "DUPLICATE_ORDER_SAME_DAY"