"""One finite surface work order, metre-scale rear axle and smooth curvature."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LENGTH=27.;VMAX=2.5;ACCEL=.8;WAIT=1.;DURATION=16.;STEP=.005
path=[];x=0.;z=-76.
def heading(s):
 q=max(0,min(1,(s-6)/18));return math.pi/2*(q*q*(3-2*q))
def curvature(s):
 q=(s-6)/18;return math.pi/2*6*q*(1-q)/18 if 0<q<1 else 0
for i in range(round(LENGTH/STEP)+1):
 s=i*STEP
 if i:x+=math.sin(heading(s-STEP/2))*STEP;z+=math.cos(heading(s-STEP/2))*STEP
 path.append((x,z))
rows=[];spins=[0.,0.,0.,0.];last_t=0.;last_s=0.
for frame in range(round(DURATION*24)+1):
 t=frame/24;u=max(0,t-WAIT);ta=VMAX/ACCEL;cruise=(LENGTH-VMAX*ta)/VMAX;end=2*ta+cruise
 if u<=ta:s=.5*ACCEL*u*u;v=ACCEL*u
 elif u<=ta+cruise:s=.5*VMAX*ta+VMAX*(u-ta);v=VMAX
 elif u<end:r=end-u;s=LENGTH-.5*ACCEL*r*r;v=ACCEL*r
 else:s=LENGTH;v=0
 s=min(LENGTH,s);h=heading(s);k=curvature(s);i=min(len(path)-2,int(s/STEP));q=s/STEP-i;x=path[i][0]*(1-q)+path[i+1][0]*q;z=path[i][1]*(1-q)+path[i+1][1]*q
 steer=[math.atan2(5.1*k,1-side*k) for side in [-1,1]]
 ds=s-last_s;mid=curvature((s+last_s)/2)
 for j,(front,side) in enumerate([(False,-1),(False,1),(True,-1),(True,1)]):
  spins[j]+=ds*math.hypot(1-side*mid,5.1*mid if front else 0)/.51
 rows.append([round(a,8) for a in [t,x+2.55*math.sin(h),-.075,z+2.55*math.cos(h),h,v,k,*steer,*spins,s]])
 last_s=s
D={'schema_version':1,'source':'Authored finite yard haul; not measured machine telemetry','duration_s':DURATION,'fps':24,'loop':False,'ground_y_m':-.035,'wheel_radius_m':.51,'axle_height_m':.55,'wheelbase_m':5.1,'half_track_m':1,'rear_axle_offset_m':-2.55,'max_speed_m_s':VMAX,'acceleration_m_s2':ACCEL,'columns':['t','x','y','z','heading','speed','curvature','steer_left','steer_right','spin_rear_left','spin_rear_right','spin_front_left','spin_front_right','distance'],'rows':rows}
(ROOT/'data/surface-haul.json').write_text(json.dumps(D,separators=(',',':'))+'\n');print('Surface haul:',len(rows),'samples,',LENGTH,'m, finite stop after',round(WAIT+end,2),'s')
