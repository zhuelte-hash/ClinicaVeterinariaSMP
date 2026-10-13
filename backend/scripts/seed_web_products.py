"""Carga el catálogo inicial de la web en Neon sin modificar productos existentes.

Ejecutar desde backend: python scripts/seed_web_products.py
La carga es repetible: solo inserta SKU ausentes; nunca restablece precios,
existencias ni productos desactivados por administración.
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.clinic import CategoriaProducto, Producto, Proveedor


# SKU, nombre, categoría, precio, existencias, imagen de muestra.
PRODUCTS = (
    ("WEB-ALI-01", "Alimento para perro adulto", "Alimentos", "74.90", 18, "photo-1589924691995-400dc9ecc119"),
    ("WEB-ALI-02", "Alimento balanceado para gato", "Alimentos", "58.90", 12, "photo-1583337130417-3346a1be7dee"),
    ("WEB-ALI-03", "Croquetas premium sabor pollo", "Alimentos", "89.90", 9, "photo-1623387641168-d9803ddd3f35"),
    ("WEB-ACC-01", "Collar ajustable acolchado", "Accesorios", "29.90", 25, "photo-1605639156481-244775d6f4f5"),
    ("WEB-ACC-02", "Correa resistente para paseo", "Accesorios", "34.90", 16, "photo-1601758124510-52d02ddb7cbd"),
    ("WEB-ACC-03", "Arnés cómodo para perro", "Accesorios", "46.50", 11, "photo-1596492784531-6e6eb5ea9993"),
    ("WEB-DES-01", "Cama acolchada lavable", "Descanso y dormitorio", "119.90", 7, "photo-1591946614720-90a587da4a36"),
    ("WEB-ACC-04", "Juguete mordedor de cuerda", "Accesorios", "19.90", 30, "photo-1599839619722-39751411ea63"),
    ("WEB-ROP-01", "Chaleco abrigador impermeable", "Ropa", "54.90", 8, "photo-1588943211346-0908a1fb0b01"),
    ("WEB-ACC-05", "Transportadora ventilada", "Accesorios", "149.90", 5, "photo-1518791841217-8f162f1e1131"),
    ("WEB-ROP-02", "Suéter suave para mascota", "Ropa", "42.90", 14, "photo-1517423440428-a5a00ad493e8"),
    ("WEB-DES-02", "Manta térmica para descanso", "Descanso y dormitorio", "64.90", 10, "photo-1560807707-8cc77767d783"),
    ("WEB-FAR-01", "Suplemento vitamínico canino", "Suplementos", "42.90", 13, "photo-1550572017-edd951b55104"),
    ("WEB-FAR-02", "Shampoo dermatológico suave", "Higiene y cuidado", "36.50", 20, "photo-1583337130417-3346a1be7dee"),
    ("WEB-FAR-03", "Antiparasitario externo", "Medicamentos veterinarios", "48.90", 15, "photo-1584308666744-24d5c474f2ae"),
    ("WEB-FAR-04", "Alimento digestivo especializado", "Alimento medicado", "18.90", 22, "photo-1574158622682-e40e69881006"),
    ("WEB-FAR-05", "Protector articular", "Suplementos", "69.90", 6, "photo-1556229010-6c3f2c9ca5f8"),
    ("WEB-FAR-06", "Solución ótica de cuidado", "Higiene y cuidado", "32.90", 17, "photo-1576091160399-112ba8d25d1d"),
    ("WEB-FAR-07", "Tabletas de cuidado dental", "Higiene y cuidado", "28.50", 19, "photo-1587854692152-cbe660dbde88"),
    ("WEB-FAR-08", "Desinfectante veterinario", "Higiene y cuidado", "39.90", 10, "photo-1585435557343-3b092031a831"),
)


def main() -> None:
    with SessionLocal() as db:
        existing = {item.sku for item in db.scalars(select(Producto)).all()}
        missing = [item for item in PRODUCTS if item[0] not in existing]
        if not missing:
            print("Catálogo de ejemplo ya cargado; ningún producto modificado.")
            return
        categories = {item.nombre: item for item in db.scalars(select(CategoriaProducto)).all()}
        for name in {item[2] for item in missing} - categories.keys():
            category = CategoriaProducto(nombre=name)
            db.add(category)
            categories[name] = category
        provider = db.scalar(select(Proveedor).where(Proveedor.razon_social == "Catálogo web de ejemplo"))
        if provider is None:
            provider = Proveedor(razon_social="Catálogo web de ejemplo")
            db.add(provider)
        db.flush()
        for sku, name, category, price, stock, image in missing:
            db.add(Producto(
                sku=sku, nombre=name, categoria_id=categories[category].id,
                proveedor_id=provider.id, precio_venta=Decimal(price),
                stock_actual=stock, stock_minimo=5,
                imagen_url=f"https://images.unsplash.com/{image}?auto=format&fit=crop&w=900&q=85",
                activo=True,
            ))
        db.commit()
        print(f"Productos de ejemplo agregados: {len(missing)}. Productos existentes sin cambios.")


if __name__ == "__main__":
    main()
