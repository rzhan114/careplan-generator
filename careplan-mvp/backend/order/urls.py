from django.urls import path
from . import views

urlpatterns = [
    path("orders/", views.create_order, name="create_order"),
    path("orders/list/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/status/", views.order_status, name="order_status"),
    path("orders/<int:order_id>/careplan/download/", views.careplan_download, name="careplan_download"),
    path("orders/<int:order_id>/retry/", views.order_retry, name="order_retry"),
    path("patients/<int:patient_id>/orders/", views.patient_orders, name="patient_orders"),
]