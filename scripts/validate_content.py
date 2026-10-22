import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import tx,Base,engine
from app.models import Challenge
from app.catalog import seed,digest
from app.validation import executable_validation

manifest_path=Path(__file__).resolve().parents[1]/'content'/'validation.json'
prior_attestations=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
Base.metadata.create_all(engine)
with tx() as db:
    seed(db)
    current_seeded=list(db.scalars(select(Challenge).where(Challenge.author=='seed',Challenge.status.in_(['published','draft']))))
    current_digests={digest(c.content) for c in current_seeded}
    records=[]
    for c in current_seeded:
        attestation=prior_attestations.get(digest(c.content),{})
        if attestation.get('ok') and attestation.get('executed'):
            continue
        records.append((c.id,c.slug,c.content))
records_by_id={record[0]:record for record in records}
def check(record):
    id,slug,content=record
    return id,slug,executable_validation(content)
failures=[]
validated=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    for task in as_completed([pool.submit(check,r) for r in records]):
        id,slug,report=task.result()
        with tx() as db:
            c=db.get(Challenge,id);c.validation=report
        print(('PASS' if report['ok'] else 'FAIL'),slug,flush=True)
        if not report['ok']:failures.append(slug)
        else:validated.append((records_by_id[id][2],report))
print(f'{len(records)-len(failures)}/{len(records)} new challenge versions passed executable validation.',flush=True)
if not failures:
    # Keep the manifest aligned with current seeded versions; edits invalidate
    # the old hash and obsolete attestations must not accumulate indefinitely.
    manifest={key:value for key,value in prior_attestations.items() if key in current_digests}
    for content,report in validated:
        key=digest(content)
        prior=prior_attestations.get(key)
        # Legacy entries are the already approved starter pack. New hashes
        # carry an explicit review gate even after references execute cleanly.
        publication=prior.get('publication','approved') if prior else 'pending_review'
        manifest[key]={**report,'publication':publication}
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
raise SystemExit(bool(failures))
