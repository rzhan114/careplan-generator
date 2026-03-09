import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')

import sys
sys.path.insert(0, '/app')

django.setup()

from careplan.models import Provider, Patient, Order, CarePlan

# ============================================================
# 先删掉所有旧数据（方便重复运行）
# 注意顺序：先删有外键依赖的表
# ============================================================
CarePlan.objects.all().delete()
Order.objects.all().delete()
Patient.objects.all().delete()
Provider.objects.all().delete()

print("旧数据清空完毕")

# ============================================================
# 第一步：插入 Provider
# ============================================================
provider1 = Provider.objects.create(name="Dr. Sarah Johnson", npi="1234567890")
provider2 = Provider.objects.create(name="Dr. Michael Chen", npi="9876543210")

print("Provider 插入完毕")

# ============================================================
# 第二步：插入 Patient
# ============================================================
patient1 = Patient.objects.create(
    first_name="Alice",
    last_name="Brown",
    mrn="001234",
    date_of_birth="1979-06-08",
)
patient2 = Patient.objects.create(
    first_name="Bob",
    last_name="Smith",
    mrn="005678",
    date_of_birth="1985-03-22",
)
patient3 = Patient.objects.create(
    first_name="Carol",
    last_name="Davis",
    mrn="009999",
    date_of_birth="1990-11-15",
)

print("Patient 插入完毕")

# ============================================================
# 第三步：插入 Order
# ============================================================
order1 = Order.objects.create(
    patient=patient1,
    provider=provider1,
    medication_name="IVIG",
    primary_diagnosis="G70.01",
    additional_diagnoses=["I10", "K21.0"],
    medication_history=["Pyridostigmine 60mg", "Prednisone 10mg"],
    patient_records="Progressive proximal muscle weakness over 2 weeks.",
)
order2 = Order.objects.create(
    patient=patient2,
    provider=provider1,
    medication_name="Rituximab",
    primary_diagnosis="M05.79",
    additional_diagnoses=["M06.09"],
    medication_history=["Methotrexate 15mg", "Folic acid 1mg"],
    patient_records="Rheumatoid arthritis with inadequate response to MTX.",
)
order3 = Order.objects.create(
    patient=patient3,
    provider=provider2,
    medication_name="Adalimumab",
    primary_diagnosis="K50.90",
    additional_diagnoses=[],
    medication_history=["Mesalamine 2.4g"],
    patient_records="Crohn's disease with moderate activity.",
)

print("Order 插入完毕")

# ============================================================
# 第四步：插入 CarePlan
# ============================================================
CarePlan.objects.create(
    order=order1,
    status=CarePlan.Status.COMPLETED,
    content="Problem List:\n- Need for rapid immunomodulation\n\nGoals:\n- Improve muscle strength within 2 weeks\n\nInterventions:\n- IVIG 2g/kg over 5 days\n\nMonitoring:\n- CBC, BMP before infusion",
)
CarePlan.objects.create(
    order=order2,
    status=CarePlan.Status.COMPLETED,
    content="Problem List:\n- Active RA despite MTX\n\nGoals:\n- Reduce joint inflammation\n\nInterventions:\n- Rituximab 1000mg IV x2 doses\n\nMonitoring:\n- CBC monthly",
)
CarePlan.objects.create(
    order=order3,
    status=CarePlan.Status.PENDING,
    content="",
)

print("CarePlan 插入完毕")
print("✅ 所有 mock data 插入成功！")