from pycomm3 import LogixDriver
import streamlit as st
from PIL import Image
import numpy as np
import cv2

st.set_page_config(page_title="Lector de QR", page_icon="📷")
st.title("📷 Lector de código QR")

# Elegir el origen de la imagen
opcion = st.radio("Elige una opción:", ["Subir foto", "Usar cámara"])

imagen = None
if opcion == "Subir foto":
    archivo = st.file_uploader("Sube una imagen con un QR", type=["png", "jpg", "jpeg"])
    if archivo is not None:
        imagen = Image.open(archivo)
else:
    foto = st.camera_input("Toma una foto del QR")
    if foto is not None:
        imagen = Image.open(foto)

# Procesar la imagen si existe
if imagen is not None:
    st.image(imagen, caption="Imagen capturada", use_container_width=True)

    # Convertir a formato compatible con OpenCV
    imagen_np = np.array(imagen.convert("RGB"))
    imagen_cv = cv2.cvtColor(imagen_np, cv2.COLOR_RGB2BGR)

    # Detectar y decodificar el QR
    detector = cv2.QRCodeDetector()
    datos, bbox, _ = detector.detectAndDecode(imagen_cv)

    if datos:
        st.success("✅ Código QR detectado:")
        st.code(datos)
    else:
        st.warning("⚠️ No se detectó ningún código QR en la imagen.")