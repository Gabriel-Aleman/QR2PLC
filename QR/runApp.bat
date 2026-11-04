@echo off

REM Ir a la carpeta donde se encuentra app.py
cd /d "C:\QR"
echo Iniciando la aplicacion...
python -m streamlit run app.py --server.port 8501
pause