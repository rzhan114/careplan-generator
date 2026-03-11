# backend/careplan/tasks.py
import os
import time
from celery import shared_task


def call_llm(patient, order, provider) -> str:
    """和之前 worker.py 里一样的 LLM 调用"""
    USE_MOCK = os.environ.get('USE_MOCK_LLM', 'true').lower() == 'true'

    if USE_MOCK:
        time.sleep(2)
        return f"""
Problem list:
- Need for treatment with {order.medication_name}
- Risk of adverse reactions

Goals (SMART):
- Complete full course within prescribed timeline
- No severe adverse reactions

Pharmacist interventions:
- Verify dosing schedule
- Screen for drug interactions
- Counsel patient on side effects

Monitoring plan:
- Baseline labs before treatment
- Follow-up at 2 weeks
        """.strip()
    else:
        from anthropic import Anthropic
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"""
Generate a care plan for:
Patient: {patient.first_name} {patient.last_name}
Medication: {order.medication_name}
Diagnosis: {order.primary_diagnosis}
Records: {order.patient_records}
Referring Provider: {provider.name} (NPI: {provider.npi})

Include: Problem list, Goals, Pharmacist interventions, Monitoring plan.
            """}]
        )
        return response.content[0].text


@shared_task(
    bind=True,
    max_retries=3,                    # 最多重试 3 次
    default_retry_delay=60,           # 默认重试间隔 60 秒
)
def generate_careplan_task(self, careplan_id: int):
    """
    Celery 异步任务：生成 Care Plan
    
    bind=True 让我们能用 self.retry()
    max_retries=3 失败最多重试 3 次
    """
    from careplan.models import CarePlan

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

        content = call_llm(patient, order, provider)

        careplan.content = content
        careplan.status = 'completed'
        careplan.save()

        print(f"[Celery] 完成 careplan_id={careplan_id}")

    except CarePlan.DoesNotExist:
        print(f"[Celery] 找不到 careplan_id={careplan_id}，跳过")

    except Exception as e:
        print(f"[Celery] 处理失败: {e}，准备重试...")

        # 指数退避：第1次等60秒，第2次等120秒，第3次等240秒
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)

        try:
            # 抛出重试，Celery 会在 countdown 秒后重新执行这个任务
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            # 3 次都失败了，标记 failed
            print(f"[Celery] 重试次数耗尽，careplan_id={careplan_id} 标记为 failed")
            careplan.status = 'failed'
            careplan.save()