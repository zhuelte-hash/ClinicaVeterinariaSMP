# Fotos del proyecto

## Revisión del 24 de noviembre de 2026

Se revisó el catálogo público del entorno local conectado a la base configurada,
la galería y los enlaces de imagen escritos en el código del frontend.
La revisión no incluye archivos privados de historias clínicas ni fotos de
mascotas accesibles únicamente después de iniciar sesión.

- 83 productos activos en total.
- 50 pertenecen al catálogo `VET-`: 33 tienen foto y 17 usan el reemplazo.
- Se agregó Aurizon 20 ml (`VET-MED-001`) desde el enlace directo de ConVet
  proporcionado por el usuario. Fuente y copia local: `fotografias_manuales.json`.
- Se agregaron las fotos proporcionadas para Cardial (`VET-MED-003`),
  Prednisolona (`VET-MED-010`), Cefavet (`VET-MED-011`), Apoquel (`VET-MED-012`)
  y Antalvet 100 ml (`VET-MED-015`). Los enlaces recibidos y las diferencias de
  presentación están en `fotos_recibidas_medicamentos.json`.
- Se recuperaron y asociaron las fotos de `VET-ACC-003` (Juguete Pulpo) y
  `VET-ACC-005` (Plato Cara de Gato), usando los registros de la tienda Fluker.
  La asociación se basa en el nombre del producto; no acredita una revisión
  visual de cada presentación.
- Las 10 fotografías publicadas de instalaciones están disponibles.
- El enlace externo de Hospedaje devolvía 404 y fue reemplazado.
- El producto `WEB-ACC-01`, Collar ajustable acolchado, tiene un enlace externo
  que devuelve 404: necesita una fotografía del collar correspondiente.

El informe comprobable, con cada URL, SKU y resultado, está en
`data/informe_imagenes.json`. Los enlaces externos pueden cambiar con el tiempo.

## Subir las fotos que faltan

1. Abre <http://localhost:4200/admin/productos> con tu cuenta administradora.
2. Marca **Solo productos con foto pendiente**. Incluye reemplazos y fotos que
   el navegador detecte como rotas al cargarlas.
3. Busca el producto por nombre o SKU y pulsa **Editar**.
4. En **Imagen del producto → Subir imagen**, selecciona JPG, PNG o WEBP de hasta
   5 MB. Comprueba la vista previa.
5. Pulsa **Guardar producto**. Subir el archivo por sí solo no guarda la edición.

Para instalar fotos de productos mediante archivos estáticos, colócalos en
`frontend/public/catalogo/productos/` y guarda en la URL del producto una ruta
como `/catalogo/productos/vet-med-001.webp`.
La ruta escrita en el formulario no incluye `frontend/public`.

## Catálogo VET pendiente (17 fotos)

| SKU | Fotografía requerida |
| --- | --- |
| VET-MED-002 | Broncopet 50 ml |
| VET-MED-013 | Dolordog 44, 40 tabletas |
| VET-MED-014 | Antalvet compuesto 50 ml |
| VET-GAT-001 | Brit Care Cat GF Indoor Anti-Stress 2 kg |
| VET-GAT-002 | Brit Care Cat Senior Weight Control 2 kg |
| VET-GAT-003 | Brit Care Cat Sterilized Weight Control 2 kg |
| VET-ANT-001 | Bravecto 10–20 kg, 500 mg |
| VET-ANT-002 | Bravecto 2–4.5 kg, 112.5 mg |
| VET-ANT-003 | Bravecto 20–40 kg, 1000 mg |
| VET-ANT-004 | Bravecto 4.5–10 kg, 250 mg |
| VET-ANT-005 | NexGard Spectra M 7.6–15 kg, 1 tableta |
| VET-HIG-003 | Arena Cristal San 1.6 kg |
| VET-HIG-004 | Arena Mitzi 5 kg |
| VET-HIG-005 | Arena Dear Cat Cero Huellas 5 kg |
| VET-ACC-001 | Microchip Pet ID |
| VET-ACC-002 | Microchip ANIMAL ID |
| VET-ACC-004 | Soga de Nylon XL |

De los enlaces recibidos, quedan tres pendientes por diferencias visibles:
Broncopet muestra 100 ml y el registro indica 50 ml; Dolordog muestra 30
comprimidos y el registro indica 40; la foto enviada para Antalvet 50 ml muestra
100 ml. No se cambiaron los nombres ni las presentaciones de los productos.

La recuperación automática no pudo completar estos registros: Villarán devuelve
un error HTTP, Argos no fue accesible desde este entorno y las demás fuentes
no ofrecieron coincidencias utilizables. NexGard ya tenía una candidata
descartada por diferencia de rango de peso. Se necesitan archivos originales o
enlaces directos correspondientes al producto y su presentación.

## Dónde están los archivos y cómo trasladarlos

| Ubicación | Contenido | Cómo se sirve |
| --- | --- | --- |
| `frontend/public/catalogo/productos/` | Copias del catálogo recuperado | Angular, `/catalogo/productos/...` |
| `frontend/public/logo.png` | Logo | Angular, `/logo.png` |
| `backend/uploads/products/` | Fotos subidas desde Productos | API, `/uploads/products/...` |
| `backend/uploads/instalaciones/` | Fotos publicadas de la galería | API, `/uploads/instalaciones/...` |
| `backend/uploads/pets/` | Fotos subidas de mascotas | API, `/uploads/pets/...` |
| `backend/assets/instalaciones/` | Copias fuente de la clínica | Se publican con los scripts de instalaciones |

**La base de datos guarda las rutas; los archivos de las fotos están en disco.**
`backend/uploads/` está excluido de Git. Al cambiar de computadora o servidor,
restaura también esta carpeta conservando sus nombres y subcarpetas. La sección
de respaldos del sistema incluye `uploads` y los archivos clínicos privados;
consulta `backend/app/services/backup_service.py` para el formato existente.

Los archivos nuevos de `frontend/public` y `backend/assets` deben incorporarse
al repositorio para que otro equipo pueda obtenerlos con `git pull`.
Una imagen que solo está como archivo local sin seguimiento no se descarga
desde GitHub. La base configurada en el otro equipo debe conservar también los
registros de productos y las rutas de la galería.

## Repetir la comprobación

Con frontend y backend iniciados, desde la raíz:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/audit_public_images.py --output data/informe_imagenes.json
```

El comando consulta las rutas públicas y valida el contenido de las imágenes;
no modifica la base de datos.

Para repetir la recuperación de fotos desde las tiendas, desde `backend`:

```powershell
.\.venv\Scripts\python.exe scripts/recover_catalog_photos.py
```

El informe de candidatas está en `data/fotografias_recuperadas.json`.
El indicador `--apply` asocia las fotos recuperadas a los SKU existentes;
para la base remota configurada se añade `--allow-remote`.
