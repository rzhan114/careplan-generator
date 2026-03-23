import re
from datetime import datetime
from careplan.exceptions import ValidationError

class PatientSerializer:
    REQUIRED_FIELDS = ['first_name', 'last_name', 'mrn', 'date_of_birth']

    def __init__(self, data: dict):
        self.data = data
        self._errors = {}

    def is_valid(self) -> bool:
        # 1. 必填字段
        for field in self.REQUIRED_FIELDS:
            if not self.data.get(field):
                self._errors[field] = f"{field} is required"
        if self._errors:
            return False

        # 2. MRN 必须是 6 位数字
        mrn = self.data.get('mrn', '')
        if not re.fullmatch(r'\d{6}', str(mrn)):
            self._errors['mrn'] = "MRN must be exactly 6 digits"

        # 3. date_of_birth 必须是 YYYY-MM-DD
        dob = self.data.get('date_of_birth', '')
        try:
            datetime.strptime(str(dob), '%Y-%m-%d')
        except ValueError:
            self._errors['date_of_birth'] = "date_of_birth must be in YYYY-MM-DD format"

        # 4. primary_diagnosis 如果传了，必须是有效 ICD-10 格式
        primary = self.data.get('primary_diagnosis', '')
        if primary:
            icd10_pattern = r'^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$'
            if not re.fullmatch(icd10_pattern, primary.upper()):
                self._errors['primary_diagnosis'] = f"'{primary}' is not a valid ICD-10 code (e.g. G70.01)"

        # 5. weight_kg 如果传了，必须大于 0
        weight = self.data.get('weight_kg')
        if weight is not None:
            try:
                if float(weight) <= 0:
                    self._errors['weight_kg'] = "weight_kg must be greater than 0"
            except (ValueError, TypeError):
                self._errors['weight_kg'] = "weight_kg must be a number"

        return len(self._errors) == 0

    def raise_if_invalid(self):
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
            'mrn': self.data['mrn'],
            'date_of_birth': self.data['date_of_birth'],
            'sex': self.data.get('sex', ''),
            'weight_kg': self.data.get('weight_kg'),
            'allergies': self.data.get('allergies', ''),
            'primary_diagnosis': self.data.get('primary_diagnosis', ''),
            'additional_diagnoses': self.data.get('additional_diagnoses', []),
        }