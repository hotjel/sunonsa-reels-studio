import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine as e
from PIL import Image,ImageDraw

class TextEffectTests(unittest.TestCase):
    def test_gungsuh_uses_correct_collection_faces(self):
        self.assertEqual(e.load_font('gungsuh',60).getname()[0],'Gungsuh')
        self.assertEqual(e.load_font('gungsuhche',60).getname()[0],'GungsuhChe')
        self.assertNotEqual(e.load_font('gungsuh',60).getmask('수논사').tobytes() if hasattr(e.load_font('gungsuh',60).getmask('수논사'),'tobytes') else bytes(e.load_font('gungsuh',60).getmask('수논사')),bytes(e.load_font('batang',60).getmask('수논사')))
    def test_gradient_direction_and_outline_are_independent(self):
        mask=Image.new('L',(100,100));ImageDraw.Draw(mask).rectangle((25,25,74,74),fill=255)
        shape=Image.new('L',(100,100));ImageDraw.Draw(shape).rectangle((20,20,79,79),fill=255)
        c={'gradient':True,'gradientEnd':'#0000ff','gradientAngle':90}
        im=e.styled_text(Image.new('RGBA',(100,100)),mask,shape,c,1,'#ff0000','#ffffff',5)
        self.assertEqual(im.getpixel((21,50)),(255,255,255,255))
        self.assertGreater(im.getpixel((50,27))[0],im.getpixel((50,27))[2])
        self.assertGreater(im.getpixel((50,72))[2],im.getpixel((50,72))[0])
        self.assertEqual(im.getpixel((0,0))[3],0)
        c['gradientAngle']=0
        im=e.styled_text(Image.new('RGBA',(100,100)),mask,shape,c,1,'#ff0000','#ffffff',5)
        self.assertGreater(im.getpixel((27,50))[0],im.getpixel((72,50))[0])
    def test_glow_extends_beyond_outline_without_clipping(self):
        p=e.validate(e.SAMPLE);c=p['captions'][0];c.update(font='gungsuh',text='수논사',style='impact',fill='#ffa5f8',outline='#ffffff',stroke=4,glow=True,glowColor='#fff66a',glowBlur=18,glowStrength=85)
        glow=e.caption_card(p,c);c['glow']=False;plain=e.caption_card(p,c)
        self.assertGreater(glow.width,plain.width);self.assertGreater(glow.height,plain.height)
        box=glow.getbbox();self.assertGreater(box[0],0);self.assertGreater(box[1],0);self.assertLess(box[2],glow.width);self.assertLess(box[3],glow.height)
        self.assertTrue(any(0<rgba[3]<255 and rgba[:3]==(255,246,106) for _,rgba in glow.getcolors(1000000)))
    def test_new_defaults_and_per_cue_roundtrip(self):
        p=e.validate(e.SAMPLE);before=e.overlay_frame(p,3.4).tobytes()
        self.assertTrue(all(not c['gradient'] and not c['glow'] for c in p['captions']))
        p['captions'][0].update(font='gungsuhche',gradient=True,gradientEnd='#11aaee',gradientAngle=135,glow=True,glowBlur=25,glowStrength=65,glowColor='#aa11ff')
        restored=e.validate(json.loads(json.dumps(p)));self.assertEqual(restored,p)
        self.assertEqual(e.overlay_frame(restored,3.4).tobytes(),before)
    def test_invalid_effect_values_are_rejected(self):
        for key,value in [('gradient','yes'),('glow',1),('gradientEnd','red'),('glowColor','#fff'),('gradientAngle',361),('glowBlur',51),('glowStrength',-1)]:
            p=copy.deepcopy(e.SAMPLE);p['captions'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):e.validate(p)
    def test_all_styles_and_negative_spacing_keep_alpha(self):
        p=e.validate(e.SAMPLE);c=p['captions'][0]
        for style in e.STYLES:
            c.update(style=style,font='gungsuh',text='그라데이션\n빛 번짐',fontSize=110,letterSpacing=-15,gradient=True,glow=True,glowBlur=50)
            for width in (720,1080):
                p['width']=width;card=e.caption_card(p,c);self.assertEqual(card.mode,'RGBA');self.assertEqual(card.getchannel('A').getextrema(),(0,255))

if __name__=='__main__':unittest.main()
