# Fotografías reales de instalaciones

## Fachada de San Martín de Porres

- Archivo: `fachada-san-martin-de-porres.jpg`.
- Fotografía real identificada y proporcionada por el usuario para la galería HU-018.
- Muestra el acceso y el letrero de la clínica en Jr. Quínua 178, Ayacucho.
- Fuente proporcionada:
  https://lh3.googleusercontent.com/gps-cs-s/ANWiy9QgqDx1V5RQf2pAgpI6xPQsQICI5xJb3QEkhNm7_pe3orzGhUmzxoG-j9p7-HWO84YivYlm2A53hattYM5XUrMZWxlcBbtAX2hRUf3J_Ol6r-BK9oVDKMmR_ZL0p4ZAZredX8p6Dw=s1360-w1360-h1020-rw

Se conserva una copia JPEG en el repositorio para no depender del enlace externo.
Para publicarla en un entorno nuevo, desde `backend`, usando su configuración local:

```powershell
.\.venv\Scripts\python.exe scripts/publish_installation_photo.py assets/instalaciones/fachada-san-martin-de-porres.jpg --title "Fachada y entrada de la Clínica Veterinaria San Martín de Porres"
```

El comando agrega la fotografía sin reemplazar las existentes ni otras políticas.
Usa un nombre derivado del contenido para evitar duplicarla al repetir el comando.
Después puede titularse, ordenarse o retirarse desde Configuración → Galería.

## Fotografías aportadas desde `frontend/public`

Se incorporaron las nueve fotografías `imgen1.png` e `ima2.png` a `ima9.png`.
Las copias JPEG de esta carpeta tienen nombres descriptivos, compresión progresiva
y un ajuste leve de contraste y nitidez. En `ima4.png` se retiró el encabezado de
captura; las fotografías se muestran completas en la galería y en el visor.
Los archivos originales permanecen en `frontend/public`.

Las nueve copias pasan de 9439 KB a 1352 KB aproximadamente (86 % menos).
Para regenerarlas y agregarlas a la galería del entorno configurado, desde `backend`:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_installation_photos.py --publish
```

Sin `--publish` solo se generan los JPEG. La publicación conserva las fotografías
existentes y permite seguir administrando los títulos y el orden desde Configuración.
Repetirla con los mismos archivos no duplica las fotografías.
