import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
from kessel_lab.observations import adapt, CONTRACT
from kessel_lab.recorder import Recorder, scan


def packet():
    return {'clock':'local-monotonic','calibration':'rig-v1','frame':CONTRACT['frame'],'sequence':0,
            'channels':{name:{'capture_s':1.,'delivery_s':1.01,'sensor_id':name,'values':values}
            for name,values in {'proprio':[0.]*15,'local_height_m':np.ones((5,5)).tolist(),
                                'range_valid':np.ones((5,5)).tolist()}.items()}}

class ObservationTests(unittest.TestCase):
    def adapt(self,p,**kwargs):return adapt(p,clock='local-monotonic',calibration='rig-v1',use_time_s=1.1,**kwargs)
    def test_alignment_and_missing_range(self):
        p=packet();p['channels']['local_height_m']['capture_s']=.5
        obs,meta=self.adapt(p)
        self.assertEqual(obs['range_valid'].sum(),0)
        self.assertEqual(obs['local_height_m'].sum(),0)
        self.assertAlmostEqual(obs['proprio'][0,11],.6)
        self.assertEqual(p['channels']['local_height_m']['values'][0][0],1.)
    def test_mixed_rate_channels(self):
        p=packet();p['channels']['proprio']['capture_s']=1.05;p['channels']['proprio']['delivery_s']=1.06
        obs,meta=self.adapt(p)
        self.assertAlmostEqual(meta['channel_age_s']['proprio'],.05)
        self.assertEqual(obs['range_valid'].sum(),25)
    def test_invalid_clock_calibration_stale_proprio_and_future(self):
        for mutation in (lambda p:p.update(clock='other'),lambda p:p.update(calibration='rig-v2'),
                         lambda p:p['channels']['proprio'].update(capture_s=0),
                         lambda p:p['channels']['range_valid'].update(delivery_s=2)):
            p=packet();mutation(p)
            with self.assertRaises(ValueError):self.adapt(p)

class LogTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'run.jsonl';self.identity={'run':'one','checkpoint':'abc','calibration':'rig-v1'}
    def tearDown(self):self.temp.cleanup()
    def test_restart_sequence_gaps_and_wrong_checkpoint(self):
        log=Recorder(self.path,self.identity);log.append('observation',0,{'value':1})
        log=Recorder(self.path,self.identity);log.append('observation',3,{'value':2})
        self.assertEqual(scan(self.path)[-1]['gap_before'],2)
        with self.assertRaises(ValueError):log.append('observation',3,{})
        with self.assertRaises(ValueError):Recorder(self.path,{'checkpoint':'other'})
        with self.assertRaises(ValueError):log.append('applied_command',0,{})
    def test_incomplete_tail_requires_explicit_recovery(self):
        log=Recorder(self.path,self.identity);log.append('proposal',0,{'action':[0,0,0,0]})
        before=self.path.read_bytes();self.path.write_bytes(before+b'{"interrupted":')
        with self.assertRaises(ValueError):Recorder(self.path,self.identity)
        resumed=Recorder(self.path,self.identity,recover=True)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.path.with_suffix('.jsonl.recovered-tail').read_bytes(),b'{"interrupted":')
        resumed.append('proposal',1,{})
    def test_quota_preserves_all_committed_bytes(self):
        log=Recorder(self.path,self.identity,quota_bytes=600);before=self.path.read_bytes()
        with self.assertRaises(BufferError):log.append('observation',0,{'large':'x'*1000})
        self.assertEqual(self.path.read_bytes(),before)
    def test_stale_second_writer_is_rejected(self):
        first=Recorder(self.path,self.identity);second=Recorder(self.path,self.identity)
        first.append('observation',0,{})
        with self.assertRaises(ValueError):second.append('proposal',0,{})
        self.assertEqual(len(scan(self.path)),2)

    def test_corruption_is_not_recovered_as_tail(self):
        Recorder(self.path,self.identity);data=self.path.read_bytes().replace(b'abc',b'xyz');self.path.write_bytes(data)
        with self.assertRaises(ValueError):Recorder(self.path,self.identity,recover=True)

if __name__=='__main__':unittest.main()
