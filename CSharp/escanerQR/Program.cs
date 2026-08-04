using System;
using System.Drawing;
using System.Windows.Forms;
using AForge.Video;
using AForge.Video.DirectShow;
using ZXing;
using ZXing.Windows.Compatibility;

namespace QrScannerAuto
{
    internal static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.SetHighDpiMode(HighDpiMode.SystemAware);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ScannerForm());
        }
    }

    /// <summary>
    /// Ventana única: apenas abre, prende la cámara. Cuando detecta un QR,
    /// muestra el contenido y cierra la aplicación automáticamente.
    /// El botón X también cierra correctamente en cualquier momento.
    /// </summary>
    public class ScannerForm : Form
    {
        private readonly PictureBox pictureBoxCamera;
        private readonly BarcodeReader barcodeReader;

        private FilterInfoCollection? videoDevices;
        private VideoCaptureDevice? videoSource;

        private int frameCounter = 0;
        private volatile bool qrEncontrado = false;
        private volatile bool cerrando = false;

        public ScannerForm()
        {
            Text = "Escaneando QR...";
            Width = 640;
            Height = 520;
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;

            pictureBoxCamera = new PictureBox
            {
                Dock = DockStyle.Fill,
                BackColor = Color.Black,
                SizeMode = PictureBoxSizeMode.Zoom
            };
            Controls.Add(pictureBoxCamera);

            barcodeReader = new BarcodeReader
            {
                AutoRotate = true,
                Options =
                {
                    PossibleFormats = new[] { BarcodeFormat.QR_CODE },
                    TryHarder = true
                }
            };

            Load += ScannerForm_Load;
            FormClosing += ScannerForm_FormClosing;
        }

        private void ScannerForm_Load(object? sender, EventArgs e)
        {
            try
            {
                videoDevices = new FilterInfoCollection(FilterCategory.VideoInputDevice);

                if (videoDevices.Count == 0)
                {
                    MessageBox.Show("No se detectó ninguna cámara conectada.", "Sin cámara",
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    Close();
                    return;
                }

                // Usa la primera cámara disponible
                videoSource = new VideoCaptureDevice(videoDevices[0].MonikerString);
                videoSource.NewFrame += VideoSource_NewFrame;
                videoSource.Start();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"No se pudo iniciar la cámara: {ex.Message}", "Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                Close();
            }
        }

        // IMPORTANTE: este evento corre en el hilo propio de la cámara (AForge),
        // nunca en el hilo de la interfaz. Por eso todo lo que toca la UI se
        // manda con BeginInvoke (asíncrono) y jamás se llama WaitForStop() desde
        // acá: si lo hiciéramos, este hilo quedaría esperando a la UI mientras la
        // UI queda esperando a este hilo -> deadlock y la ventana no cierra nunca.
        private void VideoSource_NewFrame(object sender, NewFrameEventArgs eventArgs)
        {
            if (qrEncontrado || cerrando) return;

            using var frame = (Bitmap)eventArgs.Frame.Clone();

            // Mostrar el video en la ventana (fire-and-forget, no bloquea este hilo)
            var frameParaMostrar = (Bitmap)frame.Clone();
            TryBeginInvoke(() =>
            {
                var anterior = pictureBoxCamera.Image;
                pictureBoxCamera.Image = frameParaMostrar;
                anterior?.Dispose();
            });

            // Decodificar cada 3 frames para no saturar la CPU
            frameCounter++;
            if (frameCounter % 3 != 0) return;

            try
            {
                var resultado = barcodeReader.Decode(frame);
                if (resultado != null && !string.IsNullOrWhiteSpace(resultado.Text))
                {
                    qrEncontrado = true; // evita procesar más frames
                    string contenido = resultado.Text;
                    TryBeginInvoke(() => MostrarResultadoYCerrar(contenido));
                }
            }
            catch
            {
                // Frame sin QR legible, se sigue intentando
            }
        }

        private void TryBeginInvoke(Action accion)
        {
            try
            {
                if (IsHandleCreated && !IsDisposed && !cerrando)
                    BeginInvoke(accion);
            }
            catch (ObjectDisposedException) { /* la ventana ya se cerró, se ignora */ }
            catch (InvalidOperationException) { /* handle destruido, se ignora */ }
        }

        private void MostrarResultadoYCerrar(string contenido)
        {
            if (cerrando) return;

            DesuscribirYDetener();

            MessageBox.Show(
                $"Contenido del QR:\n\n{contenido}",
                "Código QR detectado",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);

            Close();
        }

        private void ScannerForm_FormClosing(object? sender, FormClosingEventArgs e)
        {
            DesuscribirYDetener();
        }

        // Deja de recibir frames y le pide a la cámara que se detenga, SIN
        // bloquear el hilo de la UI esperando (WaitForStop). AForge libera el
        // dispositivo por su cuenta en su propio hilo apenas puede.
        private void DesuscribirYDetener()
        {
            if (cerrando) return;
            cerrando = true;

            var source = videoSource;
            videoSource = null;

            if (source != null)
            {
                source.NewFrame -= VideoSource_NewFrame;
                if (source.IsRunning)
                {
                    source.SignalToStop();
                }
            }
        }
    }
}