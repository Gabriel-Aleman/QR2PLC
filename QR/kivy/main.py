"""
Escáner de códigos QR para Android (Kivy)
-----------------------------------------
Migración de la app de Streamlit. Escanea códigos QR con la cámara
en vivo o desde una imagen de la galería, y envía el contenido a un
PLC Allen-Bradley (Logix) usando pycomm3.

Probar en PC:
    pip install kivy==2.3.0 opencv-python numpy plyer pycomm3
    python main.py

Compilar APK (Linux / WSL):
    pip install buildozer
    buildozer android debug
"""
import threading
import time
import webbrowser

import cv2
import numpy as np
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.factory import Factory
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             StringProperty)
from kivy.storage.jsonstore import JsonStore
from kivy.uix.image import Image
from kivy.utils import platform
from pycomm3 import LogixDriver

# --- Configuración PLC ------------------------------------------------------
PLC_IP_DEFAULT = "192.168.1.1"          # IP inicial (se puede cambiar en la app)
OPTIX_URL = "http://192.168.1.2:9091/"
TAG_QR = "QR_Code"
TAG_ENABLE = "EnableScan"

# En la versión de Streamlit la lectura de EnableScan estaba comentada
# (status=True). Pon True para que la app consulte el tag periódicamente.
CHECK_ENABLE_TAG = False
ENABLE_POLL_SECONDS = 2.0

SCAN_INTERVAL = 0.4                     # segundos entre análisis de cuadros
IS_ANDROID = platform == "android"

STATUS_COLORS = {
    "info": [0.65, 0.75, 0.90, 1],
    "ok": [0.35, 0.85, 0.45, 1],
    "warn": [0.98, 0.78, 0.30, 1],
    "error": [0.95, 0.40, 0.40, 1],
}

KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<RotatedCamera@Camera>:
    canvas.before:
        PushMatrix
        Rotate:
            angle: app.camera_angle
            origin: self.center
    canvas.after:
        PopMatrix

# Nombres propios (QrBoton, QrModo) para no chocar con widgets de Kivy.
<QrBoton@Button>:
    fondo: (0.16, 0.45, 0.85, 1)
    font_size: sp(17)
    color: 1, 1, 1, 1
    disabled_color: 0.72, 0.75, 0.78, 1
    background_normal: ''
    background_down: ''
    background_disabled_normal: ''
    background_disabled_down: ''
    background_color: 0, 0, 0, 0
    halign: 'center'
    valign: 'middle'
    text_size: self.width - dp(12), None
    canvas.before:
        Color:
            rgba: (0.25, 0.27, 0.30, 1) if self.disabled else ([c * 0.8 for c in self.fondo[:3]] + [1] if self.state == 'down' else self.fondo)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]

<QrModo@ToggleButton>:
    font_size: sp(17)
    color: 1, 1, 1, 1
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    group: 'mode'
    allow_no_selection: False
    canvas.before:
        Color:
            rgba: (0.17, 0.56, 0.79, 1) if self.state == 'down' else (0.23, 0.25, 0.28, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]

<QrCampo@TextInput>:
    font_size: sp(18)
    background_normal: ''
    background_active: ''
    background_color: 0.95, 0.96, 0.97, 1
    foreground_color: 0.08, 0.09, 0.11, 1
    cursor_color: 0.16, 0.45, 0.85, 1
    padding: dp(14), (self.height - self.line_height) / 2

