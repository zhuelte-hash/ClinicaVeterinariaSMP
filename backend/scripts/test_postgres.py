"""Ejecuta las integraciones PostgreSQL con una base temporal en Docker.

Desde la raíz: backend/.venv/Scripts/python.exe backend/scripts/test_postgres.py
Agrega --all para ejecutar toda la suite con PostgreSQL disponible.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
COMPOSE = [
    "docker", "compose", "--project-name", "clinica-tests",
    "--file", str(ROOT_DIR / "compose.test.yaml"),
]
DATABASE_URL = "postgresql://postgres:postgres@localhost:55432/test_clinica"
POSTGRES_TESTS = [
    "tests/test_sales_flow.py",
    "tests/test_appointment_flow_postgres.py",
    "tests/test_purchase_flow_postgres.py",
    "tests/test_backup_postgres.py",
    "tests/test_independent_stories_postgres.py",
    "tests/test_six_remaining_postgres.py",
    "tests/test_priority_partial_progress_postgres.py",
    "tests/test_veterinary_catalog_postgres.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Ejecutar toda la suite")
    args = parser.parse_args()
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": DATABASE_URL,
        "TEST_DATABASE_URL": DATABASE_URL,
        "TEST_APPOINTMENT_DATABASE_URL": DATABASE_URL,
        "SECRET_KEY": "clinica-postgres-integration-tests-only",
        "DEBUG": "false",
        "PURCHASE_DELIVERY_COST": "10.00",
    })
    try:
        subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Inicia Docker Desktop antes de ejecutar las pruebas.", file=sys.stderr)
        return 1

    result = 1
    try:
        subprocess.run(
            COMPOSE + ["up", "-d", "--wait", "--force-recreate", "database"],
            cwd=ROOT_DIR, env=env, check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR, env=env, check=True,
        )
        tests = [] if args.all else POSTGRES_TESTS
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "-rs", "--tb=short", *tests],
            cwd=BACKEND_DIR, env=env,
        ).returncode
    except subprocess.CalledProcessError as exc:
        result = exc.returncode
    finally:
        cleanup = subprocess.run(COMPOSE + ["down"], cwd=ROOT_DIR, env=env)
        if cleanup.returncode and result == 0:
            result = cleanup.returncode
    return result


if __name__ == "__main__":
    raise SystemExit(main())
