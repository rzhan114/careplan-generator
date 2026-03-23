from careplan.models import Provider
from careplan.exceptions import BlockError, WarningException

def create_provider(name: str, npi: str) -> Provider:
    # 1. 同 NPI 已存在
    try:
        existing = Provider.objects.get(npi=npi)
        if existing.name == name:
            return existing  # 复用
        else:
            raise BlockError(
                code="NPI_NAME_MISMATCH",
                message=f"NPI {npi} already belongs to '{existing.name}', not '{name}'.",
                detail={"existing_name": existing.name, "submitted_name": name},
            )
    except Provider.DoesNotExist:
        pass

    # 2. 同名字但 NPI 不同
    same_name = Provider.objects.filter(name=name).exclude(npi=npi).first()
    if same_name:
        raise WarningException(
            code="PROVIDER_NAME_DUPLICATE",
            message=f"A provider named '{name}' already exists with NPI {same_name.npi}. Please verify this is not a duplicate.",
            detail={"existing_provider_id": same_name.id, "existing_npi": same_name.npi},
        )

    return Provider.objects.create(name=name, npi=npi)