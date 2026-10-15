"""Build a clean employee bundle without personal media, caches or test files."""
from pathlib import Path
import zipfile, shutil, json
ROOT=Path(__file__).resolve().parents[1]
SAMPLE=Path(json.loads((ROOT/'tests/http-mov-report.json').read_text(encoding='utf-8'))['export']).name
archive=ROOT/'수논사_릴스스튜디오_직원배포용.zip'
files=[ROOT/f for f in ['app.py','engine.py','launch.ps1','시작.cmd','install-fonts.ps1','폰트 설치.cmd','requirements.txt','먼저 읽어주세요.txt']]
for directory in ['web','assets','vendor',f'output/{SAMPLE}','output/pdf']:
    files += [p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
files += [ROOT/'docs'/name for name in ['manual.html','text-effects-screen.jpg','text-effects-controls.jpg','text-style-sample.png']]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(set(files)):
        if p.name in ('build-debug.aep','build-error.txt'):continue
        z.write(p,Path('릴스 스튜디오')/p.relative_to(ROOT))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all('/data/' not in n and '/tests/' not in n for n in z.namelist())
print(json.dumps({'archive':str(archive),'megabytes':round(archive.stat().st_size/1024**2,1),'files':len(files)},ensure_ascii=False))
