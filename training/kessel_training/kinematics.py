"""Articulated planar geometry in the ADR-0033 physical frame."""

import numpy as np

REAR_TO_JOINT = 1.8
JOINT_TO_FRONT = 1.6
WHEEL_RADIUS_M = 0.55


def axes(yaw):
    forward = np.stack((np.cos(yaw), np.sin(yaw)), axis=-1)
    left = np.stack((-np.sin(yaw), np.cos(yaw)), axis=-1)
    return forward, left


def components(pose, joints):
    rear_forward, rear_left = axes(pose[:, 2])
    front_forward, front_left = axes(pose[:, 2] + joints[:, 0])
    rear = pose[:, :2]
    joint = rear + REAR_TO_JOINT * rear_forward
    front = joint + JOINT_TO_FRONT * front_forward
    mouth = joint + (JOINT_TO_FRONT + 1.2*np.cos(joints[:, 1]))[:, None] * front_forward
    height = 0.35 + 2.0*np.sin(joints[:, 1])
    wheels = np.stack((rear+0.65*rear_left, rear-0.65*rear_left,
                       front+0.65*front_left, front-0.65*front_left), axis=1)
    return {"rear":rear, "joint":joint, "front":front, "mouth":mouth,
            "bucket_height":height, "front_forward":front_forward,
            "rear_forward":rear_forward, "wheels":wheels}


def advance(pose, speed, joints, wheel_angles, actions, acceleration, config, dt):
    previous = components(pose, joints)
    old_joints = joints.copy()
    joints[:, 0] = np.clip(joints[:, 0]+actions[:, 1]*config.articulation_rate_rad_s*dt,
                           -config.articulation_rad,config.articulation_rad)
    joints[:, 1] = np.clip(joints[:, 1]+actions[:, 2]*config.boom_rate_rad_s*dt,
                           config.boom_min_rad,config.boom_max_rad)
    joints[:, 2] = np.clip(joints[:, 2]+actions[:, 3]*config.bucket_rate_rad_s*dt,
                           config.bucket_min_rad,config.bucket_max_rad)
    midpoint = (old_joints[:, 0]+joints[:, 0])/2
    articulation_rate = (joints[:, 0]-old_joints[:, 0])/dt
    old_speed = speed.copy()
    speed[:] = np.clip(speed+acceleration*dt,-config.reverse_m_s,config.forward_m_s)
    velocity = (old_speed+speed)/2
    yaw_rate = (velocity*np.sin(midpoint)-JOINT_TO_FRONT*articulation_rate) / (REAR_TO_JOINT*np.cos(midpoint)+JOINT_TO_FRONT)
    heading = pose[:, 2]+yaw_rate*dt/2
    pose[:, 0] += velocity*np.cos(heading)*dt
    pose[:, 1] += velocity*np.sin(heading)*dt
    pose[:, 2] = (pose[:, 2]+yaw_rate*dt+np.pi) % (2*np.pi)-np.pi
    current = components(pose,joints)
    forward = np.stack((current["rear_forward"],current["rear_forward"],
                        current["front_forward"],current["front_forward"]),axis=1)
    wheel_angles += np.sum((current["wheels"]-previous["wheels"])*forward,axis=-1)/WHEEL_RADIUS_M
    return current


def footprints(pose,joints):
    geometry = components(pose,joints)
    rear_f,rear_l = axes(pose[:, 2]); front_f,front_l = axes(pose[:, 2]+joints[:, 0])
    centres = (geometry["rear"]-0.05*rear_f, geometry["joint"]+1.2*front_f,geometry["mouth"])
    frames = ((rear_f,rear_l,1.85,0.75),(front_f,front_l,1.2,0.75),(front_f,front_l,0.6,0.75))
    rectangles = []
    for centre,(forward,left,half_length,half_width) in zip(centres,frames):
        rectangles.append(np.stack([centre+a*half_length*forward+b*half_width*left
                                    for a,b in ((-1,-1),(-1,1),(1,1),(1,-1))],axis=1))
    return np.stack(rectangles,axis=1)
