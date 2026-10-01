from pydantic import BaseModel, Field
from typing import Optional


class PatientCreate(BaseModel):
    patient_code: str
    name: str
    age: int = Field(..., ge=0, le=120)
    gender: str
    village: str

    guardian_name: Optional[str] = None
    contact: Optional[str] = None
    symptoms: Optional[str] = None
    medical_history: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    village: Optional[str] = None

    guardian_name: Optional[str] = None
    contact: Optional[str] = None
    symptoms: Optional[str] = None
    medical_history: Optional[str] = None


class PatientResponse(BaseModel):
    id: int
    patient_code: str
    name: str
    age: int
    gender: str
    village: str
    guardian_name: Optional[str] = None
    contact: Optional[str] = None
    symptoms: Optional[str] = None
    medical_history: Optional[str] = None
    registered_by: int

    class Config:
        from_attributes = True