BoxLayout:
    orientation: 'vertical'
    padding: dp(20), dp(16), dp(20), dp(20)
    spacing: dp(14)
    canvas.before:
        Color:
            rgba: 0.08, 0.09, 0.11, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(12)
        Label:
            text: 'Escáner de códigos QR'
            bold: True
            font_size: sp(24)
            text_size: self.size
            halign: 'left'
            valign: 'middle'
        QrBoton:
            text: 'OPTIX'
            fondo: (0.23, 0.25, 0.28, 1)
            size_hint_x: None
            width: dp(110)
            on_release: app.open_optix()

    BoxLayout:
        size_hint_y: None
        height: dp(50)
        spacing: dp(12)
        Label:
            text: 'IP del PLC'
            font_size: sp(17)
            color: 0.79, 0.82, 0.86, 1
            size_hint_x: None
            width: dp(96)
            text_size: self.size
            halign: 'left'
            valign: 'middle'
        QrCampo:
            id: ip_input
            multiline: False
            input_filter: lambda t, undo: ''.join(c for c in t if c.isdigit() or c == '.')
            on_text: app.set_plc_ip(self.text)

    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(12)
        QrModo:
            id: btn_camera
            text: 'Usar cámara'
            state: 'down'
            on_release: app.show_camera()
        QrModo:
            id: btn_image
            text: 'Subir imagen'
            on_release: app.pick_image()

    # Panel de vista previa: recorta la cámara para que no se salga.
    StencilView:
        id: preview_clip
        canvas.before:
            Color:
                rgba: 0.05, 0.055, 0.07, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(10)]
        FloatLayout:
            id: preview
            pos: preview_clip.pos
            size: preview_clip.size
            Image:
                id: result_image
                opacity: 0
                fit_mode: 'contain'
                size_hint: 0.94, 0.94
                pos_hint: {'center_x': 0.5, 'center_y': 0.5}

    Label:
        text: app.status_text
        color: app.status_color
        font_size: sp(18)
        bold: True
        size_hint_y: None
        height: self.texture_size[1] + dp(6)
        text_size: self.width, None
        halign: 'center'

    QrCampo:
        text: app.qr_text
        readonly: True
        multiline: False
        font_name: 'RobotoMono-Regular'
        font_size: sp(17)
        size_hint_y: None
        height: dp(60) if app.qr_text else 0
        opacity: 1 if app.qr_text else 0

    GridLayout:
        cols: 3
        size_hint_y: None
        height: dp(60)
        spacing: dp(12)
        QrBoton:
            text: 'Enviando...' if app.sending else 'Enviar QR al PLC'
            disabled: (not app.qr_text) or app.sending or (not app.scan_enabled)
            on_release: app.send_to_plc()
        QrBoton:
            text: 'Ir a la página'
            disabled: not app.qr_is_url
            on_release: app.open_qr_url()
        QrBoton:
            text: 'Escanear de nuevo'
            on_release: app.show_camera()
