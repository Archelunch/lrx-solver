#!/usr/bin/env python3
"""Build an explicit artifact allow-list; never include account or runtime data."""
from pathlib import Path
import hashlib, json, zipfile

root=Path(__file__).resolve().parents[2]
destination=root/'handoff/2026-09-23'
destination.mkdir(parents=True,exist_ok=True)
folders=['experiments/cycle6','reports/cycle6','research/cycle6','runs/cycle6','sources/2026-09-23-marked-zero']
allowed={'.py','.cpp','.md','.json','.lean','.tex','.pdf','.log','.stdout','.stderr'}
files=sorted(p for folder in folders for p in (root/folder).rglob('*')
             if p.is_file() and p.suffix in allowed and p.name!='EVIDENCE_MANIFEST.json')
required=['research/cycle6/cloud-proof/REVIEW_FINAL.md',
          'research/cycle6/cloud-proof/proof_packed_audit.json',
          'research/cycle6/cloud-proof/proof_full_slack_audit.json',
          'research/cycle6/cloud-proof/proof_final_addendum.json']
for relative in required:assert (root/relative).is_file(),relative
entries=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,
          'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
manifest={'scope':'Explicit cycle-6 research files only; hashes establish integrity, not mathematical truth.',
          'source_date':'2026-09-23','human_reviewed':False,'files':entries}
manifest_text=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
(root/'reports/cycle6/EVIDENCE_MANIFEST.json').write_text(manifest_text)
readme='''# LRX: контрпример к абсолютному радиусу проекции

23 сентября 2026. Начните с reports/cycle6/RESULTS.md.

При m=8,r=3 и v=(2,1,0,0,0,7,8,6,5,4,3): P=42, d(v)=47,
A_42(v)=49>48. Кандидат A_P<=P+m-2 опровергнут точным конечным
расчётом двух независимых алгоритмов. Основная гипотеза НЕ опровергнута.

Воспроизведение из этой папки:

    python3 experiments/cycle6/reproduce.py
    python3 experiments/cycle6/reproduce.py --full
    python3 experiments/cycle6/reproduce.py --extended

Первый режим: stdlib Python, малые графы и replay слов.
--full: полный нижний сертификат контрпримера; требуется clang++ или g++ C++17.
--extended: также соседние размеры. Запуски создают новые файлы.

План: research/cycle6/PROJECT.md.
Рецензия: research/cycle6/cloud-proof/REVIEW_FINAL.md.
Уточнение версии исходников: reports/cycle6/SOURCE_VERSION_NOTE.md.
Следующий проход: reports/cycle6/NEXT_PASS.md.
Реестр утверждений: reports/cycle6/claims.json.
Целостность: MANIFEST.json. Проверка: python3 verify_bundle.py

Отчёт подготовлен ИИ; человеческая рецензия пока не выполнена.
Lean-файлы проверяют только вспомогательные/условные леммы,
не полное перечисление графов и не общую гипотезу.
'''
verifier='''from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent
m=json.loads((r/'MANIFEST.json').read_text())
for x in m['files']:
 p=r/x['path'];assert p.is_file(),x['path']
 assert p.stat().st_size==x['bytes'],x['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
print('SHA-256 verified:',len(m['files']),'files. Integrity only; run --full for the mathematical certificate.')
'''
archive=destination/'lrx-radius-slack-20260923.zip'
prefix='lrx-radius-slack-20260923/'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,prefix+str(p.relative_to(root)))
 z.writestr(prefix+'MANIFEST.json',manifest_text)
 z.writestr(prefix+'README.md',readme)
 z.writestr(prefix+'verify_bundle.py',verifier)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for x in entries:
  assert hashlib.sha256(z.read(prefix+x['path'])).hexdigest()==x['sha256']
receipt={'archive':str(archive),'bytes':archive.stat().st_size,
         'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(files),'zip_and_hash_checks':True}
(destination/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
