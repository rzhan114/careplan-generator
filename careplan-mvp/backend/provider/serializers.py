import re
from careplan.exceptions import ValidationError

class ProviderSerializer:
    def __init__(self, data: dict):
        self.data = data
        self._errors = {}

    def is_valid(self) -> bool:
        if not self.data.get('name', '').strip():
            self._errors['name'] = "name is required"

        npi = self.data.get('npi', '')
        if not re.fullmatch(r'\d{10}', str(npi)):
            self._errors['npi'] = "NPI must be exactly 10 digits"

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
            'name': self.data['name'].strip(),
            'npi': self.data['npi'],
        }