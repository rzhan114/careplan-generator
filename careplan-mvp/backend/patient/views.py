# patient/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from . import services
from careplan.exception_handler import handle_exception

@require_http_methods(["GET"])
def patient_list(request):
    try:
        # Ticket 2 只有 search，没有 status
        search = request.GET.get('search', None)

        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
        except (ValueError, TypeError):
            return JsonResponse({"error": "page and page_size must be integers"}, status=400)

        if page_size > 100:
            page_size = 100
        if page < 1:
            page = 1

        # 调用 patient 自己的 service
        total_count, results = services.get_patients_list(
            search=search,
            page=page,
            page_size=page_size,
        )

        return JsonResponse({
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "id": p.id,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "mrn": p.mrn,
                    "created_at": p.created_at.isoformat(),
                }
                for p in results
            ]
        })
    except Exception as exc:
        return handle_exception(exc)
