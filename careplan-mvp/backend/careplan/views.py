# careplan/views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .serializers import OrderCreateSerializer
from .models import CarePlan
from . import services
from .exception_handler import handle_exception
from .adapters import get_adapter

@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    try:
        # 1. 选 Adapter
        adapter = get_adapter(request)

        # 2. run() 内部：parse → validate → transform
        internal_order = adapter.run()

        # 4. confirm 只有 JSON 请求才有，XML 请求没有
        content_type = request.content_type or ""
        confirm = adapter.get_confirm()

        careplan, warnings = services.create_order_with_careplan(
            internal_order, confirm=confirm
        )
        return JsonResponse({
            "id": careplan.id,
            "status": careplan.status,
            "message": "Received, Processing",
            "warnings": warnings,
        })
    except Exception as exc:
        print(f"Exception type: {type(exc)}, value: {exc}")
        return handle_exception(exc)


@require_http_methods(["GET"])
def get_order(request):
    try:
        # 从 query params 读取参数，提供默认值
        status = request.GET.get('status', None)
        patient_name = request.GET.get('patient_name', None)
        
        # 分页参数，注意类型转换 + 防止非法输入
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
        except (ValueError, TypeError):
            return JsonResponse({"error": "page and page_size must be integers"}, status=400)

        # 防止 page_size 太大（防止一次查几千条）
        if page_size > 100:
            page_size = 100
        if page < 1:
            page = 1

        total_count, results = services.get_orders_list(
            status=status,
            patient_name=patient_name,
            page=page,
            page_size=page_size,
        )

        return JsonResponse({
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "id": cp.id,
                    "status": cp.status,
                    "patient_name": f"{cp.order.patient.first_name} {cp.order.patient.last_name}",
                    "medication_name": cp.order.medication_name,
                    "created_at": cp.order.created_at.isoformat(),
                }
                for cp in results
            ]
        })
    except Exception as exc:
        return handle_exception(exc)


@require_http_methods(["GET"])
def get_careplan_status(request, careplan_id):
    try:
        careplan = services.get_careplan_by_id(careplan_id)
        response = {
            'id': careplan.id,
            'status': careplan.status,
            'content': None,
        }
        if careplan.status == 'completed':
            response['content'] = careplan.content
        return JsonResponse(response)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    except Exception as exc:
        return handle_exception(exc)
