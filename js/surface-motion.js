// The film and live fallback consume the same finite metre-scale haul trace.
export function sampleSurfaceHaul(data,time){
 const t=Math.max(0,Math.min(data.duration_s,time)),rows=data.rows;
 let lo=0,hi=rows.length-1;while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(rows[mid][0]<=t)lo=mid;else hi=mid-1;}
 const a=rows[lo],b=rows[Math.min(lo+1,rows.length-1)],f=b[0]>a[0]?(t-a[0])/(b[0]-a[0]):0;
 const row=a.map((v,i)=>v+(b[i]-v)*f);
 return {time:t,position:row.slice(1,4),heading:row[4],speed:row[5],steering:row.slice(7,9),wheelAngles:row.slice(9,13),distance:row[13],complete:t>=data.duration_s};
}
