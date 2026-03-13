# tests/test_provider_duplicate.py
import pytest
from unittest.mock import patch, MagicMock
from careplan.exceptions import BlockError
from careplan.services import get_or_create_provider


@pytest.fixture
def existing_provider():
    provider = MagicMock()
    provider.id = 1
    provider.name = "Dr. Sarah Johnson"
    provider.npi = "1234567890"
    return provider


# ============================================================
# NPI 相同 + 名字相同 → 复用
# ============================================================

@pytest.mark.django_db
def test_same_npi_same_name_returns_existing(existing_provider):
    with patch("careplan.services.Provider.objects.get") as mock_get:
        mock_get.return_value = existing_provider

        provider = get_or_create_provider(
            name="Dr. Sarah Johnson",
            npi="1234567890",
        )

        assert provider == existing_provider


# ============================================================
# NPI 相同 + 名字不同 → BlockError
# ============================================================

@pytest.mark.django_db
def test_same_npi_different_name_raises_block(existing_provider):
    with patch("careplan.services.Provider.objects.get") as mock_get:
        mock_get.return_value = existing_provider

        with pytest.raises(BlockError) as exc_info:
            get_or_create_provider(
                name="Dr. Wrong Name",
                npi="1234567890",
            )

        assert exc_info.value.code == "NPI_NAME_MISMATCH"
        assert exc_info.value.http_status == 409


# ============================================================
# NPI 不存在 → 创建新 provider
# ============================================================

@pytest.mark.django_db
def test_new_npi_creates_provider():
    from careplan.models import Provider as ProviderModel

    new_provider = MagicMock()

    with patch("careplan.services.Provider.objects.get") as mock_get, \
         patch("careplan.services.Provider.objects.create") as mock_create:

        mock_get.side_effect = ProviderModel.DoesNotExist
        mock_create.return_value = new_provider

        provider = get_or_create_provider(
            name="Dr. New Doctor",
            npi="9999999999",
        )

        assert provider == new_provider
        mock_create.assert_called_once_with(name="Dr. New Doctor", npi="9999999999")