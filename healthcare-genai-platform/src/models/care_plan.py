"""Care plan models aligned with FHIR R4 CarePlan resource."""

from datetime import date, datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CarePlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on-hold"
    REVOKED = "revoked"
    COMPLETED = "completed"


class ActivityKind(str, Enum):
    APPOINTMENT = "appointment"
    COMMUNICATION = "communication"
    DEVICE_REQUEST = "device-request"
    MEDICATION_REQUEST = "medication-request"
    NUTRITION_ORDER = "nutrition-order"
    SERVICE_REQUEST = "service-request"
    TASK = "task"


class CarePlanActivity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    kind: ActivityKind
    title: str
    description: str
    scheduled_date: date | None = None
    assigned_to: str | None = None
    status: str = "not-started"
    notes: str = ""


class Goal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    description: str
    target_date: date | None = None
    measure: str = ""
    target_value: str = ""
    status: str = "in-progress"


class CarePlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    fhir_id: str | None = None
    patient_id: str
    title: str
    description: str
    status: CarePlanStatus = CarePlanStatus.DRAFT
    period_start: date = Field(default_factory=date.today)
    period_end: date | None = None
    goals: list[Goal] = []
    activities: list[CarePlanActivity] = []
    created_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ai_generated: bool = False
    ai_model: str | None = None
    rationale: str = ""

    def to_fhir_dict(self) -> dict:
        return {
            "resourceType": "CarePlan",
            "id": self.fhir_id or str(self.id),
            "status": self.status.value,
            "intent": "plan",
            "title": self.title,
            "description": self.description,
            "subject": {"reference": f"Patient/{self.patient_id}"},
            "period": {
                "start": self.period_start.isoformat(),
                **({"end": self.period_end.isoformat()} if self.period_end else {}),
            },
            "goal": [{"description": {"text": g.description}} for g in self.goals],
            "activity": [
                {"detail": {"kind": a.kind.value, "description": a.description, "status": a.status}}
                for a in self.activities
            ],
        }
