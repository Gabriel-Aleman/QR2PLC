# Streamlit + pycom — Escáner de QR a PLC

Aplicación web hecha con **Streamlit** que escanea códigos QR (desde cámara o imagen subida) y envía el valor leído a un **PLC Allen-Bradley / Logix** mediante la librería `pycomm3`.

## ¿Qué hace?

1. Al iniciar, se conecta al PLC y lee el tag `EnableScan` para saber si el escaneo está habilitado.
2. Si está habilitado, muestra dos pestañas:
   - 📸 **Usar cámara**: toma una foto en vivo.
   - 🖼️ **Subir imagen**: permite cargar un archivo (`png`, `jpg`, `jpeg`, `bmp`).
3. Detecta y decodifica el código QR con OpenCV (`cv2.QRCodeDetector`) y muestra la imagen con el QR marcado.
4. Si se detecta texto, se puede enviar con el botón **"📤 Enviar QR al PLC"**, que escribe el valor en el tag `QR_Code` del PLC.
5. Si el contenido del QR es una URL, se muestra un botón para abrirla directamente.
6. En la barra lateral hay un acceso directo a una aplicación externa (OPTIX) en `http://localhost:443/`.

## Estructura de archivos

| Archivo | Descripción |
|---|---|
| `app.py` | Aplicación principal de Streamlit. |
| `requirements.txt` | Dependencias de Python (`streamlit`, `opencv-python-headless`, `Pillow`, `numpy`, `pycomm3`). |
| `Dockerfile` | Imagen Docker para desplegar la app (expone el puerto `8501`). |
| `runApp.bat` | Script de Windows que instala dependencias y ejecuta la app con Streamlit. |
| `StartApp.vbs` | Ejecuta `runApp.bat` en segundo plano (sin ventana de consola). |
| `StopApp.vbs` | Detiene la app matando el proceso que usa el puerto `8501`. |
| `test.py` | Script de prueba rápida de conexión y escritura de tags en el PLC. |

## Configuración

En `app.py`, ajustar según el proyecto:

```python
PLC_IP    = "10.16.20.20"   # IP del PLC
tagName   = "QR_Code"       # Tag donde se escribe el QR leído
tagStatus = "EnableScan"    # Tag booleano que habilita/deshabilita el escaneo
```

## Ejecución

### Opción 1: local (Windows)
Doble clic en `StartApp.vbs` (o ejecutar `runApp.bat`), y `StopApp.vbs` para detenerla.

### Opción 2: manual
```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

### Opción 3: Docker
```bash
docker build -t qr2plc-streamlit .
docker run -p 8501:8501 qr2plc-streamlit
```
> Nota: el `Dockerfile` referencia `lector_qr.py`; si se usa Docker, ajustar ese nombre a `app.py` o renombrar el archivo.

## Requisitos previos

- Python 3.11+ (o el runtime del Dockerfile).
- PLC Allen-Bradley/Logix accesible en red desde donde corre la app.
- Tags `QR_Code` y `EnableScan` creados en el PLC.