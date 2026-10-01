from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db

from app.models.patient import Patient
from app.models.screening import Screening
from app.models.screening_result import ScreeningResult
from app.models.user import User

from app.ml.inference import predict

from app.services.image_quality import check_image_quality
from app.services.risk_engine import calculate_risk
from app.services.gradcam import generate_gradcam
from app.services.audit_service import create_audit_log


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    tags=["Screenings"]
)


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

GRADCAM_DIR = UPLOAD_DIR / "gradcam"

GRADCAM_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ============================================================
# ACCESS CONTROL
# ============================================================

def can_access(
    user: User,
    patient: Patient,
) -> bool:
    """
    Determine whether the logged-in user can access
    the patient's screening information.
    """

    # ADMIN and ANM have full access
    if user.role in {
        "ADMIN",
        "ANM",
    }:
        return True

    # Future support for assigned_worker_id
    if hasattr(
        patient,
        "assigned_worker_id",
    ):
        return (
            patient.assigned_worker_id == user.id
            or patient.assigned_worker_id is None
        )

    # Current Patient model does not contain
    # assigned_worker_id, so ASHA access is allowed.
    return True


# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_image(
    filename: str | None,
    content: bytes,
) -> None:
    """
    Validate uploaded image before saving/processing.
    """

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Image filename is required.",
        )

    extension = Path(
        filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported image format.",
                "allowed_extensions": sorted(
                    ALLOWED_EXTENSIONS
                ),
            },
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Image file is too large.",
                "max_size_mb": 10,
            },
        )


# ============================================================
# CREATE SCREENING
# ============================================================

