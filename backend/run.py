"""Inicia la API usando el entorno local del proyecto cuando está disponible."""
import argparse
import importlib
import os
from pathlib import Path
import sys


def main() -> None:
    backend = Path(__file__).resolve().parent
    local_python = backend / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if sys.prefix == sys.base_prefix and local_python.is_file():
        print("Usando el entorno virtual backend/.venv para iniciar la API.", flush=True)
        os.execv(str(local_python), [str(local_python), str(backend / "run.py"), *sys.argv[1:]])

    parser = argparse.ArgumentParser(description="Inicia la API de Clínica Veterinaria SMP.")
    parser.add_argument("--check", action="store_true", help="Comprueba las dependencias y carga de la API sin ocupar el puerto 8000.")
    args = parser.parse_args()

    try:
        import uvicorn
        importlib.import_module("app.main")
    except ModuleNotFoundError as exc:
        print(f"Falta una dependencia de la API: {exc.name}.", file=sys.stderr)
        print("Ejecuta iniciar-local.ps1 desde la raíz del proyecto para instalar las dependencias en backend/.venv.", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.check:
        print(f"API importada correctamente. Entorno Python: {sys.prefix}")
        return
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
