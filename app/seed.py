"""Carga inicial del catálogo comercial (categorías, productos, tipos y colores)."""

from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import AdminUser, Category, Color, Product, ProductVariant
from app.security import hash_password

COLORS = [
    ("Cristal / Natural", "#e8f4fb"),
    ("Blanco", "#f7f7f5"),
    ("Azul", "#1d6fd0"),
    ("Azul cielo", "#63b3ed"),
    ("Verde", "#2f9e5f"),
    ("Verde esmeralda", "#0f7b5f"),
    ("Ámbar", "#b4762a"),
    ("Negro", "#22252b"),
    ("Rojo", "#d0342c"),
    ("Amarillo", "#f3c218"),
    ("Naranja", "#ef7f1a"),
    ("Gris", "#8b9099"),
]

CATEGORIES = [
    {
        "slug": "botellas-pet",
        "name": "Botellas PET",
        "icon": "bottle",
        "tagline": "Agua purificada, refrescos, jugos y bebidas saborizadas",
        "description": (
            "Botellas de PET grado alimenticio con alta transparencia y excelente barrera. "
            "Disponibles en líneas para agua purificada, bebidas carbonatadas, jugos y lácteos, "
            "con boca estándar de 28 mm y opciones personalizadas."
        ),
    },
    {
        "slug": "frascos-pet",
        "name": "Frascos PET",
        "icon": "jar",
        "tagline": "Alimentos, salsas, cosméticos y productos de cuidado personal",
        "description": (
            "Frascos de boca ancha y angosta, ideales para miel, salsas, conservas, cremas, "
            "shampoo y productos de limpieza. Compatibles con tapas de rosca continua y sellos de inducción."
        ),
    },
    {
        "slug": "garrafas-pead",
        "name": "Garrafas PEAD",
        "icon": "jug",
        "tagline": "Químicos, agroquímicos, aceites y limpieza industrial",
        "description": (
            "Garrafas de polietileno de alta densidad con asa integrada, alta resistencia al impacto "
            "y compatibilidad con productos químicos. Pigmentado a color y protección UV bajo pedido."
        ),
    },
    {
        "slug": "garrafas-pet",
        "name": "Garrafas PET",
        "icon": "jug",
        "tagline": "Presentaciones familiares con alta transparencia",
        "description": (
            "Garrafas de PET con asa ergonómica para agua, vinagre, jarabes y bebidas de alto consumo. "
            "Combinan la ligereza del PET con la practicidad del asa integrada."
        ),
    },
    {
        "slug": "garrafones-y-botellones",
        "name": "Garrafones y Botellones",
        "icon": "carboy",
        "tagline": "Retornables y de un solo uso para agua purificada",
        "description": (
            "Garrafones de 10, 11 y 20 litros en PET y policarbonato, con boca roscada de 48 y 56 mm. "
            "Personalización con insertos en alto relieve y variación de color en cuerpo y asa."
        ),
    },
    {
        "slug": "tapas",
        "name": "Tapas y Cierres",
        "icon": "cap",
        "tagline": "Rosca continua, tapas deportivas y cierres de seguridad",
        "description": (
            "Tapas de polipropileno y polietileno con banda de seguridad, liner de sellado y "
            "acabados para llenado manual o automático. Amplia gama de colores."
        ),
    },
    {
        "slug": "preformas",
        "name": "Preformas PET",
        "icon": "preform",
        "tagline": "Insumo para soplado en planta del cliente",
        "description": (
            "Preformas de PET en distintos gramajes y bocas, listas para soplado. "
            "Ideales para embotelladores que producen su propio envase."
        ),
    },
]

