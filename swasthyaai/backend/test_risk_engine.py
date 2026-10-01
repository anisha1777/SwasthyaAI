from app.services.risk_engine import calculate_risk


def test_jaundice_risk():
    result = calculate_risk(
        screening_type="JAUNDICE",
        prediction="Jaundice",
        confidence=0.9852,
    )

    assert result.risk_level == "HIGH"
    assert result.engine_version == "risk-v1"
