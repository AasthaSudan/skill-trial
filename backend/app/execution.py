import json
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from uuid import uuid4
from .config import RUNNER_MODE,OCI_RUNTIME,RUNNER_URL,RUNNER_HMAC_SECRET,RUNNER_TIMEOUT,RUNNER_READY,RUNNER_WORKDIR

SEM=threading.BoundedSemaphore(2)
IMAGES={'python':'python:3.12-alpine','javascript':'node:22-alpine','java':'eclipse-temurin:21-jdk-alpine'}
class RunnerUnavailable(Exception):pass

def sql_run(dataset,query):
    try:
        r=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('sql_worker.py'))],input=json.dumps({'dataset':dataset,'query':query}),text=True,capture_output=True,timeout=4,encoding='utf-8')
        if r.returncode:raise RunnerUnavailable('SQL worker failed')
        return json.loads(r.stdout)
    except subprocess.TimeoutExpired:return {'status':'timeout','message':'The query exceeded its execution limit.'}

def equivalent(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return abs(a-b)<=1e-7*max(1,abs(b))
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return type(a)==type(b) and a==b

def docker_code_run(language,code,inp):
    if language not in IMAGES:raise RunnerUnavailable('Unsupported execution language')
    if len(code.encode())>200000:return {'status':'compile_error','message':'Code exceeds 200 KB.'}
    if RUNNER_WORKDIR:Path(RUNNER_WORKDIR).mkdir(parents=True,exist_ok=True)
    with SEM, tempfile.TemporaryDirectory(prefix='skilltrial-',dir=RUNNER_WORKDIR or None) as tmp:
        path=Path(tmp)
        if language=='python':
            (path/'solution.py').write_text(code,encoding='utf-8')
            (path/'run.py').write_text('import json,sys\nfrom solution import solve\nprint(json.dumps(solve(json.load(sys.stdin)),allow_nan=False))\n',encoding='utf-8')
            cmd=['python','-B','/work/run.py']
        elif language=='javascript':
            (path/'run.js').write_text(code+'\nconst fs=require("fs"); const x=JSON.parse(fs.readFileSync(0,"utf8")); const r=solve(x); if(typeof r==="number"&&!Number.isFinite(r))throw Error("Non-finite result");console.log(JSON.stringify(r));',encoding='utf-8')
            cmd=['node','--max-old-space-size=128','/work/run.js']
        else:
            (path/'Solution.java').write_text(code,encoding='utf-8')
            (path/'Main.java').write_text('import java.util.*;class Main {public static void main(String[] args)throws Exception {String s=new String(System.in.readAllBytes()).trim();s=s.substring(1,s.length()-1).trim();String[] a=s.isEmpty()?new String[0]:s.split(",");int[] n=new int[a.length];for(int i=0;i<a.length;i++)n[i]=Integer.parseInt(a[i].trim());Object r=Solution.solve(n);System.out.println(r==null?"null":r);}}',encoding='utf-8')
            cmd=['sh','-c','javac -d /tmp /work/Solution.java /work/Main.java && java -XX:+UseSerialGC -Xmx128m -cp /tmp Main']
        os.chmod(path,0o755)
        name='st-'+uuid4().hex
        if OCI_RUNTIME not in ['runc','runsc']:raise RunnerUnavailable('OCI_RUNTIME must be runc or runsc.')
        args=['docker','run','--rm','--name',name,'--network=none','--read-only','--memory=256m','--memory-swap=256m','--cpus=1','--pids-limit=64','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--tmpfs=/tmp:rw,noexec,nosuid,size=64m','--log-driver=none','-i','-v',f'{tmp}:/work:ro']
        if OCI_RUNTIME=='runsc':args+=['--runtime=runsc']
        args += [IMAGES[language],*cmd]
        started=time.monotonic()
        try:
            p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        except OSError as e:raise RunnerUnavailable('Docker is not available.') from e
        out=bytearray();err=bytearray();over=threading.Event()
        def drain(stream,dest,cap):
            while True:
                chunk=stream.read(4096)
                if not chunk:break
                if len(dest)+len(chunk)>cap:
                    over.set();p.kill();break
                dest.extend(chunk)
        threads=[threading.Thread(target=drain,args=(p.stdout,out,65536),daemon=True),threading.Thread(target=drain,args=(p.stderr,err,16000),daemon=True)]
        for t in threads:t.start()
        timeout=20 if language=='java' else 8
        try:
            p.stdin.write(json.dumps(inp).encode());p.stdin.close()
            p.wait(timeout=timeout)
            for t in threads:t.join(timeout=1)
            message=err.decode(errors='replace')[-2000:]
            if p.returncode==125 or 'Cannot connect to the Docker daemon' in message or 'Unable to find image' in message:raise RunnerUnavailable('The Docker sandbox or language image is not ready. Run scripts/setup-runner.ps1.')
            if over.is_set():return {'status':'output_limit','message':'Output limit exceeded.'}
            if p.returncode:return {'status':'runtime_error','message':message}
            try:value=json.loads(out.decode().strip(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Non-finite number')))
            except (ValueError,UnicodeError):return {'status':'runtime_error','message':'Return a JSON-compatible value. Extra stdout prevents result parsing.'}
            return {'status':'ok','value':value,'stdout':out.decode()[:4000],'wall_ms':int((time.monotonic()-started)*1000)}
        except subprocess.TimeoutExpired:
            p.kill();return {'status':'timeout','message':'The sandbox exceeded its time limit.'}
        finally:
            if p.poll() is None:p.kill()
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)

def remote_code_run(language,code,inp):
    if not RUNNER_READY:raise RunnerUnavailable('The isolated remote runner is not configured.')
    if language not in IMAGES:raise RunnerUnavailable('Unsupported execution language')
    if len(code.encode())>200000:return {'status':'compile_error','message':'Code exceeds 200 KB.'}
    path='/v1/run';body=json.dumps({'language':language,'code':code,'input':inp},separators=(',',':'),ensure_ascii=False).encode('utf-8')
    if len(body)>256000:raise RunnerUnavailable('Runner request exceeds the configured size limit.')
    timestamp=str(int(time.time()));nonce=uuid4().hex
    signed='\n'.join(['POST',path,timestamp,nonce,hashlib.sha256(body).hexdigest()]).encode('utf-8')
    signature=hmac.new(RUNNER_HMAC_SECRET.encode('utf-8'),signed,hashlib.sha256).hexdigest()
    request=urllib.request.Request(RUNNER_URL+path,data=body,method='POST',headers={'Content-Type':'application/json','X-SkillTrial-Timestamp':timestamp,'X-SkillTrial-Nonce':nonce,'X-SkillTrial-Signature':signature})
    try:
        with urllib.request.urlopen(request,timeout=RUNNER_TIMEOUT) as response:
            raw=response.read(65537)
        if len(raw)>65536:raise RunnerUnavailable('The remote runner returned an oversized response.')
        result=json.loads(raw)
    except (urllib.error.URLError,TimeoutError,OSError,ValueError,TypeError) as error:
        raise RunnerUnavailable('The isolated remote runner is unavailable.') from error
    if not isinstance(result,dict) or result.get('status') not in ['ok','compile_error','runtime_error','timeout','output_limit']:
        raise RunnerUnavailable('The isolated remote runner returned an invalid response.')
    if result['status']=='ok' and 'value' not in result:raise RunnerUnavailable('The isolated remote runner returned an incomplete result.')
    if 'message' in result:result['message']=str(result['message'])[:2000]
    if 'stdout' in result:result['stdout']=str(result['stdout'])[:4000]
    return result

def code_run(language,code,inp):
    if RUNNER_MODE=='docker':return docker_code_run(language,code,inp)
    if RUNNER_MODE=='remote':return remote_code_run(language,code,inp)
    raise RunnerUnavailable('RUNNER_MODE must be docker or remote.')
