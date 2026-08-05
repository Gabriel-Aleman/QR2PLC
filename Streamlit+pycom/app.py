"""
Escáner de códigos QR con Streamlit
------------------------------------
Permite escanear un código QR usando la cámara del dispositivo
o subiendo una imagen desde el equipo.

Requisitos:
    pip install streamlit opencv-python-headless numpy

Ejecutar:
    streamlit run qr_scanner_app.py
"""
from pycomm3 import LogixDriver
import streamlit as st
import numpy as np
import time
import cv2

#Tags y PLC
PLC_IP      = "10.16.20.20"   # Cambiar por la ip del PLC
tagName     = "QR_Code"
tagStatus   = "EnableScan"

#
with LogixDriver(PLC_IP) as plc:
    status =    (plc.read(tagStatus))
    status =    bool(status.value)



st.set_page_config(page_title="Escáner de QR", page_icon="📷", layout="centered")

st.title("📷 Escáner de códigos QR")
st.write(
    "Usa la cámara para tomar una foto de un código QR, o sube una imagen. "
    "La app detectará y decodificará el contenido automáticamente."
)

detector = cv2.QRCodeDetector()


def decode_qr(image_bytes: bytes):
    """Recibe bytes de imagen y devuelve (texto, imagen_con_marcas) o (None, imagen)."""
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        return None, None

    texto, points, _ = detector.detectAndDecode(img)

    if points is not None and texto:
        cv2.polylines(
            img,
            [points.astype(int)],
            True,
            (0, 255, 0),
            3
        )

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    return texto if texto else None, img

#Aplicación:
#----------------------------------------------------------------------------------------
with st.sidebar:
    st.link_button("⚙️ Aplicación OPTIX", "http://localhost:443/")
        
if(status): #Habilitar el uso de la aplicación:

    tab1, tab2 = st.tabs(["📸 Usar cámara", "🖼️ Subir imagen"])

    image_bytes = None

    with tab1:  #Utilizar cámara
        camera_photo = st.camera_input("Apunta la cámara al código QR")
        if camera_photo is not None:
            image_bytes = camera_photo.getvalue()

    with tab2:  #Cargar imagen
        uploaded_file = st.file_uploader(
            "Sube una imagen con un código QR", type=["png", "jpg", "jpeg", "bmp"]
        )
        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()

    if image_bytes is not None:
        texto, img_procesada = decode_qr(image_bytes)

        if img_procesada is not None:
            st.image(
                img_procesada,
                caption="Imagen analizada",
                use_container_width=True
            )

        if texto:
            st.success("✅ Código QR detectado")
            st.code(texto, language=None)

            if st.button("📤 Enviar QR al PLC", use_container_width=True):

                try:
                    with LogixDriver(PLC_IP) as plc:
                        resultado = plc.write((tagName, texto))

                    if resultado:
                        st.success("Código enviado al PLC correctamente.")
                        st.html("""
                        <script>
                        window.location.reload();
                        </script>
                        """)
                    else:
                        st.error("No fue posible escribir el tag.")

                except Exception as e:
                    st.error(f"Error de comunicación: {e}")
                

            # Si el contenido parece una URL, mostrar un botón que lleva a la página
            if texto.startswith(("http://", "https://")):
                st.link_button(
                    "🔗 Ir a la página",
                    texto,
                    use_container_width=True
                )

        else:
            st.warning(
                "⚠️ No se detectó ningún código QR en la imagen. "
                "Intenta de nuevo con mejor enfoque, iluminación o acercando la cámara."
            )

    else:
        st.info("Esperando una imagen desde la cámara o un archivo subido...")

else:
    st.error("El escaneo de códigos no está habilitado") 