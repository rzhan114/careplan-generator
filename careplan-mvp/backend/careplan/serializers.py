# careplan/serializers.py
# 负责：定义前端发来的数据长什么样，以及基本格式

class OrderCreateSerializer:
    """
    验证前端 POST /api/orders/ 发来的数据
    现在只做字段提取,Day 8 会加上真正的校验逻辑
    """
    REQUIRED_FIELDS = [
        'first_name', 'last_name', 'mrn',
        'provider_name', 'provider_npi',
        'medication_name', 'primary_diagnosis',
    ]

    def __init__(self, data: dict):
        self.data = data
        self.errors = []

    def is_valid(self) -> bool:
        # 现在只检查字段存不存在，Day 8 会加格式校验
        for field in self.REQUIRED_FIELDS:
            if not self.data.get(field):
                self.errors.append(f"{field} is required")
        return len(self.errors) == 0

    def get_validated_data(self) -> dict:
        return {
            'first_name': self.data['first_name'],
            'last_name': self.data['last_name'],
            'mrn': self.data['mrn'],
            'provider_name': self.data['provider_name'],
            'provider_npi': self.data['provider_npi'],
            'medication_name': self.data['medication_name'],
            'primary_diagnosis': self.data['primary_diagnosis'],
            'additional_diagnoses': self.data.get('additional_diagnoses', []),
            'medication_history': self.data.get('medication_history', []),
            'patient_records': self.data.get('patient_records', ''),
        }