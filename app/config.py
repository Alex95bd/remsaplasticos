from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la plataforma. Se puede sobreescribir con un archivo .env"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Remsa Plásticos"
    app_tagline: str = "Envases de PET, PEAD y PVC para la industria"
    database_url: str = "sqlite:///./remsa.db"
    secret_key: str = "cambia-esta-llave-en-produccion"

    admin_email: str = "admin@remsa.com.mx"
    admin_password: str = "admin123"

    company_phone: str = "(999) 941 0145"
    company_phone_alt: str = "(999) 941 0147"
    company_email: str = "contacto@remsa.com.mx"
    company_whatsapp: str = "529999410145"
    company_address: str = (
        "Calle 60 Diagonal, Parque Industrial Yucatán (Parque de Industrias No "
        "Contaminantes Norte), C.P. 97300, Mérida, Yucatán, México"
    )

    # Chatbot: si se define una API key se usa un LLM, si no se usa el motor local.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
