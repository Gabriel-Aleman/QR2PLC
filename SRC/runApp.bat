@echo off

echo Instalando dependencias...
python -m pip install -r requirements.txt

REM Ir a la carpeta donde se encuentra app.py
cd /d "C:\QR2PLC-0.1\QR2PLC-0.1\SRC"

echo Iniciando la aplicacion...
python -m streamlit run app.py --server.port 8501

pause