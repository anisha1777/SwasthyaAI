from dataclasses import dataclass


# ============================================================
# RISK ENGINE CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class RiskEngineConfig:
    """
    Immutable configuration for one version of the
    software risk engine.

    These thresholds are prototype software rules.
    They are NOT clinical diagnostic thresholds.
    """

    version: str
    high_confidence_threshold: float
    moderate_confidence_threshold: float


# ============================================================
# RISK ENGINE V1
# ============================================================

RISK_ENGINE_V1 = RiskEngineConfig(
    version="risk-v1",
    high_confidence_threshold=0.80,
    moderate_confidence_threshold=0.60,
)


# Current active risk-engine configuration
ACTIVE_RISK_ENGINE = RISK_ENGINE_V1

# Backward-compatible constant
RISK_ENGINE_VERSION = ACTIVE_RISK_ENGINE.version


# ============================================================
# RISK DECISION
# ============================================================

@dataclass
class RiskDecision:
    """
    Final decision produced by the risk engine.
    """

    risk_level: str
    reason: str
    engine_version: str


# ============================================================
# HELPER — CONFIDENCE BASED RISK
# ============================================================

def _confidence_risk(
    prediction: str,
    confidence: float,
    config: RiskEngineConfig,
    model_name: str,
) -> RiskDecision:
    """
    Apply the configured confidence thresholds.

    This function does not claim that these thresholds
    represent clinical diagnosis.
    """

    if confidence >= config.high_confidence_threshold:

        return RiskDecision(
            risk_level="HIGH",
            reason=(
                f"{model_name} predicted {prediction} "
                f"with confidence {confidence:.4f}."
            ),
            engine_version=config.version,
        )

    if confidence >= config.moderate_confidence_threshold:

        return RiskDecision(
            risk_level="MODERATE",
            reason=(
                f"{model_name} predicted {prediction} "
                f"with confidence {confidence:.4f}."
            ),
            engine_version=config.version,
        )

    return RiskDecision(
        risk_level="LOW",
        reason=(
            f"{model_name} prediction confidence was "
            f"below the moderate-risk threshold: "
            f"{confidence:.4f}."
        ),
        engine_version=config.version,
    )


# ============================================================
# MAIN RISK ENGINE
# ============================================================

def calculate_risk(
    screening_type: str,
    prediction: str,
    confidence: float,
) -> RiskDecision:
    """
    Calculate software risk level from ML prediction.

    IMPORTANT:
    These are prototype software rules.
    They are not clinical diagnostic thresholds and must
    be clinically validated before real-world medical use.
    """

    screening_type = (
        screening_type.strip().upper()
    )

    prediction = prediction.strip()

    # --------------------------------------------------------
    # Validate confidence
    # --------------------------------------------------------

    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            "Confidence must be between 0.0 and 1.0."
        )

    config = ACTIVE_RISK_ENGINE

    # ========================================================
    # JAUNDICE
    # ========================================================

    if screening_type == "JAUNDICE":

        # Normal eye is explicitly LOW.
        if prediction == "Normal_Eye":

            return RiskDecision(
                risk_level="LOW",
                reason=(
                    "Model prediction is Normal_Eye."
                ),
                engine_version=config.version,
            )

        return _confidence_risk(
            prediction=prediction,
            confidence=confidence,
            config=config,
            model_name="Model",
        )

    # ========================================================
    # SKIN
    # ========================================================

    if screening_type == "SKIN":

        return _confidence_risk(
            prediction=prediction,
            confidence=confidence,
            config=config,
            model_name="Skin model",
        )

    # ========================================================
    # ANEMIA
    # ========================================================

    if screening_type == "ANEMIA":

        return RiskDecision(
            risk_level="LOW",
            reason=(
                "Anemia risk rules are not yet "
                "clinically configured."
            ),
            engine_version=config.version,
        )

    # ========================================================
    # UNSUPPORTED TYPE
    # ========================================================

    raise ValueError(
        f"Unsupported screening type: {screening_type}"
    )
