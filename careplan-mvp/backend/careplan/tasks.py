# careplan/tasks.py
# 负责：Celery 任务的调度和重试，业务逻辑调用 services.py

from celery import shared_task


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_careplan_task(self, careplan_id: int):
    """
    Celery 异步任务入口
    只负责：调度、重试逻辑
    真正的业务逻辑在 services.call_llm()
    """
    from careplan.models import CarePlan
    from careplan.services import call_llm  # 从 services 调用

    print(f"[Celery] 开始处理 careplan_id={careplan_id}")

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

        # 调用 services 里的 LLM 逻辑
        content = call_llm(patient, order, provider)

        careplan.content = content
        careplan.status = 'completed'
        careplan.save()

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
            careplan.status = 'failed'
            careplan.save()