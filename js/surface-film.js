// Local, authored Blender film. Decoding failure leaves the prepared 3D fallback.
export function createSurfaceFilm(onFallback=()=>{}){
 const host=document.getElementById('surface-film'),video=document.getElementById('surface-video'),button=document.getElementById('surface-motion');
 const motion=matchMedia('(prefers-reduced-motion: reduce)');let ready=false,failed=false,active=false,userPaused=false,loading=null;
 video.muted=true;
 function label(){button.textContent=video.paused?'Play scene':'Pause scene';}
 async function play(){if(!active||motion.matches||userPaused||failed)return;try{await video.play();}catch{userPaused=true;}label();}
 function fallback(){failed=true;host.hidden=true;document.body.classList.add('surface-fallback');onFallback();label();}
 video.addEventListener('error',fallback);video.addEventListener('play',label);video.addEventListener('pause',label);
 button.addEventListener('click',()=>{if(video.paused){userPaused=false;video.play().catch(()=>{userPaused=true;});}else{userPaused=true;video.pause();}label();});
 motion.addEventListener('change',()=>{if(motion.matches)video.pause();else play();label();});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();else play();});
 return {prepare(){if(loading)return loading;loading=new Promise(resolve=>{
   const finish=()=>{ready=true;resolve();};video.addEventListener('loadeddata',finish,{once:true});video.addEventListener('error',()=>resolve(),{once:true});video.src='assets/film/surface.mp4';video.preload='auto';video.load();
   // A still is a valid first frame while a slow decoder prepares motion.
   setTimeout(resolve,2500);
  });return loading;},show(){active=true;host.hidden=failed;document.body.classList.toggle('surface-fallback',failed);play();label();},hide(){active=false;host.hidden=true;video.pause();},diagnostics:()=>({ready,failed,active,paused:video.paused,time:video.currentTime,duration:Number.isFinite(video.duration)?video.duration:null,reducedMotion:motion.matches})};
}
