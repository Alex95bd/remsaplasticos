# REMSA Gestión Comercial

Aplicación web interna de Recipientes y Empaques de México S.A. de C.V. (REMSA) para la gestión
comercial: catálogo, clientes, cotizaciones, inventarios, listas de precios y agenda.
Vive en la carpeta `gestion/` y es independiente del sitio público FastAPI de la raíz del repositorio.

**Estado: Fase 1** — estructura, autenticación, roles y permisos, diseño general, catálogo de
productos (con importación/exportación Excel) y bitácora de auditoría.
Clientes, cotizaciones, inventarios, listas de precios, agenda e integración con Intelisis
se agregarán en las fases siguientes.

Stack: Python 3.12 · Django 5.2 · Django REST Framework · Bootstrap 5 + Bootstrap Icons (servidos
localmente) · SQLite (desarrollo) / PostgreSQL (producción) · openpyxl · WhiteNoise · Gunicorn.

## Instalación en Windows (PowerShell)

Requisitos: Python 3.12 y Git.

```powershell
git clone https://github.com/Alex95bd/remsaplasticos.git
cd remsaplasticos\gestion

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
# Si PowerShell bloquea el script: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

pip install -r requirements-dev.txt

Copy-Item .env.example .env
# Genera una llave y pégala en DJANGO_SECRET_KEY dentro de .env:
python -c "import secrets; print(secrets.token_urlsafe(50))"

python manage.py migrate          # crea tablas, unidades base y roles
python manage.py createsuperuser  # primer usuario (soporte técnico)
python manage.py runserver
```

Abre http://127.0.0.1:8000 e inicia sesión. Desde **Usuarios** crea las cuentas del personal y
asígnales un rol (ver [docs/ROLES.md](docs/ROLES.md)).

En Linux/macOS los pasos son iguales cambiando la activación por `source .venv/bin/activate`
y `Copy-Item` por `cp`.

### Datos de demostración (opcional)

```powershell
python manage.py cargar_demo                                   # categorías y productos [DEMO]
python manage.py cargar_demo --usuarios --password "Clave-Segura-123"  # + demo.admin, demo.ventas, demo.almacen, demo.consulta
```

Todo lo que crea este comando está marcado con `[DEMO]` / `DEMO-` para distinguirlo de datos reales.
No lo uses en producción.

## Módulos de la Fase 1

| Ruta | Descripción |
|---|---|
| `/entrar/` | Inicio de sesión (recuperación de contraseña por correo en `/cuentas/recuperar/`) |
| `/` | Panel con indicadores calculados desde la base de datos y actividad reciente |
| `/catalogo/productos/` | Búsqueda por nombre, SKU, descripción o código externo; filtros por categoría, tipo y estado; alta/edición/activación; historial de cambios |
| `/catalogo/productos/importar/` | Importación Excel con plantilla, validación y **vista previa obligatoria** antes de guardar |
| `/catalogo/productos/exportar/` | Exportación a Excel respetando filtros (sin precios si el rol no puede verlos) |
| `/catalogo/categorias/`, `/catalogo/unidades/` | Catálogos auxiliares |
| `/cuentas/usuarios/` | Administración de usuarios, roles, activación y restablecimiento de contraseña |
| `/bitacora/` | Bitácora de auditoría (solo inserción) con filtros |
| `/api/v1/` | API REST (sesión + permisos por modelo). Productos no se pueden eliminar |
| `/salud/` | Verificación de salud para monitoreo (sin datos sensibles) |
| `/django-admin/` | Panel técnico de Django, solo superusuarios (configurable con `DJANGO_ADMIN_URL`) |

## Configuración

Todas las opciones se leen de variables de entorno o del archivo `.env` (ver `.env.example`).
Con `DJANGO_DEBUG=False` la aplicación exige `DJANGO_SECRET_KEY`.

Para producción detrás de HTTPS:

```
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=gestion.ejemplo.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://gestion.ejemplo.com
DJANGO_SECURE_COOKIES=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_BEHIND_PROXY=True   # si un proxy (nginx, etc.) termina TLS
DB_ENGINE=postgres
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

Verifica la configuración con `python manage.py check --deploy`.

## Docker (PostgreSQL)

```bash
cp .env.example .env    # define DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_DEBUG=False, hosts...
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

El contenedor aplica migraciones al iniciar y sirve la app con Gunicorn en el puerto 8000;
los estáticos se sirven con WhiteNoise. Coloca un proxy HTTPS delante en producción.

## Pruebas y calidad

```powershell
python manage.py test
ruff check .
ruff format --check .
```

## Estructura

```
gestion/
├── config/      # settings (por entorno), urls, API router
├── core/        # panel, mixins de permisos/auditoría, formularios Bootstrap, utilidades
├── accounts/    # usuario personalizado, roles, usuarios, perfil, recuperación de contraseña
├── catalog/     # categorías, unidades, productos, importación/exportación Excel, API
├── audit/       # bitácora de auditoría de solo inserción
├── templates/   # plantillas Django (Bootstrap 5)
├── static/      # CSS/JS propios y Bootstrap/Bootstrap Icons locales
└── docs/        # ROLES.md, RESPALDOS.md
```

## Seguridad

- Autenticación de Django, contraseñas con hash y validadores de fortaleza.
- Permisos validados en el servidor (vistas y API); respuestas 403 si no hay permiso.
- CSRF en todos los formularios; cierre de sesión solo por POST; plantillas con autoescape.
- Consultas exclusivamente vía ORM; operaciones críticas en transacciones.
- La bitácora no registra contraseñas ni se puede editar o borrar desde la aplicación.
- Secretos solo en variables de entorno; `.env` está excluido de Git.

Respaldos: ver [docs/RESPALDOS.md](docs/RESPALDOS.md).

## Integración con Intelisis

No está conectada. Productos tienen el campo **Código externo (Intelisis)** para relacionarlos
en el futuro. La integración se diseñará cuando se cuente con la documentación y autorización
correspondientes.
