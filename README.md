# Remsa Plásticos · Plataforma comercial

Sitio web comercial y herramienta interna de Ventas, Marketing y Administración para
**Recipientes y Empaques de México (REMSA)**: catálogo técnico de envases, fichas de
producto con descarga de especificaciones en PDF, cotizador en línea, captación de
leads, newsletter, chatbot y panel de administración.

Construido con **Python (FastAPI)** y frontend propio en HTML/CSS/JS, sin dependencias
de framework frontend ni servicios externos obligatorios.

---

## 1. Qué incluye

### Sitio público
| Ruta | Descripción |
|---|---|
| `/` | Home comercial: hero, familias de producto, destacados, calculadora de tarimas, proceso, testimonios y CTA |
| `/catalogo` | Catálogo con filtros por familia, material, capacidad, color, búsqueda y orden |
| `/producto/{slug}` | Ficha de producto: capacidades, modelos, colores, descripción, características, aplicaciones, empaque y descarga de PDF |
| `/cotizacion` | Carrito de cotización (varios productos) y formulario de solicitud |
| `/nosotros` | Historia, misión, visión, capacidades y sustentabilidad |
| `/servicios` | Personalización de garrafones, pigmentado, UV, desarrollo de molde y logística |
| `/contacto` | Formulario de contacto, datos de la planta y mapa |

### Herramientas comerciales
- **Cotizador multi-producto** con carrito persistente en el navegador y folio automático (`COT-AAAAMMDD-XXXXX`).
- **Ficha técnica PDF** generada al vuelo por producto (dimensiones, empaque, colores, certificaciones).
- **Chatbot “Remi”**: busca en el catálogo real y responde FAQ (pedido mínimo, entregas, ubicación, personalización, certificaciones). Funciona sin ninguna API externa; si defines `OPENAI_API_KEY` usa un LLM y cae de vuelta al motor local si falla.
- **Captación de leads**: contacto, newsletter y cotizaciones, todos almacenados en base de datos.

### Panel interno (`/admin`)
- Resumen con KPIs (cotizaciones, mensajes, suscriptores, sesiones de chat, catálogo).
- Gestión de cotizaciones con cambio de estatus (nueva → en proceso → cotizada → ganada/perdida).
- Bandeja de mensajes de contacto y lista de suscriptores.
- Control de visibilidad de productos.
- Transcripciones de las conversaciones del chatbot.

### API pública (documentada en `/docs`)
```
GET  /api/categorias
GET  /api/productos?categoria=&material=&q=&color=&capacidad_min=&capacidad_max=&orden=
GET  /api/productos/{slug}
GET  /api/productos/{slug}/ficha-tecnica.pdf
GET  /api/buscar?q=
POST /api/cotizaciones
POST /api/contacto
POST /api/suscripciones
POST /api/chat
```

---

## 2. Requisitos

- Python 3.10 o superior
- pip
- (Opcional) PostgreSQL si no quieres usar SQLite

---

## 3. Instalación

```bash
# 1. Clonar el proyecto
git clone <url-del-repositorio> remsa-plataforma
cd remsa-plataforma

# 2. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env               # Windows: copy .env.example .env
#    Edita .env y cambia SECRET_KEY y ADMIN_PASSWORD

# 5. (Opcional) Regenerar las imágenes SVG del catálogo
python scripts/make_assets.py

# 6. Arrancar el servidor
uvicorn app.main:app --reload
```

Abre <http://127.0.0.1:8000>.

La primera vez que arranca, la aplicación **crea la base de datos SQLite (`remsa.db`),
carga el catálogo semilla** (7 familias, 13 productos, sus modelos y colores) y **crea
el usuario administrador**. No hay que ejecutar migraciones.

### Acceso al panel

| Campo | Valor por defecto |
|---|---|
| URL | <http://127.0.0.1:8000/admin> |
| Usuario | `admin@remsa.com.mx` |
| Contraseña | `admin123` |

> Cambia `ADMIN_EMAIL` y `ADMIN_PASSWORD` en `.env` **antes** del primer arranque (o borra
> `remsa.db` y vuelve a arrancar para recrear el usuario).

### Ejecutar desde Visual Studio Code

1. Abre la carpeta del proyecto (`Archivo → Abrir carpeta…`).
2. Instala las extensiones recomendadas que sugiere VS Code al abrir el proyecto:
   **Python**, **Pylance** y **Ruff**.
3. Crea el entorno virtual (`python -m venv .venv`) y selecciónalo con
   `Ctrl+Shift+P → Python: Select Interpreter → .venv`.
