"""U017 multi-keyframe value/velocity model tests (no TD required)."""
import copy,math,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/python'))
import curve_logic as m
import graph_engine as ge

class KeyframeModel(unittest.TestCase):

    def test_builtin_presets_replace_default_keyframes(self):
        fast=m.preset_state('fast')
        self.assertEqual((fast['x1'],fast['y1'],fast['x2'],fast['y2']),m.PRESETS['fast']['points'])
        self.assertEqual(fast['keyframes'][0]['right'],[1/3,2/3])
        self.assertEqual(fast['keyframes'][1]['left'],[2/3,1.0])
        self.assertNotAlmostEqual(m.evaluate(fast,.5),m.evaluate(m.preset_state('linear'),.5),delta=.02)
        for name,spec in m.PRESETS.items():
            if 'points' in spec:
                state=m.preset_state(name)
                self.assertEqual((state['x1'],state['y1'],state['x2'],state['y2']),spec['points'],name)

    def test_time_never_reverses_for_handles_or_legacy_curves(self):
        for name,spec in m.PRESETS.items():
            if 'points' in spec:self.assertLessEqual(spec['points'][0],spec['points'][2],name)
        s=m.normalized_state({'x1':.832,'y1':0.,'x2':.105,'y2':.668})
        # Crossing is allowed when the actual x derivative stays non-negative.
        self.assertTrue(m._cubic_x_monotonic(m._segment_points(s,0)))
        s=m.preset_state('smooth')
        s=m.move_keyframe_handle(s,1,'left',.05,.5)
        self.assertTrue(m._cubic_x_monotonic(m._segment_points(s,0)))
        s=m.move_keyframe_handle(s,0,'right',.95,.2)
        self.assertTrue(m._cubic_x_monotonic(m._segment_points(s,0)))

    def test_legacy_single_segment_compatibility(self):
        s=m.preset_state('linear')
        self.assertEqual(len(s['keyframes']),2)
        for u in (0,.1,.37,.5,.83,1):
            self.assertAlmostEqual(m.evaluate(s,u),u,delta=2e-3)
        raw=m.dumps_state(s)
        self.assertIn('"version":4',raw)
        self.assertEqual(m.loads_state(raw)['keyframes'],s['keyframes'])

    def test_de_casteljau_split_preserves_shape(self):
        s=m.normalized_state({'x1':.24,'y1':.68,'x2':.79,'y2':.15})
        before=m.sample_curve(s,129)[0]
        updated,index=m.add_keyframe_at(s,.37)
        self.assertEqual(index,1)
        self.assertEqual(len(updated['keyframes']),3)
        after=m.sample_curve(updated,129)[0]
        self.assertLess(max(abs(a-b) for a,b in zip(before,after)),2e-6)
        self.assertAlmostEqual(updated['keyframes'][1]['t'],.37,delta=1e-6)

    def test_multiple_splits_and_roundtrip(self):
        s=m.preset_state('smooth')
        for u in (.23,.51,.76):s,_=m.add_keyframe_at(s,u)
        self.assertEqual(len(s['keyframes']),5)
        restored=m.loads_state(m.dumps_state(s))
        self.assertEqual(restored['keyframes'],s['keyframes'])
        self.assertEqual(restored['speed_params'],s['speed_params'])
        self.assertLess(max(abs(a-b) for a,b in zip(m.sample_curve(s,65)[0],m.sample_curve(restored,65)[0])),1e-9)

    def test_move_keyframe_and_handle(self):
        s,_=m.add_keyframe_at(m.preset_state('smooth'),.45)
        moved=m.move_keyframe(s,1,.55,.72)
        self.assertAlmostEqual(m.evaluate(moved,.55),.72,delta=2e-6)
        self.assertEqual(m.evaluate(moved,0),0)
        self.assertEqual(m.evaluate(moved,1),1)
        adjusted=m.move_keyframe_handle(moved,1,'right',.7,.95)
        self.assertEqual(adjusted['keyframes'][1]['right'],[.7,.95])
        self.assertNotAlmostEqual(m.evaluate(adjusted,.6),m.evaluate(moved,.6),delta=.005)

    def test_per_segment_velocity_contract(self):
        s,_=m.add_keyframe_at(m.preset_state('smooth'),.45)
        s=m.move_keyframe(s,1,.45,.78)
        s=m.fit_velocity_points(s);s['edit_space']='speed'
        values,speeds=m.sample_curve(s,257)
        self.assertEqual(values[0],0);self.assertAlmostEqual(values[-1],1)
        self.assertAlmostEqual(m.evaluate(s,.45),.78,delta=1e-8)
        self.assertTrue(all(math.isfinite(v) for v in values+speeds))
        m.set_speed_parameters(s,1,[.2,1.8,.7,.3])
        self.assertAlmostEqual(m.evaluate(s,.45),.78,delta=1e-8)
        self.assertAlmostEqual(m.evaluate(s,1),1,delta=1e-8)

    def test_velocity_to_value_keeps_keyframes(self):
        s,_=m.add_keyframe_at(m.preset_state('fast'),.4)
        s=m.fit_velocity_points(s);s['edit_space']='speed'
        converted=m.value_points_from_velocity(s);converted['edit_space']='value'
        self.assertEqual(len(converted['keyframes']),3)
        self.assertAlmostEqual(m.evaluate(converted,.4),s['keyframes'][1]['v'],delta=1e-8)
        self.assertEqual(m.evaluate(converted,0),0);self.assertEqual(m.evaluate(converted,1),1)

    def test_reverse_multi_keyframes(self):
        s,_=m.add_keyframe_at(m.preset_state('smooth'),.4)
        r=m.reverse_state(s)
        for u in (.03,.17,.41,.69,.94):
            self.assertAlmostEqual(m.evaluate(r,u),1-m.evaluate(s,1-u),delta=3e-6)

    def test_nested_state_cache_key(self):
        s,_=m.add_keyframe_at(m.preset_state('smooth'),.4)
        key=m.state_key(s,ignore_ui=True)
        self.assertIn('keyframes',key)
        self.assertIsInstance(key,str)

    def test_add_limit(self):
        s=m.preset_state('linear')
        for u in (.1,.2,.3,.4,.5,.6,.7,.8,.9):s,_=m.add_keyframe_at(s,u)
        while len(s['keyframes'])<16:s,_=m.add_keyframe_at(s,.015+len(s['keyframes'])*.05)
        before=len(s['keyframes'])
        _,index=m.add_keyframe_at(s,.5)
        self.assertIsNone(index)
        self.assertEqual(len(s['keyframes']),before)

