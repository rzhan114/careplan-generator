# careplan/views.py
# 负责：接收 HTTP 请求，返回 HTTP 响应
# 不做任何业务逻辑，全部委托给 services

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .serializers import OrderCreateSerializer
from .models import CarePlan
from . import services


@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    # 1. 解析请求数据
    data = json.loads(request.body)

    # 2. 用 serializer 提取字段
    serializer = OrderCreateSerializer(data)
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)

    validated_data = serializer.get_validated_data()

    # 3. 调用 service 完成业务逻辑
    careplan = services.create_order_with_careplan(validated_data)

    # 4. 返回响应
    return JsonResponse({
        "id": careplan.id,
        "status": careplan.status,
        "message": "Received, Processing",
    })


@require_http_methods(["GET"])
def get_order(request, order_id):
    try:
        careplan = services.get_careplan_by_id(order_id)
        return JsonResponse({
            "id": careplan.id,
            "status": careplan.status,
            "care_plan": careplan.content,
        })
    except CarePlan.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)


@require_http_methods(["GET"])
def get_careplan_status(request, careplan_id):
    try:
        careplan = services.get_careplan_by_id(careplan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    response = {
        'id': careplan.id,
        'status': careplan.status,
        'content': None,
    }
    if careplan.status == 'completed':
        response['content'] = careplan.content

    return JsonResponse(response)