"""


class DesktopCamera(Image):
    """Cámara para PC usando OpenCV directamente.

    El proveedor de cámara de Kivy para OpenCV falla con versiones recientes
    de OpenCV ('CameraOpenCV' object has no attribute 'fps'), así que en
    escritorio se lee la webcam con cv2.VideoCapture. En Android se sigue
    usando la cámara nativa de Kivy.
    """
    play = BooleanProperty(False)

    def __init__(self, index=0, **kwargs):
        super().__init__(**kwargs)
        backend = cv2.CAP_DSHOW if platform == "win" else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(index, backend)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            raise RuntimeError("no se encontró ninguna webcam")
        self.frame_bgr = None
        self._event = Clock.schedule_interval(self._update, 1 / 30)

    def _update(self, dt):
        if not self.play:
            return
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return
        self.frame_bgr = frame
        rgb = cv2.flip(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), 0)
        h, w = rgb.shape[:2]
        tex = self.texture
        if tex is None or tex.size != (w, h):
            tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.blit_buffer(rgb.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
        self.texture = tex
        self.canvas.ask_update()

    def release(self):
        self._event.cancel()
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class QRScannerApp(App):
    plc_ip = StringProperty(PLC_IP_DEFAULT)
    status_text = StringProperty("Iniciando...")
    status_color = ListProperty(STATUS_COLORS["info"])
    qr_text = StringProperty("")
    qr_is_url = BooleanProperty(False)
    sending = BooleanProperty(False)
    scanning = BooleanProperty(False)
    scan_enabled = BooleanProperty(True)
    # En Android el sensor entrega la imagen en horizontal; se rota en pantalla.
    camera_angle = NumericProperty(-90 if IS_ANDROID else 0)

    def build(self):
        self.title = "Escáner de QR"
        self.detector = cv2.QRCodeDetector()
        self.camera = None
        self.store = JsonStore(f"{self.user_data_dir}/config.json")
        if self.store.exists("plc"):
            self.plc_ip = self.store.get("plc").get("ip", PLC_IP_DEFAULT)
        return Builder.load_string(KV)

    def on_start(self):
        self.root.ids.ip_input.text = self.plc_ip
        if IS_ANDROID:
            from android.permissions import Permission, request_permissions
            request_permissions([Permission.CAMERA], self._on_permissions)
        else:
            self._start_camera()
        self._start_enable_monitor()

    def on_pause(self):
        if self.camera:
            self.camera.play = False
        return True

    def on_stop(self):
        if isinstance(self.camera, DesktopCamera):
            self.camera.release()

    def on_resume(self):
        if self.camera and self.scanning:
            self.camera.play = True

    # --- Utilidades ---------------------------------------------------------
    def set_status(self, text, kind="info"):
        self.status_text = text
        self.status_color = STATUS_COLORS.get(kind, STATUS_COLORS["info"])

    def set_plc_ip(self, ip):
        self.plc_ip = ip.strip()
        try:
            self.store.put("plc", ip=self.plc_ip)
        except Exception:
            pass

    def open_optix(self):
        webbrowser.open(OPTIX_URL)

    def open_qr_url(self):
        if self.qr_is_url:
            webbrowser.open(self.qr_text)

    # --- Cámara -------------------------------------------------------------
    @mainthread
    def _on_permissions(self, permissions, grants):
        if all(grants):
            self._start_camera()
        else:
            self.set_status(
                "Sin permiso de cámara. Puedes usar 'Subir imagen'.", "warn")

    def _start_camera(self):
        try:
            common = dict(fit_mode="contain", size_hint=(1, 1),
                          pos_hint={"x": 0, "y": 0})
            if IS_ANDROID:
                self.camera = Factory.RotatedCamera(
                    index=0, resolution=(640, 480), play=True, **common)
            else:
                self.camera = DesktopCamera(index=0, play=True, **common)
        except Exception as e:
            self.set_status(f"No se pudo abrir la cámara: {e}", "error")
            return
        preview = self.root.ids.preview
        # Índice alto = se dibuja debajo de la imagen de resultado.
        preview.add_widget(self.camera, index=len(preview.children))
        Clock.schedule_interval(self._scan_frame, SCAN_INTERVAL)
        self.show_camera()

    def show_camera(self):
        self.root.ids.btn_camera.state = "down"
        self.root.ids.btn_image.state = "normal"
        self.root.ids.result_image.opacity = 0
        self._clear_result()
        if self.camera is None:
            self.set_status("Cámara no disponible. Usa 'Subir imagen'.", "warn")
            return
        self.camera.opacity = 1
        self.camera.play = True
        self.scanning = True
        if self.scan_enabled:
            self.set_status("Apunta la cámara al código QR...")

    def _stop_camera(self):
        self.scanning = False
        if self.camera:
            self.camera.play = False
            self.camera.opacity = 0

    def _scan_frame(self, dt):
        if not (self.scanning and self.scan_enabled and self.camera):
            return
        if isinstance(self.camera, DesktopCamera):
            bgr = self.camera.frame_bgr
            if bgr is not None:
                texto, points = self._decode(bgr)
                if texto:
                    self._show_result(texto, bgr, points)
            return
        tex = self.camera.texture
        if tex is None:
            return
        try:
            frame = np.frombuffer(tex.pixels, np.uint8).reshape(
                tex.height, tex.width, 4)
        except ValueError:
            return
        # Los píxeles de la textura vienen con el origen abajo-izquierda.
        frame = np.ascontiguousarray(np.flipud(frame))
        for candidate in (frame, np.ascontiguousarray(np.flipud(frame))):
            bgr = cv2.cvtColor(candidate, cv2.COLOR_RGBA2BGR)
            texto, points = self._decode(bgr)
            if texto:
                if IS_ANDROID:
                    bgr = cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
                    texto2, points2 = self._decode(bgr)
                    points = points2 if texto2 else None
                self._show_result(texto, bgr, points)
                return

    # --- Imagen desde galería ----------------------------------------------
    def pick_image(self):
        self._stop_camera()
        self._clear_result()
        self.root.ids.result_image.opacity = 0
        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._on_file_selected,
                filters=[["Imágenes", "*.png", "*.jpg", "*.jpeg", "*.bmp"]])
            self.set_status("Selecciona una imagen con un código QR...")
        except Exception as e:
            self.set_status(f"No se pudo abrir el selector: {e}", "error")

    @mainthread
    def _on_file_selected(self, selection):
        if not selection:
            self.set_status("No se seleccionó ninguna imagen.", "warn")
            return
        try:
            data = np.fromfile(selection[0], dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            img = None
        if img is None:
            self.set_status("No se pudo leer la imagen.", "error")
            return
        texto, points = self._decode(img)
        self._show_result(texto, img, points)

    # --- QR ----------------------------------------------------------------
    def _decode(self, bgr):
        try:
            texto, points, _ = self.detector.detectAndDecode(bgr)
        except cv2.error:
            return None, None
        return (texto or None), points

    def _show_result(self, texto, bgr, points):
        self._stop_camera()
        img = bgr.copy()
        if texto and points is not None:
            cv2.polylines(img, [points.astype(int)], True, (0, 255, 0), 3)
        self.root.ids.result_image.texture = self._to_texture(img)
        self.root.ids.result_image.opacity = 1

        if texto:
            self.qr_text = texto
            self.qr_is_url = texto.startswith(("http://", "https://"))
            self.set_status("Código QR detectado", "ok")
        else:
            self._clear_result()
            self.set_status(
                "No se detectó ningún código QR en la imagen. Intenta con "
                "mejor enfoque, iluminación o acercando la cámara.", "warn")

    def _clear_result(self):
        self.qr_text = ""
        self.qr_is_url = False

    @staticmethod
    def _to_texture(bgr):
        rgb = cv2.flip(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), 0)
        h, w = rgb.shape[:2]
        tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.blit_buffer(rgb.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
        return tex

    # --- PLC ---------------------------------------------------------------
    def send_to_plc(self):
        if not self.qr_text or self.sending:
            return
        self.sending = True
        self.set_status(f"Enviando al PLC {self.plc_ip}...")
        threading.Thread(target=self._send_worker,
                         args=(self.plc_ip, self.qr_text),
                         daemon=True).start()

    def _send_worker(self, ip, texto):
        try:
            with LogixDriver(ip) as plc:
                resultado = plc.write((TAG_QR, texto))
            if resultado:
                ok, msg = True, "Código enviado al PLC correctamente."
            else:
                err = getattr(resultado, "error", "") or ""
                ok, msg = False, f"No fue posible escribir el tag. {err}".strip()
        except Exception as e:
            ok, msg = False, f"Error de comunicación: {e}"
        self._on_send_done(ok, msg)

    @mainthread
    def _on_send_done(self, ok, msg):
        self.sending = False
        self.set_status(msg, "ok" if ok else "error")
        if ok:  # Equivalente al st.rerun(): volver a escanear.
            Clock.schedule_once(lambda dt: self.show_camera(), 1.5)

    def _start_enable_monitor(self):
        if CHECK_ENABLE_TAG:
            threading.Thread(target=self._enable_worker, daemon=True).start()

    def _enable_worker(self):
        while True:
            ip = self.plc_ip
            try:
                with LogixDriver(ip) as plc:
                    tag = plc.read(TAG_ENABLE)
                enabled = bool(tag.value) if tag else False
                err = None if tag else f"No se pudo leer el tag {TAG_ENABLE}."
            except Exception:
                enabled = False
                err = f"No se ha logrado encontrar el PLC con la IP {ip}"
            self._apply_enable(enabled, err)
            time.sleep(ENABLE_POLL_SECONDS)

    @mainthread
    def _apply_enable(self, enabled, err):
        changed = enabled != self.scan_enabled
        self.scan_enabled = enabled
        if not enabled:
            self.set_status(err or "El escaneo de códigos no está habilitado",
                            "error")
        elif changed and self.scanning:
            self.set_status("Apunta la cámara al código QR...")


if __name__ == "__main__":
    QRScannerApp().run()
