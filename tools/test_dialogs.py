"""Focused regressions; native pointer behavior is tested separately in TD."""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/python'))
import plugin_dialogs as dialogs
import curve_logic as curves
import ui_style


class DialogRegression(unittest.TestCase):
    def test_context_menu_hit_layers(self):
        base=ROOT/'src/curve_editor.tox.dir/CurveEditor'
        expected={'preset_context_bg':89,'preset_context_delete_bg':90,'preset_context_delete':92,
                  'preset_context_delete_label':93,'preset_context_export_bg':90,
                  'preset_context_export':92,'preset_context_export_label':93}
        for name,layer in expected.items():
            text=(base/(name+'.parm')).read_text()
            self.assertIn(f'layer 0 {layer}',text,name)
        self.assertLess(expected['preset_context_bg'],expected['preset_context_delete_bg'])
        self.assertLess(expected['preset_context_delete_bg'],expected['preset_context_delete'])
        self.assertLess(expected['preset_context_delete'],expected['preset_context_delete_label'])

    def test_input_layers_above_backdrop(self):
        self.assertEqual(dialogs.HIT_LAYERS['dlg_backdrop_hit'],101)
        for name,layer in dialogs.HIT_LAYERS.items():
            if name!='dlg_backdrop_hit':self.assertGreater(layer,109,name)
        self.assertFalse(hasattr(dialogs,'poll'),'No duplicate polling dispatcher')

    def test_generated_native_callbacks(self):
        base=ROOT/'src/curve_editor.tox.dir/CurveEditor'
        for name,(kind,_) in dialogs.catalogue().items():
            if kind in ('hit','slider'):
                text=(base/('event_'+name+'.parm')).read_text()
                self.assertIn('offtoon 0 on',text,name)
                self.assertIn('ontooff 0 off',text,name)
            if kind=='input':
                self.assertIn(name+'_bg',dialogs.catalogue())
                text=(base/(name+'.parm')).read_text()
                self.assertIn('clickthrough 0 off',text)
                self.assertIn('bgalpha 0 0',text)
                self.assertTrue((base/(name+'_bg_rounded.parm')).exists())

    def action_fixture(self):
        q={'input_values':{'grid_x':'6','grid_y':'7','hex_curve':'#4a90e2'},
           'field_initialized':{'grid_x','grid_y','hex_curve'}}
        s=curves.normalized_state({'grid_x':6,'grid_y':7,'compact':True})
        fake=SimpleNamespace(st=lambda c:q,state_from_component=lambda c:dict(s),
            UI_KEYS=curves.UI_KEYS,DEFAULTS=curves.DEFAULTS,assign_state=lambda c,v:s.update(v))
        c=SimpleNamespace(op=lambda n:SimpleNamespace(module=SimpleNamespace(action=lambda *a:False)))
        return c,q,s,fake

    def test_reset_invalidates_stale_field_text(self):
        c,q,s,m=self.action_fixture()
        with patch.object(dialogs,'logic',return_value=m),patch.object(dialogs,'refresh'),patch.object(dialogs,'sync'):
            dialogs.action(c,'dlg_reset')
        self.assertEqual(s['grid_x'],4)
        self.assertEqual(s['grid_y'],4)
        self.assertNotIn('grid_x',q['input_values'])
        self.assertNotIn('grid_y',q['field_initialized'])

    def test_color_choice_invalidates_hex_text(self):
        c,q,s,m=self.action_fixture()
        with patch.object(dialogs,'logic',return_value=m),patch.object(dialogs,'refresh'),patch.object(dialogs,'sync'):
            dialogs.action(c,'dlg_color_amber')
        self.assertEqual(s['theme_color'],'#f2b35d')
        self.assertNotIn('hex_curve',q['field_initialized'])
        self.assertNotIn('hex_curve',q['input_values'])

    def test_grid_invalid_value_does_not_change_state(self):
        c,q,s,m=self.action_fixture()
        with patch.object(dialogs,'logic',return_value=m),patch.object(dialogs,'refresh'),patch.object(dialogs,'sync'):
            dialogs.input_changed(c,'dlg_grid_x','0')
        self.assertEqual(s['grid_x'],6)
        self.assertIn('1–20',q['dialog_message'])

    def test_presets_keep_output_contract(self):
        for name in curves.PRESETS:
            values,speeds=curves.sample_curve(curves.preset_state(name))
            self.assertEqual(len(values),257,name)
            self.assertEqual((values[0],values[-1]),(0,1),name)
            self.assertTrue(all(math.isfinite(x) for x in values+speeds),name)


class VisualTokenRegression(unittest.TestCase):
    def test_recessed_groups_share_grayscale_and_border(self):
        base=ROOT/'src/curve_editor.tox.dir/CurveEditor'
        for name in ('equation_bg','easecopy_bg'):
            text=(base/(name+'_rounded.parm')).read_text()
            for channel in 'rgb':
                self.assertIn(f'fillcolor{channel} 0 0.145',text,name)
                self.assertIn(f'border{channel} 0 0.267',text,name)
        graph=(base/'graph_rounded.parm').read_text()
        for channel in 'rgb':self.assertIn(f'fillcolor{channel} 0 0.133',graph)
        button=(base/'easecopy_copy.parm').read_text()
        for channel in 'rgb':self.assertIn(f'color{channel} 0 0.235',button)



    def test_integer_rows_preserve_exact_four_pixel_gaps(self):
        for total,count in ((394,3),(550,4),(446,5),(260,3),(260,5)):
            widths=ui_style.row_widths(total,count)
            self.assertEqual(sum(widths)+4*(count-1),total)
            self.assertLessEqual(max(widths)-min(widths),1)



    def test_section_legends_are_transparent_captions(self):
        base=ROOT/'src/curve_editor.tox.dir/CurveEditor'
        for index in range(1,5):
            legend=(base/f'dlg_legend{index}.parm').read_text()
            self.assertIn('bgalpha 0 0',legend)
            self.assertIn('fontcolorr 0 0.62',legend)



if __name__=='__main__':unittest.main()
