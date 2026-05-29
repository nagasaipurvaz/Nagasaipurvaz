"""LangChain-compatible FHIR R4 tools for agent use."""

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config.settings import get_settings


def _fhir_headers() -> dict[str, str]:
    return {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}


def _fhir_get(path: str) -> dict:
    settings = get_settings()
    url = f"{settings.fhir_base_url}/{path}"
    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=_fhir_headers())
        response.raise_for_status()
        return response.json()


class PatientSearchInput(BaseModel):
    family: str = Field(description="Patient's family/last name")
    given: str = Field(default="", description="Patient's given/first name")
    birthdate: str = Field(default="", description="Birth date in YYYY-MM-DD format")


@tool(args_schema=PatientSearchInput)
def search_patient(family: str, given: str = "", birthdate: str = "") -> str:
    """Search for a patient in the FHIR server by name and/or birth date."""
    params = [f"family={family}"]
    if given:
        params.append(f"given={given}")
    if birthdate:
        params.append(f"birthdate={birthdate}")
    query = "&".join(params)
    data = _fhir_get(f"Patient?{query}")
    entries = data.get("entry", [])
    if not entries:
        return "No patients found matching those criteria."
    results = []
    for e in entries[:5]:
        p = e["resource"]
        name = p.get("name", [{}])[0]
        full_name = f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip()
        results.append(f"- ID: {p['id']} | Name: {full_name} | DOB: {p.get('birthDate', 'N/A')}")
    return "\n".join(results)


class PatientIdInput(BaseModel):
    patient_id: str = Field(description="FHIR patient ID")


@tool(args_schema=PatientIdInput)
def get_patient(patient_id: str) -> str:
    """Retrieve full patient record from FHIR by patient ID."""
    data = _fhir_get(f"Patient/{patient_id}")
    name = data.get("name", [{}])[0]
    full_name = f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip()
    gender = data.get("gender", "unknown")
    dob = data.get("birthDate", "unknown")
    return f"Patient {patient_id}: {full_name}, {gender}, DOB: {dob}"


@tool(args_schema=PatientIdInput)
def get_patient_conditions(patient_id: str) -> str:
    """Get all active conditions (diagnoses) for a patient from FHIR."""
    data = _fhir_get(f"Condition?patient={patient_id}&clinical-status=active")
    entries = data.get("entry", [])
    if not entries:
        return f"No active conditions found for patient {patient_id}."
    conditions = []
    for e in entries:
        c = e["resource"]
        code = c.get("code", {})
        display = code.get("text") or (code.get("coding", [{}])[0].get("display", "Unknown"))
        conditions.append(f"- {display}")
    return f"Active conditions for patient {patient_id}:\n" + "\n".join(conditions)


@tool(args_schema=PatientIdInput)
def get_patient_medications(patient_id: str) -> str:
    """Get current medication requests for a patient from FHIR."""
    data = _fhir_get(f"MedicationRequest?patient={patient_id}&status=active")
    entries = data.get("entry", [])
    if not entries:
        return f"No active medications found for patient {patient_id}."
    meds = []
    for e in entries:
        m = e["resource"]
        med = m.get("medicationCodeableConcept", {})
        display = med.get("text") or (med.get("coding", [{}])[0].get("display", "Unknown"))
        meds.append(f"- {display}")
    return f"Active medications for patient {patient_id}:\n" + "\n".join(meds)


@tool(args_schema=PatientIdInput)
def get_patient_observations(patient_id: str) -> str:
    """Get recent vital signs and lab observations for a patient from FHIR."""
    data = _fhir_get(f"Observation?patient={patient_id}&_sort=-date&_count=10")
    entries = data.get("entry", [])
    if not entries:
        return f"No observations found for patient {patient_id}."
    obs = []
    for e in entries:
        o = e["resource"]
        code = o.get("code", {})
        display = code.get("text") or (code.get("coding", [{}])[0].get("display", "Unknown"))
        value = o.get("valueQuantity", {})
        val_str = f"{value.get('value', '')} {value.get('unit', '')}".strip()
        date_str = o.get("effectiveDateTime", "")[:10]
        obs.append(f"- {display}: {val_str} ({date_str})")
    return f"Recent observations for patient {patient_id}:\n" + "\n".join(obs)


FHIR_TOOLS = [search_patient, get_patient, get_patient_conditions, get_patient_medications, get_patient_observations]
