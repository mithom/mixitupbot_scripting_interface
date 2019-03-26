.\venv\Scripts\activate &&^
pyinstaller PyChatter.py -F ^
    --hidden-import sqlite3 ^
    --hidden-import dotnet ^
    --add-data clr.py;. ^
    --add-binary .\venv\Lib\site-packages\_sounddevice_data\portaudio-binaries\libportaudio64bit.dll;.\_sounddevice_data\portaudio-binaries ^
    --add-binary .\venv\Lib\site-packages\_soundfile_data\libsndfile64bit.dll;_soundfile_data ^
    --add-data README.md;. ^
    --add-data data/script_interface.key;data ^
    --add-data data/script_interface.crt;data ^
    --noconfirm ^
    --clean ^
    --debug &&^
deactivate