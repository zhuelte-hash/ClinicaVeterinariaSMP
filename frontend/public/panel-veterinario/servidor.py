from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from functools import partial
from threading import Timer
import webbrowser

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    url = 'http://localhost:8765'
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 8765), handler)
    except OSError as error:
        print('No se pudo abrir el puerto 8765. Cierra otro servidor que lo use.')
        print(error)
        raise SystemExit(1)
    print('Panel veterinario: ' + url)
    print('Mantén esta ventana abierta. Pulsa Ctrl+C para detenerlo.')
    Timer(1, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
