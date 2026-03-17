# careplan/tasks.py
# 负责：Celery 任务的调度和重试，业务逻辑调用 llm_service.py
import time
from celery import shared_task
from careplan.metrics import careplan_generated_total, careplan_duration_seconds

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_careplan_task(self, careplan_id: int):
    from careplan.models import CarePlan
    from careplan.llm_service import get_llm_service
    from careplan.internal_models import InternalOrder, PatientInfo, ProviderInfo, MedicationInfo

    print(f"[Celery] 开始处理 careplan_id={careplan_id}")

    start_time = time.time()  # 开始计时
    careplan = None  # 先初始化为 None

    try:
        careplan = CarePlan.objects.select_related(
            'order__patient',
            'order__provider'
        ).get(id=careplan_id)

        order = careplan.order
        patient = order.patient
        provider = order.provider

        careplan.status = 'processing'
        careplan.save()

        internal_order = InternalOrder(
            patient=PatientInfo(
                first_name=patient.first_name,
                last_name=patient.last_name,
                mrn=patient.mrn,
                date_of_birth=str(patient.date_of_birth),
            ),
            provider=ProviderInfo(
                name=provider.name,
                npi=provider.npi,
            ),
            medication=MedicationInfo(
                medication_name=order.medication_name,
                primary_diagnosis=order.primary_diagnosis,
                additional_diagnoses=order.additional_diagnoses or [],
                medication_history=order.medication_history or [],
                patient_records=order.patient_records or "",
            ),
            source="webform",
        )

        llm = get_llm_service()
        content = llm.generate_care_plan(internal_order)

        careplan.content = content
        careplan.status = 'completed'
        careplan.save()

        # ✅ 成功：记录指标
        careplan_generated_total.labels(status='success').inc()
        careplan_duration_seconds.observe(time.time() - start_time)

        print(f"[Celery] 完成 careplan_id={careplan_id}")

    except CarePlan.DoesNotExist:
        print(f"[Celery] 找不到 careplan_id={careplan_id}，跳过")

    except Exception as e:
        print(f"[Celery] 处理失败: {e}，准备重试...")

        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)

        try:
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            print(f"[Celery] 重试次数耗尽，careplan_id={careplan_id} 标记为 failed")
            if careplan is not None:
                careplan.status = 'failed'
                careplan.save()

            # ❌ 彻底失败：记录指标
            careplan_generated_total.labels(status='failed').inc()
            careplan_duration_seconds.observe(time.time() - start_time)