from django.urls import path
from . import views

urlpatterns = [
    # POST /api/orders/     → 提交患者信息，同步调用 LLM，返回 care plan
    # GET  /api/orders/<id> → 查询某个订单的结果
    path("api/orders/", views.create_order, name="create_order"),
    path("api/orders/<str:order_id>/", views.get_order, name="get_order"),
    path("api/careplan/<int:careplan_id>/status/", views.get_careplan_status, name="get_careplan_status"),
]
