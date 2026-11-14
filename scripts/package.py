"""Build frontend first. Package immutable ZIP without AWS credentials."""
import shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
shutil.copytree(root/'dist',root/'backend/staticfiles',dirs_exist_ok=True)
(root/'.deploy').mkdir(exist_ok=True)
with zipfile.ZipFile(root/'.deploy/backend-latest.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in (root/'backend').rglob('*'):
  if f.is_file() and '__pycache__' not in str(f):z.write(f,str(f.relative_to(root)))
print('Packaged .deploy/backend-latest.zip')
