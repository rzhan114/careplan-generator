import os
from .models import Patient, Provider, Order, CarePlan
import anthropic
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from careplan.tasks import generate_careplan_task
from django.conf import settings
import redis
import json



# ============================================================
# 调用 Claude LLM 生成 Care Plan
# 现在是同步调用：用户等着，LLM 生成完才返回
# Day 4 会体验到这有多慢，然后引入异步
# ============================================================
def call_llm(patient_data: dict) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # 把患者信息拼成 prompt
    prompt = f"""You are a clinical pharmacist. Generate a professional care plan based on the following patient information.

Patient Information:
- Name: {patient_data.get('first_name')} {patient_data.get('last_name')}
- MRN: {patient_data.get('mrn')}
- Primary Diagnosis: {patient_data.get('primary_diagnosis')}
- Medication: {patient_data.get('medication_name')}
- Additional Diagnoses: {patient_data.get('additional_diagnoses', 'None')}
- Medication History: {patient_data.get('medication_history', 'None')}
- Patient Records: {patient_data.get('patient_records', 'None')}
- Referring Provider: {patient_data.get('provider_name')} (NPI: {patient_data.get('provider_npi')})

Please generate a comprehensive care plan that includes:

1. Problem List / Drug Therapy Problems (DTPs)
2. Goals (SMART goals)
3. Pharmacist Interventions / Plan
4. Monitoring Plan & Lab Schedule

Format the response clearly with these 4 sections."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


# ============================================================
# POST /api/orders/
# 前端提交患者信息 → 同步调用 LLM → 返回 care plan
# 这里是同步的：用户需要等 10-30 秒（Day 4 会解决这个问题）
# ============================================================
@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    # 1. 解析前端发来的 JSON 数据
    data = json.loads(request.body)

    #Use database to store data
    # 2. 找或创建 Provider（NPI 是唯一标识）
    provider, _ = Provider.objects.get_or_create(
        npi=data['provider_npi'],
        defaults={'name': data['provider_name']}
    )
    # 3. 找或创建 Patient（MRN 是唯一标识）
    patient, _ = Patient.objects.get_or_create(
        mrn=data['mrn'],
        defaults={
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'date_of_birth': '2000-01-01',
        }
    )
    # 4. 创建 Order
    order = Order.objects.create(
        patient=patient,
        provider=provider,
        medication_name=data['medication_name'],
        primary_diagnosis=data['primary_diagnosis'],
        additional_diagnoses=data.get('additional_diagnoses', []),
        medication_history=data.get('medication_history', []),
        patient_records=data.get('patient_records', ''),
    )
    # 5. 创建 CarePlan（初始状态 pending）
    careplan = CarePlan.objects.create(
        order=order,
        status=CarePlan.Status.PENDING
    )
    try:
        generate_careplan_task.delay(careplan.id)
    except Exception as e:
        # Redis放入失败：CarePlan已经存在数据库里了（status=pending）
        # 暂时先记录错误，不影响返回
        # ⚠️ 这里有个问题：数据库有记录但队列里没有任务
        # Day 5 之后我们会讨论怎么处理这种情况
        print(f"Redis error: {e}")

    # ===== 改动3：立刻返回，不等LLM =====
    return JsonResponse({
        "id": careplan.id,
        "status": careplan.status,
        "message": "Recieved,Processing",
        # 注意：这里没有 care_plan 字段了
        # 因为还没生成，用 GET /api/orders/<id>/ 来查结果
    })

# ============================================================
# GET /api/orders/<order_id>/
# 根据 ID 查询订单结果（现在 MVP 阶段基本用不到，
# 因为 POST 已经直接返回结果了，但 Day 4 之后会很重要）
# ============================================================
@require_http_methods(["GET"])
def get_order(request, order_id):
    try:
        careplan = CarePlan.objects.get(id=order_id)
        return JsonResponse({
            "id": careplan.id,
            "status": careplan.status,
            "care_plan": careplan.content,
        })
    except CarePlan.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)
@require_http_methods(["GET"])
def get_careplan_status(request, careplan_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        careplan = CarePlan.objects.get(id=careplan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    response = {
        'id': careplan.id,
        'status': careplan.status,  # pending / processing / completed / failed
        'content': None,
    }
    if careplan.status == 'completed':
        response['content'] = careplan.content
    return JsonResponse(response)
