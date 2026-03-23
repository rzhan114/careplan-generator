# patient/views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from . import services
from .serializers import PatientSerializer
from careplan.exception_handler import handle_exception

@csrf_exempt
def patient_list(request):
    if request.method == "GET":
        try:
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

            total_count, results = services.get_patients_list(
                search=search, page=page, page_size=page_size,
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

    elif request.method == "POST":
        try:
            data = json.loads(request.body)

            serializer = PatientSerializer(data)
            serializer.raise_if_invalid()
            validated = serializer.get_validated_data()

            patient = services.create_patient(**validated)

            return JsonResponse({
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "mrn": patient.mrn,
                "date_of_birth": str(patient.date_of_birth),
                "sex": patient.sex,
                "weight_kg": patient.weight_kg,
                "allergies": patient.allergies,
                "primary_diagnosis": patient.primary_diagnosis,
                "additional_diagnoses": patient.additional_diagnoses,
                "created_at": patient.created_at.isoformat(),
            }, status=201)

        except Exception as exc:
            return handle_exception(exc)

    return JsonResponse({"error": "Method not allowed"}, status=405)

# patient/views.py 加 patient_detail 函数
@csrf_exempt
def patient_detail(request, id):
    if request.method == "GET":
        try:
            patient = services.get_patient_by_id(id)
            if not patient:
                return JsonResponse({"error": "Patient not found"}, status=404)

            orders = []
            for order in patient.orders.all():
                try:
                    careplan = order.careplan
                    status = careplan.status
                except Exception:
                    status = None
                orders.append({
                    "id": order.id,
                    "medication_name": order.medication_name,
                    "status": status,
                    "created_at": order.created_at.isoformat(),
                })

            return JsonResponse({
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "mrn": patient.mrn,
                "date_of_birth": str(patient.date_of_birth),
                "sex": patient.sex,
                "weight_kg": patient.weight_kg,
                "allergies": patient.allergies,
                "primary_diagnosis": patient.primary_diagnosis,
                "additional_diagnoses": patient.additional_diagnoses,
                "orders": orders,
                "created_at": patient.created_at.isoformat(),
            })
        except Exception as exc:
            return handle_exception(exc)

    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            patient = services.update_patient(id, data)
            if not patient:
                return JsonResponse({"error": "Patient not found"}, status=404)

            return JsonResponse({
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "mrn": patient.mrn,
                "date_of_birth": str(patient.date_of_birth),
                "sex": patient.sex,
                "weight_kg": patient.weight_kg,
                "allergies": patient.allergies,
                "primary_diagnosis": patient.primary_diagnosis,
                "additional_diagnoses": patient.additional_diagnoses,
                "updated_at": patient.created_at.isoformat(),
            })
        except Exception as exc:
            return handle_exception(exc)

    elif request.method == "DELETE":
        try:
            result, _ = services.delete_patient(id)
            if result is None:
                return JsonResponse({"error": "Patient not found"}, status=404)
            return JsonResponse({}, status=204)
        except Exception as exc:
            return handle_exception(exc)