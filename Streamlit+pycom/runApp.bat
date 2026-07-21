@echo off
echo Instalando dependencias...
python -m pip install -r requirements.txt

echo Iniciando la aplicacion...
python -m streamlit run lector_qr.py

pause