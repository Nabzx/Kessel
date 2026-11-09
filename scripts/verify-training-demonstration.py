"""Independent envelope, contact, motion and conservation audit of the demo."""
import json, math
from pathlib import Path
D=json.loads((Path(__file__).resolve().parents[1]/'data/training-demonstration.json').read_text())
assert D['learned_policy_result'] is False
minimum=100

def corners(x,y,theta,front=False):
 # Bodies include wheel width and a conservative rear overhang.
 bounds=(-1.85,1.85) if not front else (-.3,2.15)
 return [(x+a*math.cos(theta)-b*math.sin(theta),y+a*math.sin(theta)+b*math.cos(theta)) for a,b in [(bounds[0],-.86),(bounds[0],.86),(bounds[1],.86),(bounds[1],-.86)]]
def separate(poly,rect):
 # SAT tests convex machine footprints against obstacle / receiver boxes.
 for shape in (poly,rect):
  for a,b in zip(shape,shape[1:]+shape[:1]):
   axis=(b[1]-a[1],a[0]-b[0]);p=[x*axis[0]+y*axis[1] for x,y in poly];r=[x*axis[0]+y*axis[1] for x,y in rect]
   if max(p)<min(r) or max(r)<min(p):return True
 return False
def rectangle(cx,cy,hx,hy):return [(cx-hx,cy-hy),(cx+hx,cy-hy),(cx+hx,cy+hy),(cx-hx,cy+hy)]
for trial in D['trials']:
 previous=None
 for row in trial['rows']:
  t,x,y,theta,v,steer,boom,bucket,source,load,delivered,travel,phase,inflight=row[:14]
  assert abs(source+load+delivered+inflight-3000)<.01,(trial['id'],t,'mass')
  assert min(source,load,delivered,inflight)>-.01
  assert abs(v)<=1.6001
  if phase==6 and abs(v)>.01:
   r=8 if trial['obstacle'] else 6
   assert abs(r*math.sin(steer)-(1.8*math.cos(steer)+1.6))<1e-5,'front axle rolling constraint'
  # Dense retained samples cover all travel; no renderer interpolation shortcuts.
  j=(x+1.8*math.cos(theta),y+1.8*math.sin(theta));forward=theta+steer
  body=[corners(x,y,theta),corners(*j,forward,True)]
  px,py=trial['load_point'];receiver=rectangle(*trial['receiver'],1.2,1.1)
  pile=rectangle(px,py,1.4,1.1)
  obstacles=[receiver,pile]
  if trial['obstacle']:obstacles.append(rectangle(*trial['obstacle']['centre'],*trial['obstacle']['half_extents']))
  if trial['obstacle']:
   base=1.6+1.2*math.cos(boom)-.6*math.cos(bucket)
   bucket_poly=[(j[0]+(base+d*math.cos(bucket))*math.cos(forward)-side*.75*math.sin(forward),j[1]+(base+d*math.cos(bucket))*math.sin(forward)+side*.75*math.cos(forward)) for d,side in [(.18,-1),(.18,1),(1.08,1),(1.08,-1)]]
   assert separate(bucket_poly,obstacles[-1]),(trial['id'],t,'bucket obstacle contact')
  for poly in body:
   for ob in obstacles:assert separate(poly,ob),(trial['id'],t,'body collision')
  for axle in [(x,y),(j[0]+1.6*math.cos(forward),j[1]+1.6*math.sin(forward))]:
   # All tyres stay clear of the pile and receiver. Conservative radius .55.
   for ob in obstacles:
    ox=[a for a,b in ob];oy=[b for a,b in ob];distance=math.hypot(max(min(ox)-axle[0],0,axle[0]-max(ox)),max(min(oy)-axle[1],0,axle[1]-max(oy)))-.55
    assert distance>0,(trial['id'],t,'tyre collision',distance)
    minimum=min(minimum,distance)
  if previous:
   dt=t-previous[0]
   if dt>1e-6:
    distance=math.hypot(x-previous[1],y-previous[2]);assert distance/dt<1.601
    assert abs(v-previous[4])/dt<.552
    if distance>.0001:
     dot=((x-previous[1])*math.cos((theta+previous[3])/2)+(y-previous[2])*math.sin((theta+previous[3])/2))/distance
     assert dot*(1 if v+previous[4]>=0 else -1)>.999,'travel direction'
   if source<previous[8]-.001:
    mouth=(j[0]+(1.6+1.2*math.cos(boom))*math.cos(forward),j[1]+(1.6+1.2*math.cos(boom))*math.sin(forward))
    height=.35+2*math.sin(boom)
    assert px-1.4-.1<=mouth[0]<=px+1.4 and abs(mouth[1]-py)<1.1 and -.02<height<.5,'scoop contact'
   if delivered>previous[10]+.001:
    reach=1.6+1.2*math.cos(boom)-.6*math.cos(bucket)+1.05*math.cos(bucket)
    lip=(j[0]+reach*math.cos(forward),j[1]+reach*math.sin(forward));height=.35+2*math.sin(boom)-.6*math.sin(bucket)+1.05*math.sin(bucket)
    assert trial['receiver'][0]-1.2<lip[0]<trial['receiver'][0]+1.2 and abs(lip[1]-trial['receiver'][1])<1.1 and height>.65,'tip contact'
  previous=row
 if trial['outcome']=='success':assert abs(trial['rows'][-1][10]-2000)<.01
assert sum(t['outcome']=='success' for t in D['trials'])==3
assert sum(t['rows'][-1][10] for t in D['trials'])==6000
print(f'PASS: 3 jobs, 6000 kg, conserved mass, contact, tangency, acceleration, clearance >= {minimum:.2f} m')
