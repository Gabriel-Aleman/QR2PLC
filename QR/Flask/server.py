"""
Versión web sin librerías JS: el navegador envía imágenes de la cámara,
Python lee el QR con OpenCV y lo envía al PLC Allen-Bradley Logix.

Instalar:
    pip install flask pycomm3 opencv-python-headless numpy
Ejecutar:
    python web_qr_plc.py
Abrir en Edge/Chrome:
    http://localhost:5000
"""
import cv2
import numpy as np
from flask import Flask, request, jsonify
from pycomm3 import LogixDriver

# ===== CONFIGURACIÓN =====
PLC_IP = "192.168.1.10"   # CompactLogix: solo IP. ControlLogix: "192.168.1.10/0"
TAG = "CodigoQR"          # Tag tipo STRING en el PLC (controller tags)
# =========================

detector = cv2.QRCodeDetector()

PAGINA = open(r"C:\QR\Flask\ui.html", encoding="utf-8").read()


@app.route("/")
def inicio():
    return PAGINA


@app.route("/leer", methods=["POST"])
def leer():
    imagen = cv2.imdecode(np.frombuffer(request.data, np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        return jsonify(codigo="")
    codigo, _, _ = detector.detectAndDecode(imagen)
    return jsonify(codigo=codigo)


@app.route("/enviar", methods=["POST"])
def enviar():
    codigo = request.get_json().get("codigo", "")
    try:
        with LogixDriver(PLC_IP) as plc:
            res = plc.write((TAG, codigo))
        if res.error:
            return jsonify(ok=False, error=str(res.error))
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)