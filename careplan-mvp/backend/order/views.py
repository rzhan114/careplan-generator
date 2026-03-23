import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from . import services
from careplan.exception_handler import handle_exception
from careplan.models import CarePlan
from careplan import services as careplan_services
from careplan.adapters import get_adapter

@csrf_exempt
def create_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        adapter = get_adapter(request)
        internal_order = adapter.run()
        confirm = adapter.get_confirm()
        careplan, warnings = careplan_services.create_order_with_careplan(
            internal_order, confirm=confirm
        )
        return JsonResponse({
            "id": careplan.id,
            "status": careplan.status,
            "message": "Received, Processing",
            "warnings": warnings,
        })
    except Exception as exc:
        return handle_exception(exc)

@require_http_methods(["GET"])
def order_list(request):
    try:
        status = request.GET.get('status', None)
        patient_name = request.GET.get('patient_name', None)
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
        except (ValueError, TypeError):
            return JsonResponse({"error": "page and page_size must be integers"}, status=400)
        if page_size > 100:
            page_size = 100
        if page < 1:
            page = 1
        total_count, results = services.get_orders_list(
            status=status, patient_name=patient_name, page=page, page_size=page_size,
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
def order_status(request, order_id):
    try:
        careplan = services.get_careplan_by_order_id(order_id)
        response = {"order_id": order_id, "status": careplan.status}
        if careplan.status == 'completed':
            response["careplan_preview"] = careplan.content[:100] if careplan.content else None
        elif careplan.status == 'failed':
            response["error_message"] = "LLM service unavailable"
        return JsonResponse(response)
    except CarePlan.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)
    except Exception as exc:
        return handle_exception(exc)

@require_http_methods(["GET"])
def careplan_download(request, order_id):
    try:
        careplan = services.get_careplan_by_order_id(order_id)
        if careplan.status != 'completed':
            return JsonResponse({"error": "CarePlan not yet generated"}, status=404)
        response = HttpResponse(careplan.content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="careplan_order_{order_id}.txt"'
        return response
    except CarePlan.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)
    except Exception as exc:
        return handle_exception(exc)

@csrf_exempt
@require_http_methods(["POST"])
def order_retry(request, order_id):
    try:
        careplan = services.retry_careplan(order_id)
        return JsonResponse({
            "order_id": order_id,
            "status": careplan.status,
            "message": "CarePlan generation restarted",
        }, status=202)
    except CarePlan.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)
    except Exception as exc:
        return handle_exception(exc)

@require_http_methods(["GET"])
def patient_orders(request, patient_id):
    try:
        patient, careplans = services.get_orders_by_patient(patient_id)
        if patient is None:
            return JsonResponse({"error": "Patient not found"}, status=404)
        return JsonResponse({
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "orders": [
                {
                    "id": cp.order.id,
                    "medication_name": cp.order.medication_name,
                    "status": cp.status,
                    "created_at": cp.order.created_at.isoformat(),
                }
                for cp in careplans
            ]
        })
    except Exception as exc:
        return handle_exception(exc)