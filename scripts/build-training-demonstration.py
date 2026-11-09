"""Build authored kinematic work orders, not a learned-policy result.

Motion has bounded acceleration, rear-axle tangency, articulated steering,
stationary scoop/tip phases and explicit resets between independent episodes.
Payload is conserved within each episode. Positions use simulator XY metres.
"""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DT=.05
columns=['t','x','y','heading','speed','articulation','boom','bucket','source_kg','payload_kg','delivered_kg','travel_m','phase','inflight_kg']
phases=['Approach the face','Bucket too high','Engage the ore','Curl and lift','Reverse clear','Obstacle detected','Follow clear route','Approach the receiver','Raise the bucket','Tip into receiver','Task complete','Pickup incomplete']
trials=[]
for idx,(name,y,r,payload) in enumerate([('Early policy',-6,6,0),('Partial pickup',-3,6,600),('Work order 01',-6,6,2000),('Work order 02',-3,6,2000),('Work order 03',0,8,2000)]):
 rows=[];t=0.;travel=0.;inflight=0.;pose=[0.,y,0.,0.,0.,-.11 if idx else .65,0.,3000.,0.,0.]
 # pose: x,y,heading,speed,articulation,boom,bucket,source,payload,delivered
 def row(phase):rows.append([round(t,6)]+[round(v,6) for v in pose]+[round(travel,6),phase,round(inflight,6)])
 def hold(seconds,phase,target=None):
  global t,pose
  start=pose.copy();n=max(1,round(seconds/DT))
  for k in range(n+1):
   if k:t+=DT
   q=k/n;q=q*q*(3-2*q)
   if target:
    for col,val in target.items():pose[col]=start[col]+(val-start[col])*q
   pose[3]=0;row(phase)
 def drive(length,phase,position,reverse=False):
  global t,pose,travel
  accel=.55;vmax=1.6;ta=min(vmax/accel,math.sqrt(length/accel));vc=accel*ta;cruise=max(0,(length-accel*ta*ta)/vc);end=2*ta+cruise;n=math.ceil(end/DT);previous=0
  for k in range(n+1):
   q=min(end,k*end/n)
   if q<ta:d=.5*accel*q*q;v=accel*q
   elif q<ta+cruise:d=.5*accel*ta*ta+vc*(q-ta);v=vc
   else:
    rem=end-q;d=length-.5*accel*rem*rem;v=accel*rem
   x,yy,heading,steer=position(d/length)
   if k:t+=end/n
   pose[:5]=[x,yy,heading,-v if reverse else v,steer];travel+=(-1 if reverse else 1)*(d-previous);previous=d;row(phase)
 hold(.7,0)
 drive(7.8,0,lambda q:(7.8*q,y,0,0))
 if idx==0:
  hold(2,1);drive(7.8,4,lambda q:(7.8*(1-q),y,0,0),True);hold(1,11)
 else:
  hold(3,2,{7:3000-payload,8:payload})
  hold(2.5,3,{5:.1,6:.45})
  drive(7.8,4,lambda q:(7.8*(1-q),y,0,0),True)
  if idx==1:hold(1,11)
  else:
   if idx==4:hold(2,5)
   # Enter and leave a constant-radius turn at rest, steering stationary first.
   steering=math.atan2(1.8,r)+math.asin(1.6/math.hypot(r,1.8))
   hold(.7,6,{4:steering})
   drive(math.pi*r,6,lambda q:(r*math.sin(math.pi*q),y+r*(1-math.cos(math.pi*q)),math.pi*q,steering))
   hold(.7,6,{4:0})
   drive(3.9,7,lambda q:(-3.9*q,y+2*r,math.pi,0))
   hold(3,8,{5:.45})
   hold(1.5,9,{6:-.8})
   # A 0.42 s bounded transfer delay retains material in flight.
   for k in range(80):
    t+=DT;leaving=min(1,(k+1)*DT/3.5);arrived=max(0,min(1,((k+1)*DT-.42)/3.5));pose[8]=payload*(1-leaving);pose[9]=payload*arrived;inflight=payload*(leaving-arrived);row(9)
   inflight=0;pose[8]=0;pose[9]=payload
   hold(1,10)
 destination_y=y+2*r
 trials.append({'id':f'episode-{idx+1:02}', 'name':name,'outcome':'success' if idx>1 else 'missed pickup' if idx==0 else 'partial pickup','load_point':[13.8,y], 'receiver':[-9.5,destination_y], 'obstacle':{'centre':[5,8],'half_extents':[.65,.8]} if idx==4 else None,'represented_episodes': [500,48000,320000,1200000,2400000][idx], 'reward':[-.41,.12,.68,.83,.96][idx], 'initial_ore_kg':3000,'goal_kg':2000,'rows':rows,'duration_s':round(t,6)})
# Integrate each tyre's actual path independently, including reverse travel.
for trial in trials:
 angles=[0.,0.,0.,0.];previous=None;previous_speed=0
 for row in trial['rows']:
  _,x,y,h,v,a,*_=row;j=(x+1.8*math.cos(h),y+1.8*math.sin(h));f=h+a
  centres=[(x-side*.65*math.sin(h),y+side*.65*math.cos(h)) for side in [1,-1]]+[(j[0]+1.6*math.cos(f)-side*.65*math.sin(f),j[1]+1.6*math.sin(f)+side*.65*math.cos(f)) for side in [1,-1]]
  if previous:
   for k,(point,last) in enumerate(zip(centres,previous)):
    angles[k]+=math.hypot(point[0]-last[0],point[1]-last[1])/.55*(1 if v+previous_speed>=0 else -1)
  row.extend(round(a,6) for a in angles);previous=centres;previous_speed=v
columns.extend(['rear_left_rad','rear_right_rad','front_left_rad','front_right_rad'])
result={'schema_version':1,'source':'authored kinematic training demonstration','learned_policy_result':False,'replay_speed':6,'reset_seconds':.85,'units':'metres, seconds, radians, kilograms','columns':columns,'phases':phases,'floor_bounds':[-13,-10,18,21],'trials':trials,'notes':'Independent evaluation episodes. Episode progression and rewards are illustrative. No live training, measured policy success or granular dynamics is claimed. New episodes reset the scenario explicitly.'}
(ROOT/'data/training-demonstration.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
print(f'{sum(len(t["rows"]) for t in trials)} samples; {sum(t["duration_s"] for t in trials)/6:.1f}s replay plus labelled resets')
