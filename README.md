# mixitupbot_scripting_interface
## running the program
to run this program, you'll need to have python 2.7.13 installed.
You can try to just double click mxpy.py (or mxpy if you don't see extensions). If you're lucky i'll run.
If not, you open click on File Explorer and locate the place where you placed this folder, go inside it. Then open the File menu (top left blue button) and select "Open Windows Powershell" or "Open Command Prompt" depending on your settings and windows version.
then copy and paste `python -m mxpy` into the shell that opened and press enter

## Settings
you will need to configure some settings to let the program know it is you, copy the 'settingsM.json.example' file and call it settingsM.json
now open it and fill in your username and channel name. For now, you also need a secret_key and client_id for those you can either make an OAuth client on (https://mixer.com/lab/oauth)[mixer dev lab] or contact me. (i will update this)
if you make an OAuth client yourself, enable secret key and fill in 'localhost' as host.
Do this before running the program (or restart afterwards)

## loading scripts
just put your script folders (unpack them if they are zipped) in the scripts folder you see in the map, and they will be automatically loaded!

## issues
any problems? make an issue or contact me at mi_thom@hotmail.com
