from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import admin, api, web
from app.seed import init_db
from app.templating import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=f"{settings.app_name} · Plataforma comercial",
    description="Sitio comercial, catálogo técnico, cotizador y asistente virtual.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api.router)
app.include_router(admin.router)
app.include_router(web.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code in (301, 302, 303, 307) and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        return templates.TemplateResponse(request, "404.html", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/salud", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/robots.txt", include_in_schema=False, response_class=HTMLResponse)
def robots() -> str:
    return "User-agent: *\nAllow: /\n"
