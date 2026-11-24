"""Lectura y normalización del catálogo. No importa configuración ni abre conexiones."""
import csv
import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
PLACEHOLDER = "/catalogo/producto-sin-foto.svg"
CATEGORIES = {
    "Medicamentos veterinarios": "Medicamentos veterinarios",
    "Antiparasitarios": "Medicamentos veterinarios",
    "Alimentos para perros": "Alimentos",
    "Alimentos para gatos": "Alimentos",
    "Higiene y cuidado animal": "Higiene y cuidado",
    "Accesorios para mascotas": "Accesorios",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_float=Decimal)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def nullable(value):
    return None if value is None or str(value).strip() in ("", "Por confirmar") else value


def load_catalog(directory=DATA, *, check_photo_files=True):
    directory = Path(directory)
    rows = read_json(directory / "productos_veterinarios.json")
    if not isinstance(rows, list) or len(rows) != 50:
        raise ValueError("El catálogo debe contener exactamente 50 productos")
    codes = [row["codigo"] for row in rows]
    if len(set(codes)) != len(codes):
        raise ValueError("Hay códigos de producto duplicados")
    with (directory / "productos_veterinarios.csv").open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    with (directory / "fotografias.csv").open(encoding="utf-8-sig", newline="") as stream:
        photo_rows = list(csv.DictReader(stream))
    for label, source in [("CSV de productos", csv_rows), ("CSV de fotografías", photo_rows)]:
        if len(source) != 50 or {row["codigo"] for row in source} != set(codes):
            raise ValueError(f"{label}: los códigos no coinciden con el JSON")
    csv_by_code = {row["codigo"]: row for row in csv_rows}
    photos_by_code = {row["codigo"]: row for row in photo_rows}
    manifest_file = directory / "fotografias_verificadas.json"
    verified = read_json(manifest_file) if manifest_file.exists() else {}
    if set(verified) - set(codes):
        raise ValueError("El manifiesto de fotografías contiene códigos desconocidos")
    result = []
    for source in rows:
        code = source["codigo"]
        if source["categoria"] not in CATEGORIES or source["moneda"] != "PEN":
            raise ValueError(f"{code}: categoría o moneda no admitida")
        for key, value in source.items():
            cell = csv_by_code[code].get(key, "")
            if key in ("precio_compra", "precio_venta", "stock_inicial", "stock_minimo"):
                matches = (None if cell == "" else Decimal(cell)) == value
            else:
                matches = cell == ("" if value is None else str(value))
            if not matches:
                raise ValueError(f"{code}: diferencia JSON/CSV en {key}")
        for key, value in photos_by_code[code].items():
            if value != ("" if source[key] is None else str(source[key])):
                raise ValueError(f"{code}: diferencia en fotografías: {key}")
        for key in ("fecha_consulta", "fecha_vencimiento"):
            if source[key]:
                dt.date.fromisoformat(source[key])
        for key in ("precio_compra", "precio_venta", "stock_inicial", "stock_minimo"):
            value = source[key]
            if value is not None and (not Decimal(str(value)).is_finite() or value < 0):
                raise ValueError(f"{code}: {key} inválido")
        if type(source["stock_demostracion"]) is not bool or type(source["vencimiento_ficticio"]) is not bool:
            raise ValueError(f"{code}: indicadores de demostración inválidos")
        species = nullable(source["especie"])
        category = "Alimento medicado" if source["subcategoria"] == "Dieta veterinaria" else CATEGORIES[source["categoria"]]
        image = PLACEHOLDER
        proof = verified.get(code)
        if proof:
            image = proof["archivo"]
            if not image.startswith("/catalogo/productos/") or ".." in image or not proof.get("verificado_en") or not proof.get("criterio") or proof["url_origen"] != source["url_fotografia"]:
                raise ValueError(f"{code}: verificación de fotografía incompleta")
            if check_photo_files and not (ROOT / "frontend" / "public" / image.lstrip("/")).is_file():
                raise ValueError(f"{code}: falta la copia local verificada")
        metadata = {key: nullable(value) for key, value in source.items()}
        metadata.update({"archivo_origen": "data/productos_veterinarios.json", "version": "2026-11-23", "fotografia_verificada": proof})
        metadata = json.loads(json_text(metadata))
        product = {
            "sku": f"VET-{code}", "nombre": source["nombre"], "categoria_nombre": category,
            "marca": nullable(source["marca"]), "presentacion": nullable(source["presentacion"]),
            "subcategoria": nullable(source["subcategoria"]), "descripcion": nullable(source["descripcion"]),
            "precio_venta": source["precio_venta"], "especies": species.split(" y ") if species else [],
            "unidad_medida": "unidad", "fraccionable": False,
            "requiere_vencimiento": source["categoria"] in ("Medicamentos veterinarios", "Antiparasitarios", "Alimentos para perros", "Alimentos para gatos") or source["subcategoria"] == "Champú",
            "imagen_url": image, "catalogo_origen": metadata,
        }
        # Normalizar el singular de las especies sin inventar una especie desconocida.
        product["especies"] = [value.capitalize() for value in product["especies"]]
        for key, limit in [("sku", 50), ("nombre", 150), ("marca", 150), ("presentacion", 250), ("subcategoria", 100)]:
            if product[key] is not None and len(product[key]) > limit:
                raise ValueError(f"{code}: {key} supera {limit} caracteres")
        result.append(product)
    return result


