# careplan/services.py

import os
import time
from datetime import date
from .models import Patient, Provider, Order, CarePlan
from .exceptions import BlockError, WarningException


# ============================================================
# LLM 调用逻辑
# 从 tasks.py 搬过来，tasks.py 改成调用这里
# ============================================================
def call_llm(patient, order, provider) -> str:
    USE_MOCK = os.environ.get('USE_MOCK_LLM', 'true').lower() == 'true'

    if USE_MOCK:
        time.sleep(2)
        return f"""
Problem list:
- Need for treatment with {order.medication_name}
- Risk of adverse reactions

Goals (SMART):
- Complete full course within prescribed timeline
- No severe adverse reactions

Pharmacist interventions:
- Verify dosing schedule
- Screen for drug interactions
- Counsel patient on side effects

Monitoring plan:
- Baseline labs before treatment
- Follow-up at 2 weeks
        """.strip()
    else:
        from anthropic import Anthropic
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"""
You are a clinical pharmacist. Generate a professional care plan based on the following patient information.
Patient Information:
Patient: {patient.first_name} {patient.last_name}
MRN: {patient.mrn}
Medication: {order.medication_name}
Primary Diagnosis: {order.primary_diagnosis}
Additional Diagnoses: {order.additional_diagnoses}
Medication History: {order.medication_history}
Patient Records: {order.patient_records}
Referring Provider: {provider.name} (NPI: {provider.npi})

Please generate a comprehensive care plan that includes:

1. Problem List / Drug Therapy Problems (DTPs)
2. Goals (SMART goals)
3. Pharmacist Interventions / Plan
4. Monitoring Plan & Lab Schedule

Format the response clearly with these 4 sections.
            """}]
        )
        return response.content[0].text


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


def create_order_with_careplan(validated_data: dict, confirm: bool = False) -> CarePlan:
    # 1. Provider 重复检测（可能 raise BlockError）
    provider = get_or_create_provider(
        name=validated_data['provider_name'],
        npi=validated_data['provider_npi'],
    )

    # 2. Patient 重复检测（可能 raise WarningException）
    patient, warnings = get_or_create_patient(
        first_name=validated_data['first_name'],
        last_name=validated_data['last_name'],
        mrn=validated_data['mrn'],
        date_of_birth=validated_data['date_of_birth'],
        confirm=confirm,
    )

    # 3. Order 重复检测（可能 raise BlockError 或 WarningException）
    check_order_duplicate(
        patient=patient,
        medication_name=validated_data['medication_name'],
        confirm=confirm,
    )

    # 4. 创建 Order
    order = Order.objects.create(
        patient=patient,
        provider=provider,
        medication_name=validated_data['medication_name'],
        primary_diagnosis=validated_data['primary_diagnosis'],
        additional_diagnoses=validated_data.get('additional_diagnoses', []),
        medication_history=validated_data.get('medication_history', []),
        patient_records=validated_data.get('patient_records', ''),
    )

    # 5. 创建 CarePlan
    careplan = CarePlan.objects.create(
        order=order,
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