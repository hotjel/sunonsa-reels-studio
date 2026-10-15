import copy, json, sys, tempfile, threading, unittest
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine as e
tempfile.tempdir=str(e.ROOT/'tests')

class CaptionTests(unittest.TestCase):
    def test_old_projects_migrate_without_audio_or_mutation(self):
        p=copy.deepcopy(e.SAMPLE);p.update(version=1,font='nanumround',fontSize=80,voice={'asset':'missing.wav'},customSfx={'asset':'missing.wav'})
        for c in p['captions']:
            for key in ('font','fontSize','letterSpacing'):c.pop(key,None)
            c.update(sfx='custom',voiceRole='sports')
        before=copy.deepcopy(p);result=e.validate(p)
        self.assertEqual(p,before)
        self.assertEqual(result['version'],6);self.assertNotIn('voice',result)
        self.assertTrue(all((c['font'],c['fontSize'],c['letterSpacing'])==('nanumround',80,0) for c in result['captions']))
        self.assertTrue(all('sfx' not in c and 'voiceRole' not in c for c in result['captions']))

    def test_legacy_colors_preserve_each_styles_appearance(self):
        p=copy.deepcopy(e.SAMPLE);p.update(version=2,fill='#abcdef',outline='#fa1234',stroke=9)
        result=e.validate(p)
        expected=[('#22242a','#22242a',0),('#abcdef','#fa1234',9),('#abcdef','#fa1234',9),('#ffffff','#191b22',3)]
        self.assertEqual([(c['fill'],c['outline'],c['stroke']) for c in result['captions']],expected)
        self.assertNotIn('fill',p['captions'][0])

    def test_per_caption_colors_render_and_roundtrip_for_all_styles(self):
        p=e.validate(e.SAMPLE);before=e.overlay_frame(p,3.4).tobytes()
        for style in e.STYLES:
            p['captions'][0].update(fill='#12D46F',outline='#4422CC',stroke=5,style=style)
            result=e.validate(json.loads(json.dumps(p)))
            colors=dict((rgba,count) for count,rgba in e.caption_card(result,result['captions'][0]).getcolors(1000000))
            self.assertGreater(colors.get((18,212,111,255),0),10)
            self.assertGreater(colors.get((68,34,204,255),0),10)
            self.assertEqual(e.overlay_frame(result,3.4).tobytes(),before)
            self.assertEqual(result['captions'][0]['fill'],'#12d46f')
        p['captions'][0]['stroke']=0
        colors=dict((rgba,count) for count,rgba in e.caption_card(e.validate(p),e.validate(p)['captions'][0]).getcolors(1000000))
        self.assertNotIn((68,34,204,255),colors)

    def test_per_cue_settings_are_independent_and_persist(self):
        p=e.validate(e.SAMPLE);before=e.overlay_frame(p,3.4).tobytes()
        p['captions'][0].update(font='gmarket_bold',fontSize=95,letterSpacing=8)
        restored=e.validate(json.loads(json.dumps(p)))
        self.assertEqual(restored['captions'][0]['letterSpacing'],8)
        self.assertEqual(restored['captions'][1]['fontSize'],66)
        self.assertEqual(e.overlay_frame(restored,3.4).tobytes(),before)
        self.assertNotEqual(e.overlay_frame(restored,.4).tobytes(),e.overlay_frame(e.SAMPLE,.4).tobytes())

    def test_tracking_changes_real_glyph_width(self):
        p=e.validate(e.SAMPLE);c=p['captions'][0];c.update(text='수논사 ABC',style='clean',font='gmarket_medium')
        widths=[]
        for spacing in (-15,0,12):
            c['letterSpacing']=spacing;card=e.caption_card(p,c);widths.append(card.width)
            self.assertEqual(card.getchannel('A').getextrema(),(0,255))
        self.assertLess(widths[0],widths[1]);self.assertLess(widths[1],widths[2])
        c['fontSize']=100;self.assertGreater(e.caption_card(p,c).height,50)
        c.update(text='illl!!! 수논사',fontSize=24,letterSpacing=-15)
        card=e.caption_card(p,c)
        self.assertGreater(card.width,0);self.assertLessEqual(card.width,920)

    def test_invalid_cue_settings_are_rejected(self):
        for key,val in [('font','missing'),('fontSize',200),('fontSize',float('nan')),('letterSpacing',-16),('letterSpacing',31),('fill','red'),('outline','#12345'),('stroke',13),('stroke',float('nan'))]:
            p=copy.deepcopy(e.SAMPLE);p['captions'][0][key]=val
            with self.subTest(key=key,value=val),self.assertRaises(ValueError):e.validate(p)
        p=copy.deepcopy(e.SAMPLE);p['captions'][1]['start']=1
        with self.assertRaises(ValueError):e.validate(p)

    def test_fonts_wrapping_animations_and_transparency(self):
        p=e.validate(e.SAMPLE)
        for key in e.available_fonts():
            for style in e.STYLES:
                p['captions'][0].update(font=key,text='읽기 쉬운 자막을 만드세요! '*8,fontSize=160,letterSpacing=30,style=style)
                card=e.caption_card(p,p['captions'][0]);self.assertLessEqual(card.width,920);self.assertLessEqual(card.height,520)
        p=e.validate(e.SAMPLE)
        for animation in e.ANIMATIONS:
            p['captions'][0]['animation']=animation
            image=e.overlay_frame(p,.4);self.assertEqual(image.getchannel('A').getextrema(),(0,255))
        self.assertEqual(e.overlay_frame(p,2.9).getchannel('A').getextrema(),(0,0))

    def test_xml_is_caption_only_and_srt_is_text(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);e.write_xml(path/'timeline.xml',e.SAMPLE,12);e.write_srt(path/'captions.srt',e.SAMPLE)
            root=ET.parse(path/'timeline.xml').getroot()
            self.assertEqual(len(root.findall('.//clipitem')),1)
            self.assertEqual(len(root.findall('.//sequence/media/video/track')),2)
            self.assertEqual(root.findall('.//sequence/media/audio/track'),[])
            self.assertIn('왜 감점일까요?',(path/'captions.srt').read_text(encoding='utf-8-sig'))

    def test_removed_effects_are_ignored_in_legacy_projects(self):
        p=copy.deepcopy(e.SAMPLE);p['version']=4
        p['effects']=[{'file':'missing-effect.mov','start':0,'end':180}]
        p['video']['speed']=2
        restored=e.validate(p)
        self.assertNotIn('effects',restored);self.assertNotIn('speed',restored['video'])
        self.assertEqual(restored['captions'],e.validate(e.SAMPLE)['captions'])
        self.assertEqual(e.overlay_frame(restored,.4).tobytes(),e.overlay_frame(e.validate(e.SAMPLE),.4).tobytes())

    def test_cancel(self):
        flag=threading.Event();flag.set()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'취소'):e.export_project(e.SAMPLE,d,cancel=flag)

if __name__=='__main__':unittest.main()
