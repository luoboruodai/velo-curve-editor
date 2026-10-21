"""U024 adaptive theme role regressions; no TD required."""
import copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/python'))
ROOT=Path(__file__).resolve().parents[1]
import curve_logic as m
import graph_engine as ge
import plugin_dialogs as dialogs
import ui_style

class Param:
    def __init__(self,value=0):self.value=value
    def eval(self):return self.value
class Params:
    def __getitem__(self,name):return self.__dict__.setdefault(name,Param())
    def __setitem__(self,name,value):self.__dict__[name]=Param(value)
    def __getattr__(self,name):return self[name]
    def __setattr__(self,name,value):self.__dict__[name]=Param(value)
class ThemeRegression(unittest.TestCase):
    def fixture(self,color,handles='#dcdcdc'):
        state=m.preset_state('smooth');state['theme_color']=color;state['theme_handles']=handles
        names=('curve_mat','handle_mat','speed_mat','anchor_mat','selected_keyframe_mat',
               'preset_curves_mat','preset_selected_mat','preset_hover_mat','ui_icons_mat',
               'param1_knob_rounded','param1_halo_rounded','settings_compact_knob_rounded',
               'settings_theme_swatch_rounded','dlg_swatch_curve','dlg_swatch_handles',
               'dlg_swatch_background','graph_rounded')
        nodes={name:SimpleNamespace(par=Params()) for name in names}
        nodes['curve_logic']=SimpleNamespace(module=m)
        c=SimpleNamespace(op=lambda name:nodes.get(name));cache={}
        return c,state,cache,nodes
    def apply(self,c,state,cache):
        with patch.object(m,'st',return_value=cache),patch.object(m,'state_from_component',return_value=copy.deepcopy(state)):
            ge.apply_visuals(c)
    def assert_rgb(self,node,prefix,color):
        for channel,expected in zip('rgb',color):self.assertAlmostEqual(node[prefix+channel].eval(),expected)
    def test_amber_updates_all_accent_roles(self):
        c,state,cache,nodes=self.fixture('#f2b35d');self.apply(c,state,cache);amber=ge.rgb('#f2b35d')
        for name in ('selected_keyframe_mat','preset_curves_mat','preset_selected_mat','preset_hover_mat','ui_icons_mat'):
            self.assert_rgb(nodes[name].par,'color',amber)
        for name in ('param1_knob_rounded','param1_halo_rounded','settings_compact_knob_rounded'):
            self.assert_rgb(nodes[name].par,'fillcolor',ge.rgb('#dcdcdc'))
        self.assert_rgb(nodes['anchor_mat'].par,'color',ge.rgb('#dcdcdc'))
        self.assert_rgb(nodes['settings_theme_swatch_rounded'].par,'fillcolor',amber)
        self.assert_rgb(nodes['graph_rounded'].par,'fillcolor',ge.rgb('#222222'))
        self.assert_rgb(nodes['dlg_swatch_handles'].par,'bgcolor',ge.rgb('#dcdcdc'))
    def test_second_theme_change_does_not_use_stale_material_cache(self):
        c,state,cache,nodes=self.fixture('#f2b35d');self.apply(c,state,cache)
        state['theme_color']='#39c5cf';self.apply(c,state,cache);cyan=ge.rgb('#39c5cf')
        self.assert_rgb(nodes['preset_curves_mat'].par,'color',cyan)
        self.assert_rgb(nodes['preset_hover_mat'].par,'color',cyan)
        self.assert_rgb(nodes['ui_icons_mat'].par,'color',cyan)
    def test_custom_handle_color_remains_independent(self):
        c,state,cache,nodes=self.fixture('#f2b35d','#ffffff');self.apply(c,state,cache)
        self.assert_rgb(nodes['anchor_mat'].par,'color',(1,1,1))
        self.assert_rgb(nodes['preset_curves_mat'].par,'color',ge.rgb('#f2b35d'))
        self.assert_rgb(nodes['dlg_swatch_handles'].par,'bgcolor',(1,1,1))

    def test_dialog_selection_and_primary_actions_follow_theme(self):
        state=m.preset_state('smooth');state['theme_color']='#f2b35d'
        nodes={name:SimpleNamespace(par=Params(),panel=SimpleNamespace(rollover=False,lselect=False)) for name in dialogs.NAMES}
        nodes['curve_logic']=SimpleNamespace(module=m);nodes['graph_engine']=SimpleNamespace(module=ge);nodes['ui_style']=SimpleNamespace(module=ui_style)
        params=Params();params['w']=760;params['h']=760
        c=SimpleNamespace(op=lambda name:nodes.get(name),par=params)
        q={'modal_kind':'settings','settings_open':True,'dialog_page':'interface','modal_amount':1.0,
           'field_initialized':set(),'input_values':{},'dialog_targets':{}}
        with patch.object(m,'st',return_value=q),patch.object(m,'state_from_component',return_value=copy.deepcopy(state)):
            dialogs.layout(c);dialogs.motion(c,1.0)
        amber=ge.rgb('#f2b35d')
        for name in ('page_interface','loc_right','fit'):
            self.assert_rgb(q['dialog_targets'][name] and nodes['dlg_'+name+'_bg'].par,'bgcolor',amber)
        self.assertEqual(q['dialog_targets']['compact'],(.14,.14,.14))
        border=(ROOT/'src/curve_editor.tox.dir/CurveEditor/dlg_compact_bg_rounded.parm').read_text()
        self.assertIn('borderwidth 0 1',border)
        self.assertIn('borderr 0 0.32',border)


    def test_glass_tools_use_native_translucent_materials(self):
        base=ROOT/'src/curve_editor.tox.dir/CurveEditor'
        for name in ('view_group_bg','segment_group_bg'):
            text=(base/(name+'_rounded.parm')).read_text()
            self.assertIn('fillalpha 0 0.42',text)
            self.assertIn('borderalpha 0 0.58',text)
        for name in ('view_fit_bg','view_in_bg','view_out_bg','segment_prev_bg','segment_next_bg'):
            self.assertIn('fillalpha 0 0.72',(base/(name+'_rounded.parm')).read_text())



if __name__=='__main__':unittest.main()
