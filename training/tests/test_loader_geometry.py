import numpy as np

from kessel_training.contracts import LoaderConfig
from kessel_training.kinematics import advance,components,footprints
from kessel_training.pile import PileGrid


def test_reverse_preserves_heading_lamps_and_signed_wheel_motion():
    pose=np.zeros((1,3));joints=np.zeros((1,3));speed=np.array([-1.0]);wheels=np.zeros((1,4))
    geometry=advance(pose,speed,joints,wheels,np.zeros((1,4)),np.zeros(1),LoaderConfig(),0.1)
    assert pose[0,0]<0 and pose[0,2]==0
    assert (wheels<0).all()
    np.testing.assert_allclose(geometry["front_forward"],[[1,0]])


def test_joint_limits_and_vehicle_envelope():
    c=LoaderConfig();pose=np.zeros((1,3));joints=np.zeros((1,3));speed=np.zeros(1);wheels=np.zeros((1,4))
    envelope=footprints(pose,joints)
    assert abs(np.ptp(envelope[...,0])-c.length_m)<1e-12
    assert abs(np.ptp(envelope[...,1])-c.width_m)<1e-12
    for _ in range(100): advance(pose,speed,joints,wheels,np.ones((1,4)),np.zeros(1),c,0.1)
    np.testing.assert_allclose(joints,[[c.articulation_rad,c.boom_max_rad,c.bucket_max_rad]])


def test_bucket_transfer_conserves_mass_and_obeys_capacity_and_contact():
    pile=PileGrid(2)
    for i in range(2):pile.reset_one(i,np.random.default_rng(42))
    original=pile.mass().copy()
    mouth=np.array([[9,0],[100,100]],dtype=float)
    total=np.zeros(2)
    for _ in range(50):
        mass,_=pile.extract(mouth,np.array([[1,0],[1,0]]),np.zeros(2),500-total,np.ones(2))
        total+=mass
    np.testing.assert_allclose(pile.mass()+total,original,atol=1e-8)
    np.testing.assert_allclose(total,[500,0])
    assert (pile.height>=0).all()


def test_seeded_pile_mass_matches_height_integral():
    p=PileGrid(1);p.reset_one(0,np.random.default_rng(9))
    first=p.height.copy();mass=p.mass().copy()
    p.reset_one(0,np.random.default_rng(9))
    np.testing.assert_array_equal(p.height,first)
    np.testing.assert_array_equal(p.mass(),mass)