class BezierHandleFreedom(unittest.TestCase):
    def test_handle_and_keyframe_y_are_finite_but_unclamped(self):
        s=m.preset_state('smooth')
        s=m.move_keyframe_handle(s,0,'right',.42,8.5)
        self.assertEqual(s['y1'],8.5)
        s=m.move_keyframe_handle(s,1,'left',.58,-6.5)
        self.assertEqual(s['y2'],-6.5)
        s,_=m.add_keyframe_at(s,.5)
        moved=m.move_keyframe(s,1,.55,12.25)
        self.assertEqual(moved['keyframes'][1]['v'],12.25)
        values,_=m.sample_curve(moved)
        self.assertTrue(all(math.isfinite(v) for v in values))
        self.assertEqual((values[0],values[-1]),(0,1))

    def test_crossing_and_out_of_unit_handles_stay_when_monotonic(self):
        s=m.preset_state('smooth')
        right=m.move_keyframe_handle(s,0,'right',1.2,8.5)
        self.assertEqual((right['x1'],right['y1']),(1.2,8.5))
        left=m.move_keyframe_handle(s,1,'left',-.2,-6.5)
        self.assertEqual((left['x2'],left['y2']),(-.2,-6.5))
        crossed=m.move_keyframe_handle(s,1,'left',.1,1.)
        crossed=m.move_keyframe_handle(crossed,0,'right',.95,0.)
        self.assertGreater(crossed['x1'],crossed['x2'])
        for state in (right,left,crossed):
            self.assertTrue(m._cubic_x_monotonic(m._segment_points(state,0)))

    def test_true_time_reversal_uses_nearest_valid_position(self):
        s=m.preset_state('smooth')
        adjusted=m.move_keyframe_handle(s,0,'right',100.,0.)
        self.assertNotEqual(adjusted['x1'],100.)
        self.assertGreater(adjusted['x1'],s['x2'])
        self.assertTrue(m._cubic_x_monotonic(m._segment_points(adjusted,0)))
        repaired=m.normalized_state({'x1':100.,'y1':0.,'x2':-100.,'y2':1.})
        self.assertTrue(m._cubic_x_monotonic(m._segment_points(repaired,0)))

    def test_free_handles_roundtrip_and_viewport_expansion(self):
        s=m.normalized_state({'x1':1.2,'y1':8.5,'x2':.58,'y2':-6.5})
        restored=m.loads_state(m.dumps_state(s))
        self.assertEqual(tuple(restored[k] for k in ('x1','y1','x2','y2')),(1.2,8.5,.58,-6.5))
        points=ge.bezier_control_points(s)
        self.assertIn((1.2,8.5),points)
        self.assertIn((.58,-6.5),points)
        changed=ge.expand_view_to_point(s,1.2,8.5)
        self.assertTrue(changed)
        self.assertGreaterEqual(s['view_xmax'],1.2)
        self.assertGreaterEqual(s['view_ymax'],8.5)
        before=(s['view_xmin'],s['view_xmax'],s['view_ymin'],s['view_ymax'])
        self.assertFalse(ge.expand_view_to_point(s,.5,.5))
        self.assertEqual(before,(s['view_xmin'],s['view_xmax'],s['view_ymin'],s['view_ymax']))


    def test_panel_release_expands_view_to_freed_handle(self):
        state=m.preset_state('smooth');cache={'drag':'bezier1'}
        graph=SimpleNamespace(par=SimpleNamespace(w=SimpleNamespace(eval=lambda:560),h=SimpleNamespace(eval=lambda:400)),
                              panel=SimpleNamespace(u=0,v=0,shift=0,lselect=0))
        nodes={'curve_logic':SimpleNamespace(module=m),'graph':graph}
        c=SimpleNamespace(op=lambda name:nodes.get(name),par=SimpleNamespace(Selectedhandle=0))
        with patch.object(m,'st',return_value=cache),              patch.object(m,'state_from_component',side_effect=lambda _c:copy.deepcopy(state)),              patch.object(m,'assign_state',side_effect=lambda _c,value:state.clear() or state.update(copy.deepcopy(value))),              patch.object(m,'update'):
            _,screen,_=ge.transform(c)
            x,y=screen(1.2,8.5);graph.panel.u=x/560;graph.panel.v=y/400
            ge.panel_event(c,'release')
        self.assertAlmostEqual(state['x1'],1.2)
        self.assertAlmostEqual(state['y1'],8.5)
        self.assertGreaterEqual(state['view_xmax'],1.2)
        self.assertGreaterEqual(state['view_ymax'],8.5)
        self.assertIsNone(cache['drag'])


if __name__=='__main__':unittest.main()
