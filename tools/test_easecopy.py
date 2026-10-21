"""EaseCopy clipboard semantics; no TD or real user data required."""
import json
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/python'))
import curve_logic as m
import easecopy as ec
import esc_events_callbacks as keyboard
import graph_engine


class Params:
    def __init__(self):
        object.__setattr__(self, '_values', {'X1': 1/3, 'Y1': 1/3, 'X2': 2/3, 'Y2': 2/3})

    def __getattr__(self, name):
        return SimpleNamespace(eval=lambda: self._values[name])

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._values[name] = value


class FakeComponent:
    def __init__(self):
        self.id = id(self)
        self.cache = {}
        self.nodes = {
            'state_store': SimpleNamespace(text='{}'),
            'easecopy_store': SimpleNamespace(text=json.dumps(ec.empty_buffer())),
            'selected_keyframe_shape': SimpleNamespace(cook=lambda force: None),
            'curve_logic': SimpleNamespace(module=m),
        }
        self.par = Params()

    def op(self, name):
        return self.nodes.get(name)


class EaseCopyTests(unittest.TestCase):
    def setUp(self):
        self.c = FakeComponent()
        m.CACHE[self.c.id] = self.c.cache
        self.patches = [patch.object(m, 'update'), patch.object(m, 'layout_ui')]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        m.CACHE.pop(self.c.id, None)

    @staticmethod
    def keys(count):
        state = m.preset_state('smooth')
        for index in range(1, count - 1):
            state, _ = m.add_keyframe_at(state, index / (count - 1))
        state['edit_space'] = 'value'
        return state

    def assign(self, state, selection=None):
        m.assign_state(self.c, state)
        if selection is None:
            self.c.cache.pop('easecopy_range', None)
            self.c.cache.pop('easecopy_anchor', None)
        else:
            self.c.cache['easecopy_range'] = selection

    def test_keyboard_shift_tracks_native_modifier(self):
        dat = SimpleNamespace(parent=lambda: self.c)
        args = dict(key='shift', character='', alt=0, lAlt=0, rAlt=0, ctrl=0, lCtrl=0, rCtrl=0,
                    shift=1, lShift=0, rShift=0, state=1, time=0, cmd=0, lCmd=0, rCmd=0)
        with patch.object(keyboard, 'parent', return_value=self.c, create=True):
            keyboard.onKey(dat, **args)
            self.assertTrue(self.c.cache['key_shift'])
            args['state'] = 0
            keyboard.onKey(dat, **args)
            self.assertFalse(self.c.cache['key_shift'])

    def test_right_click_extends_selection_range(self):
        state = self.keys(4)
        self.assign(state)
        ec.select_keyframe(self.c, 1)
        graph = SimpleNamespace(par=SimpleNamespace(w=SimpleNamespace(eval=lambda: 560), h=SimpleNamespace(eval=lambda: 400)),
                                panel=SimpleNamespace(u=0, v=0, shift=0, lselect=0))
        self.c.nodes['graph'] = graph
        self.c.nodes['easecopy'] = SimpleNamespace(module=ec)
        _, screen, _ = graph_engine.transform(self.c)
        x, y = screen(state['keyframes'][3]['t'], state['keyframes'][3]['v'])
        graph.panel.u = x / 560
        graph.panel.v = y / 400
        graph_engine.panel_event(self.c, 'context')
        self.assertEqual(ec.selection_range(self.c), (1, 3))

    def test_single_and_range_copy_then_clear(self):
        self.assign(self.keys(4))
        ec.select_keyframe(self.c, 1)
        ec.select_keyframe(self.c, 3, extend=True)
        self.assertEqual(ec.selection_range(self.c), (1, 3))
        self.assertTrue(ec.action(self.c, 'easecopy_copy'))
        self.assertEqual(len(ec.clipboard(self.c)['keys']), 3)
        self.assertTrue(ec.action(self.c, 'easecopy_clear'))
        self.assertEqual(ec.clipboard(self.c)['keys'], [])
        before = m.dumps_state(m.state_from_component(self.c))
        self.assertFalse(ec.action(self.c, 'easecopy_paste_ease'))
        self.assertEqual(before, m.dumps_state(m.state_from_component(self.c)))

    def test_paste_ease_preserves_times_values_and_output(self):
        source = self.keys(2)
        m.set_speed_parameters(source, 0, [.2, 1.8, .65, .35])
        self.assign(source)
        ec.action(self.c, 'easecopy_copy')
        target = self.keys(2)
        before = [(k['t'], k['v']) for k in target['keyframes']]
        self.assign(target)
        self.assertTrue(ec.action(self.c, 'easecopy_paste_ease'))
        result = m.state_from_component(self.c)
        self.assertEqual([(k['t'], k['v']) for k in result['keyframes']], before)
        for a, b in zip(m.speed_parameters(result, 0), [.2, 1.8, .65, .35]):
            self.assertAlmostEqual(a, b)
        values, speeds = m.sample_curve(result)
        self.assertEqual((values[0], values[-1]), (0, 1))
        self.assertTrue(all(math.isfinite(v) for v in values + speeds))

    def test_paste_value_preserves_eases_and_endpoints(self):
        source = self.keys(4)
        source['keyframes'][1]['v'] = .2
        source['keyframes'][2]['v'] = .8
        self.assign(source)
        ec.action(self.c, 'easecopy_copy')
        target = self.keys(4)
        for index, params in enumerate(([.2, 1.8, .65, .35], [.3, .7, .55, 1.1], [.4, 1.2, .6, .5])):
            m.set_speed_parameters(target, index, params)
        original_eases = [m.speed_parameters(target, i) for i in range(3)]
        self.assign(target)
        self.assertTrue(ec.action(self.c, 'easecopy_paste_value'))
        result = m.state_from_component(self.c)
        self.assertAlmostEqual(result['keyframes'][1]['v'], .2)
        self.assertAlmostEqual(result['keyframes'][2]['v'], .8)
        self.assertEqual(result['keyframes'][0]['v'], 0)
        self.assertEqual(result['keyframes'][-1]['v'], 1)
        for index in range(3):
            for a, b in zip(m.speed_parameters(result, index), original_eases[index]):
                self.assertAlmostEqual(a, b, places=7)

    def test_equal_multiple_and_rejected_count(self):
        source = self.keys(3)
        self.assign(source)
        ec.action(self.c, 'easecopy_copy')
        target = self.keys(4)
        self.assign(target)
        before = m.dumps_state(m.state_from_component(self.c))
        self.assertFalse(ec.action(self.c, 'easecopy_paste_ease'))
        self.assertEqual(before, m.dumps_state(m.state_from_component(self.c)))
        source = self.keys(2)
        self.assign(source)
        ec.action(self.c, 'easecopy_copy')
        self.assign(target)
        self.assertTrue(ec.action(self.c, 'easecopy_paste_ease'))

    def test_preserve_passthroughs(self):
        source = self.keys(2)
        m.set_speed_parameters(source, 0, [.2, 1.8, .65, .35])
        self.assign(source)
        ec.action(self.c, 'easecopy_copy')
        ec.action(self.c, 'easecopy_passthrough')
        target = self.keys(4)
        m.set_speed_parameters(target, 2, [.8, 2.5, .9, .2])
        self.assertIn(1, ec.passthrough_keys(target))
        self.assertNotIn(2, ec.passthrough_keys(target))
        original = [m.speed_parameters(target, i) for i in range(3)]
        original_value = target['keyframes'][1]['v']
        self.assign(target)
        self.assertTrue(ec.action(self.c, 'easecopy_paste_ease'))
        result = m.state_from_component(self.c)
        self.assertEqual(m.speed_parameters(result, 0), original[0])
        self.assertEqual(m.speed_parameters(result, 1), original[1])
        for a, b in zip(m.speed_parameters(result, 2), [.2, 1.8, .65, .35]):
            self.assertAlmostEqual(a, b)
        self.assign(target)
        self.assertTrue(ec.action(self.c, 'easecopy_paste_value'))
        result = m.state_from_component(self.c)
        self.assertEqual(result['keyframes'][1]['v'], original_value)
        self.assertEqual(result['keyframes'][2]['v'], 0)
        ec.action(self.c, 'easecopy_passthrough')
        self.assign(target)
        ec.action(self.c, 'easecopy_paste_value')
        self.assertEqual(m.state_from_component(self.c)['keyframes'][1]['v'], 1)


if __name__ == '__main__':
    unittest.main()
