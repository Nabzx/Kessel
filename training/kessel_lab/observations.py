"""Proposed numeric sensor contract. No raw perception or machine I/O."""
import numpy as np
from kessel_training.environment import PROPRIO_NAMES

SHAPES={'proprio':(15,), 'local_height_m':(5,5), 'range_valid':(5,5)}
UNITS={'proprio':'proprio-fields-v1','local_height_m':'m','range_valid':'boolean'}
CONTRACT={'version':'loader-observation-1','frame':'loader-local-metres-radians',
          'proprio_fields':list(PROPRIO_NAMES),'grid_spacing_m':.75,
          'grid_along_m':[-.75,0,.75,1.5,2.25],'grid_across_m':[-1.5,-.75,0,.75,1.5],
          'calibration_required':True,'applied_commands':False}


def adapt(packet, *, clock, calibration, use_time_s, max_age_s=.2):
    if packet.get('version')!=CONTRACT['version']:raise ValueError('observation schema version differs')
    if packet['clock']!=clock or packet['calibration']!=calibration or packet['frame']!=CONTRACT['frame']:
        raise ValueError('clock, frame or calibration identity differs')
    if not isinstance(packet['sequence'],int) or isinstance(packet['sequence'],bool) or packet['sequence']<0:
        raise ValueError('invalid sequence')
    if not np.isfinite(use_time_s) or not np.isfinite(max_age_s) or max_age_s<0:
        raise ValueError('invalid use time or age limit')
    result={};ages={}
    for name,shape in SHAPES.items():
        channel=packet['channels'][name]
        if channel.get('units')!=UNITS[name]:raise ValueError('channel units differ: '+name)
        capture=float(channel['capture_s']);delivery=float(channel['delivery_s'])
        if not np.isfinite([capture,delivery]).all() or capture>delivery or delivery>use_time_s:
            raise ValueError('timestamps are unordered or outside the use clock')
        values=np.asarray(channel['values'],dtype=float)
        if values.shape!=shape or not np.isfinite(values).all(): raise ValueError('invalid '+name)
        if not channel['sensor_id']: raise ValueError('sensor identity required')
        result[name]=values.copy()[None];ages[name]=use_time_s-capture
    if not np.isin(result['range_valid'],[0,1]).all() or (result['local_height_m']<0).any():
        raise ValueError('invalid range height or validity')
    range_age=max(ages['local_height_m'],ages['range_valid'])
    if range_age>max_age_s: result['range_valid'].fill(0)
    result['local_height_m']*=result['range_valid']
    result['proprio'][0,11]=range_age
    result['proprio'][0,12]=float(range_age<=max_age_s and result['range_valid'].any())
    # Stale proprio cannot be repaired by masking geometry. Caller receives an error.
    if ages['proprio']>max_age_s: raise ValueError('proprioception is stale; no policy proposal produced')
    return result, {'channel_age_s':ages,'sequence':packet['sequence'],'calibration':calibration,
                    'claim':'numeric alignment only; missing-data handling is not a stopping guarantee'}
