.\venv\Scripts\activate &&^
pyinstaller PyChatter.py -F ^
    --add-data README.md;. ^
    --add-data data/script_interface.key;data ^
    --add-data data/script_interface.crt;data ^
    --noconfirm ^
    --log-level DEBUG ^
    --debug &&^
deactivate