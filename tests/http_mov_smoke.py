"""Exercise styled captions, project persistence and the MOV-only export contract."""
import copy,io,json,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine as e
from PIL import Image
base=json.loads((e.ROOT/'data/server.json').read_text())['url']
def call(path,obj=None,token=None,headers=None):
    headers=dict(headers or {});data=None
    if token:headers['X-Studio-Token']=token
    if obj is not None:data=json.dumps(obj).encode();headers['Content-Type']='application/json'
    with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers),timeout=60) as response:return response.read(),response.status
cfg=json.loads(call('/api/config')[0]);token=cfg['token']
def api(path,obj=None):return json.loads(call(path,obj,token)[0])
assert cfg['version']=='1.6' and all(key in cfg['fonts'] for key in ('gungsuh','gungsuhche','bithumb_original'))
p=copy.deepcopy(e.SAMPLE);p.update(name='수논사 - 그라데이션과 빛 번짐',width=720);p['captions']=p['captions'][:2]
p['captions'][0].update(start=0,end=1.5,text='궁서체 · 그라데이션',font='gungsuh',fontSize=90,style='impact',animation='fade',fill='#ffa5f8',outline='#ffffff',stroke=4,gradient=True,gradientEnd='#f555e7',gradientAngle=90,glow=True,glowColor='#fff66a',glowBlur=18,glowStrength=85)
p['captions'][1].update(start=1.5,end=3,text='투명 자막 MOV로!',font='gungsuhche',fontSize=95,fill='#80e9ff',outline='#ffffff',stroke=3,gradient=True,gradientEnd='#6554ff',gradientAngle=45,glow=True,glowColor='#65d8ff',glowBlur=20,glowStrength=80)
saved=api('/api/save',p)['project'];assert api('/api/validate',saved)['project']==saved
frame=call('/api/frame',{'project':saved,'time':.6},token)[0];im=Image.open(io.BytesIO(frame));assert im.getchannel('A').getextrema()==(0,255)
(e.ROOT/'tests/qa/styled-actual-frame.png').write_bytes(frame)
jid=api('/api/render',saved)['id']
for _ in range(180):
    state=api('/api/job/'+jid)
    if state['state']!='running':break
    time.sleep(.3)
assert state['state']=='done',state
folder=e.ROOT/'output'/jid;assert sorted(f.name for f in folder.iterdir())==['captions_alpha.mov']
metadata=json.loads((e.ROOT/'data/export-meta'/(jid+'.json')).read_text('utf-8'));assert metadata['files']==['captions_alpha.mov']
rgba=e.run(['-ss','0.6','-i',folder/'captions_alpha.mov','-frames:v','1','-f','rawvideo','-pix_fmt','rgba','pipe:1'])
alpha=rgba[3::4];assert min(alpha)==0 and max(alpha)==255 and any(0<value<255 for value in alpha)
probe=subprocess.run([e.FFMPEG,'-hide_banner','-i',str(folder/'captions_alpha.mov')],capture_output=True);assert 'Audio:' not in probe.stderr.decode('utf-8','replace')
data,status=call('/output/'+jid+'/captions_alpha.mov',headers={'Range':'bytes=0-99'});assert status==206 and len(data)==100
assert any(row['id']==jid for row in api('/api/exports'))
report={'gungsuh_faces':True,'gradient_glow_save_load':True,'actual_styled_preview':True,'mov_only_export':True,'transparent_soft_glow':True,'no_audio':True,'range_download':True,'export':str(folder)}
(e.ROOT/'tests/http-mov-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
(e.ROOT/'tests/qa/mov-demo-project.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
