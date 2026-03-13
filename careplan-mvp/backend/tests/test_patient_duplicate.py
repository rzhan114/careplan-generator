# tests/test_patient_duplicate.py
import pytest
from unittest.mock import patch, MagicMock
from careplan.exceptions import WarningException
from careplan.services import get_or_create_patient


# ============================================================
# 测试用的 fixture
# ============================================================

@pytest.fixture
def existing_patient():
    """模拟数据库里已有的 patient"""
    patient = MagicMock()
    patient.id = 1
    patient.first_name = "Alice"
    patient.last_name = "Brown"
    patient.mrn = "001234"
    patient.date_of_birth = "1979-06-08"
    return patient


# ============================================================
# MRN 相同 + 名字和DOB都相同 → 复用，无警告
# ============================================================

@pytest.mark.django_db
def test_same_mrn_same_info_returns_existing(existing_patient):
    """MRN相同，名字DOB也相同 → 直接复用，不创建新patient"""
    with patch("careplan.services.Patient.objects.get") as mock_get:
        mock_get.return_value = existing_patient

        patient, warnings = get_or_create_patient(
            first_name="Alice",
            last_name="Brown",
            mrn="001234",
            date_of_birth="1979-06-08",
        )

        assert patient == existing_patient
        assert warnings == []
        mock_get.assert_called_once_with(mrn="001234")


# ============================================================
# MRN 相同 + 名字不同 → 警告
# ============================================================

@pytest.mark.django_db
def test_same_mrn_different_name_raises_warning(existing_patient):
    """MRN相同但名字不同 → 抛 WarningException"""
    with patch("careplan.services.Patient.objects.get") as mock_get:
        mock_get.return_value = existing_patient

        with pytest.raises(WarningException) as exc_info:
            get_or_create_patient(
                first_name="Alice",
                last_name="Smith",   # ← 名字不同
                mrn="001234",
                date_of_birth="1979-06-08",
                confirm=False,
            )

        assert exc_info.value.code == "MRN_INFO_MISMATCH"
        assert exc_info.value.http_status == 200


@pytest.mark.django_db
def test_same_mrn_different_dob_raises_warning(existing_patient):
    """MRN相同但DOB不同 → 抛 WarningException"""
    with patch("careplan.services.Patient.objects.get") as mock_get:
        mock_get.return_value = existing_patient

        with pytest.raises(WarningException) as exc_info:
            get_or_create_patient(
                first_name="Alice",
                last_name="Brown",
                mrn="001234",
                date_of_birth="1990-01-01",  # ← DOB 不同
                confirm=False,
            )

        assert exc_info.value.code == "MRN_INFO_MISMATCH"


# ============================================================
# MRN 相同 + 名字不同 + confirm=True → 复用，有警告记录
# ============================================================

@pytest.mark.django_db
def test_same_mrn_different_name_with_confirm_returns_existing(existing_patient):
    """MRN相同但名字不同，用户confirm=True → 复用现有patient，返回警告"""
    with patch("careplan.services.Patient.objects.get") as mock_get:
        mock_get.return_value = existing_patient

        patient, warnings = get_or_create_patient(
            first_name="Alice",
            last_name="Smith",
            mrn="001234",
            date_of_birth="1979-06-08",
            confirm=True,
        )

        assert patient == existing_patient
        assert len(warnings) == 1
        assert warnings[0]["code"] == "MRN_INFO_MISMATCH"


# ============================================================
# 名字+DOB 相同 + MRN 不同 → 警告
# ============================================================

@pytest.mark.django_db
def test_same_name_dob_different_mrn_raises_warning(existing_patient):
    """同名同DOB但MRN不同 → 抛 WarningException"""
    from careplan.models import Patient as PatientModel
    from django.core.exceptions import ObjectDoesNotExist

    with patch("careplan.services.Patient.objects.get") as mock_get, \
         patch("careplan.services.Patient.objects.filter") as mock_filter, \
         patch("careplan.services.Patient.objects.create") as mock_create:

        # MRN 查不到
        mock_get.side_effect = PatientModel.DoesNotExist

        # 名字+DOB 能查到
        mock_queryset = MagicMock()
        mock_queryset.exclude.return_value = mock_queryset
        mock_queryset.first.return_value = existing_patient
        mock_filter.return_value = mock_queryset

        with pytest.raises(WarningException) as exc_info:
            get_or_create_patient(
                first_name="Alice",
                last_name="Brown",
                mrn="999999",   # ← MRN 不同
                date_of_birth="1979-06-08",
                confirm=False,
            )

        assert exc_info.value.code == "POSSIBLE_DUPLICATE_PATIENT"


# ============================================================
# 全新 patient → 创建
# ============================================================

@pytest.mark.django_db
def test_new_patient_creates_successfully():
    """完全没有重复 → 创建新 patient"""
    from careplan.models import Patient as PatientModel

    new_patient = MagicMock()
    new_patient.id = 99

    with patch("careplan.services.Patient.objects.get") as mock_get, \
         patch("careplan.services.Patient.objects.filter") as mock_filter, \
         patch("careplan.services.Patient.objects.create") as mock_create:

        mock_get.side_effect = PatientModel.DoesNotExist

        mock_queryset = MagicMock()
        mock_queryset.exclude.return_value = mock_queryset
        mock_queryset.first.return_value = None  # 名字+DOB 也查不到
        mock_filter.return_value = mock_queryset

        mock_create.return_value = new_patient

        patient, warnings = get_or_create_patient(
            first_name="Bob",
            last_name="New",
            mrn="999888",
            date_of_birth="1990-01-01",
        )

        assert patient == new_patient
        assert warnings == []
        mock_create.assert_called_once()