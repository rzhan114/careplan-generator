# backend/worker.py
import redis
import time
import os

redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=6379,
    decode_responses=True
)

def call_llm(patient, order, provider) -> str:  # ← 加 provider
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


def process_one_task():
    result = redis_client.blpop('careplan_queue', timeout=0)
    if result is None:
        return
    
    import json
    _, raw_value = result
    data = json.loads(raw_value)
    careplan_id = data['careplan_id']
    print(f"[Worker] 收到任务: careplan_id={careplan_id}")
    
    # 必须在 django.setup() 之后才能 import models
    from careplan.models import CarePlan
    
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
        print(f"[Worker] 开始处理 careplan_id={careplan_id}")
        
        content = call_llm(patient, order, provider)
        
        careplan.content = content
        careplan.status = 'completed'
        careplan.save()
        print(f"[Worker] 完成 careplan_id={careplan_id}")
        
    except CarePlan.DoesNotExist:
        print(f"[Worker] 找不到 careplan_id={careplan_id}，跳过")
        
    except Exception as e:
        print(f"[Worker] 处理失败: {e}")
        try:
            careplan.status = 'failed'
            careplan.save()
        except:
            pass


def run_forever():
    print("[Worker] 启动，等待任务...")
    while True:
        try:
            process_one_task()
        except Exception as e:
            print(f"[Worker] 意外错误: {e}")
            time.sleep(1)


if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')
    django.setup()
    run_forever()