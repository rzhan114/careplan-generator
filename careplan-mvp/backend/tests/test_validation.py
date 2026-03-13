# tests/test_validation.py
import pytest
from careplan.serializers import OrderCreateSerializer
from careplan.exceptions import ValidationError


def valid_data():
    return {
        "first_name": "Alice",
        "last_name": "Brown",
        "mrn": "001234",
        "date_of_birth": "1979-06-08",
        "provider_name": "Dr. Sarah Johnson",
        "provider_npi": "1234567890",
        "medication_name": "IVIG",
        "primary_diagnosis": "G70.01",
    }


def test_valid_data_passes():
    s = OrderCreateSerializer(valid_data())
    assert s.is_valid() is True


def test_missing_required_field_fails():
    data = valid_data()
    del data["first_name"]
    s = OrderCreateSerializer(data)
    assert s.is_valid() is False
    assert "first_name" in s._errors


def test_npi_not_10_digits_fails():
    data = valid_data()
    data["provider_npi"] = "123"
    s = OrderCreateSerializer(data)
    assert s.is_valid() is False
    assert "provider_npi" in s._errors


def test_npi_with_letters_fails():
    data = valid_data()
    data["provider_npi"] = "123abc7890"
    s = OrderCreateSerializer(data)
    assert s.is_valid() is False
    assert "provider_npi" in s._errors


def test_mrn_not_6_digits_fails():
    data = valid_data()
    data["mrn"] = "123"
    s = OrderCreateSerializer(data)
    assert s.is_valid() is False
    assert "mrn" in s._errors


def test_invalid_icd10_fails():
    data = valid_data()
    data["primary_diagnosis"] = "not-valid"
    s = OrderCreateSerializer(data)
    assert s.is_valid() is False
    assert "primary_diagnosis" in s._errors


def test_valid_icd10_without_decimal_passes():
    data = valid_data()
    data["primary_diagnosis"] = "I10"
    s = OrderCreateSerializer(data)
    assert s.is_valid() is True


def test_raise_if_invalid_throws_validation_error():
    data = valid_data()
    data["provider_npi"] = "123"
    s = OrderCreateSerializer(data)
    with pytest.raises(ValidationError) as exc_info:
        s.raise_if_invalid()
    assert exc_info.value.http_status == 400