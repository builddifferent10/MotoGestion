# MotoGestión – Entrega 3

Aplicación académica de inventario, clientes, ventas, cuentas por cobrar y abonos, desarrollada en Flask + SQLite.

## Ejecutar en el computador

1. Instala Python 3.10 o posterior.
2. Abre una terminal dentro de esta carpeta.
3. Ejecuta `python -m venv .venv` y activa el entorno (`.venv\Scripts\activate` en Windows).
4. Ejecuta `pip install -r requirements.txt`.
5. Define variables de entorno `SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD` (contraseña segura propia). Ejemplo Windows PowerShell: `$env:SECRET_KEY='clave-larga-y-aleatoria'; $env:ADMIN_PASSWORD='OtraClaveSegura123!'`.
6. Ejecuta `python app.py` y abre `http://localhost:5000`.

**Solo entorno local:** Si no configuras usuario y contraseña, se crean credenciales iniciales `admin / Moto2026!`. NO usar estas credenciales en una instalación pública.

## Publicar en Render

1. Crear repositorio de GitHub y subir el contenido de esta carpeta (`app.py`, `requirements.txt`, `render.yaml`, `Procfile`, etc.). **No subir archivos `.sqlite3` ni contraseñas.**
2. Entrar a Render y seleccionar **New → Blueprint**, conectar el repositorio y usar `render.yaml`. Si no aparece Blueprint, crear un **Web Service** de Python, con Build Command `pip install -r requirements.txt` y Start Command `gunicorn app:app`.
3. En variables de entorno configurar `SECRET_KEY` (cadena aleatoria larga), `ADMIN_USER` y `ADMIN_PASSWORD` (secreto propio, diferente del valor de ejemplo).
4. Esperar el despliegue y abrir la URL HTTPS que proporcione Render. Verificar desde una ventana de incógnito.
5. Registrar esa URL y las credenciales **de prueba** en el documento de evidencias.

**Advertencia importante sobre hosting gratuito:** Render puede suspender servicios gratuitos y su sistema de archivos puede ser efímero. SQLite en almacenamiento efímero puede perder los datos al reiniciar o redesplegar el servicio. Esta configuración es adecuada únicamente para una demostración temporal con datos ficticios. Para persistencia real se requiere una base de datos durable y adaptar `app.py` a ella (por ejemplo PostgreSQL administrado); este paquete NO implementa esa migración. La disponibilidad del 95% no está garantizada en alojamiento gratuito.

## Prueba manual sugerida

1. Iniciar sesión.
2. Crear producto `LL-001` / Llanta / 80000 COP / stock 5.
3. Crear cliente `123456` / Cliente Demo.
4. Registrar venta a crédito de 2 llantas a Cliente Demo. Stock esperado: 3; saldo pendiente: 160000.
5. Registrar abono de 60000. Saldo esperado: 100000.
6. Intentar venta de 10 llantas: debe rechazarse y mantener stock 3.
7. Revisar informe de ventas, inventario y saldos.
8. Cerrar sesión.

## Alcance de esta versión

Ventas de un producto por transacción, edición de clientes/productos, reportes en pantalla, un usuario administrador y registro de abonos. No incluye facturación DIAN ni pagos en línea. Falta endurecimiento para producción (CSRF, manejo de sesiones, permisos granulares, respaldos programados, almacenamiento persistente).
