"""Short-lived process: trusted fixture setup, then restricted candidate SELECT."""
import json
import sqlite3
import sys
import time
import math

def execute(dataset,query):
    if not query.strip():return {'status':'sql_error','message':'Write a SELECT query first.'}
    if len(query)>10000:return {'status':'sql_error','message':'Query exceeds 10,000 characters.'}
    db=sqlite3.connect(':memory:')
    try:
        db.executescript(dataset)
        db.execute('PRAGMA query_only=ON')
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,1_000_000)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,10000)
        allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
        denied={'load_extension','randomblob','random','writefile','readfile'}
        db.set_authorizer(lambda action,a,b,c,d:sqlite3.SQLITE_OK if action in allowed and not(action==sqlite3.SQLITE_FUNCTION and (b or '').lower() in denied) else sqlite3.SQLITE_DENY)
        end=time.monotonic()+2
        db.set_progress_handler(lambda:int(time.monotonic()>end),1000)
        cur=db.execute(query)
        if not cur.description:return {'status':'sql_error','message':'Only a single read-only query is permitted.'}
        rows=cur.fetchmany(5001)
        if len(rows)>5000:return {'status':'sql_error','message':'The result exceeds 5,000 rows.'}
        if any(isinstance(v,float) and not math.isfinite(v) for row in rows for v in row):return {'status':'sql_error','message':'The query returned a non-finite number.'}
        return {'status':'ok','columns':[c[0] for c in cur.description],'rows':[list(r) for r in rows]}
    except sqlite3.Error as e:
        return {'status':'timeout' if 'interrupted' in str(e) else 'sql_error','message':str(e)[:240]}
    finally:db.close()

if __name__=='__main__':
    req=json.load(sys.stdin)
    print(json.dumps(execute(req['dataset'],req['query'])))
