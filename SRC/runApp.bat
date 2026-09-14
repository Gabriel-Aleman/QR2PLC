@echo off

echo Instalando dependencias...
python -m pip install -r requirements.txt

REM Ir a la carpeta donde se encuentra app.py
cd /d "C:\Users\galeman\OneDrive - ELVATRON S.A\Desktop\QR2PLC\Streamlit+pycom"

echo Iniciando la aplicacion...
python -m streamlit run app.py --server.port 8501

pause