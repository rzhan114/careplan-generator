# careplan/services.py
# 负责：所有业务逻辑（数据库操作、调用LLM、放队列）

import os
import time
from .models import Patient, Provider, Order, CarePlan


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


# ============================================================
# 创建订单的完整业务流程
# 从 views.py 的 create_order 搬过来
# ============================================================
def create_order_with_careplan(validated_data: dict) -> CarePlan:
    """
    接收已经验证过的数据，完成：
    1. 找或创建 Provider
    2. 找或创建 Patient
    3. 创建 Order
    4. 创建 CarePlan(status=pending)
    5. 把任务放进 Celery 队列
    返回创建好的 CarePlan 对象
    """
    # 1. 找或创建 Provider
    provider, _ = Provider.objects.get_or_create(
        npi=validated_data['provider_npi'],
        defaults={'name': validated_data['provider_name']}
    )

    # 2. 找或创建 Patient
    patient, _ = Patient.objects.get_or_create(
        mrn=validated_data['mrn'],
        defaults={
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
            'date_of_birth': '2000-01-01',
        }
    )

    # 3. 创建 Order
    order = Order.objects.create(
        patient=patient,
        provider=provider,
        medication_name=validated_data['medication_name'],
        primary_diagnosis=validated_data['primary_diagnosis'],
        additional_diagnoses=validated_data.get('additional_diagnoses', []),
        medication_history=validated_data.get('medication_history', []),
        patient_records=validated_data.get('patient_records', ''),
    )

    # 4. 创建 CarePlan（初始状态 pending）
    careplan = CarePlan.objects.create(
        order=order,
        status=CarePlan.Status.PENDING
    )

    # 5. 放进 Celery 队列
    try:
        from careplan.tasks import generate_careplan_task
        generate_careplan_task.delay(careplan.id)
    except Exception as e:
        # Redis 放入失败，数据库里已有 pending 记录
        # Day 8 会加上更好的错误处理
        print(f"Redis error: {e}")

    return careplan


# ============================================================
# 查询 CarePlan
# 从 views.py 的 get_order / get_careplan_status 搬过来
# ============================================================
def get_careplan_by_id(careplan_id: int) -> CarePlan:
    """
    根据 ID 查 CarePlan,找不到抛 CarePlan.DoesNotExist
    views.py 负责捕捉这个异常并返回 404
    """
    return CarePlan.objects.get(id=careplan_id)