4. Instala dependencias y copia `.env` como en los pasos 3 y 4 de arriba, usando la
   terminal integrada (`Ctrl+ñ` / `Ctrl+``).
5. Pulsa `F5` y elige **Remsa: uvicorn (reload)** para arrancar con depurador y recarga
   automática, o ejecuta `uvicorn app.main:app --reload` en la terminal.

Los puntos de interrupción funcionan en los routers de `app/routers/` y en las plantillas
Jinja2 (`jinja: true` ya está activado en `.vscode/launch.json`).

---

## 4. Configuración (`.env`)

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `APP_NAME` | Remsa Plásticos | Nombre mostrado en el sitio |
| `DATABASE_URL` | `sqlite:///./remsa.db` | Conexión a la base de datos |
| `SECRET_KEY` | `cambia-esta-llave-en-produccion` | Firma de las cookies de sesión del panel |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@remsa.com.mx` / `admin123` | Credenciales del panel |
| `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_WHATSAPP`, `COMPANY_ADDRESS` | datos de Mérida | Datos de contacto del sitio |
| `OPENAI_API_KEY` | vacío | Opcional: activa el chatbot con LLM |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo usado cuando hay llave |

### Usar PostgreSQL

```bash
pip install "psycopg[binary]"
# en .env
DATABASE_URL=postgresql+psycopg://usuario:password@localhost:5432/remsa
```

---

## 5. Administrar el catálogo

El catálogo inicial vive en `app/seed.py`. Para agregar o modificar productos:

1. Edita la lista `PRODUCTS` en `app/seed.py` (nombre, material, descripción, características,
   aplicaciones, empaque, colores y la lista de `variants` con modelo, capacidad, peso,
   altura, diámetro, boca, piezas por caja y cajas por tarima).
2. Recarga el catálogo:

```bash
python -c "from app.seed import reseed; reseed()"
```

> `reseed()` reemplaza el catálogo sembrado. Las cotizaciones, mensajes y suscriptores no se tocan.

Desde `/admin/productos` puedes ocultar o publicar productos sin tocar código.

---

## 6. Estructura del proyecto

```
app/
├── main.py            # Aplicación FastAPI, middleware, manejo de errores
├── config.py          # Configuración vía .env (pydantic-settings)
├── database.py        # Engine, sesión y Base de SQLAlchemy
├── models.py          # Category, Product, ProductVariant, Color, Quote, ContactMessage…
├── schemas.py         # Esquemas Pydantic de entrada/salida
├── seed.py            # Catálogo semilla + creación de la base
├── security.py        # Hash de contraseñas (PBKDF2-SHA256)
├── pdf.py             # Generación de la ficha técnica con ReportLab
├── chatbot.py         # Motor local de intenciones + integración LLM opcional
├── templating.py      # Configuración de Jinja2
├── routers/
│   ├── web.py         # Páginas públicas
│   ├── api.py         # API JSON y PDF
│   └── admin.py       # Panel interno
├── templates/         # Plantillas Jinja2 (incluye admin/ y partials/)
└── static/
    ├── css/styles.css
    ├── js/main.js     # Carrito, filtros, formularios, buscador
    ├── js/chatbot.js  # Widget del asistente
    └── img/           # SVG generados
scripts/make_assets.py # Genera logotipos e imágenes de categoría
```

---

## 7. Despliegue en producción

```bash
pip install gunicorn
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

Recomendaciones:
- Define `SECRET_KEY` y `ADMIN_PASSWORD` con valores fuertes.
- Sirve detrás de Nginx/Caddy con HTTPS.
- Usa PostgreSQL y respaldos si esperas volumen de cotizaciones.
- Sirve `app/static/` directamente desde el servidor web para mejor rendimiento.

Ejemplo con Docker:

```dockerfile
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 8. Verificación rápida

```bash
curl localhost:8000/salud
curl localhost:8000/api/productos | head -c 300
curl -X POST localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"Necesito garrafones de 20 litros"}'
curl -o ficha.pdf localhost:8000/api/productos/botella-pet-agua-purificada/ficha-tecnica.pdf
```

---

## 9. Notas

- El contenido del catálogo (productos, medidas, empaque) es una **carga inicial de ejemplo
  basada en las familias que Remsa comercializa**; debe validarse con las especificaciones
  reales de planta antes de publicar.
- Las imágenes son SVG generados localmente; sustitúyelas por fotografía de producto
  colocando los archivos en `app/static/img/` y actualizando el campo `image` de cada producto.
