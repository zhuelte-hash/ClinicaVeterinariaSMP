"""Levanta la aplicación completa; opcionalmente comparte una URL HTTPS temporal."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import set_key

BACKEND = Path(__file__).resolve().parents[1]
TEMP = Path(r"C:\Users\nomad\AppData\Local\Temp\opencode")
CLOUDFLARED = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def lan_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("1.1.1.1", 80))
            address = probe.getsockname()[0]
        return address if not address.startswith("127.") else "127.0.0.1"
    except OSError:
        return "127.0.0.1"


def healthy(url):
    try:
        with urlopen(Request(url.rstrip("/") + "/api/health", headers={"User-Agent": "ClinicaSMP/1.0"}), timeout=8) as response:
            return response.status == 200 and json.load(response).get("status") == "ok"
    except (OSError, URLError, ValueError):
        return False


def download_tunnel(path):
    total = 0
    with urlopen(CLOUDFLARED, timeout=120) as response, path.open("wb") as output:
        while chunk := response.read(512 * 1024):
            total += len(chunk)
            if total > 120 * 1024 * 1024:
                raise ValueError("Descarga de túnel demasiado grande")
            output.write(chunk)
    with path.open("rb") as binary:
        if binary.read(2) != b"MZ":
            raise ValueError("La descarga no es el ejecutable esperado")


def set_frontend_url(url):
    if not re.fullmatch(r"https?://[A-Za-z0-9.:-]+", url):
        raise ValueError("Origen de aplicación inválido")
    path = BACKEND / ".env"
    if not path.is_file():
        raise ValueError("Falta backend/.env")
    set_key(str(path), "FRONTEND_URL", url, quote_mode="always", encoding="utf-8")


def serve(session):
    log = (session / "api.log").open("ab")
    env = {**os.environ, "DEBUG": "false"}
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    for _ in range(40):
        if process.poll() is not None:
            raise RuntimeError("La API no pudo iniciarse; revisa api.log de la sesión")
        if healthy("http://127.0.0.1:8000"):
            return process
        time.sleep(0.5)
    process.terminate()
    raise RuntimeError("La API no respondió dentro del plazo de inicio")


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


def run(session, public):
    session = session.resolve()
    if not session.is_relative_to(TEMP.resolve()):
        raise ValueError("La sesión debe estar dentro de la carpeta temporal de OpenCode")
    session.mkdir(parents=False, exist_ok=False)
    if not (BACKEND.parent / "frontend/dist/browser/index.html").is_file():
        raise RuntimeError("Compila primero el frontend con npm run build")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("El puerto 8000 está ocupado; detén la API anterior antes de usar este lanzador")
    state_file = session / "state.json"
    api, tunnel = None, None
    local_url = f"http://{lan_address()}:8000"
    chosen_url = local_url
    state = {"estado": "iniciando", "manager_pid": os.getpid(), "url_local": "http://localhost:8000", "url_lan": local_url, "url_publica": None, "sesion": str(session)}
    def persist():
        state["api_pid"] = api.pid if api else None
        state["tunnel_pid"] = tunnel.pid if tunnel else None
        temporary = state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(state_file)
    try:
        set_frontend_url(local_url)
        api = serve(session); state["estado"] = "local_listo"; persist()
        print(f"Aplicación local: http://localhost:8000 | Red local: {local_url}", flush=True)
        if public:
            try:
                print("Preparando acceso HTTPS temporal, sin cuenta adicional…", flush=True)
                executable = session / "cloudflared.exe"
                download_tunnel(executable)
                log_path = session / "tunnel.log"
                with log_path.open("wb") as output:
                    tunnel = subprocess.Popen([str(executable), "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate", "--protocol", "http2"], stdout=output, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 100
                candidate = None
                while time.monotonic() < deadline and tunnel.poll() is None:
                    if log_path.is_file():
                        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", log_path.read_text(encoding="utf-8", errors="replace"))
                        if match:
                            candidate = match[0]
                            if healthy(candidate):
                                break
                    time.sleep(1)
                if candidate and healthy(candidate):
                    chosen_url = candidate
                    set_frontend_url(chosen_url)
                    stop(api); api = serve(session)
                    state["url_publica"] = chosen_url; state["estado"] = "publico_listo"
                    print(f"Aplicación HTTPS lista y comprobada: {chosen_url}", flush=True)
                else:
                    stop(tunnel); tunnel = None
                    state["aviso"] = "El túnel no respondió; la aplicación sigue disponible en la red local."
                    print(state["aviso"], flush=True)
            except (OSError, URLError, ValueError, RuntimeError):
                stop(tunnel); tunnel = None
                state["aviso"] = "No se pudo habilitar el túnel. La aplicación local sigue operativa."
                print(state["aviso"], flush=True)
        state["frontend_url"] = chosen_url; persist()
        observed = (BACKEND / ".env").stat().st_mtime_ns
        print(f"Estado de la sesión: {state_file}", flush=True)
        print("Para configurar correo: .\\.venv\\Scripts\\python.exe scripts/configure_email.py", flush=True)
        while not (session / "stop.flag").exists():
            modified = (BACKEND / ".env").stat().st_mtime_ns
            if modified != observed:
                stop(api); api = serve(session); observed = modified; persist()
                print("API reiniciada con la configuración local actualizada.", flush=True)
            if api.poll() is not None:
                raise RuntimeError("La API se detuvo; revisa api.log")
            if tunnel is not None and tunnel.poll() is not None:
                state["estado"] = "tunel_interrumpido"; persist()
            time.sleep(2)
    finally:
        stop(api); stop(tunnel)
        state["estado"] = "detenido"; persist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--public", action="store_true", help="Intenta acceso HTTPS temporal mediante Cloudflare Tunnel")
    parser.add_argument("--stop", action="store_true", help="Detiene únicamente los procesos de esta sesión")
    args = parser.parse_args()
    try:
        if args.stop:
            session = args.session.resolve()
            if not session.is_relative_to(TEMP.resolve()) or not session.is_dir():
                parser.error("Sesión no válida")
            (session / "stop.flag").touch()
        else:
            run(args.session, args.public)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
