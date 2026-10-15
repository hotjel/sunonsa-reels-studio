'use strict';
const textEffectCache=new Map();
function effectColorField(c,i,key,label){
 const pair=document.createElement('label');pair.textContent=label;const field=document.createElement('div');field.className='color-field';
 const picker=document.createElement('input');picker.type='color';picker.value=c[key];picker.setAttribute('aria-label',`${i+1}번 ${label}`);
 const hex=document.createElement('input');Object.assign(hex,{type:'text',value:c[key],maxLength:7,spellcheck:false});hex.setAttribute('aria-label',`${i+1}번 ${label} HEX`);
 const apply=value=>{c[key]=value.toLowerCase();picker.value=c[key];hex.value=c[key];hex.removeAttribute('aria-invalid');focusCue(i);persist()};
 picker.oninput=()=>apply(picker.value);hex.oninput=()=>{if(/^#[0-9a-fA-F]{6}$/.test(hex.value))apply(hex.value);else hex.setAttribute('aria-invalid','true')};hex.onblur=()=>{if(hex.hasAttribute('aria-invalid')){hex.value=c[key];hex.removeAttribute('aria-invalid');toast('색상 코드는 #RRGGBB 형식으로 입력하세요.')}};
 field.append(picker,hex);pair.append(field);return pair;
}
function appendCaptionEffects(parent,c,i){
 const details=document.createElement('details');details.className='cue-text-effects';const summary=document.createElement('summary');summary.textContent='그라데이션 · 테두리 빛 번짐';details.append(summary);
 const grid=document.createElement('div');grid.className='text-effects-grid';
 for(const [key,label]of [['gradient','그라데이션 사용'],['glow','테두리 빛 번짐 사용']]){const pair=document.createElement('label');pair.className='check effect-toggle';const input=document.createElement('input');input.type='checkbox';input.checked=c[key];input.setAttribute('aria-label',`${i+1}번 ${label}`);input.onchange=()=>{c[key]=input.checked;focusCue(i);persist()};pair.append(input,document.createTextNode(label));grid.append(pair)}
 grid.append(effectColorField(c,i,'gradientEnd','그라데이션 끝색'),effectColorField(c,i,'glowColor','빛 번짐 색'));
 for(const [key,label,min,max,step] of [['gradientAngle','그라데이션 방향 (°)',0,360,15],['glowBlur','빛 번짐 크기',0,50,1],['glowStrength','빛 번짐 강도 (%)',0,100,1]]){const pair=document.createElement('label');pair.textContent=label;const input=document.createElement('input');Object.assign(input,{type:'number',min,max,step,value:c[key]});input.setAttribute('aria-label',`${i+1}번 ${label}`);input.oninput=()=>{if(input.value==='')return;c[key]=Number(input.value);focusCue(i);persist()};input.onblur=()=>{if(input.value==='')input.value=c[key]};pair.append(input);grid.append(pair)}
 const preset=document.createElement('button');preset.type='button';preset.className='reference-preset';preset.textContent='참고 사진 스타일';preset.setAttribute('aria-label',`${i+1}번 참고 사진 스타일`);preset.onclick=()=>{Object.assign(c,{font:config.fonts.gungsuh?'gungsuh':c.font,style:'impact',fill:'#ffa5f8',outline:'#ffffff',stroke:4,gradient:true,gradientEnd:'#f555e7',gradientAngle:90,glow:true,glowColor:'#fff66a',glowBlur:18,glowStrength:85});renderRows();const next=$('rows').children[i].querySelector('.cue-text-effects');next.open=true;focusCue(i);persist()};grid.append(preset);
 const note=document.createElement('p');note.className='muted';note.textContent='글자색이 그라데이션 시작색입니다. 0° 왼쪽→오른쪽 / 90° 위→아래. 빛은 글자·테두리 바깥으로 번집니다.';details.append(grid,note);parent.append(details);
}
function captionTextCard(ctx,c,lines,size,spacing){
 const key=JSON.stringify([c,lines,size,spacing,ctx.font,loadedFonts.has(c.font)]);if(textEffectCache.has(key))return textEffectCache.get(key);
 const stroke=Math.max(0,c.stroke)*.8,radius=Math.max(0,c.glowBlur)*.4,glow=c.glow&&c.glowStrength>0&&radius>0;
 const pad=Math.ceil(stroke+size+4+(glow?radius*3:0)),width=Math.ceil(Math.max(1,...lines.map(line=>lineWidth(ctx,line,spacing)))+2*pad),height=Math.ceil(lines.length*size*1.24+2*pad);
 function canvas(){const cv=document.createElement('canvas');cv.width=width;cv.height=height;return cv}
 const fill=canvas(),shape=canvas();
 for(const [cv,outlined]of [[fill,false],[shape,true]]){const cx=cv.getContext('2d');cx.font=ctx.font;cx.textBaseline='middle';cx.textAlign='left';cx.lineJoin='round';cx.fillStyle=cx.strokeStyle='white';cx.lineWidth=stroke;lines.forEach((line,i)=>{const layout=layoutLine(cx,line,spacing),y=height/2+(i-(lines.length-1)/2)*size*1.24,x0=width/2-layout.width/2-layout.left;for(const [ch,pos]of layout.positions){if(outlined&&stroke>0)cx.strokeText(ch,x0+pos,y);cx.fillText(ch,x0+pos,y)}})}
 const result=canvas(),out=result.getContext('2d');
 function tint(mask,color){const cv=canvas(),cx=cv.getContext('2d');cx.drawImage(mask,0,0);cx.globalCompositeOperation='source-in';cx.fillStyle=color;cx.fillRect(0,0,width,height);return cv}
 if(glow){const halo=tint(shape,c.glowColor),strength=c.glowStrength/100;for(const [blur,alpha]of [[radius,.9*strength],[radius,.9*strength],[radius*.35,strength]]){out.save();out.filter=`blur(${blur}px)`;out.globalAlpha=alpha;out.drawImage(halo,0,0);out.restore()}}
 if(stroke>0)out.drawImage(tint(shape,c.outline),0,0);
 const ink=canvas(),ix=ink.getContext('2d');ix.fillStyle=c.fill;
 if(c.gradient){const pixels=fill.getContext('2d').getImageData(0,0,width,height).data;let left=width,top=height,right=0,bottom=0;for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(pixels[(y*width+x)*4+3]){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y)}
  const angle=c.gradientAngle*Math.PI/180,dx=Math.cos(angle),dy=Math.sin(angle),half=Math.max(1,(Math.abs(dx)*(right-left)+Math.abs(dy)*(bottom-top))/2),cx=(left+right)/2,cy=(top+bottom)/2;
  const gradient=ix.createLinearGradient(cx-dx*half,cy-dy*half,cx+dx*half,cy+dy*half);gradient.addColorStop(0,c.fill);gradient.addColorStop(1,c.gradientEnd);ix.fillStyle=gradient;
 }
 ix.fillRect(0,0,width,height);ix.globalCompositeOperation='destination-in';ix.drawImage(fill,0,0);out.drawImage(ink,0,0);
 const card={canvas:result,width,height};textEffectCache.set(key,card);if(textEffectCache.size>16)textEffectCache.delete(textEffectCache.keys().next().value);return card;
}
