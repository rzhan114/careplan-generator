from django.urls import path, include
from . import views

urlpatterns = [
    path("api/careplan/<int:careplan_id>/status/", views.get_careplan_status, name="get_careplan_status"),
    path("api/", include("patient.urls")),
    path("api/", include("provider.urls")),
    path("api/", include("order.urls")),
    path('', include('django_prometheus.urls')),
]