PRODUCTS = [
    {
        "category": "botellas-pet",
        "slug": "botella-pet-agua-purificada",
        "name": "Botella PET Línea Agua Purificada",
        "line": "Agua purificada",
        "material": "PET",
        "featured": True,
        "summary": "Botella ligera de alta transparencia para agua purificada, con boca 28 mm PCO y rosca corta.",
        "description": (
            "Envase de PET grado alimenticio diseñado para agua purificada y mineralizada. Su perfil de "
            "paneles reforzados permite reducir gramaje sin perder rigidez en estiba, y su alta "
            "transparencia resalta la pureza del producto. Compatible con llenado en frío en líneas "
            "automáticas de alta velocidad."
        ),
        "features": (
            "Resina PET virgen grado alimenticio (FDA)\n"
            "Alta transparencia y brillo superficial\n"
            "Paneles de refuerzo para estiba de hasta 4 camas\n"
            "Boca 28 mm PCO 1810 estándar del mercado\n"
            "Base petaloide en presentaciones con gas\n"
            "Opción de aligeramiento (light weight) para reducir costo por pieza"
        ),
        "applications": "Agua purificada\nAgua mineralizada\nBebidas saborizadas sin gas\nTé y bebidas frías",
        "packaging": (
            "Empaque en caja de cartón corrugado o bolsa de polietileno\n"
            "Tarima de madera de 1.00 x 1.20 m con esquineros\n"
            "Emplayado con film estirable y fleje perimetral\n"
            "Producto entregado libre de humedad y polvo"
        ),
        "neck_finish": "28 mm PCO 1810 / 28 mm rosca corta",
        "colors": ["Cristal / Natural", "Azul cielo", "Verde", "Ámbar"],
        "variants": [
            ("BPET-250", 250, 12.0, 152, 55, "28 mm PCO", 300, 12),
            ("BPET-500", 500, 17.5, 205, 63, "28 mm PCO", 240, 10),
            ("BPET-600", 600, 19.0, 218, 65, "28 mm PCO", 200, 10),
            ("BPET-1000", 1000, 26.0, 268, 80, "28 mm PCO", 120, 8),
            ("BPET-1500", 1500, 33.0, 310, 88, "28 mm PCO", 90, 8),
        ],
    },
    {
        "category": "botellas-pet",
        "slug": "botella-pet-carbonatada",
        "name": "Botella PET Bebidas Carbonatadas",
        "line": "Carbonatadas",
        "material": "PET",
        "featured": True,
        "summary": "Botella con base petaloide para refrescos y bebidas con gas hasta 4.2 volúmenes de CO₂.",
        "description": (
            "Diseñada para soportar la presión interna de bebidas carbonatadas. La base petaloide de cinco "
            "pies distribuye la presión y evita deformaciones, mientras que el cuerpo con distribución de "
            "material optimizada mantiene la estabilidad dimensional durante toda la vida de anaquel."
        ),
        "features": (
            "Base petaloide de 5 pies para alta presión\n"
            "Resistencia hasta 4.2 volúmenes de CO₂\n"
            "Cuello reforzado antiovalamiento\n"
            "Compatible con llenado isobárico\n"
            "Distribución de material optimizada por simulación\n"
            "Superficie apta para etiqueta wrap-around o manga termoencogible"
        ),
        "applications": "Refrescos\nAgua mineral con gas\nBebidas energizantes\nCervezas artesanales",
        "packaging": (
            "Bolsa de polietileno por camada\n"
            "Tarima estándar 1.00 x 1.20 m\n"
            "Separadores de cartón entre camas\n"
            "Etiquetado de lote y fecha de fabricación por tarima"
        ),
        "neck_finish": "28 mm PCO 1881",
        "colors": ["Cristal / Natural", "Verde esmeralda", "Ámbar"],
        "variants": [
            ("BPET-C355", 355, 20.0, 168, 62, "28 mm PCO 1881", 280, 12),
            ("BPET-C600", 600, 24.0, 225, 66, "28 mm PCO 1881", 200, 10),
            ("BPET-C1250", 1250, 34.0, 295, 86, "28 mm PCO 1881", 100, 8),
            ("BPET-C2000", 2000, 44.0, 325, 96, "28 mm PCO 1881", 72, 8),
            ("BPET-C3000", 3000, 58.0, 360, 108, "28 mm PCO 1881", 48, 6),
        ],
    },
    {
        "category": "botellas-pet",
        "slug": "botella-pet-jugos-lacteos",
        "name": "Botella PET Jugos y Lácteos",
        "line": "Jugos y lácteos",
        "material": "PET",
        "summary": "Envase de boca ancha 38 mm para llenado en caliente de jugos, néctares y bebidas lácteas.",
        "description": (
            "Botella con anillo de soporte y paneles de vacío para procesos hot-fill hasta 85 °C. "
            "La boca ancha de 38 mm facilita el llenado con pulpa y el consumo directo del producto."
        ),
        "features": (
            "Apta para llenado en caliente (hot-fill) hasta 85 °C\n"
            "Paneles de absorción de vacío\n"
            "Boca ancha 38 mm para producto con pulpa\n"
            "Opción de barrera UV para proteger vitaminas\n"
            "Compatible con sello de inducción"
        ),
        "applications": "Jugos y néctares\nBebidas lácteas\nSmoothies\nTé helado",
        "packaging": (
            "Caja de cartón corrugado con divisiones\n"
            "Tarima 1.00 x 1.20 m con film estirable\n"
            "Máximo 4 camas por tarima"
        ),
        "neck_finish": "38 mm rosca continua",
        "colors": ["Cristal / Natural", "Blanco", "Ámbar"],
        "variants": [
            ("BPET-J250", 250, 16.0, 140, 60, "38 mm RC", 240, 12),
            ("BPET-J500", 500, 24.0, 190, 72, "38 mm RC", 160, 10),
            ("BPET-J1000", 1000, 38.0, 240, 90, "38 mm RC", 96, 8),
        ],
    },
    {
        "category": "frascos-pet",
        "slug": "frasco-pet-boca-ancha",
        "name": "Frasco PET Boca Ancha",
        "line": "Alimentos",
        "material": "PET",
        "featured": True,
        "summary": "Frasco cilíndrico de boca ancha para miel, conservas, botanas y productos secos.",
        "description": (
            "Frasco de PET con boca ancha de 63 a 89 mm que facilita el llenado y la extracción del "
            "producto. Sustituye al vidrio con una reducción de peso superior al 80 % y sin riesgo de rotura."
        ),
        "features": (
            "Boca ancha de 63, 70 y 89 mm\n"
            "Apto para sello de inducción y tapa de rosca continua\n"
            "Alternativa ligera e irrompible al vidrio\n"
            "Paredes uniformes para etiquetado a 360°\n"
            "Apilable en estiba sin deformación"
        ),
        "applications": "Miel y jarabes\nBotanas y granola\nSalsas y conservas\nSuplementos en polvo",
        "packaging": (
            "Caja de cartón corrugado de 25 a 100 piezas\n"
            "Tarima de 1.00 x 1.20 m\n"
            "Bolsa interior de polietileno por caja"
        ),
        "neck_finish": "63 / 70 / 89 mm rosca continua",
        "colors": ["Cristal / Natural", "Blanco", "Ámbar", "Negro"],
        "variants": [
            ("FPET-A250", 250, 18.0, 95, 70, "63 mm RC", 120, 20),
            ("FPET-A500", 500, 28.0, 130, 85, "70 mm RC", 80, 16),
            ("FPET-A1000", 1000, 45.0, 165, 100, "89 mm RC", 48, 14),
            ("FPET-A2000", 2000, 78.0, 215, 125, "89 mm RC", 24, 12),
        ],
    },
    {
        "category": "frascos-pet",
        "slug": "frasco-pet-cosmetico",
        "name": "Frasco PET Línea Cosmética",
        "line": "Cuidado personal",
        "material": "PET",
        "summary": "Frascos cilíndricos y ovalados para shampoo, cremas, geles y productos de cuidado personal.",
        "description": (
            "Línea de frascos con acabado brillante o mate, compatibles con válvulas dosificadoras, "
            "atomizadores y tapas flip-top. Permiten pigmentado a color y efecto perlado."
        ),
        "features": (
            "Compatible con dosificador, atomizador y flip-top\n"
            "Acabado brillante, mate o perlado\n"
            "Pigmentado a color Pantone bajo pedido\n"
            "Superficie apta para serigrafía y etiqueta autoadherible\n"
            "Resistente a tensoactivos y alcoholes"
        ),
        "applications": "Shampoo y acondicionador\nGeles y cremas\nLoción y tónicos\nGel antibacterial",
        "packaging": (
            "Caja de cartón con separadores de cartoncillo\n"
            "50 a 200 piezas por caja según capacidad\n"
            "Tarima emplayada con esquineros"
        ),
        "neck_finish": "24 / 28 / 38 mm rosca continua",
        "colors": ["Cristal / Natural", "Blanco", "Negro", "Ámbar", "Azul"],
        "variants": [
            ("FPET-C120", 120, 12.0, 110, 45, "24 mm RC", 200, 20),
            ("FPET-C250", 250, 18.0, 145, 55, "28 mm RC", 150, 18),
            ("FPET-C500", 500, 30.0, 185, 68, "28 mm RC", 100, 16),
            ("FPET-C1000", 1000, 48.0, 225, 85, "38 mm RC", 60, 12),
        ],
    },
    {
        "category": "garrafas-pead",
        "slug": "garrafa-pead-industrial",
        "name": "Garrafa PEAD Industrial",
        "line": "Química e industrial",
        "material": "PEAD",
        "featured": True,
        "summary": "Garrafa de polietileno de alta densidad con asa integrada para productos químicos y de limpieza.",
        "description": (
            "Garrafa soplada en PEAD de alto peso molecular, con excelente resistencia al impacto y a la "
            "fisuración por esfuerzo ambiental (ESCR). Su asa integrada facilita el manejo y vertido, y su "
            "boca roscada acepta tapas con liner químico."
        ),
        "features": (
            "Resina PEAD de alto peso molecular con alto ESCR\n"
            "Asa integrada ergonómica\n"
            "Compatible con ácidos y álcalis diluidos, cloro y detergentes\n"
            "Opción de protección UV y pigmentado a color\n"
            "Boca roscada de 38, 48 y 63 mm\n"
            "Superficie apta para etiqueta y codificado láser"
        ),
        "applications": "Cloro y sanitizantes\nDetergentes industriales\nAgroquímicos\nAceites y lubricantes",
        "packaging": (
            "Empaque a granel en bolsa de polietileno\n"
            "Tarima de 1.00 x 1.20 m con esquineros y fleje\n"
            "Separadores de cartón entre camas\n"
            "Tapas empacadas por separado en bolsa de 500 piezas"
        ),
        "neck_finish": "38 / 48 / 63 mm rosca continua",
        "colors": ["Blanco", "Cristal / Natural", "Azul", "Negro", "Amarillo", "Rojo"],
        "variants": [
            ("GPEAD-1L", 1000, 60.0, 230, 95, "38 mm RC", 60, 10),
            ("GPEAD-4L", 4000, 160.0, 300, 160, "48 mm RC", 24, 8),
            ("GPEAD-10L", 10000, 380.0, 400, 215, "63 mm RC", 12, 6),
            ("GPEAD-20L", 20000, 750.0, 480, 290, "63 mm RC", 6, 4),
        ],
    },
    {
        "category": "garrafas-pead",
        "slug": "garrafa-pead-alimenticia",
        "name": "Garrafa PEAD Grado Alimenticio",
        "line": "Alimentos y bebidas",
        "material": "PEAD",
        "summary": "Garrafa natural translúcida para agua, lácteos, vinagre y aceites comestibles.",
        "description": (
            "Fabricada con resina PEAD grado alimenticio, permite visualizar el nivel de producto y "
            "mantiene la inocuidad durante el almacenamiento. Disponible con asa integrada y boca ancha."
        ),
        "features": (
            "Resina PEAD grado alimenticio\n"
            "Cuerpo translúcido para control de nivel\n"
            "Asa integrada de alta resistencia\n"
            "Apta para refrigeración\n"
            "Compatible con sello de inducción"
        ),
        "applications": "Agua purificada\nLeche y bebidas lácteas\nVinagre\nAceite comestible",
        "packaging": (
            "Bolsa de polietileno por camada\n"
            "Tarima 1.00 x 1.20 m emplayada\n"
            "Hasta 4 camas por tarima"
        ),
        "neck_finish": "38 / 48 mm rosca continua",
        "colors": ["Cristal / Natural", "Blanco", "Azul cielo"],
        "variants": [
            ("GPEAD-A1L", 1000, 45.0, 225, 92, "38 mm RC", 60, 10),
            ("GPEAD-A2L", 2000, 75.0, 265, 120, "38 mm RC", 40, 8),
            ("GPEAD-A4L", 4000, 140.0, 300, 158, "48 mm RC", 24, 8),
        ],
    },
    {
        "category": "garrafas-pet",
        "slug": "garrafa-pet-con-asa",
        "name": "Garrafa PET con Asa",
        "line": "Presentación familiar",
        "material": "PET",
        "summary": "Garrafa transparente con asa integrada para presentaciones familiares de 3 a 6 litros.",
        "description": (
            "Combina la transparencia del PET con el asa integrada del soplado por extrusión. Ideal para "
            "presentaciones familiares de agua purificada, vinagre y bebidas de alto consumo."
        ),
        "features": (
            "Alta transparencia tipo cristal\n"
            "Asa integrada ergonómica\n"
            "Paneles antivacío para llenado en caliente moderado\n"
            "Base estable para estiba\n"
            "Boca roscada 38 y 48 mm"
        ),
        "applications": "Agua purificada familiar\nVinagre\nJarabes\nBebidas de alto consumo",
        "packaging": (
            "Empaque a granel con separadores\n"
            "Tarima 1.00 x 1.20 m\n"
            "Film estirable y fleje perimetral"
        ),
        "neck_finish": "38 / 48 mm rosca continua",
        "colors": ["Cristal / Natural", "Azul cielo", "Verde"],
        "variants": [
            ("GPET-3L", 3000, 68.0, 300, 150, "38 mm RC", 24, 8),
            ("GPET-4L", 4000, 85.0, 330, 165, "48 mm RC", 20, 8),
            ("GPET-6L", 6000, 120.0, 380, 195, "48 mm RC", 12, 6),
        ],
    },
    {
        "category": "garrafones-y-botellones",
        "slug": "garrafon-pet-20l",
        "name": "Garrafón PET 20 L Personalizable",
        "line": "Agua purificada",
        "material": "PET",
        "featured": True,
        "summary": (
            "Garrafón retornable de 20 litros con asa y boca roscada de 56 mm, "
            "personalizable con insertos en alto relieve."
        ),
        "description": (
            "Garrafón de PET para agua purificada con asa integrada y boca roscada de 56 mm. La "
            "personalización se realiza mediante dos insertos con el grabado de su marca en alto relieve, "
            "además de variación de color en cuerpo y asa para diferenciar su producto en el punto de venta."
        ),
        "features": (
            "Capacidad nominal de 20 litros (5 galones)\n"
            "Boca roscada de 56 mm y opción de 48 mm\n"
            "Asa integrada reforzada\n"
            "Personalización con dos insertos en alto relieve\n"
            "Variación de color en cuerpo y asa\n"
            "Apto para lavado y reúso en plantas purificadoras"
        ),
        "applications": "Agua purificada retornable\nServicio a domicilio\nDispensadores de oficina",
        "packaging": (
            "Producto entregado a granel en camión con separadores\n"
            "Tarima de 1.20 x 1.20 m para 36 piezas\n"
            "Emplayado por cama\n"
            "Tapas y sellos de garantía disponibles por separado"
        ),
        "neck_finish": "56 mm rosca / 48 mm rosca",
        "colors": ["Cristal / Natural", "Azul cielo", "Azul", "Verde esmeralda"],
        "variants": [
            ("GRF-PET-10L", 10000, 420.0, 380, 240, "48 mm", 1, 60),
            ("GRF-PET-11L", 11000, 450.0, 395, 245, "48 mm", 1, 54),
            ("GRF-PET-20L", 20000, 750.0, 490, 275, "56 mm", 1, 36),
        ],
    },
    {
        "category": "garrafones-y-botellones",
        "slug": "botellon-desechable",
        "name": "Botellón Desechable PET",
        "line": "Un solo uso",
        "material": "PET",
        "summary": "Botellón ligero de un solo uso para agua purificada, con menor costo logístico.",
        "description": (
            "Botellón de un solo uso con gramaje optimizado, pensado para purificadoras que no manejan "
            "retorno de envase. Reduce costos de lavado, inspección y manejo de inventario."
        ),
        "features": (
            "Gramaje optimizado para un solo uso\n"
            "Boca 48 mm con sello de garantía\n"
            "100 % reciclable\n"
            "Menor costo logístico frente al retornable\n"
            "Disponible con asa o sin asa"
        ),
        "applications": "Agua purificada de un solo uso\nEventos y servicios temporales\nVenta en autoservicio",
        "packaging": (
            "Entrega a granel con separadores de cartón\n"
            "Tarima 1.20 x 1.20 m\n"
            "Emplayado completo"
        ),
        "neck_finish": "48 mm rosca",
        "colors": ["Cristal / Natural", "Azul cielo"],
        "variants": [
            ("BTL-10L", 10000, 300.0, 375, 235, "48 mm", 1, 60),
            ("BTL-19L", 19000, 520.0, 480, 270, "48 mm", 1, 40),
        ],
    },
    {
        "category": "tapas",
        "slug": "tapa-rosca-continua",
        "name": "Tapa de Rosca Continua con Banda de Seguridad",
        "line": "Cierres estándar",
        "material": "PP",
        "featured": True,
        "summary": (
            "Tapas de polipropileno con banda de seguridad y liner de sellado "
            "para líneas manuales y automáticas."
        ),
        "description": (
            "Tapas inyectadas en polipropileno con banda de garantía que evidencia la apertura. "
            "Disponibles con liner de espuma o sello de inducción, en una amplia gama de colores y con "
            "posibilidad de impresión tampográfica del logotipo."
        ),
        "features": (
            "Banda de seguridad evidente a la apertura\n"
            "Liner de espuma, EPE o sello de inducción\n"
            "Torque de apertura controlado\n"
            "Colores sólidos bajo carta Pantone\n"
            "Impresión tampográfica opcional\n"
            "Compatible con taponadoras automáticas"
        ),
        "applications": "Agua y bebidas\nSalsas y aderezos\nProductos de limpieza\nCosméticos",
        "packaging": (
            "Bolsa de polietileno de 1,000 a 5,000 piezas\n"
            "Caja de cartón corrugado por 5,000 a 20,000 piezas\n"
            "Tarima de 1.00 x 1.20 m\n"
            "Identificación de lote por caja"
        ),
        "neck_finish": "28 / 38 / 48 / 56 mm",
        "colors": ["Blanco", "Azul", "Verde", "Rojo", "Negro", "Amarillo", "Naranja", "Gris"],
        "variants": [
            ("TAP-28PCO", 0, 2.4, 17, 28, "28 mm PCO", 5000, 20),
            ("TAP-38RC", 0, 3.6, 19, 38, "38 mm RC", 3000, 20),
            ("TAP-48RC", 0, 5.2, 22, 48, "48 mm RC", 2000, 18),
            ("TAP-56RC", 0, 7.8, 26, 56, "56 mm RC", 1000, 16),
        ],
    },
    {
        "category": "tapas",
        "slug": "tapa-deportiva-dosificadora",
        "name": "Tapa Deportiva y Dosificadora",
        "line": "Cierres especiales",
        "material": "PP",
        "summary": "Tapas push-pull, flip-top y dosificadoras para bebidas deportivas y productos viscosos.",
        "description": (
            "Cierres de alto valor agregado para diferenciar su marca: push-pull para bebidas deportivas, "
            "flip-top para geles y salsas, y dosificadores de flujo controlado."
        ),
        "features": (
            "Apertura con una mano (push-pull)\n"
            "Sello secundario antiderrame\n"
            "Flip-top con bisagra de larga vida\n"
            "Dosificación de flujo controlado\n"
            "Colores y combinaciones bicolor"
        ),
        "applications": "Bebidas deportivas\nSalsas y aderezos\nGeles y cremas\nProductos para bebé",
        "packaging": (
            "Bolsa de polietileno de 500 a 2,000 piezas\n"
            "Caja de cartón corrugado\n"
            "Tarima emplayada"
        ),
        "neck_finish": "28 / 38 mm",
        "colors": ["Blanco", "Azul", "Rojo", "Negro", "Naranja"],
        "variants": [
            ("TAP-SP28", 0, 4.2, 32, 28, "28 mm PCO", 2000, 18),
            ("TAP-FT38", 0, 5.0, 28, 38, "38 mm RC", 1500, 18),
        ],
    },
    {
        "category": "preformas",
        "slug": "preforma-pet-28mm",
        "name": "Preforma PET Boca 28 mm",
        "line": "Insumo para soplado",
        "material": "PET",
        "summary": "Preformas de PET en distintos gramajes para soplado de botellas de 250 ml a 2 L.",
        "description": (
            "Preformas inyectadas en PET virgen o con porcentaje de PCR, con control dimensional estricto "
            "de boca y peso. Entregadas secas y libres de acetaldehído para embotelladores que soplan en planta."
        ),
        "features": (
            "Disponible en PET virgen y con resina reciclada (rPCR)\n"
            "Control estadístico de peso y dimensiones de boca\n"
            "Bajo contenido de acetaldehído\n"
            "Compatible con sopladoras lineales y rotativas\n"
            "Opción de barrera UV y pigmento"
        ),
        "applications": "Soplado de botellas de agua\nSoplado de botellas carbonatadas\nEnvases personalizados",
        "packaging": (
            "Caja octabin de 1,000 a 4,000 piezas\n"
            "Bolsa interior de polietileno sellada\n"
            "Tarima de madera con fleje\n"
            "Identificación de lote, peso y fecha"
        ),
        "neck_finish": "28 mm PCO 1810 / PCO 1881",
        "colors": ["Cristal / Natural", "Azul cielo", "Verde", "Ámbar"],
        "variants": [
            ("PRF-12.5", 0, 12.5, 78, 24, "28 mm PCO 1810", 4000, 1),
            ("PRF-19", 0, 19.0, 92, 24, "28 mm PCO 1810", 3000, 1),
            ("PRF-26", 0, 26.0, 105, 24, "28 mm PCO 1881", 2500, 1),
            ("PRF-42", 0, 42.0, 125, 24, "28 mm PCO 1881", 1500, 1),
        ],
    },
]


