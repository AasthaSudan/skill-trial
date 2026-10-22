import argparse
import getpass
from sqlalchemy import select
from .db import Base,engine,tx
from .models import User
from .security import HASHER,password_ok
from .catalog import seed

parser=argparse.ArgumentParser(description='SkillTrial local administration')
parser.add_argument('command',choices=['create-admin','seed','export-validation'])
parser.add_argument('--email')
parser.add_argument('--name',default='Content Administrator')
args=parser.parse_args()
Base.metadata.create_all(engine)
with tx() as db:
    if args.command=='seed':seed(db);print('Versioned content loaded.')
    elif args.command=='export-validation':
        import json
        from .models import Challenge
        from .catalog import digest
        from .config import ROOT
        rows=list(db.scalars(select(Challenge).where(Challenge.author=='seed',Challenge.status=='published')))
        if not rows or any(not c.validation.get('executed') or not c.validation.get('ok') for c in rows):parser.error('Run scripts/validate_content.py first.')
        (ROOT/'content'/'validation.json').write_text(json.dumps({digest(c.content):c.validation for c in rows},indent=2),encoding='utf-8')
        print(f'Exported executable-validation attestations for {len(rows)} challenge versions.')
    else:
        if not args.email:parser.error('--email is required')
        email=args.email.strip().lower();password=getpass.getpass('New administrator password: ')
        password_ok(password,email)
        if db.scalar(select(User).where(User.email==email)):parser.error('This email already exists. Use a new administrator email.')
        db.add(User(email=email,name=args.name,password=HASHER.hash(password),role='admin',verified=True))
        print('Administrator created. Sign in normally. Create a second administrator for independent content review.')
