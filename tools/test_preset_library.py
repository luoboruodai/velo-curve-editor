"""U017 user-preset deletion and reorder tests (no TD or real user library)."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/python'))
import curve_logic as m
import preset_layout

class FakeComponent:
    def __init__(self,entries,path):
        self.id=id(self);self.path=path
        self.nodes={'user_presets':SimpleNamespace(text=json.dumps(entries)),'state_store':SimpleNamespace(text='{}')}
        self.par=SimpleNamespace(X1=SimpleNamespace(eval=lambda:1/3),Y1=SimpleNamespace(eval=lambda:1/3),X2=SimpleNamespace(eval=lambda:2/3),Y2=SimpleNamespace(eval=lambda:2/3))
        self.ops={'user_presets':self.nodes['user_presets'],'state_store':self.nodes['state_store'],'plugin_dialogs':SimpleNamespace(module=self),'preset_layout':SimpleNamespace(module=preset_layout)}
        self.status=[];self.cache={}
    def op(self,name):return self.ops.get(name)
    def persist_library(self,c,entries):
        self.path.write_text(json.dumps({'format':'velo-presets','version':3,'presets':entries},ensure_ascii=False),encoding='utf-8')
        return True

class PresetLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'qa.json'
        self.entries=[{'name':'QA_A','curve':m.preset_state('linear')},{'name':'QA_B','curve':m.preset_state('fast')}]
        self.c=FakeComponent(self.entries,self.path);m.CACHE[self.c.id]=self.c.cache
    def tearDown(self):
        m.CACHE.pop(self.c.id,None);self.tmp.cleanup()
    def test_delete_only_selected_user_preset(self):
        with patch.object(m,'update'),patch.object(m,'layout_ui'):
            self.assertTrue(m.delete_user_preset(self.c,0))
        self.assertEqual([e['name'] for e in m.user_presets(self.c)],['QA_B'])
        persisted=json.loads(self.path.read_text())['presets']
        self.assertEqual([e['name'] for e in persisted],['QA_B'])
    def test_invalid_delete_does_not_write(self):
        before=self.path.exists() and self.path.read_text()
        self.assertFalse(m.delete_user_preset(self.c,99))
        self.assertEqual([e['name'] for e in m.user_presets(self.c)],['QA_A','QA_B'])
    def test_reorder_to_end_persists(self):
        with patch.object(m,'update'),patch.object(m,'layout_ui'):
            self.assertTrue(m.move_user_preset(self.c,0,len(m.page_entries(self.c))))
        self.assertEqual([e['name'] for e in m.user_presets(self.c)],['QA_B','QA_A'])
        self.assertEqual([e['name'] for e in json.loads(self.path.read_text())['presets']],['QA_B','QA_A'])


    def test_builtin_drag_reorders_without_touching_user_library(self):
        before=self.path.read_text() if self.path.exists() else None
        with patch.object(m,'update'),patch.object(m,'layout_ui'):
            self.assertTrue(self.c.ops['preset_layout'].module.move(self.c,'linear',2))
        entries=m.preset_entries(self.c)
        self.assertEqual([entry[0] for entry in entries[:3]],['fast','linear','slow'])
        after=self.path.read_text() if self.path.exists() else None
        self.assertEqual(before,after)

    def test_builtin_context_and_recoverable_delete(self):
        with patch.object(m,'update'),patch.object(m,'layout_ui'):
            m.preset_card_event(self.c,0,'context')
            self.assertEqual(self.c.cache.get('preset_context'),0)
            self.assertTrue(self.c.ops['preset_layout'].module.delete_builtin(self.c,'linear'))
        self.assertNotIn('linear',[entry[0] for entry in m.preset_entries(self.c)])
        state=m.state_from_component(self.c)
        for field in m.UI_KEYS:state[field]=m.DEFAULTS[field]
        m.assign_state(self.c,state)
        self.assertIn('linear',[entry[0] for entry in m.preset_entries(self.c)])


    def test_delete_invalidates_catalogue_after_layout_and_clamps_page(self):
        self.c.cache['preset_page'] = 1
        self.c.cache['render_update_keys'] = {'catalogue': 'stale', 'selection': 'stale'}
        calls = []
        with patch.object(m, 'layout_ui', side_effect=lambda c: calls.append('layout')), patch.object(m, 'update', side_effect=lambda c: calls.append('update')):
            self.assertTrue(m.delete_user_preset(self.c, 1))
            self.assertNotIn('QA_B', [entry[1] for entry in m.page_entries(self.c)])
            self.assertTrue(m.delete_user_preset(self.c, 0))
        self.assertEqual(calls, ['layout', 'update', 'layout', 'update'])
        self.assertEqual(self.c.cache['preset_page'], 0)
        self.assertNotIn('catalogue', self.c.cache['render_update_keys'])
        self.assertNotIn('selection', self.c.cache['render_update_keys'])
        self.assertEqual(len(m.page_entries(self.c)), 16)



class PresetGridRegression(unittest.TestCase):
    class Param:
        def __init__(self, value): self.value = value
        def eval(self): return self.value

    def cells(self, count, width, height, grid_width, grid_height, location):
        grid = SimpleNamespace(par=SimpleNamespace(w=self.Param(grid_width), h=self.Param(grid_height)))
        c = SimpleNamespace(par=SimpleNamespace(w=self.Param(width), h=self.Param(height)),
                            op=lambda name: grid if name == 'preset_grid' else None)
        state = {'preset_size': 80.0, 'preset_location': location, 'compact': False}
        entries = [('preset_user_%d' % (i + 1), 'QA_%d' % i, {}) for i in range(count)]
        with patch.object(m, 'state_from_component', return_value=state), patch.object(m, 'page_entries', return_value=entries):
            return m.preset_grid_cells(c)

    def test_wide_survivor_keeps_exact_cell_after_delete(self):
        before = self.cells(2, 760, 760, 180, 700, 'right')
        after = self.cells(1, 760, 760, 180, 700, 'right')
        self.assertEqual(after[0], before[0])
        self.assertEqual(before[0][2], 83.0)

    def test_bottom_survivor_keeps_exact_cell_after_delete(self):
        before = self.cells(2, 560, 760, 540, 100, 'bottom')
        after = self.cells(1, 560, 760, 540, 100, 'bottom')
        self.assertEqual(after[0], before[0])
        self.assertEqual(m.preset_grid_spec(None, 1, False), (4, 1))
        self.assertEqual(m.preset_grid_spec(None, 2, False), (4, 1))


if __name__=='__main__':unittest.main()
