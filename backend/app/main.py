from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import get_settings
from app.services import audit_service
from app.routers import operations, clinical_operations, messaging, reports
from app.routers import admin, appointments, auth, cashier, catalog, sales, users, purchases

settings = get_settings()
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    description="API del sistema de gestion para clinica veterinaria",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class PublicUploads(StaticFiles):
    async def get_response(self, path, scope):
        if path.replace("\\", "/").split("/")[0] == "clinical":
            from starlette.exceptions import HTTPException
            raise HTTPException(404)
        return await super().get_response(path, scope)


app.mount("/uploads", PublicUploads(directory=UPLOADS_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(cashier.router)
app.include_router(sales.router)
app.include_router(appointments.router)
app.include_router(catalog.router)
app.include_router(purchases.router)
app.include_router(operations.router)
app.include_router(clinical_operations.router)
app.include_router(messaging.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
