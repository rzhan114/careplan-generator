# careplan/views.py

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .serializers import OrderCreateSerializer
from .models import CarePlan
from . import services
from .exception_handler import handle_exception


@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    try:
        data = json.loads(request.body)

        # serializer 验证，不通过直接 raise ValidationError
        serializer = OrderCreateSerializer(data)
        serializer.raise_if_invalid()

        validated_data = serializer.get_validated_data()
        confirm = data.get("confirm", False)

        careplan, warnings = services.create_order_with_careplan(validated_data, confirm=confirm)

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
