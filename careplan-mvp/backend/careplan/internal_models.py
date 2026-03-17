# internal_models.py
#
# 定义内部标准数据格式
# 所有外部数据源都要转换成这个格式
# 业务逻辑（services.py）只认识这个格式，不认识任何外部格式

from dataclasses import dataclass, field
from typing import List


@dataclass
class PatientInfo:
    # 患者基本信息
    first_name: str
    last_name: str
    mrn: str            # 6位数字，唯一标识
    date_of_birth: str  # 格式统一为 "YYYY-MM-DD"


@dataclass
class ProviderInfo:
    # 开单医生信息
    name: str
    npi: str            # 10位数字，全国唯一


@dataclass
class MedicationInfo:
    # 药物和诊断信息
    medication_name: str
    primary_diagnosis: str        # ICD-10 格式，如 "G70.01"
    additional_diagnoses: List[str] = field(default_factory=list)
    medication_history: List[str] = field(default_factory=list)
    patient_records: str = ""


@dataclass
class InternalOrder:
    # 内部标准订单格式
    # 这是唯一一个 services.py 会接触到的数据结构
    patient: PatientInfo
    provider: ProviderInfo
    medication: MedicationInfo
    source: str = "webform"   # 记录数据来源，方便排查问题