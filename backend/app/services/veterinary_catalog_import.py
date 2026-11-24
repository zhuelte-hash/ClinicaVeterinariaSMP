"""Importación transaccional de productos, sin modificar los SKU ya existentes."""
import datetime as dt
from decimal import Decimal

from sqlalchemy import select, text

from app.models.clinic import CategoriaProducto, Producto
from app.models.operations import Sucursal
from app.services.inventory_service import InventoryService


def require_demo_database(url):
    if url.get_backend_name() != "postgresql" or url.host not in ("localhost", "127.0.0.1", "database") or not (url.database or "").startswith("test_"):
        raise ValueError("El stock de demostración solo se permite en PostgreSQL local test_*")


def preview_catalog(db, products, branch=1):
    location = db.get(Sucursal, branch)
    if location is None or not location.activa:
        raise ValueError("La sucursal no existe o está inactiva")
    existing = {p.sku: p for p in db.scalars(select(Producto).execution_options(skip_branch_filter=True)).all()}
    report = {"por_insertar": [], "conservados": [], "conflictos": []}
    for record in products:
        sku = record["sku"]
        if sku not in existing:
            report["por_insertar"].append(sku)
        elif existing[sku].sucursal_id != branch:
            report["conflictos"].append(sku)
        else:
            report["conservados"].append(sku)
    return report


def import_catalog(db, products, branch=1, *, demo=False):
    if demo:
        require_demo_database(db.get_bind().engine.url)
    if db.get_bind().dialect.name == "postgresql":
        # Mismo bloqueo que el SQL exportado: serializa seeds y altas concurrentes.
        db.execute(text("LOCK TABLE clinica_veterinaria.categorias_producto, clinica_veterinaria.productos IN SHARE ROW EXCLUSIVE MODE"))
    location = db.get(Sucursal, branch)
    if location is None or not location.activa:
        raise ValueError("La sucursal no existe o está inactiva")
    existing = {p.sku: p for p in db.scalars(select(Producto).execution_options(skip_branch_filter=True)).all()}
    categories = {}
    for category in db.scalars(select(CategoriaProducto)).all():
        key = category.nombre.strip().casefold()
        categories.setdefault(key, []).append(category)
    conflicts = [p["sku"] for p in products if p["sku"] in existing and existing[p["sku"]].sucursal_id != branch]
    if conflicts:
        raise ValueError("SKU existentes en otra sede: " + ", ".join(conflicts))
    db.info["sucursal_id"] = branch
    report = {"insertados": [], "conservados": [], "modo": "demostracion" if demo else "catalogo_sin_existencias"}
    for record in products:
        sku = record["sku"]
        if sku in existing:
            report["conservados"].append(sku)
            continue
        values = dict(record)
        category_name = values.pop("categoria_nombre")
        key = category_name.casefold()
        matches = categories.get(key, [])
        if len(matches) > 1:
            raise ValueError(f"Categorías ambiguas: {category_name}")
        if not matches:
            category = CategoriaProducto(nombre=category_name)
            db.add(category)
            db.flush()
            categories[key] = [category]
        else:
            category = matches[0]
        source = values["catalogo_origen"]
        product = Producto(**values, categoria_id=category.id, proveedor_id=None, sucursal_id=branch,
                           stock_actual=0, stock_minimo=source["stock_minimo"], costo_unitario=0,
                           activo=True, es_demostracion=demo)
        db.add(product)
        db.flush()
        if demo and source["stock_inicial"]:
            InventoryService(db).increase(product, Decimal(str(source["stock_inicial"])),
                "Saldo ficticio de demostración; no es una compra real", "ingreso",
                lot_code=f"DEMO-20261123-{sku}",
                expiry=dt.date.fromisoformat(source["fecha_vencimiento"]) if source["fecha_vencimiento"] else None,
                cost=Decimal(str(source["precio_compra"] or 0)), reference=f"DEMO-CATALOGO:{sku}")
        existing[sku] = product
        report["insertados"].append(sku)
    db.flush()
    return report