@router.post(
    "",
    status_code=201,
)
def create_screening(
    patient_id: int,
    screening_type: str,
    symptoms: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new screening record.

    Supported types:
        ANEMIA
        JAUNDICE
        SKIN
    """

    patient = db.get(
        Patient,
        patient_id,
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    if not can_access(
        user,
        patient,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this patient."
            ),
        )

    screening_type = (
        screening_type
        .strip()
        .upper()
    )

    allowed_types = {
        "ANEMIA",
        "JAUNDICE",
        "SKIN",
    }

    if screening_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported screening type.",
                "allowed_types": sorted(
                    allowed_types
                ),
            },
        )

    screening = Screening(
        patient_id=patient.id,
        created_by=user.id,
        screening_type=screening_type,
        symptoms=symptoms,
        status="PENDING",
    )

    db.add(screening)

    try:
        db.flush()

        create_audit_log(
            db=db,
            action="SCREENING_CREATED",
            user_id=user.id,
            entity_type="SCREENING",
            entity_id=screening.id,
            details={
                "patient_id": patient.id,
                "screening_type": screening_type,
            },
        )

        db.commit()

        db.refresh(
            screening
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create screening.",
        )

    return {
        "message": (
            "Screening created successfully."
        ),
        "screening": {
            "id": screening.id,
            "patient_id": screening.patient_id,
            "screening_type": screening.screening_type,
            "symptoms": screening.symptoms,
            "status": screening.status,
            "created_by": screening.created_by,
            "created_at": screening.created_at,
        },
    }


# ============================================================
# ANALYZE SCREENING
# ============================================================

@router.post(
    "/{screening_id}/analyze"
)
async def analyze_screening(
    screening_id: int,
    image: UploadFile = File(...),
    symptoms: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Analyze a screening image.

    Pipeline:

        Upload
          ↓
        Validation
          ↓
        Image Quality
          ↓
        ML Inference
          ↓
        Risk Engine
          ↓
        Grad-CAM
          ↓
        Database
          ↓
        Audit Log
    """

    # ========================================================
    # FIND SCREENING
    # ========================================================

    screening = db.get(
        Screening,
        screening_id,
    )

    if screening is None:
        raise HTTPException(
            status_code=404,
            detail="Screening not found.",
        )

    # ========================================================
    # FIND PATIENT
    # ========================================================

    patient = db.get(
        Patient,
        screening.patient_id,
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Patient associated with "
                "screening not found."
            ),
        )

    # ========================================================
    # ACCESS CONTROL
    # ========================================================

    if not can_access(
        user,
        patient,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this screening."
            ),
        )

    # ========================================================
    # VALIDATE SCREENING TYPE
    # ========================================================

    screening_type = (
        screening.screening_type
        .strip()
        .upper()
    )

    allowed_types = {
        "ANEMIA",
        "JAUNDICE",
        "SKIN",
    }

    if screening_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Unsupported screening type."
                ),
                "screening_type": screening_type,
            },
        )

    # ========================================================
    # READ IMAGE
    # ========================================================

    content = await image.read()

    validate_image(
        filename=image.filename,
        content=content,
    )

    # ========================================================
    # SAVE IMAGE
    # ========================================================

    extension = Path(
        image.filename or ".jpg"
    ).suffix.lower()

    filename = (
        f"screening_"
        f"{screening.id}_"
        f"{screening.patient_id}"
        f"{extension}"
    )

    image_path = (
        UPLOAD_DIR / filename
    )

    try:
        image_path.write_bytes(
            content
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save "
                "uploaded image."
            ),
        )

    # ========================================================
    # SAVE IMAGE METADATA
    # ========================================================

    screening.image_reference = str(
        image_path
    )

    screening.image_filename = (
        image.filename
    )

    screening.image_size = len(
        content
    )

    # ========================================================
    # READ IMAGE DIMENSIONS
    # ========================================================

    try:
        from PIL import Image

        with Image.open(
            image_path
        ) as img:

            screening.image_width = (
                img.width
            )

            screening.image_height = (
                img.height
            )

    except Exception:
        screening.image_width = None
        screening.image_height = None

    # ========================================================
    # UPDATE SYMPTOMS
    # ========================================================

    if symptoms is not None:
        screening.symptoms = symptoms

    try:
        db.commit()

        db.refresh(
            screening
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save "
                "image metadata."
            ),
        )

    # ========================================================
    # IMAGE QUALITY CHECK
    # ========================================================

    quality_result = check_image_quality(
        str(image_path)
    )

    # ========================================================
    # QUALITY FAILED
    # ========================================================

    if (
        quality_result[
            "quality_status"
        ]
        != "PASS"
    ):

        screening.status = (
            "QUALITY_FAILED"
        )

        create_audit_log(
            db=db,
            action="IMAGE_QUALITY_FAILED",
            user_id=user.id,
            entity_type="SCREENING",
            entity_id=screening.id,
            details={
                "patient_id": screening.patient_id,
                "screening_type": screening.screening_type,
                "reason_code": (
                    quality_result[
                        "reason_code"
                    ]
                ),
                "quality_status": (
                    quality_result[
                        "quality_status"
                    ]
                ),
                "metrics": (
                    quality_result.get(
                        "metrics"
                    )
                ),
            },
        )

        try:
            db.commit()

        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Image quality "
                    "check failed."
                ),
                "quality_status": (
                    quality_result[
                        "quality_status"
                    ]
                ),
                "reason_code": (
                    quality_result[
                        "reason_code"
                    ]
                ),
                "recapture_guidance": (
                    quality_result[
                        "message"
                    ]
                ),
                "metrics": (
                    quality_result.get(
                        "metrics"
                    )
                ),
            },
        )

    # ========================================================
    # ANEMIA MODEL
    # ========================================================

    if screening_type == "ANEMIA":

        screening.status = "PENDING"

        try:
            db.commit()

        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=501,
            detail=(
                "Anemia model integration "
                "is pending."
            ),
        )

    # ========================================================
    # ML INFERENCE
    # ========================================================

    try:

        prediction = predict(
            str(image_path),
            screening_type.lower(),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        screening.status = (
            "INFERENCE_FAILED"
        )

        try:
            db.commit()

        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "ML inference failed."
                ),
                "error": str(exc),
            },
        )

    # ========================================================
    # EXTRACT PREDICTION
    # ========================================================

    predicted_label = prediction[
        "prediction"
    ]

    confidence = float(
        prediction[
            "confidence"
        ]
    )

    class_index = int(
        prediction[
            "class_index"
        ]
    )

    model_version = prediction.get(
        "model_version",
        "EfficientNet-B5",
    )

    # ========================================================
    # RISK ENGINE
    # ========================================================

    risk_result = calculate_risk(
        prediction=predicted_label,
        confidence=confidence,
        screening_type=screening_type,
    )

    # RiskDecision is a dataclass,
    # therefore use attributes, not dictionary indexing.
    risk_level = risk_result.risk_level
    risk_reason = risk_result.reason
    risk_engine_version = (
        risk_result.engine_version
    )

    # ========================================================
    # GRAD-CAM
    # ========================================================

    gradcam_path = None
    gradcam_error = None

    gradcam_filename = (
        f"screening_"
        f"{screening.id}_"
        f"{screening.patient_id}_"
        f"gradcam.jpg"
    )

    gradcam_output_path = (
        GRADCAM_DIR
        / gradcam_filename
    )

    try:

        gradcam_path = generate_gradcam(
            image_path=str(
                image_path
            ),
            screening_type=screening_type,
            target_class_index=class_index,
            output_path=str(
                gradcam_output_path
            ),
        )

    except Exception as exc:

        # Grad-CAM failure should not
        # invalidate the ML prediction.
        gradcam_error = str(
            exc
        )

    # ========================================================
    # SAVE SCREENING RESULT
    # ========================================================

    existing_result = db.scalar(
        select(
            ScreeningResult
        ).where(
            ScreeningResult.screening_id
            == screening.id
        )
    )

    if existing_result:

        existing_result.prediction = (
            predicted_label
        )

        existing_result.confidence = (
            confidence
        )

        existing_result.risk_level = (
            risk_level
        )

        existing_result.risk_engine_version = (
            risk_engine_version
        )

        existing_result.risk_reason = (
            risk_reason
        )

        existing_result.model_version = (
            model_version
        )

        existing_result.gradcam_path = (
            gradcam_path
        )

        existing_result.explanation = (
            risk_reason
        )

        result = existing_result

    else:

        result = ScreeningResult(
            screening_id=screening.id,
            prediction=predicted_label,
            confidence=confidence,
            risk_level=risk_level,
            risk_engine_version=(
                risk_engine_version
            ),
            risk_reason=(
                risk_reason
            ),
            model_version=model_version,
            gradcam_path=gradcam_path,
            explanation=(
                risk_reason
            ),
        )

        db.add(
            result
        )

    # ========================================================
    # SCREENING STATUS
    # ========================================================

    screening.status = "ANALYZED"

    # ========================================================
    # AUDIT: SCREENING ANALYZED
    # ========================================================

    create_audit_log(
        db=db,
        action="SCREENING_ANALYZED",
        user_id=user.id,
        entity_type="SCREENING",
        entity_id=screening.id,
        details={
            "patient_id": (
                screening.patient_id
            ),
            "screening_type": (
                screening.screening_type
            ),
            "prediction": (
                predicted_label
            ),
            "confidence": (
                confidence
            ),
            "risk_level": (
                risk_level
            ),
            "risk_engine_version": (
                risk_engine_version
            ),
            "risk_reason": (
                risk_reason
            ),
            "model_version": (
                model_version
            ),
            "gradcam_generated": (
                gradcam_path is not None
            ),
        },
    )

    # ========================================================
    # DATABASE COMMIT
    # ========================================================

    try:

        db.commit()

        db.refresh(
            screening
        )

        db.refresh(
            result
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save "
                "screening result."
            ),
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    response = {

        "message": (
            "Screening analyzed "
            "successfully."
        ),

        "screening": {
            "id": screening.id,
            "patient_id": (
                screening.patient_id
            ),
            "screening_type": (
                screening.screening_type
            ),
            "status": screening.status,
        },

        "image": {

            "filename": (
                screening.image_filename
            ),

            "size": (
                screening.image_size
            ),

            "width": (
                screening.image_width
            ),

            "height": (
                screening.image_height
            ),

            "path": (
                screening.image_reference
            ),

            "quality": {

                "status": (
                    quality_result[
                        "quality_status"
                    ]
                ),

                "reason_code": (
                    quality_result[
                        "reason_code"
                    ]
                ),

                "message": (
                    quality_result[
                        "message"
                    ]
                ),

                "metrics": (
                    quality_result.get(
                        "metrics"
                    )
                ),
            },
        },

        "inference": {

            "prediction": (
                predicted_label
            ),

            "confidence": (
                confidence
            ),

            "class_index": (
                class_index
            ),

            "screening_type": (
                screening_type.lower()
            ),

            "model_version": (
                model_version
            ),
        },

        "risk": {

            "risk_level": (
                risk_level
            ),

            "reason": (
                risk_reason
            ),

            "risk_engine_version": (
                risk_engine_version
            ),
        },

        "gradcam": {

            "generated": (
                gradcam_path is not None
            ),

            "path": gradcam_path,
        },
    }

    if gradcam_error:

        response[
            "gradcam"
        ][
            "error"
        ] = gradcam_error

    return response


