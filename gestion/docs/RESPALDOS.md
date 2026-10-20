# Copias de seguridad y restauración

Respalda **la base de datos** y la carpeta **`media/`** (archivos subidos). El código vive en Git y
el archivo `.env` debe guardarse aparte en un lugar seguro (contiene secretos).

## SQLite (desarrollo / instalación pequeña) — PowerShell

```powershell
# Detén el servidor antes de copiar para evitar un archivo inconsistente.
New-Item -ItemType Directory -Force backups | Out-Null
$fecha = Get-Date -Format "yyyyMMdd-HHmm"
Copy-Item gestion.sqlite3 "backups\gestion-$fecha.sqlite3"
if (Test-Path media) { Compress-Archive -Path media -DestinationPath "backups\media-$fecha.zip" }
```

Restaurar:

```powershell
Copy-Item backups\gestion-AAAAMMDD-HHMM.sqlite3 gestion.sqlite3 -Force
python manage.py migrate
```

## PostgreSQL (producción)

```bash
# Respaldo comprimido (formato custom)
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f backups/gestion-$(date +%Y%m%d-%H%M).dump

# Con docker compose
docker compose exec -T db pg_dump -U remsa -d remsa_gestion -Fc > backups/gestion-$(date +%Y%m%d-%H%M).dump
```

Restaurar (sobre una base vacía):

```bash
pg_restore -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists backups/gestion-AAAAMMDD-HHMM.dump
# Con docker compose
docker compose exec -T db pg_restore -U remsa -d remsa_gestion --clean --if-exists < backups/gestion-AAAAMMDD-HHMM.dump
```

## Recomendaciones

- Programa el respaldo diario (Programador de tareas de Windows o `cron`) y conserva al menos
  7 diarios y 4 semanales, con una copia fuera del servidor.
- **Prueba la restauración** periódicamente en un equipo distinto al de producción.
- La bitácora de auditoría forma parte de la base de datos: se respalda con ella.
- Los respaldos contienen datos comerciales y contraseñas cifradas: guárdalos con acceso restringido.
