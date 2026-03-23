from django.db import models

class Provider(models.Model):
    name = models.CharField(max_length=200)
    npi = models.CharField(max_length=10, unique=True)  # NPI 全国唯一
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(max_length=6, unique=True)
    date_of_birth = models.DateField()
    sex = models.CharField(max_length=10, blank=True, default='')
    weight_kg = models.FloatField(null=True, blank=True)
    allergies = models.TextField(blank=True, default='')
    primary_diagnosis = models.CharField(max_length=20, blank=True, default='')
    additional_diagnoses = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (MRN: {self.mrn})"


class Order(models.Model):
    patient = models.ForeignKey(
        Patient, 
        on_delete=models.PROTECT,  # 不能随便删有订单的病人
        related_name='orders'
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    medication_name = models.CharField(max_length=200)
    primary_diagnosis = models.CharField(max_length=20)  # ICD-10 code
    additional_diagnoses = models.JSONField(default=list)  # ICD-10 codes list
    medication_history = models.JSONField(default=list)    # strings list
    patient_records = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.patient} - {self.medication_name}"


class CarePlan(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    order = models.OneToOneField(  # 一个订单只有一个 care plan
        Order,
        on_delete=models.CASCADE,
        related_name='careplan'
    )
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 每次保存自动更新

    def __str__(self):
        return f"CarePlan for Order #{self.order.id} - {self.status}"