# ============================================================
# GET SCREENING
# ============================================================

@router.get(
    "/{screening_id}"
)
def get_screening(
    screening_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    screening = db.get(
        Screening,
        screening_id,
    )

    if screening is None:

        raise HTTPException(
            status_code=404,
            detail="Screening not found.",
        )

    patient = db.get(
        Patient,
        screening.patient_id,
    )

    if patient is None:

        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    if not can_access(
        user,
        patient,
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this screening."
            ),
        )

    return {

        "id": screening.id,

        "patient_id": (
            screening.patient_id
        ),

        "created_by": (
            screening.created_by
        ),

        "screening_type": (
            screening.screening_type
        ),

        "symptoms": (
            screening.symptoms
        ),

        "status": (
            screening.status
        ),

        "screening_date": (
            screening.screening_date
        ),

        "created_at": (
            screening.created_at
        ),

        "image_reference": (
            screening.image_reference
        ),

        "image_filename": (
            screening.image_filename
        ),

        "image_size": (
            screening.image_size
        ),

        "image_width": (
            screening.image_width
        ),

        "image_height": (
            screening.image_height
        ),
    }


# ============================================================
# GET SCREENING RESULT
# ============================================================

@router.get(
    "/{screening_id}/result"
)
def get_screening_result(
    screening_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Find screening
    # --------------------------------------------------------

    screening = db.get(
        Screening,
        screening_id,
    )

    if screening is None:

        raise HTTPException(
            status_code=404,
            detail="Screening not found.",
        )

    # --------------------------------------------------------
    # Find patient
    # --------------------------------------------------------

    patient = db.get(
        Patient,
        screening.patient_id,
    )

    if patient is None:

        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    # --------------------------------------------------------
    # Access control
    # --------------------------------------------------------

    if not can_access(
        user,
        patient,
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this screening."
            ),
        )

    # --------------------------------------------------------
    # Find result
    # --------------------------------------------------------

    result = db.scalar(
        select(
            ScreeningResult
        ).where(
            ScreeningResult.screening_id
            == screening_id
        )
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Screening result "
                "not available yet."
            ),
        )

    # ========================================================
    # AUDIT: RESULT VIEWED
    # ========================================================

    create_audit_log(
        db=db,
        action="RESULT_VIEWED",
        user_id=user.id,
        entity_type="SCREENING_RESULT",
        entity_id=result.id,
        details={
            "screening_id": (
                screening.id
            ),
            "patient_id": (
                screening.patient_id
            ),
        },
    )

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save "
                "audit log."
            ),
        )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "id": result.id,

        "screening_id": (
            result.screening_id
        ),

        "prediction": (
            result.prediction
        ),

        "confidence": (
            result.confidence
        ),

        "risk_level": (
            result.risk_level
        ),

        "risk_engine_version": (
            result.risk_engine_version
        ),

        "risk_reason": (
            result.risk_reason
        ),

        "model_version": (
            result.model_version
        ),

        "gradcam_path": (
            result.gradcam_path
        ),

        "explanation": (
            result.explanation
        ),

        "created_at": (
            result.created_at
        ),
    }
