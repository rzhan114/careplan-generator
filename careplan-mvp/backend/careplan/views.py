import os
import uuid
import anthropic
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

# ============================================================
# 内存存储 - 代替数据库（Day 3 会换成真正的 PostgreSQL）
# 就是一个 Python 字典，key 是订单 ID，value 是订单数据
# 注意：服务器重启后数据会消失，这是 MVP 的故意局限
# ============================================================
ORDERS_STORE = {}


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
        model="claude-opus-4-5",
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

    # 2. 生成一个唯一的订单 ID
    order_id = str(uuid.uuid4())[:8]

    # 3. 把订单先存到内存（状态：processing）
    ORDERS_STORE[order_id] = {
        "id": order_id,
        "status": "processing",
        "patient_data": data,
        "care_plan": None,
    }

    # 4. 同步调用 LLM（用户在这里等待，可能 10-30 秒）
    # Day 4 会把这步改成异步，用户不用等了
    try:
        care_plan_content = call_llm(data)

        # 5. 更新内存里的订单状态
        ORDERS_STORE[order_id]["status"] = "completed"
        ORDERS_STORE[order_id]["care_plan"] = care_plan_content

        return JsonResponse({
            "id": order_id,
            "status": "completed",
            "care_plan": care_plan_content,
        })

    except Exception as e:
        ORDERS_STORE[order_id]["status"] = "failed"
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================
# GET /api/orders/<order_id>/
# 根据 ID 查询订单结果（现在 MVP 阶段基本用不到，
# 因为 POST 已经直接返回结果了，但 Day 4 之后会很重要）
# ============================================================
@require_http_methods(["GET"])
def get_order(request, order_id):
    order = ORDERS_STORE.get(order_id)

    if not order:
        return JsonResponse({"error": "Order not found"}, status=404)

    return JsonResponse(order)
