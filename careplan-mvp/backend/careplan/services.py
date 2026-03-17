# careplan/services.py

import os
import time
from datetime import date
from .models import Patient, Provider, Order, CarePlan
from .exceptions import BlockError, WarningException
from .internal_models import InternalOrder

def get_or_create_provider(name: str, npi: str) -> Provider:
    try:
        existing = Provider.objects.get(npi=npi)
        if existing.name == name:
            return existing
        else:
            raise BlockError(
                code="NPI_NAME_MISMATCH",
                message=f"NPI {npi} already belongs to '{existing.name}', not '{name}'.",
                detail={
                    "existing_name": existing.name,
                    "submitted_name": name,
                },
            )
    except Provider.DoesNotExist:
        return Provider.objects.create(name=name, npi=npi)


def get_or_create_patient(
    first_name: str,
    last_name: str,
    mrn: str,
    date_of_birth: str,
    confirm: bool = False,
) -> tuple[Patient, list]:
    warnings = []

    try:
        existing = Patient.objects.get(mrn=mrn)
        name_match = (existing.first_name == first_name and existing.last_name == last_name)
        dob_match = str(existing.date_of_birth) == str(date_of_birth)

        if name_match and dob_match:
            return existing, []

        if not confirm:
            raise WarningException(
                code="MRN_INFO_MISMATCH",
                message=f"A patient with MRN {mrn} already exists but has different information (name or date of birth). Please verify and confirm to proceed.",
                detail={
                    "existing_patient_id": existing.id,
                    "existing_name": f"{existing.first_name} {existing.last_name}",
                    "existing_dob": str(existing.date_of_birth),
                },
            )
        else:
            warnings.append({"code": "MRN_INFO_MISMATCH", "message": "MRN info mismatch, user confirmed."})
            return existing, warnings

    except Patient.DoesNotExist:
        pass

    duplicate = Patient.objects.filter(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
    ).exclude(mrn=mrn).first()

    if duplicate and not confirm:
        raise WarningException(
            code="POSSIBLE_DUPLICATE_PATIENT",
            message=f"A patient with the same name and date of birth already exists with a different MRN ({duplicate.mrn}). This may be the same person. Please verify and confirm to proceed.",
            detail={"existing_patient_id": duplicate.id, "existing_mrn": duplicate.mrn},
        )

    patient = Patient.objects.create(
        first_name=first_name,
        last_name=last_name,
        mrn=mrn,
        date_of_birth=date_of_birth,
    )
    return patient, warnings


def check_order_duplicate(patient: Patient, medication_name: str, confirm: bool = False):
    today = date.today()

    same_day = Order.objects.filter(
        patient=patient,
        medication_name=medication_name,
        created_at__date=today,
    ).first()

    if same_day:
        raise BlockError(
            code="DUPLICATE_ORDER_SAME_DAY",
             message=f"A previous order for {medication_name} already exists for this patient. This may be a refill. Please verify and confirm to proceed.",
            detail={"existing_order_id": same_day.id},
        )

    previous = Order.objects.filter(
        patient=patient,
        medication_name=medication_name,
    ).order_by("-created_at").first()

    if previous and not confirm:
        raise WarningException(
            code="POSSIBLE_DUPLICATE_ORDER",
            message=f"A previous order for {medication_name} exists. Click process to proceed.",
            detail={
                "existing_order_id": previous.id,
                "existing_order_date": str(previous.created_at.date()),
            },
        )


# 函数签名改成接收 InternalOrder
def create_order_with_careplan(order: InternalOrder, confirm: bool = False) -> CarePlan:
    # 1. Provider 重复检测
    provider = get_or_create_provider(
        name=order.provider.name,
        npi=order.provider.npi,
    )
    # 2. Patient 重复检测
    patient, warnings = get_or_create_patient(
        first_name=order.patient.first_name,
        last_name=order.patient.last_name,
        mrn=order.patient.mrn,
        date_of_birth=order.patient.date_of_birth,
        confirm=confirm,
    )
    # 3. Order 重复检测
    check_order_duplicate(
        patient=patient,
        medication_name=order.medication.medication_name,
        confirm=confirm,
    )
    # 4. 创建 Order
    order_obj = Order.objects.create(
        patient=patient,
        provider=provider,
        medication_name=order.medication.medication_name,
        primary_diagnosis=order.medication.primary_diagnosis,
        additional_diagnoses=order.medication.additional_diagnoses,
        medication_history=order.medication.medication_history,
        patient_records=order.medication.patient_records,
    )
    # 5. 创建 CarePlan
    careplan = CarePlan.objects.create(
        order=order_obj,
        status=CarePlan.Status.PENDING
    )
    # 6. 放进 Celery 队列
    try:
        from careplan.tasks import generate_careplan_task
        generate_careplan_task.delay(careplan.id)
    except Exception as e:
        print(f"Redis error: {e}")
    return careplan, warnings


def get_careplan_by_id(careplan_id: int) -> CarePlan:
    return CarePlan.objects.get(id=careplan_id)