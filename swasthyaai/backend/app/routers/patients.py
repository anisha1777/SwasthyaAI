from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.patient import Patient
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
)

# Change this import if your auth dependency has a different filename/function
from app.core.security import get_current_user


router = APIRouter()


# CREATE PATIENT
@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED
)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Check duplicate patient code
    existing_patient = (
        db.query(Patient)
        .filter(Patient.patient_code == patient_data.patient_code)
        .first()
    )

    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient code already exists"
        )

    patient = Patient(
        **patient_data.model_dump(),
        registered_by=current_user.id
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient


# GET ALL PATIENTS
@router.get(
    "/",
    response_model=list[PatientResponse]
)
def get_patients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()

    return patients


# GET ONE PATIENT
@router.get(
    "/{patient_id}",
    response_model=PatientResponse
)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient


# UPDATE PATIENT
@router.put(
    "/{patient_id}",
    response_model=PatientResponse
)
def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    update_data = patient_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(patient, key, value)

    db.commit()
    db.refresh(patient)

    return patient
