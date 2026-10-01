from pathlib import Path
import secrets

import qrcode


# ============================================================
# QR CODE STORAGE DIRECTORY
# ============================================================

QR_DIR = Path("uploads/health_cards")

QR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# GENERATE SECURE HEALTH CARD TOKEN
# ============================================================

def generate_health_card_token() -> str:
    """
    Generate a cryptographically secure opaque token.

    The token does not contain:
    - patient name
    - patient ID
    - disease information
    - medical information
    """

    return secrets.token_urlsafe(48)


# ============================================================
# GENERATE QR CODE
# ============================================================

def generate_qr_code(
    token: str,
    card_id: int,
) -> str:
    """
    Generate a QR image containing only the
    health-card access URL.
    """

    qr_url = (
        f"http://127.0.0.1:8000/"
        f"api/health-card/{token}"
    )

    # --------------------------------------------------------
    # Create QR object
    # --------------------------------------------------------

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    # --------------------------------------------------------
    # Add URL
    # --------------------------------------------------------

    qr.add_data(qr_url)

    qr.make(
        fit=True
    )

    # --------------------------------------------------------
    # Generate image
    # --------------------------------------------------------

    image = qr.make_image()

    # --------------------------------------------------------
    # File name
    # --------------------------------------------------------

    filename = (
        f"health_card_{card_id}.png"
    )

    file_path = QR_DIR / filename

    # --------------------------------------------------------
    # Save QR image
    # --------------------------------------------------------

    image.save(
        file_path
    )

    # --------------------------------------------------------
    # Return relative path
    # --------------------------------------------------------

    return str(file_path)
