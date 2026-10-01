from fastapi import FastAPI

from app.routers import patients
from app.routers import screenings
from app.routers.auth import router as auth_router
from app.routers import audit_logs
from app.routers import followups
from app.routers import dashboard
from app.routers import health_card


app = FastAPI(
    title="SwasthyaAI Backend",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "SwasthyaAI Backend is running"
    }


# ============================================================
# AUTHENTICATION
# ============================================================

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)


# ============================================================
# PATIENTS
# ============================================================

app.include_router(
    patients.router,
    prefix="/api/patients",
    tags=["Patients"]
)


# ============================================================
# SCREENINGS
# ============================================================

app.include_router(
    screenings.router,
    prefix="/api/screenings",
    tags=["Screenings"]
)


# ============================================================
# AUDIT LOGS
# ============================================================

app.include_router(
    audit_logs.router,
    prefix="/api/audit-logs",
    tags=["Audit Logs"]
)


# ============================================================
# FOLLOW-UPS
# ============================================================

app.include_router(
    followups.router,
    prefix="/api/followups",
    tags=["Follow-ups"]
)


# ============================================================
# DASHBOARDS
# ============================================================

app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


# ============================================================
# HEALTH CARD - CREATE
# ============================================================

app.include_router(
    health_card.router,
    prefix="/api/healthcard",
    tags=["Health Card"]
)


# ============================================================
# HEALTH CARD - ACCESS USING QR TOKEN
# ============================================================

app.include_router(
    health_card.health_card_access_router,
    prefix="/api/health-card",
    tags=["Health Card"]
)
