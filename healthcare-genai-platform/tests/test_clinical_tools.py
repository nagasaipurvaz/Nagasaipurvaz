"""Clinical tools unit tests (no external API calls)."""

import pytest

from src.tools.clinical_tools import (
    calculate_readmission_risk,
    check_drug_interactions,
    identify_care_gaps,
)


def test_high_risk_readmission():
    result = calculate_readmission_risk.invoke({
        "age": 75,
        "conditions": ["congestive heart failure", "diabetes", "renal disease"],
        "medications": ["furosemide", "metformin", "lisinopril", "aspirin", "atorvastatin",
                        "spironolactone", "carvedilol", "insulin", "potassium chloride", "warfarin"],
        "recent_hospitalizations": 2,
    })
    assert "High" in result
    assert "Intensive" in result


def test_low_risk_readmission():
    result = calculate_readmission_risk.invoke({
        "age": 35,
        "conditions": ["mild sinusitis"],
        "medications": ["amoxicillin"],
        "recent_hospitalizations": 0,
    })
    assert "Low" in result


def test_drug_interaction_detected():
    result = check_drug_interactions.invoke({
        "medications": ["warfarin 5mg", "aspirin 81mg"]
    })
    assert "bleeding" in result.lower() or "HIGH" in result


def test_no_drug_interactions():
    result = check_drug_interactions.invoke({
        "medications": ["lisinopril 10mg", "atorvastatin 20mg"]
    })
    assert "No known interactions" in result


def test_care_gaps_diabetes():
    result = identify_care_gaps.invoke({
        "age": 58,
        "gender": "male",
        "conditions": ["Type 2 diabetes", "hypertension"],
        "last_screenings": {},
    })
    assert "HbA1c" in result or "blood pressure" in result.lower()


def test_care_gaps_none():
    result = identify_care_gaps.invoke({
        "age": 30,
        "gender": "male",
        "conditions": [],
        "last_screenings": {"colonoscopy": "2023-01-01", "flu_vaccine": "2024-09-01"},
    })
    assert "No preventive care gaps" in result
