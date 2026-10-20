# Roles y permisos

Los roles son **grupos de Django** que se crean y sincronizan automáticamente al ejecutar
`python manage.py migrate` (o manualmente con `python manage.py sync_roles`). Los permisos
se validan **en el servidor** en cada vista y en la API; ocultar un botón es solo una ayuda visual.

| Acción | Administrador | Ventas | Almacén | Consulta |
|---|:-:|:-:|:-:|:-:|
| Ver panel, catálogo, categorías y unidades | ✔ | ✔ | ✔ | ✔ |
| Ver precios de referencia | ✔ | ✔ | — | — |
| Exportar catálogo a Excel | ✔ | ✔ | — | — |
| Crear / editar / activar / desactivar productos | ✔ | — | — | — |
| Importar productos desde Excel | ✔ | — | — | — |
| Crear / editar categorías y unidades | ✔ | — | — | — |
| Administrar usuarios y asignar roles | ✔ | — | — | — |
| Consultar bitácora de auditoría completa | ✔ | — | — | — |
| Editar su propio perfil y contraseña | ✔ | ✔ | ✔ | ✔ |

Notas:

- Los productos **no se eliminan**: se desactivan, para conservar el historial.
- Un usuario con rol Administrador no puede quitarse su propio rol ni desactivarse a sí mismo,
  y no puede ver ni modificar superusuarios.
- El **superusuario** (creado con `createsuperuser`) tiene todos los permisos y acceso al panel
  técnico de Django (`/django-admin/` por defecto, configurable con `DJANGO_ADMIN_URL`). Úsalo solo
  para soporte técnico.
- Las fases siguientes (clientes, cotizaciones, inventarios, listas de precios, agenda) agregarán
  sus permisos a estos mismos roles en `accounts/roles.py`.

La definición exacta vive en `accounts/roles.py` (`ROLE_PERMISSIONS`). Si se modifica, ejecuta
`python manage.py sync_roles`: el comando informa si algún permiso no existe.
