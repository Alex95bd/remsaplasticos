from fastapi.templating import Jinja2Templates

from app.config import settings

templates = Jinja2Templates(directory="app/templates")
templates.env.globals.update(
    settings=settings,
    company={
        "name": settings.app_name,
        "tagline": settings.app_tagline,
        "phone": settings.company_phone,
        "phone_alt": settings.company_phone_alt,
        "email": settings.company_email,
        "whatsapp": settings.company_whatsapp,
        "address": settings.company_address,
    },
)
