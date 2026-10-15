from pathlib import Path
import html, sys
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Korean','C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('KoreanBold','C:/Windows/Fonts/malgunbd.ttf'))
W,H=595.28,841.89; M=43; CW=W-2*M
INK=HexColor('#253047'); PURPLE=HexColor('#6250cf'); MUTED=HexColor('#788398'); LIGHT=HexColor('#f3f1fb')
body=ParagraphStyle('Body',fontName='Korean',fontSize=10,leading=17,textColor=INK,wordWrap='CJK',spaceAfter=5)
small=ParagraphStyle('Small',parent=body,fontSize=8.2,leading=13,textColor=MUTED)
bold=ParagraphStyle('Bold',parent=body,fontName='KoreanBold')
tablehead=ParagraphStyle('TH',parent=body,fontName='KoreanBold',fontSize=9,leading=14,textColor=white)
c=canvas.Canvas(str(OUT/'수논사_릴스_스튜디오_직원매뉴얼.pdf'),pagesize=(W,H))
c.setTitle('수논사 릴스 스튜디오 | 직원 사용 매뉴얼');c.setAuthor('수논사')
page=0; y=0; sections=[]

def plain(text):return html.escape(text).replace('\n','<br/>')
def start(title,kicker,anchor):
    global page,y
    if page:c.showPage()
    page+=1;c.setFillColor(white);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(PURPLE);c.setFont('KoreanBold',8);c.drawString(M,H-35,'SUNONSA / REELS STUDIO')
    c.setFillColor(MUTED);c.setFont('Korean',8);c.drawRightString(W-M,H-35,'직원 사용 매뉴얼 · 2026.10.15')
    c.setStrokeColor(HexColor('#e5e8ee'));c.line(M,45,W-M,45)
    c.setFont('Korean',8);c.drawString(M,30,'수논사 · 1.6');c.drawRightString(W-M,30,f'{page:02}')
    c.setFillColor(PURPLE);c.setFont('KoreanBold',9);c.drawString(M,H-76,kicker)
    c.setFillColor(INK);c.setFont('KoreanBold',25);c.drawString(M,H-112,title)
    y=H-137
    sections.append({'title':title,'kicker':kicker,'id':anchor,'blocks':[]})

def para(text,style=body,gap=8,record=True):
    global y
    p=Paragraph(plain(text),style);_,height=p.wrap(CW,1000)
    if y-height<58:raise RuntimeError(f'Page {page} overflow: {text[:35]}')
    p.drawOn(c,M,y-height);y-=height+gap
    if record:sections[-1]['blocks'].append(('p',text))

def sub(title):
    global y
    y-=6;para(title,bold,gap=7,record=False);sections[-1]['blocks'].append(('h3',title))

def note(title,text):
    global y
    p=Paragraph(plain(title),bold);q=Paragraph(plain(text),body)
    _,a=p.wrap(CW-28,1000);_,b=q.wrap(CW-28,1000);h=a+b+30
    if y-h<58:raise RuntimeError('note overflow')
    c.setFillColor(LIGHT);c.roundRect(M,y-h,CW,h,9,fill=1,stroke=0)
    p.drawOn(c,M+14,y-14-a);q.drawOn(c,M+14,y-20-a-b);y-=h+14
    sections[-1]['blocks'].append(('note',(title,text)))

