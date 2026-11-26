"""Las suites históricas ejercitan Meta; no dependen del proveedor elegido en .env."""
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def whatsapp_provider_for_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "whatsapp_provider", "meta")
