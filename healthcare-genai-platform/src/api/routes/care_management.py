"""Care management API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.agents.care_manager import run_care_management
from src.hipaa.access_control import TokenData, require_permission
from src.hipaa.audit_logger import AuditAction, get_audit_logger

router = APIRouter(prefix="/care", tags=["Care Management"])


class CarePlanResponse(BaseModel):
    patient_id: str
    care_plan_output: str
    status: str


@router.post("/plan/{patient_id}", response_model=CarePlanResponse)
async def generate_care_plan(
    patient_id: str,
    current_user: TokenData = Depends(require_permission("care_plan:write")),
):
    """Generate a comprehensive AI care plan using the multi-agent crew."""
    audit = get_audit_logger()
    audit.log(
        AuditAction.CREATE,
        user_id=current_user.user_id,
        resource_type="CarePlan",
        resource_id=f"new-{patient_id}",
        patient_id=patient_id,
        details={"agent": "care_management_crew"},
    )
    result = await run_care_management(patient_id)
    return CarePlanResponse(**result)
