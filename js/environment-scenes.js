// One decoded photograph per transition; late requests cannot overwrite selection.
export function createEnvironmentScenes(config) {
  const root=document.getElementById("environment-backdrop"),layers=[...root.querySelectorAll("img")],cache=new Map();
  let token=0,active=0,requested=null,displayed=null,state="idle";
  function decode(url){
    if(!cache.has(url)){
      const promise=new Promise((resolve,reject)=>{const image=new Image();image.decoding="async";image.onload=()=>image.decode().then(()=>resolve(image)).catch(()=>resolve(image));image.onerror=()=>reject(new Error("Environment image unavailable"));image.src=url;});
      cache.set(url,promise);promise.catch(()=>cache.delete(url));
    }
    return cache.get(url);
  }
  async function select(item){
    const request=++token;requested=item.id;state="loading";root.dataset.loading="true";
    document.getElementById("selector").setAttribute("aria-busy","true");
    let image,fallback=false;
    try{image=await decode(item.background_image.path);}catch{try{image=await decode(item.preview.path);fallback=true;}catch{image=null;}}
    if(request!==token)return false;
    if(image){
      if(image!==layers[active]){
        const next=1-active;image.alt="";image.style.objectPosition="50% 50%";
        layers[next].replaceWith(image);layers[next]=image;image.classList.add("current");layers[active].classList.remove("current");active=next;
      }
      displayed=item.id;state=fallback?"fallback":"ready";
    }else{layers.forEach(layer=>layer.classList.remove("current"));displayed=null;state="unavailable";}
    root.dataset.environment=item.id;root.dataset.loading="false";root.dataset.state=state;document.getElementById("selector").setAttribute("aria-busy","false");
    document.getElementById("environment-credit").textContent=image?`${item.preview.caption}${fallback?" · preview resolution":""}`:"Reference image unavailable";
    return true;
  }
  function warm(index){
    for(const offset of [-1,0,1]){
      const item=config.environments[(index+offset+config.environments.length)%config.environments.length];decode(item.background_image.path).catch(()=>{});
    }
  }
  return {select,warm,visible(value){root.classList.toggle("visible",value);root.setAttribute("aria-hidden",String(!value));},diagnostics(){return{requested,displayed,state,pending:state==="loading"};}};
}
