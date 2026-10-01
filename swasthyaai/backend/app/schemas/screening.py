from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ScreeningCreate(BaseModel):
    patient_id: int
    screening_type: str
    symptoms: Optional[str] = None


class ScreeningResponse(BaseModel):
    id: int
    patient_id: int
    created_by: int
    screening_type: str
    symptoms: Optional[str] = None
    status: str
    screening_date: datetime
    created_at: datetime

    image_reference: Optional[str] = None
    image_filename: Optional[str] = None
    image_size: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ScreeningResultResponse(BaseModel):
    id: int
    screening_id: int
    prediction: str
    confidence: float
    risk_level: str
    model_version: Optional[str] = None
    gradcam_path: Optional[str] = None
    explanation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
