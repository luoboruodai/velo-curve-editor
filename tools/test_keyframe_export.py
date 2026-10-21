import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/python'))
import curve_logic as m
import keyframe_export as ke

class FakeAnim:
    def __init__(self):
        self.name='';self.calls=[];self.keys=SimpleNamespace(text='')
    @property
    def path(self):return self.name
    def setKeyframe(self,position,channel='*',value=None,function=None):self.calls.append((position,channel,value,function))
    def op(self,name):
        if name=='keyframe':return SimpleNamespace(chans=lambda:[SimpleNamespace(name='fade')])
        if name=='keys':return self.keys
        raise KeyError(name)
class FakeOut:
    def __init__(self,anim):self.anim=anim
    def convertToKeyframes(self,tolerance):return self.anim
class FakeStatus:
    def __init__(self):self.par=SimpleNamespace(text=SimpleNamespace(eval=lambda:'',))
class KeyframeExportTests(unittest.TestCase):
    def make(self,names):
        anim=FakeAnim();parent=SimpleNamespace(children=[SimpleNamespace(name=n) for n in names])
        nodes={'curve_logic':SimpleNamespace(module=m),'out1':FakeOut(anim),'status':FakeStatus()}
        c=SimpleNamespace(id=id(self),op=lambda name:nodes[name],parent=lambda:parent,children=[SimpleNamespace(name=n) for n in names])
        m.CACHE[c.id]={}
        self.addCleanup(lambda:m.CACHE.pop(c.id,None))
        return c,anim
    def test_export_writes_all_samples_with_unique_name(self):
        c,anim=self.make(['velo_animation','velo_animation_01'])
        with patch.object(m,'state_from_component',return_value=m.preset_state('smooth')):
            path=ke.export(c)
        self.assertEqual(path,'velo_animation_02')
        self.assertEqual(len(anim.calls),257)
        self.assertEqual(anim.calls[0],(0,'fade',0.0,'linear()'))
        self.assertEqual(anim.calls[-1],(256,'fade',1.0,'linear()'))
        self.assertIn('velo_animation_02',m.st(c)['status'])
    def test_export_failure_returns_none_and_sets_status(self):
        c,anim=self.make([])
        c.op('out1').convertToKeyframes=lambda tolerance:(_ for _ in ()).throw(RuntimeError('no export'))
        with patch.object(m,'state_from_component',return_value=m.preset_state('smooth')):
            self.assertIsNone(ke.export(c))
        self.assertIn('失败',m.st(c)['status'])

if __name__=='__main__':unittest.main()
