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