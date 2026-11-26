"""Publicación del frontend compilado y configuración de API del mismo origen."""
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "browser"
PAGES = {"", "inicio", "productos", "farmacia", "blog", "contacto", "carrito", "login", "registro", "mis-mascotas", "mis-compras", "mis-pagos", "mi-perfil", "checkout", "compra", "servicios", "no-autorizado", "admin", "reservar-cita", "veterinario", "caja", "users", "encuesta", "verificar-correo", "recuperar-clave"}


def install_frontend(app):
    @app.middleware("http")
    async def frontend_document(request: Request, call_next):
        segment = request.url.path.strip("/").split("/", 1)[0]
        if request.method in {"GET", "HEAD"} and "text/html" in request.headers.get("accept", "") and segment in PAGES:
            index = DIST / "index.html"
            if index.is_file():
                html = index.read_text(encoding="utf-8").replace("<head>", '<head><script>globalThis.__CLINIC_API_URL__="/api";</script>', 1)
                return HTMLResponse(html if request.method == "GET" else "", headers={"Content-Length": str(len(html.encode("utf-8"))), "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
        return await call_next(request)
    if DIST.is_dir():
        app.mount("/", StaticFiles(directory=DIST), name="frontend-assets")
