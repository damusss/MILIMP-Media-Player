"""
Executable creation steps:
1. delete the old executable
2. create the new executable using pyinstaler without a console and with a custom icon
3. copy the executable from the dist folder to the main folder
4. delete the spec file
5. delete the dist folder and its contents
6. delete the build folder and its contents
"""

import os
import shutil

MP = "MILIMP"
EMBED = "ytembed"
icon = {MP: "playlist", EMBED: "playc"}
SKIP = []

for app in [MP, EMBED]:
    if app in SKIP:
        continue
    if os.path.exists(f"{app}.exe"):
        os.remove(f"{app}.exe")

    os.system(
        f"pyinstaller --onefile --icon=appdata/icons/{icon[app]}.png --windowed {app}.py"
    )

    shutil.copyfile(f"dist/{app}.exe", f"{app}.exe")
    os.remove(f"{app}.spec")
    shutil.rmtree("dist")
    shutil.rmtree("build")
