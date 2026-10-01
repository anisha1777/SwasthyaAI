from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResultResponse(BaseModel):
    id: int
    screening_id: int
    prediction: str
    confidence: float
    risk_level: str
    model_version: str | None = None
    gradcam_path: str | None = None
    explanation: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
