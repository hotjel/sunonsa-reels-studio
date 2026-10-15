from __future__ import annotations
import argparse, io, json, mimetypes, os, re, secrets, shutil, socket, threading, time, traceback, uuid, webbrowser
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote
import engine

ROOT=engine.ROOT
for d in ['data/media','data/projects','data/export-meta','output']: (ROOT/d).mkdir(parents=True,exist_ok=True)
TOKEN=secrets.token_urlsafe(32)
JOBS={}; LOCK=threading.Lock(); ACTIVE=None
ALLOWED={'.mp4','.mov','.webm','.m4v'}
def korean_stamp(): return datetime.now(timezone(timedelta(hours=9))).strftime('%Y%m%d-%H%M%S')

def job_worker(jid,p):
    global ACTIVE
    job=JOBS[jid]; folder=ROOT/'output'/jid
    def progress(value,message): job.update(progress=value,message=message)
    try:
        job['result']=engine.export_project(p,folder,progress,job['cancel'])
        (ROOT/'data/export-meta'/(jid+'.json')).write_text(json.dumps(job['result'],ensure_ascii=False,indent=2),encoding='utf-8')
        job['state']='done'; job['folder']=str(folder)
    except Exception as ex:
        job.update(state='cancelled' if job['cancel'].is_set() else 'error',message=str(ex))
        folder.mkdir(exist_ok=True); (folder/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        with LOCK: ACTIVE=None

class Handler(BaseHTTPRequestHandler):
    server_version='SunonsaStudio/1.6'
    def log_message(self,fmt,*args): pass
    def safe_request(self,mutation=False):
        expected={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host','') not in expected: raise ValueError('허용되지 않은 호스트입니다.')
        if mutation:
            if not secrets.compare_digest(self.headers.get('X-Studio-Token',''),TOKEN): raise ValueError('보안 토큰이 만료되었습니다. 페이지를 새로고침하세요.')
            origin=self.headers.get('Origin')
            if origin and origin not in {'http://'+s for s in expected}: raise ValueError('허용되지 않은 요청 출처입니다.')
    def send_bytes(self,body,ctype='application/json; charset=utf-8',status=200):
        self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store'); self.end_headers()
        self.wfile.write(body)
    def json(self,obj,status=200): self.send_bytes(json.dumps(obj,ensure_ascii=False).encode('utf-8'),status=status)
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        if not 0<n<=1024*1024: raise ValueError('요청 크기가 올바르지 않습니다.')
        return json.loads(self.rfile.read(n))
    def file(self,path):
        if not path.is_file(): return self.json({'error':'파일을 찾을 수 없습니다.'},404)
        size=path.stat().st_size; start,end=0,size-1; partial=False
        r=self.headers.get('Range','')
        if r:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',r)
            if not match: return self.json({'error':'지원하지 않는 Range'},416)
            a,b=match.groups()
            if a: start=int(a); end=min(size-1,int(b)) if b else size-1
            elif b: start=max(0,size-int(b))
            if start>end or start>=size: return self.json({'error':'범위를 벗어났습니다.'},416)
            partial=True
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges','bytes'); self.send_header('Content-Length',str(end-start+1)); self.send_header('X-Content-Type-Options','nosniff')
        if partial: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with path.open('rb') as f:
            f.seek(start); remaining=end-start+1
            while remaining:
                chunk=f.read(min(1024*1024,remaining))
                if not chunk: break
                self.wfile.write(chunk); remaining-=len(chunk)
    def do_GET(self):
        try:
            self.safe_request(); url=urlparse(self.path); route=unquote(url.path)
            if route=='/api/config':
                return self.json({'token':TOKEN,'sample':engine.SAMPLE,'fonts':engine.available_fonts(),'fontLocals':engine.FONT_LOCALS,'root':str(ROOT),'version':'1.6','maxSeconds':180})
            if route.startswith('/api/job/'):
                jid=route.rsplit('/',1)[1]; j=JOBS.get(jid)
                return self.json({k:v for k,v in j.items() if k!='cancel'} if j else {'error':'작업을 찾을 수 없습니다.'},200 if j else 404)
            if route=='/api/exports':
                rows=[]
                for p in sorted((ROOT/'output').iterdir(),reverse=True):
                    metadata=ROOT/'data/export-meta'/(p.name+'.json')
                    if not metadata.exists():metadata=p/'export_info.json'
                    if re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{6}',p.name) and metadata.exists() and (p/'captions_alpha.mov').exists(): rows.append({'id':p.name,**json.loads(metadata.read_text(encoding='utf-8'))})
                return self.json(rows[:30])
            if route.startswith('/media/'): return self.file(engine.asset_path(route[len('/media/'):]))
            if route.startswith('/font/'):
                key=route.rsplit('/',1)[1]
                if key not in engine.FONTS: raise ValueError('알 수 없는 글꼴입니다.')
                return self.file(engine.font_path(key))
            if route.startswith('/output/') or route.startswith('/docs/') or route.startswith('/premiere/'):
                target=(ROOT/route.lstrip('/')).resolve()
                if not target.is_relative_to(ROOT/route.split('/')[1]): raise ValueError('잘못된 파일 경로입니다.')
                return self.file(target)
            if route in ('/','/index.html','/app.js','/text-effects.js','/style.css'):
                return self.file(ROOT/'web'/('index.html' if route=='/' else route[1:]))
            self.json({'error':'페이지를 찾을 수 없습니다.'},404)
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as ex: self.json({'error':str(ex)},400)
    def do_POST(self):
        global ACTIVE
        try:
            self.safe_request(True); url=urlparse(self.path); route=url.path
            if route=='/api/upload':
                name=parse_qs(url.query).get('name',[''])[0]; suffix=Path(name).suffix.lower()
                if suffix not in ALLOWED: raise ValueError('촬영 영상만 지원합니다: MP4, MOV, WebM, M4V')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=2*1024**3: raise ValueError('미디어는 2GB 이하로 준비하세요.')
                if shutil.disk_usage(ROOT).free < n+500*1024**2: raise ValueError('저장 공간이 부족합니다.')
                aid=uuid.uuid4().hex+suffix; dst=engine.MEDIA/aid; temp=dst.with_suffix('.partial')
                try:
                    with temp.open('wb') as f:
                        remaining=n
                        while remaining:
                            data=self.rfile.read(min(1024*1024,remaining))
                            if not data: raise ValueError('파일 전송이 중단되었습니다.')
                            f.write(data); remaining-=len(data)
                    temp.replace(dst)
                finally:
                    if temp.exists(): temp.unlink()
                return self.json({'asset':aid,'name':Path(name).name,'url':'/media/'+aid})
            raw=self.body()
            if route=='/api/validate':
                warnings=[]
                if isinstance(raw,dict):
                    for key,label in [('video','촬영 영상')]:
                        entry=raw.get(key)
                        if isinstance(entry,dict) and entry.get('asset'):
                            try:engine.asset_path(entry['asset'])
                            except ValueError:
                                entry['asset']='';entry['name']=''
                                warnings.append(label+' 원본 파일을 다시 선택하세요.')
                return self.json({'project':engine.validate(raw),'warnings':warnings})
            if route=='/api/save':
                p=engine.validate(raw); name=korean_stamp()+'-'+uuid.uuid4().hex[:6]+'.sunonsa.json'
                (ROOT/'data/projects'/name).write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
                return self.json({'name':name,'project':p})
            if route=='/api/render':
                p=engine.validate(raw)
                if shutil.disk_usage(ROOT).free<2*1024**3: raise ValueError('출력 전 여유 공간을 2GB 이상 확보하세요. 긴 영상은 더 많은 공간이 필요합니다.')
                with LOCK:
                    if ACTIVE: return self.json({'error':'이미 출력 중입니다. 완료 또는 취소 후 다시 시도하세요.'},409)
                    jid=korean_stamp()+'-'+uuid.uuid4().hex[:6]; ACTIVE=jid
                    JOBS[jid]={'id':jid,'state':'running','progress':0,'message':'준비 중','cancel':threading.Event()}
                threading.Thread(target=job_worker,args=(jid,p),daemon=True).start()
                return self.json({'id':jid})
            if route=='/api/cancel':
                j=JOBS.get(raw.get('id'))
                if j and j['state']=='running': j['cancel'].set()
                return self.json({'ok':True})
            if route=='/api/frame':
                p=engine.validate(raw['project']); t=engine.number(raw.get('time',0),0,180,'시간')
                im=engine.overlay_frame(p,t); im.thumbnail((432,768)); buf=io.BytesIO(); im.save(buf,format='PNG')
                return self.send_bytes(buf.getvalue(),'image/png')
            if route=='/api/open-output':
                jid=raw.get('id','')
                if jid and not re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{6}',jid): raise ValueError('출력 ID가 잘못되었습니다.')
                target=ROOT/'output'/jid
                if not target.is_dir(): raise ValueError('출력 폴더가 없습니다.')
                os.startfile(target); return self.json({'ok':True})
            self.json({'error':'알 수 없는 요청입니다.'},404)
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as ex: self.json({'error':str(ex)},400)

def main():
    args=argparse.ArgumentParser(); args.add_argument('--no-browser',action='store_true'); args.add_argument('--port',type=int,default=8877); opts=args.parse_args()
    server=None
    for port in range(opts.port,opts.port+10):
        try: server=ThreadingHTTPServer(('127.0.0.1',port),Handler); break
        except OSError: continue
    if server is None: raise RuntimeError('8877~8886 포트를 사용할 수 없습니다.')
    url=f'http://127.0.0.1:{server.server_port}'
    (ROOT/'data/server.json').write_text(json.dumps({'pid':os.getpid(),'url':url}),encoding='utf-8')
    print('Sunonsa Reels Studio: '+url,flush=True)
    if not opts.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
