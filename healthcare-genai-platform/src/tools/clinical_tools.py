"""Clinical decision support tools for AI agents."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class RiskInput(BaseModel):
    age: int = Field(description="Patient age in years")
    conditions: list[str] = Field(description="List of active diagnoses (SNOMED display names)")
    medications: list[str] = Field(description="List of active medications")
    recent_hospitalizations: int = Field(default=0, description="Number of hospitalizations in last 12 months")


# Evidence-based risk factors (simplified Charlson Comorbidity Index weights)
_HIGH_RISK_CONDITIONS = {
    "myocardial infarction": 1, "congestive heart failure": 1, "peripheral vascular disease": 1,
    "cerebrovascular disease": 1, "dementia": 1, "chronic pulmonary disease": 1,
    "diabetes": 1, "mild liver disease": 1, "renal disease": 1,
    "hemiplegia": 2, "moderate or severe renal disease": 2, "diabetes with end organ damage": 2,
    "any tumor": 2, "leukemia": 2, "lymphoma": 2,
    "moderate or severe liver disease": 3, "metastatic solid tumor": 6, "aids": 6,
}


@tool(args_schema=RiskInput)
def calculate_readmission_risk(
    age: int,
    conditions: list[str],
    medications: list[str],
    recent_hospitalizations: int = 0,
) -> str:
    """Calculate 30-day hospital readmission risk score using evidence-based criteria."""
    score = 0

    # Age factor (Charlson)
    if age >= 80:
        score += 4
    elif age >= 70:
        score += 3
    elif age >= 60:
        score += 2
    elif age >= 50:
        score += 1

    # Condition weights
    for condition in conditions:
        cond_lower = condition.lower()
        for key, weight in _HIGH_RISK_CONDITIONS.items():
            if key in cond_lower:
                score += weight

    # Polypharmacy risk
    if len(medications) >= 10:
        score += 2
    elif len(medications) >= 5:
        score += 1

    # Prior hospitalizations (LACE index component)
    score += min(recent_hospitalizations * 2, 6)

    if score <= 2:
        risk_level, recommendation = "Low", "Standard monitoring. Follow-up in 30 days."
    elif score <= 5:
        risk_level, recommendation = "Moderate", "Enhanced monitoring. Follow-up call at 7 days, visit at 14 days."
    else:
        risk_level, recommendation = "High", "Intensive care management. Daily check-in × 7 days, visit within 72h of discharge."

    return (
        f"Readmission Risk: {risk_level} (score: {score})\n"
        f"Recommendation: {recommendation}\n"
        f"Factors: age={age}, conditions={len(conditions)}, meds={len(medications)}, "
        f"prior hospitalizations={recent_hospitalizations}"
    )


class DrugInteractionInput(BaseModel):
    medications: list[str] = Field(description="List of medication names to check for interactions")


_KNOWN_INTERACTIONS: list[tuple[str, str, str]] = [
    ("warfarin", "aspirin", "HIGH: Increased bleeding risk"),
    ("warfarin", "ibuprofen", "HIGH: Increased bleeding risk"),
    ("metformin", "contrast dye", "MODERATE: Hold metformin 48h before/after contrast"),
    ("ssri", "maoi", "CONTRAINDICATED: Serotonin syndrome risk"),
    ("ace inhibitor", "potassium", "MODERATE: Hyperkalemia risk"),
    ("digoxin", "amiodarone", "HIGH: Digoxin toxicity risk — reduce dose by 50%"),
    ("statin", "fibrate", "MODERATE: Myopathy risk"),
]


@tool(args_schema=DrugInteractionInput)
def check_drug_interactions(medications: list[str]) -> str:
    """Check for known drug-drug interactions in the patient's medication list."""
    meds_lower = [m.lower() for m in medications]
    found = []
    for drug_a, drug_b, severity in _KNOWN_INTERACTIONS:
        a_match = any(drug_a in m for m in meds_lower)
        b_match = any(drug_b in m for m in meds_lower)
        if a_match and b_match:
            found.append(f"⚠ {drug_a.title()} + {drug_b.title()}: {severity}")

    if not found:
        return "No known interactions detected in the provided medication list."
    return "Drug interaction alerts:\n" + "\n".join(found)


class CareGapInput(BaseModel):
    age: int
    gender: str
    conditions: list[str]
    last_screenings: dict[str, str] = Field(
        default={},
        description="Dict of screening name to last date (YYYY-MM-DD)",
    )


@tool(args_schema=CareGapInput)
def identify_care_gaps(age: int, gender: str, conditions: list[str], last_screenings: dict = {}) -> str:
    """Identify preventive care gaps based on USPSTF guidelines."""
    gaps = []
    conds_lower = [c.lower() for c in conditions]

    if age >= 50 and "colonoscopy" not in last_screenings:
        gaps.append("Colorectal cancer screening (USPSTF: every 10 years age 45-75)")
    if gender.lower() == "female" and age >= 40 and "mammogram" not in last_screenings:
        gaps.append("Mammography screening (USPSTF: every 2 years age 40-74)")
    if age >= 65 and "flu_vaccine" not in last_screenings:
        gaps.append("Annual influenza vaccination")
    if any("diabetes" in c for c in conds_lower) and "hba1c" not in last_screenings:
        gaps.append("HbA1c monitoring (target: every 3-6 months for uncontrolled DM)")
    if any("hypertension" in c for c in conds_lower) and "bp_check" not in last_screenings:
        gaps.append("Blood pressure monitoring (target: < 130/80 mmHg)")

    if not gaps:
        return "No preventive care gaps identified based on available data."
    return "Identified care gaps:\n" + "\n".join(f"- {g}" for g in gaps)


CLINICAL_TOOLS = [calculate_readmission_risk, check_drug_interactions, identify_care_gaps]
