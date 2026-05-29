"""Pydantic models aligned with FHIR R4 Patient resource."""

from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class Address(BaseModel):
    line: list[str] = []
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


class ContactPoint(BaseModel):
    system: str  # phone | fax | email
    value: str
    use: str = "home"


class Condition(BaseModel):
    code: str
    display: str
    system: str = "http://snomed.info/sct"
    onset_date: date | None = None
    clinical_status: str = "active"


class Medication(BaseModel):
    code: str
    display: str
    system: str = "http://www.nlm.nih.gov/research/umls/rxnorm"
    dosage: str = ""
    status: str = "active"


class Patient(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    fhir_id: str | None = None
    mrn: str
    given_name: str
    family_name: str
    birth_date: date
    gender: Gender
    address: Address = Field(default_factory=Address)
    telecoms: list[ContactPoint] = []
    conditions: list[Condition] = []
    medications: list[Medication] = []
    organization_id: str

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.family_name}"

    @property
    def age(self) -> int:
        today = date.today()
        return (today - self.birth_date).days // 365

    def to_fhir_dict(self) -> dict[str, Any]:
        return {
            "resourceType": "Patient",
            "id": self.fhir_id or str(self.id),
            "identifier": [{"system": "urn:oid:2.16.840.1.113883.2.4.6.3", "value": self.mrn}],
            "name": [{"family": self.family_name, "given": [self.given_name]}],
            "gender": self.gender.value,
            "birthDate": self.birth_date.isoformat(),
            "address": [self.address.model_dump(exclude_none=True)],
        }
