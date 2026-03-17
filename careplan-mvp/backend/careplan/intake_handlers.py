from .internal_models import InternalOrder


def internal_order_to_serializer_data(order: InternalOrder) -> dict:
    """
    InternalOrder → serializer 认识的 dict
    services.py 目前还是用 dict，所以需要这个转换
    """
    return {
        "first_name":           order.patient.first_name,
        "last_name":            order.patient.last_name,
        "mrn":                  order.patient.mrn,
        "date_of_birth":        order.patient.date_of_birth,
        "provider_name":        order.provider.name,
        "provider_npi":         order.provider.npi,
        "medication_name":      order.medication.medication_name,
        "primary_diagnosis":    order.medication.primary_diagnosis,
        "additional_diagnoses": order.medication.additional_diagnoses,
        "medication_history":   order.medication.medication_history,
        "patient_records":      order.medication.patient_records,
    }
