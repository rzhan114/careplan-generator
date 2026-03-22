from django.db.models import Q
from careplan.models import Patient
def get_patients_list(search=None,page=1, page_size=20):
    queryset = Patient.objects.all().order_by('-id')
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    total_count = queryset.count()
    offset = (page - 1) * page_size
    results = queryset[offset: offset + page_size]
    return total_count, list(results)