# careplan/lambda_handlers.py

import json
import os
import django
import boto3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')
django.setup()

from careplan import services
from careplan.models import CarePlan
from careplan.adapters import BaseIntakeAdapter

sqs = boto3.client('sqs')


class LambdaWebFormAdapter(BaseIntakeAdapter):
    def __init__(self, data):
        super().__init__(data)

    def get_source(self):
        return "webform"

    def parse(self):
        return self.raw_data

    def get_confirm(self):
        return self.raw_data.get('confirm', False)


def get_order_handler(event, context):
    try:
        order_id = event['pathParameters']['id']
    except (KeyError, TypeError):
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Missing order id'})
        }

    try:
        careplan = services.get_careplan_by_id(order_id)
    except CarePlan.DoesNotExist:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Order not found'})
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'id': careplan.id,
            'status': careplan.status,
            'care_plan': careplan.content,
        })
    }


def create_order_handler(event, context):
    try:
        body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON'})
        }

    try:
        adapter = LambdaWebFormAdapter(body)
        internal_order = adapter.run()
        confirm = adapter.get_confirm()
    except Exception as exc:
        from careplan.exception_handler import handle_exception
        response = handle_exception(exc)
        return {
            'statusCode': response.status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': response.content.decode('utf-8')
        }

    try:
        careplan, warnings = services.create_order_with_careplan(
            internal_order, confirm=confirm
        )
    except Exception as exc:
        from careplan.exception_handler import handle_exception
        response = handle_exception(exc)
        return {
            'statusCode': response.status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': response.content.decode('utf-8')
        }

    try:
        sqs.send_message(
            QueueUrl=os.environ['SQS_URL'],
            MessageBody=json.dumps({'careplan_id': careplan.id})
        )
    except Exception as e:
        print(f"SQS error: {e}")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'id': careplan.id,
            'status': careplan.status,
            'message': 'Received, Processing',
            'warnings': warnings,
        })
    }


def generate_careplan_handler(event, context):
    from careplan.llm_service import get_llm_service
    from careplan.internal_models import InternalOrder, PatientInfo, ProviderInfo, MedicationInfo

    for record in event['Records']:
        body = json.loads(record['body'])
        careplan_id = body['careplan_id']

        print(f"开始处理 careplan_id={careplan_id}")

        try:
            careplan = CarePlan.objects.select_related(
                'order__patient',
                'order__provider'
            ).get(id=careplan_id)
        except CarePlan.DoesNotExist:
            print(f"找不到 careplan_id={careplan_id}，跳过")
            continue

        careplan.status = 'processing'
        careplan.save()

        try:
            order = careplan.order
            patient = order.patient
            provider = order.provider

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

            print(f"完成 careplan_id={careplan_id}")

        except Exception as e:
            print(f"处理失败 careplan_id={careplan_id}: {e}")
            careplan.status = 'failed'
            careplan.save()
            raise