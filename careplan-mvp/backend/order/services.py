from django.db.models import Q
from careplan.models import CarePlan, Patient
from careplan.exceptions import BlockError

def get_orders_list(status=None, patient_name=None, page=1, page_size=20):
    queryset = CarePlan.objects.select_related('order__patient').order_by('-id')
    if status:
        queryset = queryset.filter(status=status)
    if patient_name:
        queryset = queryset.filter(
            Q(order__patient__first_name__icontains=patient_name) |
            Q(order__patient__last_name__icontains=patient_name)
        )
    total_count = queryset.count()
    offset = (page - 1) * page_size
    results = queryset[offset: offset + page_size]
    return total_count, list(results)

def get_orders_by_patient(patient_id: int):
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return None, None
    careplans = CarePlan.objects.filter(
        order__patient=patient
    ).select_related('order').order_by('-id')
    return patient, list(careplans)

def get_careplan_by_order_id(order_id: int):
    return CarePlan.objects.select_related('order').get(order__id=order_id)

def retry_careplan(order_id: int):
    careplan = CarePlan.objects.get(order__id=order_id)
    if careplan.status != 'failed':
        raise BlockError(
            code="ORDER_NOT_FAILED",
            message="Order is not in failed status.",
            detail={"current_status": careplan.status},
        )
    careplan.status = CarePlan.Status.PENDING
    careplan.save()
    try:
        from careplan.tasks import generate_careplan_task
        generate_careplan_task.delay(careplan.id)
    except Exception as e:
        print(f"Redis error: {e}")
    return careplan