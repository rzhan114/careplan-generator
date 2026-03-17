# llm_service.py

import os
import time
from abc import ABC, abstractmethod
from anthropic import Anthropic
from openai import OpenAI
from .internal_models import InternalOrder


class BaseLLMService(ABC):

    def build_prompt(self, order: InternalOrder) -> str:
        return f"""
You are a clinical pharmacist. Generate a professional care plan based on the following patient information.

Patient Information:
Patient: {order.patient.first_name} {order.patient.last_name}
MRN: {order.patient.mrn}
Medication: {order.medication.medication_name}
Primary Diagnosis: {order.medication.primary_diagnosis}
Additional Diagnoses: {order.medication.additional_diagnoses}
Medication History: {order.medication.medication_history}
Patient Records: {order.medication.patient_records}
Referring Provider: {order.provider.name} (NPI: {order.provider.npi})

Please generate a comprehensive care plan that includes:
1. Problem List / Drug Therapy Problems (DTPs)
2. Goals (SMART goals)
3. Pharmacist Interventions / Plan
4. Monitoring Plan & Lab Schedule

Format the response clearly with these 4 sections.
        """.strip()

    @abstractmethod
    def call_llm(self, prompt: str) -> str:
        pass

    def generate_care_plan(self, order: InternalOrder) -> str:
        prompt = self.build_prompt(order)
        result = self.call_llm(prompt)
        return result


class OpenAIService(BaseLLMService):

    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content


class ClaudeService(BaseLLMService):

    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def call_llm(self, prompt: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class MockLLMService(BaseLLMService):

    def call_llm(self, prompt: str) -> str:
        time.sleep(2)
        return """
Problem list:
- Need for rapid immunomodulation
- Risk of infusion-related reactions

Goals (SMART):
- Complete full course within prescribed timeline
- No severe adverse reactions

Pharmacist interventions:
- Verify dosing schedule
- Screen for drug interactions

Monitoring plan:
- Baseline labs before treatment
- Follow-up at 2 weeks
        """.strip()


PROVIDERS = {
    "openai": OpenAIService,
    "claude": ClaudeService,
    "mock": MockLLMService,
}


def get_llm_service() -> BaseLLMService:
    provider = os.environ.get("LLM_PROVIDER", "mock").lower()
    service_class = PROVIDERS.get(provider)

    if service_class is None:
        raise ValueError(f"Unknown LLM provider: {provider}")

    return service_class()