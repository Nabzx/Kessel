from dataclasses import replace
from kessel_training.export_reference_viewer import export_episode
from kessel_training.scenarios import family


def test_reference_export_keeps_post_action_transfers_and_replays_every_state():
    scene,_=family('standard');episode=export_episode(replace(scene,max_steps=600))
    assert episode['policy'] is None and episode['outcome']=='success'
    assert episode['action_replay']['max_state_absolute_error']<1e-10
    assert episode['action_replay']['max_mass_residual_kg']<1e-7
    for event in episode['timeline']:
        assert abs(episode['records'][event['index']]['t_s']-event['t_s'])<1e-9
    delivery=next(e for e in episode['timeline'] if e['kind']=='Deposition')
    assert episode['records'][delivery['index']]['state'][8]>0
    assert episode['records'][delivery['index']-1]['state'][8]==0
