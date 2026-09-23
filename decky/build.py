#!/usr/bin/env python3
"""Package the existing Decky runtime JS and the canonical charge helper."""
from pathlib import Path
import shutil
import zipfile

root = Path(__file__).resolve().parent
(root / 'dist').mkdir(exist_ok=True)
shutil.copyfile(root / 'src/index.js', root / 'dist/index.js')
shutil.copyfile(root.parent / 'charge-control/system/charge-helper', root / 'scripts/charge-helper')
files = ['main.py', 'plugin.json', 'package.json', 'LICENSE', 'README.md',
         'dist/index.js', 'scripts/charge-helper', 'scripts/wifi-recovery.sh']
with zipfile.ZipFile(root / 'ApexFixes.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root / name, 'ApexFixes/' + name)
print(root / 'ApexFixes.zip')
