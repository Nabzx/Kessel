// Interpolate retained authored samples. A renderer cannot change task outcomes.
export function sampleTrial(trial,time) {
  const rows=trial.rows,t=Math.max(0,Math.min(trial.duration_s,time));
  let lo=0,hi=rows.length-1;
  while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(rows[mid][0]<=t)lo=mid;else hi=mid-1;}
  const a=rows[lo],b=rows[Math.min(lo+1,rows.length-1)],f=b[0]>a[0]?(t-a[0])/(b[0]-a[0]):0;
  const v=a.map((n,i)=>i===12?n:n+(b[i]-n)*f);
  return {time:t,pose:[v[1],v[2],v[3],v[4],v[5],v[6],v[7]],sourceKg:v[8],payloadKg:v[9],deliveredKg:v[10],travel:v[11],phase:v[12],inflightKg:v[13],wheelAngles:v.slice(14,18)};
}
export function trainingClock(data,elapsed) {
 let cursor=0;
 for(let i=0;i<data.trials.length;i++){
  const trial=data.trials[i],duration=trial.duration_s/data.replay_speed;
  if(elapsed<=cursor+duration||i===data.trials.length-1){const raw=Math.max(0,(elapsed-cursor)*data.replay_speed),time=raw>=trial.duration_s-1e-7?trial.duration_s:raw;return {...sampleTrial(trial,time),index:i,trial,reset:0,complete:i===data.trials.length-1&&time>=trial.duration_s};}
  cursor+=duration;
  if(elapsed<cursor+data.reset_seconds){
   const reset=(elapsed-cursor)/data.reset_seconds,next=reset>=.5,index=next?i+1:i,selected=data.trials[index];
   // Switch independent episodes at the fully covered midpoint. Both poses
   // remain stationary while the source-labelled reset fades out and in.
   return {...sampleTrial(selected,next?0:trial.duration_s),index,trial:selected,reset,complete:false};
  }
  cursor+=data.reset_seconds;
 }
}
export function trainingDuration(data){return data.trials.reduce((s,t)=>s+t.duration_s/data.replay_speed,0)+(data.trials.length-1)*data.reset_seconds;}
