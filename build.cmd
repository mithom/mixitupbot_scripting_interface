cd .\venv\Scripts\activate
pyinstaller PyChatter.py --onedir ^
    --add-data settingsM.json;. ^
    --add-data README.md;. ^
    --add-data script_interface.key;. ^
    --add-data script_interface.crt;. ^
    --noconfirm