def render_sql(products, branch=1):
    """SQL solo de catálogo operativo; misma normalización que el seed Python."""
    if branch < 1:
        raise ValueError("La sede debe ser positiva")
    payload = json_text(products).replace("'", "''")
    return f"""-- Generado por seed_veterinary_products.py; revisar antes de ejecutar.
-- Requiere migración 20261124_27. NO ejecuta migraciones. Stock operativo = 0.
-- Costos, cantidades y vencimientos ficticios se conservan en catalogo_origen.
BEGIN;
SET LOCAL search_path TO clinica_veterinaria, public;
LOCK TABLE categorias_producto, productos IN SHARE ROW EXCLUSIVE MODE;
DO $catalogo$
DECLARE
    item jsonb;
    categoria bigint;
    nuevo bigint;
    sede integer := {branch};
    datos jsonb := '{payload}'::jsonb;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sucursales WHERE id = sede AND activa) THEN
        RAISE EXCEPTION 'La sucursal no existe o está inactiva';
    END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(datos) LOOP
        IF EXISTS (SELECT 1 FROM productos WHERE sku = item->>'sku' AND sucursal_id <> sede) THEN
            RAISE EXCEPTION 'SKU existente en otra sede: %', item->>'sku';
        END IF;
        IF EXISTS (SELECT 1 FROM productos WHERE sku = item->>'sku') THEN
            CONTINUE;
        END IF;
        IF (SELECT count(*) FROM categorias_producto WHERE lower(trim(nombre)) = lower(item->>'categoria_nombre')) > 1 THEN
            RAISE EXCEPTION 'Categorías ambiguas: %', item->>'categoria_nombre';
        END IF;
        SELECT id INTO categoria FROM categorias_producto WHERE lower(trim(nombre)) = lower(item->>'categoria_nombre');
        IF categoria IS NULL THEN
            INSERT INTO categorias_producto(nombre) VALUES (item->>'categoria_nombre') RETURNING id INTO categoria;
        END IF;
        INSERT INTO productos(categoria_id, proveedor_id, sku, nombre, precio_venta, marca, presentacion, subcategoria,
            descripcion, especies, unidad_medida, fraccionable, requiere_vencimiento, sucursal_id,
            costo_unitario, stock_actual, stock_minimo, activo, imagen_url, catalogo_origen, es_demostracion)
        VALUES (categoria, NULL, item->>'sku', item->>'nombre', (item->>'precio_venta')::numeric,
            item->>'marca', item->>'presentacion', item->>'subcategoria', item->>'descripcion',
            (item->'especies')::json, 'unidad', false, (item->>'requiere_vencimiento')::boolean, sede,
            0, 0, (item->'catalogo_origen'->>'stock_minimo')::numeric, true, item->>'imagen_url', (item->'catalogo_origen')::json, false)
        RETURNING id INTO nuevo;
        INSERT INTO eventos_auditoria(usuario_id, sucursal_id, entidad, registro_id, accion, cambios)
        VALUES (NULL, sede, 'productos', nuevo::text, 'crear', json_build_object('origen', 'catalogo-veterinario-20261123', 'sku', item->>'sku'));
    END LOOP;
END $catalogo$;
COMMIT;
"""