CATEGORY_PHOTOS = {
    "botellas-pet": "/static/img/foto-botella-pet.webp",
    "frascos-pet": "/static/img/foto-frasco-granulos.webp",
    "garrafas-pead": "/static/img/foto-garrafa-pead.webp",
    "garrafas-pet": "/static/img/foto-garrafa-pet.webp",
    "garrafones-y-botellones": "/static/img/foto-garrafon-azul.webp",
    "tapas": "/static/img/foto-tapa-azul.webp",
    "preformas": "/static/img/foto-preforma-transparente.webp",
}


def category_image(slug: str) -> str:
    return CATEGORY_PHOTOS.get(slug, f"/static/img/cat-{slug}.svg")


def seed(db: Session, *, force: bool = False) -> None:
    if db.query(Category).count() and not force:
        return

    color_map: dict[str, Color] = {}
    for name, hex_code in COLORS:
        color = db.query(Color).filter_by(name=name).one_or_none()
        if color is None:
            color = Color(name=name, hex_code=hex_code)
            db.add(color)
        color_map[name] = color
    db.flush()

    category_map: dict[str, Category] = {}
    for index, data in enumerate(CATEGORIES):
        category = db.query(Category).filter_by(slug=data["slug"]).one_or_none()
        if category is None:
            category = Category(**data, position=index, image=category_image(data["slug"]))
            db.add(category)
        else:
            category.image = category_image(data["slug"])
        category_map[data["slug"]] = category
    db.flush()

    for index, data in enumerate(PRODUCTS):
        if db.query(Product).filter_by(slug=data["slug"]).count():
            continue
        product = Product(
            slug=data["slug"],
            name=data["name"],
            category=category_map[data["category"]],
            material=data["material"],
            line=data.get("line", ""),
            summary=data["summary"],
            description=data["description"],
            features=data["features"],
            applications=data["applications"],
            packaging=data["packaging"],
            neck_finish=data["neck_finish"],
            featured=data.get("featured", False),
            position=index,
            image=category_image(data["category"]),
        )
        product.colors = [color_map[name] for name in data["colors"] if name in color_map]
        for model, capacity, weight, height, diameter, neck, upb, bpp in data["variants"]:
            product.variants.append(
                ProductVariant(
                    model=model,
                    capacity_ml=capacity,
                    weight_g=weight,
                    height_mm=height,
                    diameter_mm=diameter,
                    neck_finish=neck,
                    units_per_box=upb,
                    boxes_per_pallet=bpp,
                )
            )
        db.add(product)

    if not db.query(AdminUser).count():
        db.add(
            AdminUser(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                name="Administrador Remsa",
            )
        )
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)


def reseed() -> None:
    """Reemplaza el catálogo sembrado conservando leads, mensajes y cotizaciones."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.query(ProductVariant).delete()
        for product in db.query(Product).all():
            product.colors.clear()
            db.delete(product)
        db.query(Category).delete()
        db.commit()
        seed(db, force=True)


if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada con el catálogo de ejemplo.")
