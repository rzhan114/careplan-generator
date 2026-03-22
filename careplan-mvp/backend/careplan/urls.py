from django.urls import path,include
from . import views

urlpatterns = [
    # POST /api/orders/     → 提交患者信息，同步调用 LLM，返回 care plan
    path("api/orders/", views.create_order, name="create_order"),
    path("api/orders/list/", views.get_order, name="get_order"),
    path("api/careplan/<int:careplan_id>/status/", views.get_careplan_status, name="get_careplan_status"),
    path('', include('django_prometheus.urls')),  # 暴露 /metrics 接口
    # patients's urls
    path("api/", include("patient.urls")),
]
