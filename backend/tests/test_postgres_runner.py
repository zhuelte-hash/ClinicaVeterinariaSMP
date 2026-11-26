"""Aislamiento y limpieza del ejecutor PostgreSQL, sin iniciar contenedores."""
import subprocess
import sys

import pytest

from scripts import test_postgres as runner


@pytest.mark.parametrize("arguments,port,all_tests", [
    ([], 55432, False),
    (["--all", "--port", "55433"], 55433, True),
])
def test_runner_uses_the_selected_database_for_migrations_and_tests(monkeypatch, arguments, port, all_tests):
    monkeypatch.setattr(sys, "argv", ["test_postgres.py", *arguments])
    monkeypatch.setenv("DATABASE_URL", "postgresql://operational.invalid/clinic")
    monkeypatch.setenv("TEST_POSTGRES_PORT", "5432")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", run)
    assert runner.main() == 0
    expected = f"postgresql://postgres:postgres@localhost:{port}/test_clinica"
    for command, options in calls[1:]:
        assert options["env"]["TEST_POSTGRES_PORT"] == str(port)
        for key in ("DATABASE_URL", "TEST_DATABASE_URL", "TEST_APPOINTMENT_DATABASE_URL"):
            assert options["env"][key] == expected
    tests = next(command for command, _ in calls if "pytest" in command)
    assert tests[6:] == ([] if all_tests else runner.POSTGRES_TESTS)
    assert calls[-1][0] == runner.COMPOSE + ["down"]


def test_runner_removes_its_container_when_migrations_fail(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_postgres.py", "--port", "55433"])
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "alembic" in command:
            raise subprocess.CalledProcessError(3, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", run)
    assert runner.main() == 3
    assert not any("pytest" in command for command in calls)
    assert calls[-1] == runner.COMPOSE + ["down"]


@pytest.mark.parametrize("port", ["0", "65536"])
def test_runner_rejects_invalid_ports_before_starting_docker(monkeypatch, port):
    monkeypatch.setattr(sys, "argv", ["test_postgres.py", "--port", port])

    def run(*args, **kwargs):
        pytest.fail("Un puerto inválido no debe iniciar Docker")

    monkeypatch.setattr(runner.subprocess, "run", run)
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2
