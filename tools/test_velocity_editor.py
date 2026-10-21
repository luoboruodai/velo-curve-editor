"""U015 velocity editor, preset identity and display fixes (no TD required)."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/python'))
import curve_logic as m
import curve_model as cm
import graph_engine as ge

class VelocityModel(unittest.TestCase):
    def test_constant_speed_is_linear(self):
        s=m.normalized_state({'edit_space':'speed'})
        for u in (0,0.1,0.37,0.5,0.83,1.0):
            v,d=m.value_and_speed(s,u)
            self.assertAlmostEqual(v,u,delta=2e-3)
            self.assertAlmostEqual(d,1.0,delta=2e-3)
    def test_value_contract(self):
        for vy1,vy2 in ((0,4),(2,0.4),(0.2,6),(8,8)):
            s=m.normalized_state({'edit_space':'speed','vx1':0.2,'vy1':vy1,'vx2':0.8,'vy2':vy2})
            values,speeds=m.sample_curve(s)
            self.assertEqual(len(values),257)
            self.assertEqual(values[0],0.0)
            self.assertAlmostEqual(values[-1],1.0,places=9)
            self.assertTrue(all(math.isfinite(v) for v in values+speeds))
            self.assertTrue(all(b>=a-1e-9 for a,b in zip(values,values[1:])))
    def test_velocity_beats_value_space_only_when_selected(self):
        s=m.normalized_state({'edit_space':'value'})
        v1,_=m.value_and_speed(s,0.5)
        s['edit_space']='speed';s['vy1']=3.0
        v2,_=m.value_and_speed(s,0.5)
        self.assertNotAlmostEqual(v1,v2,delta=0.02)
        self.assertAlmostEqual(m.evaluate(s,0.5),v2,places=9)
    def test_normalized_state_clamps(self):
        s=m.normalized_state({'vy1':-2,'vy2':99,'vx1':-1,'vx2':2,'edit_space':'bogus'})
        self.assertEqual((s['vy1'],s['vy2'],s['vx1'],s['vx2'],s['edit_space']),(0.0,cm.VEL_MAX,0.0,1.0,'value'))
    def test_serialization_roundtrip_and_compat(self):
        s=m.normalized_state({'edit_space':'speed','vx1':0.25,'vy1':1.5,'vx2':0.75,'vy2':0.5})
        s2=m.loads_state(m.dumps_state(s))
        for k in ('edit_space','vx1','vy1','vx2','vy2'):self.assertEqual(s2[k],s[k])
        old=m.loads_state('{"format":"td-curve-editor","version":3,"curve":{"mode":"bezier","bezier":[0.3,0.3,0.7,0.7]}}')
        self.assertEqual(old['edit_space'],'value')
    def test_fit_velocity_points(self):
        for name in ('linear','fast','slow','smooth'):
            s=m.fit_velocity_points(m.preset_state(name))
            self.assertTrue(0<=s['vy1']<=cm.VEL_MAX and 0<=s['vy2']<=cm.VEL_MAX)
            values,_=m.sample_curve({**s,'edit_space':'speed'})
            self.assertAlmostEqual(values[-1],1.0,places=9)

class BezierSpeedDisplayFix(unittest.TestCase):
    def test_reversal_cusp_is_clipped_by_display_scale(self):
        s=m.normalized_state({'x1':1.0,'y1':0.35,'x2':0.01,'y2':0.73})
        speeds=[m.value_and_speed(s,(i+0.5)/1024)[1] for i in range(1024)]
        finite=sorted(abs(v) for v in speeds if v is not None)
        scale=finite[int(0.95*(len(finite)-1))]
        clipped=[v for v in speeds if v is not None and abs(v)>scale]
        self.assertLessEqual(len(clipped),int(0.06*len(speeds)),'spike occupies only the narrow near-vertical window')
        self.assertLess(scale,10,'percentile scale keeps the meaningful trace readable')
    def test_monotonic_curve_has_no_breaks(self):
        s=m.normalized_state({'x1':0.42,'y1':0.0,'x2':0.58,'y2':1.0})
        speeds=[m.value_and_speed(s,(i+0.5)/256)[1] for i in range(256)]
        self.assertNotIn(None,speeds)


class Motion4SpeedSemantics(unittest.TestCase):
    def test_reference_preset_shapes_and_exact_derivative(self):
        for name in ('linear','fast','slow','smooth'):
            value=m.preset_state(name)
            speed=m.fit_velocity_points(value);speed['edit_space']='speed'
            samples=[i/128 for i in range(129)]
            for u in samples:
                expected=m.value_and_speed(value,u)[1]
                actual=m.value_and_speed(speed,u)[1]
                self.assertAlmostEqual(expected,actual,delta=2e-6,msg=f'{name} at {u}')
            start=m.value_and_speed(speed,0)[1];mid=m.value_and_speed(speed,.5)[1];end=m.value_and_speed(speed,1)[1]
            if name=='linear':self.assertAlmostEqual(start,mid,delta=1e-8);self.assertAlmostEqual(mid,end,delta=1e-8)
            elif name=='fast':self.assertAlmostEqual(start,2,delta=1e-8);self.assertAlmostEqual(end,0,delta=1e-8);self.assertGreater(start,mid)
            elif name=='slow':self.assertAlmostEqual(start,0,delta=1e-8);self.assertAlmostEqual(end,7,delta=1e-8);self.assertGreater(end,mid)
            else:
                self.assertAlmostEqual(start,0,delta=1e-8);self.assertAlmostEqual(end,0,delta=1e-8)
                self.assertGreater(mid,1.7)
                self.assertAlmostEqual(m.value_and_speed(speed,.25)[1],m.value_and_speed(speed,.75)[1],delta=1e-8)

    def test_value_speed_roundtrip_preserves_every_bezier_preset(self):
        for name,spec in m.PRESETS.items():
            if spec['mode']!='bezier':continue
            value=m.preset_state(name);before=m.sample_curve(value,129)[0]
            speed=m.fit_velocity_points(value);speed['edit_space']='speed'
            restored=m.value_points_from_velocity(speed);restored['edit_space']='value'
            after=m.sample_curve(restored,129)[0]
            self.assertLess(max(abs(a-b) for a,b in zip(before,after)),2e-6,name)

    def test_speed_controls_update_shared_value_cubic(self):
        s=m.fit_velocity_points(m.preset_state('smooth'));s['edit_space']='speed'
        m.set_speed_parameters(s,0,[.5,.8,.5,.4])
        self.assertAlmostEqual(m.value_and_speed(s,0)[1],.8,delta=1e-8)
        self.assertAlmostEqual(m.value_and_speed(s,1)[1],.4,delta=1e-8)
        self.assertAlmostEqual(s['keyframes'][0]['right'][0],.5,delta=1e-8)
        self.assertAlmostEqual(s['keyframes'][0]['right'][1],.4,delta=1e-8)
        self.assertAlmostEqual(s['keyframes'][1]['left'][1],.8,delta=1e-8)
        values,speeds=m.sample_curve(s)
        self.assertEqual((values[0],values[-1]),(0,1))
        self.assertTrue(all(b>=a-1e-9 for a,b in zip(values,values[1:])))
        self.assertTrue(all(math.isfinite(v) for v in values+speeds))




class SpeedDisplayRegression(unittest.TestCase):
    def test_singular_peak_cannot_escape_plot(self):
        data={'speed_constant':False,'speed_min':0.,'speed_range':3.174}
        self.assertAlmostEqual(ge.speed_screen(data,16,16,100,100,.5,434)[1],16+100*.96)
        data={'speed_constant':False,'speed_min':-3.174,'speed_range':6.348}
        self.assertAlmostEqual(ge.speed_screen(data,16,16,100,100,.5,-434)[1],16+100*.04)
        data={'speed_constant':True,'speed_min':0.,'speed_range':1.}
        self.assertEqual(ge.speed_screen(data,16,16,100,100,.5,1)[1],66)


class ModeControlRegression(unittest.TestCase):
    def test_non_bezier_hidden_sliders_are_inert(self):
        for mode in ('elastic','bounce'):
            for model in ('continuous-v3','legacy-v2'):
                s=m.normalized_state({'mode':mode,'model':model})
                self.assertIsNotNone(m.parameter_control(s,1))
                self.assertIsNotNone(m.parameter_control(s,2))
                for group in (3,4):
                    self.assertIsNone(m.parameter_control(s,group))
                    self.assertEqual(m.slider_display_ratio(s,group),0)


class PresetIdentity(unittest.TestCase):
    def test_same_curve_separates_edit_spaces(self):
        a=m.normalized_state({'edit_space':'value'})
        b=m.normalized_state({'edit_space':'speed'})
        self.assertFalse(m.same_curve(a,b))
        self.assertTrue(m.same_curve(a,a))
        c=m.normalized_state({'edit_space':'speed','vy1':2.0})
        self.assertFalse(m.same_curve(b,c))
    def test_identical_content_presets_are_distinct_actions(self):
        # Two saved presets with identical curves keep separate identities;
        # selection follows the action id, handled host-side via selected_preset.
        first={'name':'A','curve':m.normalized_state()}
        second={'name':'B','curve':m.normalized_state()}
        self.assertTrue(m.same_curve(first['curve'],second['curve']))
        self.assertNotEqual(first['name'],second['name'])

if __name__=='__main__':unittest.main()
