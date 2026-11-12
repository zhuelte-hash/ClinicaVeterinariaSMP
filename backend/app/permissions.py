"""Matriz transversal: los permisos se suman a la pertenencia y al rol del portal."""
MODULES = ("productos", "inventario", "ventas", "usuarios", "citas", "mascotas", "historias_clinicas")
DEFAULTS = {
    "administrador": {module: "ver crear editar eliminar aprobar" for module in MODULES},
    "veterinario": {"productos": "ver", "inventario": "ver", "ventas": "ver crear", "usuarios": "ver crear editar", "citas": "ver crear editar eliminar aprobar", "mascotas": "ver crear editar", "historias_clinicas": "ver crear editar"},
    "cajero": {"productos": "ver", "inventario": "ver", "ventas": "ver crear editar eliminar aprobar", "usuarios": "ver crear", "citas": "ver", "mascotas": "ver"},
    "cliente": {"productos": "ver", "ventas": "ver crear editar", "citas": "ver crear editar eliminar", "mascotas": "ver crear editar", "historias_clinicas": "ver"},
}


def default_permission(role, module, action):
    return action in DEFAULTS.get(str(getattr(role, "value", role)), {}).get(module, "").split()


def portal_permission(path, method):
    if path.startswith("/auth/") or "notificaciones" in path:
        return None
    if path.startswith(("/api/ventas", "/api/admin/ventas", "/caja", "/pedidos-web", "/operaciones/")):
        module = "ventas"
    elif path.startswith("/portal/"):
        module = "historias_clinicas" if any(part in path for part in ("/historial", "/atencion", "/receta", "/examen", "/derivacion", "/notas-privadas")) else "mascotas" if "/mascotas" in path else "usuarios" if "/clientes" in path else "citas"
    else:
        return None
    action = "ver" if method == "GET" else "eliminar" if method == "DELETE" else "editar" if method in {"PATCH", "PUT"} else "crear"
    if any(part in path for part in ("/revision", "/validar", "/aprobar")):
        action = "aprobar"
    if path.endswith(("/anular", "/rechazar")):
        action = "eliminar" if path.endswith("/anular") else "aprobar"
    return module, action
