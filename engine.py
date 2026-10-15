"""Sunonsa Reels Studio: deterministic captions and Premiere exports."""
from __future__ import annotations
import copy, hashlib, json, math, os, re, subprocess, sys, time
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter, ImageOps
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, MAX_SECONDS = 30, 180
MEDIA = ROOT / 'data' / 'media'
FONTS = {
 'nanumsquare': ('나눔스퀘어 ExtraBold · 기본', 'NanumSquareEB.ttf'),
 'nanumsquare_b': ('나눔스퀘어 Bold · 담백한 설명', 'NanumSquareB.ttf'),
 'nanumround': ('나눔스퀘어라운드 ExtraBold · 말풍선', 'NanumSquareRoundEB.ttf'),
 'nanumneo': ('나눔스퀘어네오 ExtraBold · 깔끔한 강조', 'NanumSquareNeo-dEb.ttf'),
 'nanumneo_heavy': ('나눔스퀘어네오 Heavy · 강한 강조', 'NanumSquareNeo-eHv.ttf'),
 'dohyeon': ('배민 도현 · 개성 있는 제목', 'DoHyeon-Regular.ttf'),
 'gmarket_bold': ('지마켓 산스 Bold · 또렷한 강조', 'GmarketSansTTFBold.ttf'),
 'gmarket_medium': ('지마켓 산스 Medium · 깔끔한 설명', 'GmarketSansTTFMedium.ttf'),
 'gmarket_light': ('지마켓 산스 Light · 가벼운 글씨', 'GmarketSansTTFLight.ttf'),
 'bithumb_original': ('빗썸고딕 Original · 기울어진 강조', 'Bithumb Gothic Original.ttf'),
 'bithumb_basic': ('빗썸고딕 Basic · 반듯한 강조', 'Bithumb Gothic Basic.ttf'),
 'gungsuh': ('궁서 · 붓글씨', 'batang.ttc'),
 'gungsuhche': ('궁서체 · 고정폭 붓글씨', 'batang.ttc'),
 'malgunbd': ('맑은 고딕 Bold', 'malgunbd.ttf'), 'malgun': ('맑은 고딕', 'malgun.ttf'), 'batang': ('바탕', 'batang.ttc')}
STYLES = {'impact', 'bubble', 'clean'}
ANIMATIONS = {'pop', 'shake', 'type', 'fade', 'none'}
FONT_INDICES={'gungsuh':2,'gungsuhche':3}
FONT_LOCALS={'gungsuh':['궁서','Gungsuh'],'gungsuhche':['궁서체','GungsuhChe']}
SAMPLE = {
 'version': 6, 'name': '수논사 - 답보다 중요한 것', 'width': 1080,
 'font': 'nanumsquare', 'fontSize': 66, 'y': 64, 'fill': '#ffe04b',
 'outline': '#e13c36', 'stroke': 6, 'strength': 75,
 'video': {'asset': '', 'name': ''},
 'captions': [
  {'start': 0, 'end': 2.8, 'text': '정답은 맞았는데,\n왜 감점일까요?', 'style': 'bubble', 'animation': 'pop', 'font':'nanumsquare','fontSize':66,'letterSpacing':0},
  {'start': 3, 'end': 5.7, 'text': '계산만 쓰고 끝내면?', 'style': 'impact', 'animation': 'shake', 'font':'nanumsquare','fontSize':66,'letterSpacing':0},
  {'start': 5.9, 'end': 9, 'text': '왜 그런지, 근거를 쓰세요!', 'style': 'impact', 'animation': 'pop', 'font':'nanumsquare','fontSize':66,'letterSpacing':0},
  {'start': 9.2, 'end': 12, 'text': '수리논술, 논리적으로 서술하기\n수논사', 'style': 'clean', 'animation': 'fade', 'font':'nanumsquare','fontSize':66,'letterSpacing':0}
 ]
}