def table(headers,rows,widths):
    global y
    data=[[Paragraph(plain(x),tablehead) for x in headers]]+[[Paragraph(plain(x),small if len(x)>90 or page==7 else body) for x in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PURPLE),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#fafaff'),white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,1),(-1,-1),.4,HexColor('#e5e8ee'))]))
    _,height=t.wrap(CW,1000)
    if y-height<58:raise RuntimeError(f'table overflow page {page}, height {height}, y {y}')
    t.drawOn(c,M,y-height);y-=height+14
    sections[-1]['blocks'].append(('table',(headers,rows)))

start('자막을 만들고 MOV로 내보내기','01 / 직원용 빠른 시작','start')
para('대본마다 글꼴·크기·자간·색상을 정하고, 그라데이션과 빛 번짐을 더하는 Windows용 프로그램입니다. 투명 자막 MOV 하나를 내보내 프리미어에서 촬영 영상 위에 올립니다.')
note('1.6 버전에서 추가한 기능','궁서·궁서체, 글자 그라데이션, 테두리 빛 번짐을 지원합니다. 내보내기는 투명 MOV 하나로 정리했습니다. 프로젝트는 상단의 프로젝트 저장으로 따로 보관합니다.')
shot=ROOT/'docs/text-effects-screen.jpg'
if shot.exists():
    from PIL import Image
    im=Image.open(shot);width=440;height=width*im.height/im.width
    c.drawImage(str(shot),M+(CW-width)/2,y-height,width,height);y-=height+15
    sections[-1]['blocks'].append(('image','text-effects-screen.jpg'))
sub('매일 사용하는 순서')
para('① 시작.cmd를 열고 실행 창을 켜 둡니다.\n② 대본을 입력하고 시작·끝 시간을 맞춥니다.\n③ 글꼴과 글자 모양을 정하고 미리보기를 확인합니다.\n④ 프로젝트 저장 → 투명 자막 MOV 내보내기를 누릅니다.\n⑤ Premiere에서 촬영 영상 V1 / 자막 MOV V2 / 별도 오디오 A1에 배치합니다.')
para('다른 PC에서는 압축을 풀고 실행하세요. Windows와 Python 3.11 이상이 필요하며, 첫 실행에는 인터넷에 연결합니다.',small)

start('대본마다 글자 모양 바꾸기','02 / 글꼴 · 크기 · 자간 · 색상','captions')
para('왼쪽 대본 한 개가 한 장면입니다. 입력칸을 바꾸면 그 장면이 미리보기에 나타나고 보라색으로 표시됩니다. 다른 대본의 설정은 바뀌지 않습니다.')
table(['조절 항목','범위와 사용법'],[
 ('글꼴','대본 아래에서 선택합니다. 나눔스퀘어 계열·도현·지마켓 산스·빗썸고딕·궁서 등을 사용할 수 있습니다.'),
 ('글씨 크기','24~160. 1080 폭 기준이며 720 출력에서는 비례해서 줄어듭니다.'),
 ('자간 (px)','-15~30. 0은 기본, 양수는 넓게, 음수는 좁게입니다.'),
 ('글자색 / 테두리색','색상표 또는 #RRGGBB 코드로 고릅니다. 글자색은 그라데이션의 시작색으로도 사용합니다.'),
 ('테두리 두께','0~12. 0이면 테두리가 보이지 않습니다. 그라데이션과 빛 번짐을 켜도 테두리색은 따로 유지됩니다.'),
 ('스타일 / 움직임','말풍선·강조·기본 자막 / 팝업·흔들림·한 글자씩·페이드·고정을 선택합니다.')
],[140,CW-140])
sub('공통 설정과 실제 출력 모양')
para('오른쪽 세로 위치·움직임 강도는 모든 자막에 공통입니다. “현재 장면 실제 출력 모양 확인”은 현재 시점의 투명 자막을 실제 렌더러로 보여 줍니다. 바둑판은 투명 배경을 나타냅니다.')
note('긴 문장과 복제','긴 문장은 자동 줄바꿈·축소됩니다. 자막을 복제하면 글꼴·크기·자간·색상·그라데이션·빛 번짐도 함께 복사됩니다. 복제 후 시작·끝 시간을 확인하세요.')
para('최대 180초 / 100개 대본 / 대본당 160자입니다. 자막끼리 시간이 겹치면 내보낼 수 없습니다. 자동 음성 인식이나 자동 싱크 기능은 없습니다.',small)

start('그라데이션과 테두리 빛 번짐','03 / 참고 사진 스타일','text-effects')
para('각 대본 아래의 “그라데이션 · 테두리 빛 번짐”을 펼칩니다. 두 기능은 각각 켜고 끌 수 있습니다.')
table(['조절 항목','사용 방법'],[
 ('그라데이션','사용을 켜면 글자색 → 그라데이션 끝색으로 이어집니다. 테두리에는 적용되지 않습니다.'),
 ('그라데이션 방향','0°는 왼쪽→오른쪽, 90°는 위→아래, 45°는 좌상→우하입니다. 0~360°를 입력할 수 있습니다.'),
 ('테두리 빛 번짐','사용을 켜고 빛 번짐 색을 고릅니다. 글자와 테두리의 바깥으로 빛이 퍼집니다.'),
 ('빛 번짐 크기 / 강도','크기 0~50 (1080 폭 기준), 강도 0~100%. 크기를 높이면 넓게 퍼지고 강도를 높이면 진해집니다. 둘 중 하나가 0이면 번짐이 보이지 않습니다.'),
 ('참고 사진 스타일','궁서 + 분홍 그라데이션 + 흰 테두리 + 노란 빛 번짐을 적용합니다. 선택한 대본의 글꼴·색상·스타일을 바꾸며, 문구·시간·글씨 크기는 유지합니다.')
],[140,CW-140])
style_image=ROOT/'docs/text-style-sample.png'
if style_image.exists():
    from PIL import Image
    im=Image.open(style_image);width=CW;height=width*im.height/im.width
    c.drawImage(str(style_image),M,y-height,width,height);y-=height+12
    sections[-1]['blocks'].append(('image','text-style-sample.png'))
para('말풍선에서도 글자에만 적용됩니다. 큰 빛 번짐은 주변 여백을 넓게 사용합니다. 진한 촬영 영상과 밝은 영상 모두에서 확인하고, 필요하면 테두리 두께와 빛 강도를 낮추세요.',small)

start('글꼴 미리 보기','04 / 제공 글꼴과 Windows 글꼴','fonts')
para('기본 글꼴은 나눔스퀘어 ExtraBold입니다. 궁서·궁서체는 Windows에 설치된 글꼴을 사용하며 글꼴 파일을 배포본에 포함하지 않습니다.',small)
font_rows=[
 ('1','나눔스퀘어 ExtraBold','NanumSquareEB.ttf'),('2','나눔스퀘어 Bold','NanumSquareB.ttf'),
 ('3','나눔스퀘어라운드 ExtraBold','NanumSquareRoundEB.ttf'),('4','나눔스퀘어 네오 ExtraBold','NanumSquareNeo-dEb.ttf'),
 ('5','나눔스퀘어 네오 Heavy','NanumSquareNeo-eHv.ttf'),('6','배민 도현','DoHyeon-Regular.ttf'),
 ('7','지마켓 산스 Bold','GmarketSansTTFBold.ttf'),('8','지마켓 산스 Medium','GmarketSansTTFMedium.ttf'),('9','지마켓 산스 Light','GmarketSansTTFLight.ttf'),
 ('10','빗썸고딕 Original','Bithumb Gothic Original.ttf'),('11','빗썸고딕 Basic','Bithumb Gothic Basic.ttf'),
 ('12','궁서 · Windows 글꼴','batang.ttc'),('13','궁서체 · Windows 고정폭 글꼴','batang.ttc')]
for num,name,filename in font_rows:
    family='Specimen'+num;path=Path('C:/Windows/Fonts')/filename if num in ('12','13') else ROOT/'assets/fonts'/filename
    pdfmetrics.registerFont(TTFont(family,str(path),subfontIndex={'12':2,'13':3}.get(num,0)))
    para(name,small,gap=1)
    specimen=ParagraphStyle(family,parent=body,fontName=family,fontSize=15,leading=20)
    para('왜 그런지, 근거를 쓰세요!',specimen,gap=3)
para('폰트 설치.cmd는 동봉한 무료 글꼴 11종을 현재 사용자에게 설치합니다. 궁서가 목록에 없으면 Windows에 해당 한국어 글꼴을 설치하세요. Premiere에서는 완성된 MOV를 사용하므로 별도 글꼴 설치가 필요 없습니다.',small)

start('MOV를 프리미어에 올리기','05 / 내보내기 · 저장 · 문제 해결','premiere')
para('투명 자막 MOV 내보내기를 누르고 완료되면 “투명 자막 MOV 받기” 또는 “내보낸 폴더 열기”를 누릅니다. 생성되는 영상 파일은 captions_alpha.mov 하나입니다. MOV는 ProRes 4444 알파 채널 형식이며 소리는 없습니다.')
table(['프리미어 트랙','올릴 파일'],[('V2','내보낸 captions_alpha.mov'),('V1','직접 촬영한 영상'),('A1 등','별도로 만든 목소리와 효과음')],[140,CW-140])
para('MOV를 0초에 맞춥니다. 시퀀스는 1080 × 1920 / 30fps를 사용하고, 720으로 출력했다면 720 × 1280 / 30fps로 맞춥니다. 일반 플레이어에서 검게 보여도 Premiere에서 배경 영상이 비치면 정상입니다.')
note('문구와 디자인을 바꾸려면','MOV의 글자는 영상으로 완성되어 있습니다. 앱에서 수정한 뒤 다시 내보내세요. 그라데이션·빛 번짐·글꼴·움직임이 모두 MOV에 포함됩니다. 앱에 미리 넣은 촬영 영상은 배치 확인용이며 자막 MOV에는 포함되지 않습니다.')
sub('프로젝트 저장과 다른 PC로 이동')
para('프로젝트 저장은 편집 가능한 JSON을 내려받고 data/projects에도 사본을 남깁니다. 다른 PC에는 프로그램 폴더와 JSON을 옮깁니다. 미리보기용 촬영 영상을 넣었다면 data/media도 복사합니다. 궁서·궁서체로 다시 렌더링할 PC에는 해당 Windows 글꼴이 필요합니다.')
sub('문제가 생기면')
para('자막이 안 나오면 현재 시간이 자막의 시작·끝 사이인지 확인합니다. 내보내기 오류는 시간 겹침·입력 범위·여유 공간을 확인합니다. 세부 오류는 data/export-logs와 실패 폴더의 error.txt를 담당자에게 전달합니다.',small)
para('목소리 기준: 캡컷 애덤 1.3배속 / 화낼 때 스포츠엠씨. 목소리와 효과음은 별도로 만든 뒤 Premiere에 추가합니다. 이전 프로젝트는 자막을 유지해 불러오고 그라데이션·빛 번짐은 기본 꺼짐으로 시작합니다.',small)
c.save()

css='''body{margin:0;background:#f2f3f7;color:#263247;font:15px/1.9 "Malgun Gothic",sans-serif}header,main{max-width:960px;margin:auto;padding:30px}header{padding-bottom:5px}h1{font-size:32px}nav{display:flex;gap:10px;flex-wrap:wrap}nav a{padding:5px 10px;background:white;border-radius:6px;font-size:12px}section{background:white;padding:32px;border-radius:14px;margin:20px 0;scroll-margin-top:20px}h2{font-size:25px;margin-top:4px}h3{font-size:17px;margin-top:28px}small{color:#7765c7;font-weight:bold;letter-spacing:1px}.note{background:#f4f1fc;border-radius:10px;padding:20px;margin:20px 0}.note p{margin-bottom:0}table{border-collapse:collapse;width:100%;font-size:13px;margin:18px 0}th{background:#6553cd;color:white}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #e8e9f1}td:first-child{min-width:110px}a{color:#6250cf;text-decoration:none}img{max-width:100%;border:1px solid #eee;border-radius:10px}.actions{display:flex;gap:18px;font-size:13px}@media print{body{background:white}section{break-before:page;border-radius:0;padding:0}header,nav,.actions{display:none}}'''
parts=['<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>수논사 직원 매뉴얼</title><style>'+css+'</style><header><small>SUNONSA / EMPLOYEE GUIDE</small><h1>릴스 스튜디오 직원 매뉴얼</h1><div class="actions"><a href="/">← 프로그램으로</a><a href="../output/pdf/수논사_릴스_스튜디오_직원매뉴얼.pdf" target="_blank">PDF 열기 ↗</a></div><nav>']
for s in sections:parts.append(f'<a href="#{s["id"]}">{html.escape(s["title"])}</a>')
parts.append('</nav></header><main>')
for s in sections:
    parts.append(f'<section id="{s["id"]}"><small>{s["kicker"]}</small><h2>{s["title"]}</h2>')
    for kind,value in s['blocks']:
        if kind in ('p','h3'):parts.append(f'<{kind}>{plain(value)}</{kind}>')
        elif kind=='note':parts.append(f'<div class="note"><b>{plain(value[0])}</b><p>{plain(value[1])}</p></div>')
        elif kind=='image':parts.append(f'<img src="{value}" alt="릴스 스튜디오 작업 화면">')
        elif kind=='table':
            headers,rows=value;parts.append('<table><tr>'+''.join('<th>'+plain(x)+'</th>' for x in headers)+'</tr>')
            parts.extend('<tr>'+''.join('<td>'+plain(x)+'</td>' for x in row)+'</tr>' for row in rows);parts.append('</table>')
        elif kind=='links':parts.append('<p>'+'<br>'.join(f'<a href="{url}" target="_blank">{plain(label)} ↗</a>' for label,url in value)+'</p>')
    parts.append('</section>')
parts.append('</main></html>');(ROOT/'docs/manual.html').write_text(''.join(parts),encoding='utf-8')
print('PDF + HTML manual created:',page,'pages')
