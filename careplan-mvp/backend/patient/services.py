from django.db.models import Q
from careplan.models import Patient
from careplan.exceptions import BlockError, WarningException

def get_patients_list(search=None,page=1, page_size=20):
    queryset = Patient.objects.all().order_by('-id')
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    total_count = queryset.count()
    offset = (page - 1) * page_size
    results = queryset[offset: offset + page_size]
    return total_count, list(results)


def create_patient(
    first_name: str,
    last_name: str,
    mrn: str,
    date_of_birth: str,
    sex: str = '',
    weight_kg=None,
    allergies: str = '',
    primary_diagnosis: str = '',
    additional_diagnoses: list = None,
) -> Patient:
    # 1. MRN 已存在 → BlockError
    if Patient.objects.filter(mrn=mrn).exists():
        existing = Patient.objects.get(mrn=mrn)
        raise BlockError(
            code="DUPLICATE_MRN",
            message=f"A patient with MRN {mrn} already exists.",
            detail={"existing_patient_id": existing.id},
        )

    # 2. 同名+同DOB → WarningException
    duplicate = Patient.objects.filter(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
    ).first()
    if duplicate:
        raise WarningException(
            code="POSSIBLE_DUPLICATE_PATIENT",
            message=f"A patient with the same name and date of birth already exists (MRN: {duplicate.mrn}). Please verify this is not a duplicate.",
            detail={"existing_patient_id": duplicate.id, "existing_mrn": duplicate.mrn},
        )

    # 3. 创建
    return Patient.objects.create(
        first_name=first_name,
        last_name=last_name,
        mrn=mrn,
        date_of_birth=date_of_birth,
        sex=sex,
        weight_kg=weight_kg,
        allergies=allergies,
        primary_diagnosis=primary_diagnosis,
        additional_diagnoses=additional_diagnoses or [],
    )

def get_patient_by_id(patient_id: int):
    from careplan.models import Patient
    try:
        return Patient.objects.prefetch_related('orders__careplan').get(id=patient_id)
    except Patient.DoesNotExist:
        return None


def update_patient(patient_id: int, data: dict):
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return None

    # mrn 不允许修改
    if 'mrn' in data:
        raise BlockError(
            code="MRN_CANNOT_BE_MODIFIED",
            message="MRN cannot be modified.",
            detail={},
        )

    # 更新允许的字段
    allowed_fields = ['first_name', 'last_name', 'date_of_birth', 'sex', 'weight_kg', 'allergies', 'primary_diagnosis', 'additional_diagnoses']
    for field in allowed_fields:
        if field in data:
            setattr(patient, field, data[field])

    patient.save()
    return patient


def delete_patient(patient_id: int):
    from careplan.models import CarePlan
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return None, None

    # 有 pending 或 processing 的订单不能删除
    active_careplan_ids = CarePlan.objects.filter(
        order__patient=patient,
        status__in=['pending', 'processing']
    ).values_list('order__id', flat=True)

    if active_careplan_ids:
        raise BlockError(
            code="PATIENT_HAS_ACTIVE_ORDERS",
            message="Cannot delete patient with active orders.",
            detail={"active_orders": list(active_careplan_ids)},
        )

    patient.delete()
    return True, None