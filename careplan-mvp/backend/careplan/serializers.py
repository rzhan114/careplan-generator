# careplan/serializers.py

import re
from .exceptions import ValidationError
from datetime import datetime

class OrderCreateSerializer:
    REQUIRED_FIELDS = [
        'first_name', 'last_name', 'mrn',
        'date_of_birth',   
        'provider_name', 'provider_npi',
        'medication_name', 'primary_diagnosis',
    ]

    def __init__(self, data: dict):
        self.data = data
        self._errors = {}

    def is_valid(self) -> bool:
        # 1. 必填字段检查
        for field in self.REQUIRED_FIELDS:
            if not self.data.get(field):
                self._errors[field] = f"{field} is required"

        if self._errors:
            return False
        #check date of birth
        dob = self.data.get('date_of_birth', '')
        try:
            datetime.strptime(str(dob), '%Y-%m-%d')
        except ValueError:
            self._errors['date_of_birth'] = "date_of_birth must be in YYYY-MM-DD format"

        # 2. NPI：必须是 10 位数字
        npi = self.data.get('provider_npi', '')
        if not re.fullmatch(r'\d{10}', str(npi)):
            self._errors['provider_npi'] = "NPI must be exactly 10 digits"

        # 3. MRN：必须是 6 位数字
        mrn = self.data.get('mrn', '')
        if not re.fullmatch(r'\d{6}', str(mrn)):
            self._errors['mrn'] = "MRN must be exactly 6 digits"

        # 4. ICD-10 格式：字母开头，后面跟数字，可以有小数点
        # 例：G70.01, I10, Z79.899
        icd10_pattern = r'^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$'
        primary = self.data.get('primary_diagnosis', '')
        if not re.fullmatch(icd10_pattern, primary.upper()):
            self._errors['primary_diagnosis'] = f"'{primary}' is not a valid ICD-10 code (e.g. G70.01)"

        return len(self._errors) == 0

    def raise_if_invalid(self):
        """
        is_valid() 返回 False 的时候调用这个，直接 raise ValidationError。
        view 里不用自己判断，调这个就行。
        """
        if not self.is_valid():
            raise ValidationError(
                message="Input validation failed",
                code="VALIDATION_ERROR",
                detail=self._errors,
            )

    def get_validated_data(self) -> dict:
        return {
            'first_name': self.data['first_name'],
            'last_name': self.data['last_name'],
            'date_of_birth': self.data['date_of_birth'],
            'mrn': self.data['mrn'],
            'provider_name': self.data['provider_name'],
            'provider_npi': self.data['provider_npi'],
            'medication_name': self.data['medication_name'],
            'primary_diagnosis': self.data['primary_diagnosis'],
            'additional_diagnoses': self.data.get('additional_diagnoses', []),
            'medication_history': self.data.get('medication_history', []),
            'patient_records': self.data.get('patient_records', ''),
        }