def number(v, lo, hi, label):
    try: n = float(v)
    except (ValueError, TypeError): raise ValueError(f'{label}: 숫자를 입력하세요.')
    if not math.isfinite(n) or not lo <= n <= hi:
        raise ValueError(f'{label}: {lo} ~ {hi} 범위로 입력하세요.')
    return n

def asset_path(asset):
    if not re.fullmatch(r'[a-f0-9]{32}\.[a-z0-9]{2,5}', str(asset)):
        raise ValueError('미디어 파일 ID가 올바르지 않습니다. 파일을 다시 선택하세요.')
    p = MEDIA / asset
    if not p.is_file(): raise ValueError('원본 미디어가 없습니다. 영상 파일을 다시 선택하세요.')
    return p

def validate(raw):
    if not isinstance(raw, dict): raise ValueError('프로젝트 JSON 형식이 아닙니다.')
    p = copy.deepcopy(SAMPLE)
    p.update(copy.deepcopy({k: v for k, v in raw.items() if k in p}))
    if p['version'] not in (1,2,3,4,5,6): raise ValueError('지원하지 않는 프로젝트 버전입니다.')
    p['version']=6
    if not isinstance(p['name'], str) or not 1 <= len(p['name']) <= 100: raise ValueError('프로젝트 이름은 1~100자입니다.')
    if p['width'] not in (720, 1080): raise ValueError('해상도는 720 또는 1080입니다.')
    if p['font'] not in FONTS: raise ValueError('글꼴을 다시 선택하세요.')
    for key, lo, hi in [('fontSize', 24, 160), ('y', 15, 80), ('stroke', 0, 12), ('strength', 0, 100)]:
        p[key] = number(p[key], lo, hi, key)
    for key in ('fill', 'outline'):
        if not isinstance(p[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', p[key]): raise ValueError('색상은 #RRGGBB 형식이어야 합니다.')
    if not isinstance(p['captions'], list) or not 1 <= len(p['captions']) <= 100:
        raise ValueError('자막은 1~100개까지 입력할 수 있습니다.')
    for i, c in enumerate(p['captions']):
        if not isinstance(c, dict): raise ValueError('자막 형식이 잘못되었습니다.')
        c['start'] = number(c.get('start'), 0, MAX_SECONDS, f'{i+1}번 시작')
        c['end'] = number(c.get('end'), 0, MAX_SECONDS, f'{i+1}번 끝')
        if c['end'] - c['start'] < 1/FPS: raise ValueError(f'{i+1}번: 자막은 최소 1프레임 이상이어야 합니다.')
        if not isinstance(c.get('text'), str) or not c['text'].strip() or len(c['text']) > 160:
            raise ValueError(f'{i+1}번: 자막은 1~160자로 입력하세요.')
        c['text'] = c['text'].strip().replace('\r', '')
        c['font']=c.get('font',p['font'])
        if c['font'] not in FONTS: raise ValueError(f'{i+1}번: 글꼴을 다시 선택하세요.')
        c['fontSize']=number(c.get('fontSize',p['fontSize']),24,160,f'{i+1}번 글씨 크기')
        c['letterSpacing']=number(c.get('letterSpacing',0),-15,30,f'{i+1}번 자간')
        if c.get('style') not in STYLES or c.get('animation') not in ANIMATIONS:
            raise ValueError(f'{i+1}번: 스타일/효과를 다시 선택하세요.')
        default_fill,default_outline,default_stroke=caption_colors(p,c)
        c.setdefault('fill',default_fill);c.setdefault('outline',default_outline)
        c.setdefault('stroke',default_stroke)
        for key in ('fill','outline'):
            if not isinstance(c[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',c[key]):
                raise ValueError(f'{i+1}번: 색상은 #RRGGBB 형식이어야 합니다.')
            c[key]=c[key].lower()
        c['stroke']=number(c['stroke'],0,12,f'{i+1}번 테두리 두께')
        for key in ('gradient','glow'):
            c.setdefault(key,False)
            if not isinstance(c[key],bool):raise ValueError(f'{i+1}번: 그라데이션·빛 번짐 켜기 설정이 올바르지 않습니다.')
        for key,default in [('gradientEnd','#f555e7'),('glowColor','#fff66a')]:
            c.setdefault(key,default)
            if not isinstance(c[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',c[key]):raise ValueError(f'{i+1}번: 색상은 #RRGGBB 형식이어야 합니다.')
            c[key]=c[key].lower()
        for key,default,lo,hi in [('gradientAngle',90,0,360),('glowBlur',18,0,50),('glowStrength',85,0,100)]:
            c[key]=number(c.get(key,default),lo,hi,f'{i+1}번 {key}')
        for old in ('sfx','voiceRole'): c.pop(old,None)
    p['captions'].sort(key=lambda c: c['start'])
    for a, b in zip(p['captions'], p['captions'][1:]):
        if a['end'] > b['start'] + 1e-8: raise ValueError('자막 시간이 겹칩니다. 앞 자막의 끝과 다음 자막의 시작을 확인하세요.')
    if not isinstance(p['video'], dict): raise ValueError('영상 설정 형식이 잘못되었습니다.')
    if p['video'].get('asset'): asset_path(p['video']['asset'])
    p['video']={key:p['video'].get(key,'') for key in ('asset','name')}
    return p

def run(args, cancel=None, timeout=900):
    """No shell; FFmpeg stderr stays in a temporary file to avoid pipe deadlocks."""
    import tempfile
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen([FFMPEG, '-hide_banner','-loglevel','error','-nostdin','-y', *map(str,args)],
            stdout=subprocess.PIPE, stderr=log, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        started = time.monotonic()
        while True:
            try:
                out, _ = proc.communicate(timeout=.3)
                break
            except subprocess.TimeoutExpired:
                if (cancel and cancel.is_set()) or time.monotonic()-started > timeout:
                    proc.kill(); proc.communicate()
                    raise RuntimeError('작업을 취소했습니다.' if cancel and cancel.is_set() else '처리 시간이 초과되었습니다.')
        if proc.returncode:
            log.seek(0)
            detail = log.read().decode('utf-8', 'replace')[-1600:]
            raise RuntimeError('미디어 처리 실패. 파일 형식 또는 저장 공간을 확인하세요.\n'+detail)
        return out

def font_path(key):
    path = ROOT / 'assets/fonts' / FONTS[key][1]
    if not path.exists(): path = Path(os.environ.get('WINDIR','C:/Windows')) / 'Fonts' / FONTS[key][1]
    if not path.exists(): raise ValueError(f'{FONTS[key][0]} 글꼴이 없습니다. 프로그램 폴더 전체를 복사했는지 확인하세요.')
    return path

def available_fonts():
    result={}
    for key,value in FONTS.items():
        try:font_path(key);result[key]=value[0]
        except ValueError:pass
    return result

def load_font(key,size):
    return ImageFont.truetype(str(font_path(key)),size,index=FONT_INDICES.get(key,0))

def gradient_image(size,bounds,start,end,angle):
    """Project a linear gradient across actual text ink, independent of glow padding."""
    x0,y0,x1,y1=bounds;dx=math.cos(math.radians(angle));dy=math.sin(math.radians(angle))
    values=[x*dx+y*dy for x in (x0,x1-1) for y in (y0,y1-1)]
    low=min(values);span=max(1,max(values)-low);width,height=size
    ramp=bytes(max(0,min(255,round(255*(x*dx+y*dy-low)/span))) for y in range(height) for x in range(width))
    return ImageOps.colorize(Image.frombytes('L',size,ramp),start,end).convert('RGBA')

def styled_text(image,fill_mask,shape_mask,c,ratio,fill,outline,stroke):
    glow=c.get('glow',False) and c.get('glowStrength',85)>0 and c.get('glowBlur',18)>0
    radius=c.get('glowBlur',18)*ratio
    extra=math.ceil(radius*3)+2 if glow else 0
    if extra:
        expanded=Image.new('RGBA',(image.width+2*extra,image.height+2*extra))
        expanded.alpha_composite(image,(extra,extra));image=expanded
        fill_mask=ImageOps.expand(fill_mask,extra);shape_mask=ImageOps.expand(shape_mask,extra)
    if glow:
        strength=c.get('glowStrength',85)/100
        for blur,opacity in [(radius,.9*strength),(radius,.9*strength),(radius*.35,strength)]:
            alpha=shape_mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda value:round(value*opacity))
            halo=Image.new('RGBA',image.size,c.get('glowColor','#fff66a'));halo.putalpha(alpha);image.alpha_composite(halo)
    if stroke:
        edge=Image.new('RGBA',image.size,outline);edge.putalpha(shape_mask);image.alpha_composite(edge)
    bounds=fill_mask.getbbox()
    ink=gradient_image(image.size,bounds,fill,c.get('gradientEnd','#f555e7'),c.get('gradientAngle',90)) if c.get('gradient') and bounds else Image.new('RGBA',image.size,fill)
    ink.putalpha(fill_mask);image.alpha_composite(ink)
    return image

def caption_colors(p,c):
    """Legacy defaults preserve the appearance of projects made before v1.3."""
    if c['style']=='bubble': defaults=('#22242a','#22242a',0)
    elif c['style']=='clean': defaults=('#ffffff','#191b22',3)
    else: defaults=(p['fill'],p['outline'],p['stroke'])
    return c.get('fill',defaults[0]),c.get('outline',defaults[1]),c.get('stroke',defaults[2])

def text_layout(font,text,tracking,stroke=0):
    """Return glyph origins and their actual ink bounds, including negative tracking."""
    positions=[];prefix='';left=top=float('inf');right=bottom=float('-inf')
    for i,char in enumerate(text):
        x=font.getlength(prefix+char)-font.getlength(char)+i*tracking
        positions.append((char,x))
        box=font.getbbox(char,stroke_width=stroke)
        left=min(left,x+box[0]);top=min(top,box[1]);right=max(right,x+box[2]);bottom=max(bottom,box[3])
        prefix+=char
    if not positions:return [],(0,0,0,0)
    return positions,(left,top,right,bottom)

def caption_card(p, c, text=None):
    """Per-caption font, size and pixel tracking; wrap and shrink within safe bounds."""
    ratio=p['width']/1080
    requested=c.get('fontSize',p['fontSize']);size=max(1,round(requested*ratio))
    fill,outline,stroke_width=caption_colors(p,c)
    stroke=round(stroke_width*ratio)
    txt=c['text'] if text is None else text
    maxw,maxh=p['width']*.85,p['width']*.48
    pad=round(32*ratio)+stroke;tail=round(24*ratio) if c['style']=='bubble' else 0
    while True:
        font=load_font(c.get('font',p['font']),size)
        tracking=c.get('letterSpacing',0)*size/requested
        lines=[]
        for line in txt.split('\n'):
            row=''
            for char in line:
                measured=font.getlength(row+char)+len(row)*tracking+2*stroke
                if row and measured>maxw-pad*2:lines.append(row);row=char
                else:row+=char
            lines.append(row)
        layouts=[text_layout(font,line,tracking,stroke) for line in lines]
        step=round(size*1.24)
        left=min([bounds[0] for _,bounds in layouts]+[0])
        top=min(bounds[1]+i*step for i,(_,bounds) in enumerate(layouts))
        bottom=max(bounds[3]+i*step for i,(_,bounds) in enumerate(layouts))
        width=max(bounds[2]-bounds[0] for _,bounds in layouts)
        if (bottom-top<=maxh-pad*2-tail and width<=maxw-pad*2) or size<=max(1,round(12*ratio)):break
        size-=1
    w=max(2,math.ceil(width+pad*2));h=max(2,math.ceil(bottom-top+pad*2))
    image=Image.new('RGBA',(w,h+tail),(0,0,0,0));d=ImageDraw.Draw(image)
    if c['style']=='bubble':
        d.rounded_rectangle((1,1,w-2,h-2),radius=round(h*.42),fill='white',outline='#303338',width=max(1,round(2*ratio)))
        d.polygon([(w*.23,h-4),(w*.18,h+tail-1),(w*.38,h-4)],fill='white')
    styled=c.get('gradient',False) or c.get('glow',False) or c.get('font',p['font']) in FONT_INDICES
    if styled:
        fill_mask=Image.new('L',image.size);shape_mask=Image.new('L',image.size)
        fill_draw=ImageDraw.Draw(fill_mask)
    for i,(positions,bounds) in enumerate(layouts):
        x0=(w-(bounds[2]-bounds[0]))/2-bounds[0]
        y0=pad-top+i*step
        for char,x in positions:
            if styled:
                fill_draw.text((x0+x,y0),char,font=font,fill=255)
            else:d.text((x0+x,y0),char,font=font,fill=fill,stroke_width=stroke,stroke_fill=outline)
    if styled:
        # Dilate the complete fill mask: TTC composite glyphs can otherwise lose
        # their circular components in FreeType's separate stroked outline.
        shape_mask=fill_mask.filter(ImageFilter.MaxFilter(2*stroke+1)) if stroke else fill_mask.copy()
        return styled_text(image,fill_mask,shape_mask,c,ratio,fill,outline,stroke)
    return image

def overlay_frame(p, t, cache=None):
    w, h=p['width'],p['width']*16//9
    frame=Image.new('RGBA',(w,h),(0,0,0,0))
    for idx,c in enumerate(p['captions']):
        if c['start'] <= t < c['end']:
            elapsed=t-c['start']; length=c['end']-c['start']; strength=p['strength']/100
            txt=c['text']
            if c['animation']=='type': txt=txt[:max(1,math.ceil(len(txt)*min(1,elapsed/min(.9,length*.65))))]
            key=(idx,txt)
            if cache is not None and key in cache: card=cache[key]
            else:
                card=caption_card(p,c,txt)
                if cache is not None: cache[key]=card
            scale,dx,dy,alpha=1,0,0,1
            if c['animation']=='pop' and elapsed < .3:
                scale=1+.18*strength*math.sin(math.pi*elapsed/.3)*math.exp(-elapsed*4)
            elif c['animation']=='shake' and elapsed < .6:
                dx=math.sin(elapsed*72)*10*strength*(1-elapsed/.6)*w/1080
                dy=math.cos(elapsed*63)*5*strength*(1-elapsed/.6)*w/1080
            elif c['animation']=='fade': alpha=min(1,elapsed/.18,(length-elapsed)/.12)
            if scale!=1: card=card.resize((max(1,round(card.width*scale)),max(1,round(card.height*scale))),Image.Resampling.LANCZOS)
            if alpha<1:
                card=card.copy(); card.putalpha(card.getchannel('A').point(lambda x: round(x*max(0,alpha))))
            frame.alpha_composite(card,(round((w-card.width)/2+dx),round(h*p['y']/100-card.height/2+dy)))
            break
    return frame

def timestamp(t):
    ms=round(t*1000); sec,ms=divmod(ms,1000); minute,sec=divmod(sec,60); hour,minute=divmod(minute,60)
    return f'{hour:02}:{minute:02}:{sec:02},{ms:03}'

def write_srt(path,p):
    text='\n\n'.join(f'{i+1}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for i,c in enumerate(p['captions']))+'\n'
    path.write_text(text,encoding='utf-8-sig')

def write_xml(path,p,dur):
    """FCP 7 XML imports a transparent overlay above an empty footage track."""
    def el(parent,tag,text=None,**attrs):
        node=ET.SubElement(parent,tag,attrs)
        if text is not None: node.text=str(text)
        return node
    def rate(parent):
        r=el(parent,'rate'); el(r,'timebase',FPS); el(r,'ntsc','FALSE')
    frames=round(dur*FPS); root=ET.Element('xmeml',version='4'); seq=el(root,'sequence',id='sunonsa-sequence')
    el(seq,'name',p['name']); el(seq,'duration',frames); rate(seq)
    media=el(seq,'media'); video=el(media,'video'); fmt=el(video,'format'); sc=el(fmt,'samplecharacteristics')
    rate(sc); el(sc,'width',p['width']); el(sc,'height',p['width']*16//9); el(sc,'pixelaspectratio','square'); el(sc,'fielddominance','none')
    el(video,'track') # V1 reserved for future footage.
    audio=el(media,'audio'); el(audio,'numOutputChannels',2)
    for idx,(filename,kind) in enumerate([('captions_alpha.mov','video')]):
        track=el(video if kind=='video' else audio,'track'); clip=el(track,'clipitem',id=f'clip-{idx}')
        el(clip,'name',filename); el(clip,'enabled','TRUE'); el(clip,'duration',frames); rate(clip)
        for k,v in [('start',0),('end',frames),('in',0),('out',frames)]: el(clip,k,v)
        if kind=='video': el(clip,'alphatype','straight')
        f=el(clip,'file',id=f'file-{idx}'); el(f,'name',filename); el(f,'pathurl',(path.parent/filename).resolve().as_uri()); rate(f); el(f,'duration',frames)
        fm=el(f,'media'); sub=el(fm,kind); char=el(sub,'samplecharacteristics')
        if kind=='video':
            rate(char); el(char,'width',p['width']); el(char,'height',p['width']*16//9); el(char,'pixelaspectratio','square'); el(char,'fielddominance','none')
        else: el(char,'depth',16); el(char,'samplerate',48000); el(sub,'channelcount',1)
        source=el(clip,'sourcetrack'); el(source,'mediatype',kind); el(source,'trackindex',1)
    ET.indent(root)
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n'+ET.tostring(root,encoding='unicode'),encoding='utf-8')

def export_project(raw, folder, progress=lambda x,y: None, cancel=None):
    p=validate(raw); folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    if cancel and cancel.is_set(): raise RuntimeError('작업을 취소했습니다.')
    progress(2,'자막 설정 준비 중')
    dur=math.ceil(max(c['end'] for c in p['captions'])*FPS)/FPS
    w,h=p['width'],p['width']*16//9; count=round(dur*FPS)
    log_folder=ROOT/'data/export-logs';log_folder.mkdir(parents=True,exist_ok=True)
    log_path=log_folder/(folder.name+'-'+hashlib.sha256(str(folder.resolve()).encode()).hexdigest()[:8]+'.log')
    with log_path.open('wb') as log:
        proc=subprocess.Popen([FFMPEG,'-hide_banner','-loglevel','error','-nostdin','-y','-f','rawvideo','-pixel_format','rgba','-video_size',f'{w}x{h}','-framerate',str(FPS),'-i','pipe:0','-an','-c:v','prores_ks','-profile:v','4','-pix_fmt','yuva444p10le','-alpha_bits','16','-threads','4',str(folder/'captions_alpha.mov')],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            cache={}
            for i in range(count):
                if cancel and cancel.is_set(): raise RuntimeError('작업을 취소했습니다.')
                proc.stdin.write(overlay_frame(p,i/FPS,cache).tobytes())
                if i%FPS==0: progress(8+int(65*i/count),f'투명 자막 렌더링 {i/FPS:.0f} / {dur:.1f}초')
            proc.stdin.close(); proc.wait(timeout=180)
            if proc.returncode: raise RuntimeError('투명 자막 인코딩 실패. data/export-logs의 로그를 확인하세요.')
        except BaseException:
            proc.kill(); proc.wait(); raise
    metadata={'version':'1.6','duration':dur,'width':w,'height':h,'fps':FPS,'hasAudio':False,'files':['captions_alpha.mov']}
    progress(100,'투명 자막 MOV 내보내기 완료')
    return metadata
