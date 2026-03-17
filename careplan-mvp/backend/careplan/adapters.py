# adapters.py

import json
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime

from .exceptions import ValidationError
from .internal_models import InternalOrder, MedicationInfo, PatientInfo, ProviderInfo
from .serializers import OrderCreateSerializer


class BaseIntakeAdapter(ABC):
    """
    所有数据源 Adapter 的基类

    使用方式：
        adapter = ClinicBAdapter(request)
        order = adapter.run()
    """

    def __init__(self, raw_data):
        # 保存原始数据，方便排查问题
        self.raw_data = raw_data
        self.internal_order: InternalOrder | None = None

    @abstractmethod
    def parse(self) -> dict:
        """
        解析原始数据，输出字段名统一的 dict
        这是每个 Adapter 唯一需要实现的方法

        输出的 dict key 必须和 serializer 的字段名一致：
        first_name, last_name, mrn, date_of_birth,
        provider_name, provider_npi, medication_name,
        primary_diagnosis, additional_diagnoses,
        medication_history, patient_records
        """
        pass

    def get_source(self) -> str:
        """子类重写这个方法来声明自己的来源"""
        return "unknown"

    def validate(self, parsed_data: dict) -> dict:
        """
        用 Serializer 验证 parsed_data
        包含：必填字段检查 + NPI/MRN/ICD-10 格式验证
        验证失败直接 raise ValidationError
        返回 validated_data
        """
        serializer = OrderCreateSerializer(parsed_data)
        serializer.raise_if_invalid()
        return serializer.get_validated_data()

    def transform(self, validated_data: dict) -> InternalOrder:
        """
        把 validated_data 组装成 InternalOrder
        所有 Adapter 的 transform 逻辑完全一样，放在基类
        """
        return InternalOrder(
            patient=PatientInfo(
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                mrn=validated_data["mrn"],
                date_of_birth=validated_data["date_of_birth"],
            ),
            provider=ProviderInfo(
                name=validated_data["provider_name"],
                npi=validated_data["provider_npi"],
            ),
            medication=MedicationInfo(
                medication_name=validated_data["medication_name"],
                primary_diagnosis=validated_data["primary_diagnosis"],
                additional_diagnoses=validated_data.get("additional_diagnoses", []),
                medication_history=validated_data.get("medication_history", []),
                patient_records=validated_data.get("patient_records", ""),
            ),
            source=self.get_source(),
        )

    def run(self) -> InternalOrder:
        """顺序：parse → validate → transform"""
        parsed_data = self.parse()
        validated_data = self.validate(parsed_data)
        self.internal_order = self.transform(validated_data)
        return self.internal_order


# ========================================
# Clinic B：小型诊所 JSON 格式
# ========================================

class ClinicBAdapter(BaseIntakeAdapter):

    def __init__(self, request):
        raw_data = json.loads(request.body)
        super().__init__(raw_data)

    def get_source(self) -> str:
        return "clinic_b"

    def parse(self) -> dict:
        pt = self.raw_data["pt"]
        provider = self.raw_data["provider"]
        dx = self.raw_data["dx"]
        rx = self.raw_data["rx"]

        # 日期格式转换：MM/DD/YYYY → YYYY-MM-DD
        date_of_birth = datetime.strptime(
            pt["dob"], "%m/%d/%Y"
        ).strftime("%Y-%m-%d")

        return {
            "first_name":           pt["fname"],
            "last_name":            pt["lname"],
            "mrn":                  pt["mrn"],
            "date_of_birth":        date_of_birth,
            "provider_name":        provider["name"],
            "provider_npi":         provider["npi_num"],
            "medication_name":      rx["med_name"],
            "primary_diagnosis":    dx["primary"],
            "additional_diagnoses": dx["secondary"],
            "medication_history":   self.raw_data["med_hx"],
            "patient_records":      self.raw_data["clinical_notes"],
        }


# ========================================
# PharmaCorp：药企 XML 格式
# ========================================

class PharmaCorpAdapter(BaseIntakeAdapter):

    def __init__(self, request):
        raw_data = request.body.decode("utf-8")
        super().__init__(raw_data)

    def get_source(self) -> str:
        return "pharmcorp"

    def parse(self) -> dict:
        root = ET.fromstring(self.raw_data)

        # 用药历史：每个 <Medication> 拼成一个字符串
        medication_history = []
        for med in root.findall(".//MedicationHistory/Medication"):
            med_name = med.find("MedicationName").text or ""
            dosage   = med.find("Dosage").text or ""
            route    = med.find("Route").text or ""
            freq     = med.find("Frequency").text or ""
            medication_history.append(
                f"{med_name} {dosage} {route} {freq}".strip()
            )

        return {
            "first_name":           root.find(".//PatientName/FirstName").text,
            "last_name":            root.find(".//PatientName/LastName").text,
            "mrn":                  root.find(".//MedicalRecordNumber").text,
            "date_of_birth":        root.find(".//DateOfBirth").text,
            "provider_name":        root.find(".//PrescriberInformation/FullName").text,
            "provider_npi":         root.find(".//PrescriberInformation/NPINumber").text,
            "medication_name":      root.find(".//MedicationOrder/DrugName").text,
            "primary_diagnosis":    root.find(".//PrimaryDiagnosis/ICDCode").text,
            "additional_diagnoses": [
                e.text for e in
                root.findall(".//SecondaryDiagnoses/Diagnosis/ICDCode")
            ],
            "medication_history":   medication_history,
            "patient_records":      root.find(".//NarrativeText").text or "",
        }


# ========================================
# WebForm：CVS 内部表单（已经是标准格式）
# ========================================

class WebFormAdapter(BaseIntakeAdapter):

    def __init__(self, request):
        raw_data = json.loads(request.body)
        super().__init__(raw_data)

    def get_source(self) -> str:
        return "webform"

    def parse(self) -> dict:
        # 已经是标准格式，直接返回
        return self.raw_data


# ========================================
# 工厂函数
# ========================================

ADAPTER_REGISTRY = {
    "webform":   WebFormAdapter,
    "clinic_b":  ClinicBAdapter,
    "pharmcorp": PharmaCorpAdapter,
}


def get_adapter(request) -> BaseIntakeAdapter:
    """
    从 X-Source-System header 读来源，查注册表返回 Adapter 实例

    新增数据源只需要：
    1. 写一个新 Adapter 类
    2. 在 ADAPTER_REGISTRY 加一行
    """
    source = request.headers.get("X-Source-System", "webform")

    adapter_class = ADAPTER_REGISTRY.get(source)
    if adapter_class is None:
        raise ValidationError(
            message=f"Unknown source: '{source}'",
            code="UNKNOWN_SOURCE",
            detail={"source": f"Must be one of: {list(ADAPTER_REGISTRY.keys())}"}
        )

    return adapter_class(request)