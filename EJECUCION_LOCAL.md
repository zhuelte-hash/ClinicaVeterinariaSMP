# Ejecutar en Windows con Neon, sin Docker

## Requisitos

- Python 3.11.
- Node.js compatible con Angular 21 (por ejemplo, Node 24).
- `backend/.env` con `DATABASE_URL` de Neon y `SECRET_KEY` configurados.

La conexion a Neon debe conservar `sslmode=require`. No hace falta instalar
PostgreSQL en la PC. No publiques el archivo `.env` ni sus credenciales.

## Inicio

Desde PowerShell, en la carpeta principal del proyecto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar-local.ps1
```

La primera ejecucion crea `backend/.venv` e instala las dependencias de Python.
Tambien instala las dependencias de Angular si no estan disponibles.
Abre ventanas para la API, el trabajador de citas automaticas y Angular.
Si el puerto 4200 ya esta ocupado, conserva el frontend existente.

- Aplicacion: http://localhost:4200
- Documentacion de la API: http://localhost:8000/docs

Deten cada proceso con **Ctrl+C** en su ventana. Para volver a iniciar,
asegurate de haber detenido el backend anterior.

El trabajador aplica las reglas existentes de inasistencia sobre las citas
de la base configurada. Para iniciar sin ese proceso:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar-local.ps1 -SinWorker
```

Si los contenedores anteriores siguen ocupando los puertos, detenlos primero:

```powershell
docker compose -f compose.neon.yaml stop backend frontend
```

Esto solo es necesario al pasar de Docker a la ejecucion local.

## Migraciones

El inicio no modifica el esquema de Neon automaticamente. Cuando haya nuevas
migraciones, ejecuta desde la carpeta `backend`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Actualizar dependencias

Si cambia `backend/requirements.txt`, ejecuta desde la raiz:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

Si cambia `frontend/package-lock.json`, ejecuta `npm ci` desde `frontend`.
