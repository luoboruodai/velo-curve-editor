"""Regression coverage for render invalidation and state caches (no TD required)."""
import json,sys,unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/python'))
import curve_logic as m
import plugin_dialogs as dialogs
import preset_layout

class Par:
    def __init__(self,value):self.value=value
    def eval(self):return self.value
class Pars:
    def __init__(self,**values):
        self.items={k:Par(v) for k,v in values.items()};self.writes=[]
    def __getattr__(self,key):return self.items[key]
    def __setitem__(self,key,value):
        self.writes.append((key,value));self.items[key].value=value
class Component:
    def __init__(self):
        self.id=id(self)
        self.par=Pars(X1=1/3,Y1=1/3,X2=2/3,Y2=2/3,w=760,h=760,Duration=2)
        self.nodes={'state_store':SimpleNamespace(text='{}'),'user_presets':SimpleNamespace(text='[]'),'preset_layout':SimpleNamespace(module=preset_layout)}
    def op(self,name):return self.nodes.get(name)

class PerformanceRegression(unittest.TestCase):
    def tearDown(self):m.CACHE.clear()
    def test_state_cache_is_copy_and_observes_direct_edits(self):
        c=Component()
        with patch.object(m,'normalized_state',wraps=m.normalized_state) as norm:
            s=m.state_from_component(c);s['grid_x']=19
            self.assertEqual(m.state_from_component(c)['grid_x'],4)
            self.assertEqual(norm.call_count,1)
            c.par['X1']=.7
            self.assertEqual(m.state_from_component(c)['x1'],.7)
            c.nodes['state_store'].text='{"grid_x":6}'
            self.assertEqual(m.state_from_component(c)['grid_x'],6)
            self.assertEqual(norm.call_count,3)
    def test_preset_list_is_not_regenerated_for_handle_motion(self):
        c=Component();first=m.preset_entries(c)
        c.par['X1']=.7
        self.assertIs(m.preset_entries(c),first)
        c.nodes['user_presets'].text=json.dumps([{'name':'test','curve':m.DEFAULTS}])
        second=m.preset_entries(c)
        self.assertEqual(len(second),len(first)+1)
        c.nodes['state_store'].text='{"mode":"elastic"}'
        self.assertEqual(m.preset_entries(c)[0][2]['mode'],'elastic')
    def test_fractional_panel_target_does_not_repeat_integer_writes(self):
        c=Component();par=Pars(x=0,y=0,w=100,h=20)
        c.nodes['field']=SimpleNamespace(par=par)
        m.place(c,'field',10.3,25.7,100.3,22.7)
        first=list(par.writes);self.assertTrue(first)
        m.place(c,'field',10.3,25.7,100.3,22.7)
        self.assertEqual(par.writes,first)
    def test_closed_dialog_hides_only_once(self):
        c=Component();q=m.st(c)
        c.nodes['ui_style']=SimpleNamespace(module=SimpleNamespace(MODAL_NAMES=('old1',)))
        with patch.object(dialogs,'logic',return_value=m),patch.object(m,'set_visible') as vis:
            dialogs.sync(c);self.assertGreater(vis.call_count,0);vis.reset_mock()
            dialogs.motion(c,1/60);dialogs.sync(c)
            vis.assert_not_called()
    def test_drag_does_not_rebuild_grid_or_preset_library(self):
        c=Component();count=Counter()
        for name in ('curve_values','curve_shape','speed_shape','handle_shape','anchor_shape','playhead_shape','grid_shape','grid_main_shape','preset_cards_shape','preset_curves_shape','preset_frames_shape','preset_selected_shape','preset_hover_shape'):
            c.nodes[name]=SimpleNamespace(cook=lambda force,n=name:count.update([n]))
        with patch.object(m,'update_controls'),patch.object(m,'update_equation'),patch.object(m,'update_button_styles'),patch.object(m,'sync_to_parent'),patch.object(m,'update_preset_labels'):
            m.update(c);count.clear();c.par['X1']=.4;m.update(c)
            self.assertEqual(count['curve_values'],1)
            self.assertEqual(count['curve_shape'],1)
            self.assertEqual(count['preset_curves_shape'],0)
            self.assertEqual(count['preset_cards_shape'],0)
            self.assertEqual(count['grid_shape'],0)
            count.clear();m.update(c);self.assertEqual(sum(count.values()),0)
    def test_grid_change_does_not_recook_output(self):
        c=Component();count=Counter()
        for name in ('curve_values','grid_shape','grid_main_shape'):
            c.nodes[name]=SimpleNamespace(cook=lambda force,n=name:count.update([n]))
        with patch.object(m,'update_controls'),patch.object(m,'update_equation'),patch.object(m,'update_button_styles'),patch.object(m,'sync_to_parent'),patch.object(m,'update_preset_labels'):
            m.update(c);count.clear();c.nodes['state_store'].text='{"grid_x":6}';m.update(c)
            self.assertEqual(count['grid_shape'],1)
            self.assertEqual(count['curve_values'],0)

if __name__=='__main__':unittest.main()
