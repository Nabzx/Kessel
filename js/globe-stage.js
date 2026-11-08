import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

// NASA imagery keeps its original north-up UV frame. All lighting is world-space.
export function createGlobe(scene, config) {
  const home=config.visuals.home, R=2.38;
  const layerState={day:false,night:false,clouds:false,station:false,satellite:false};
  let elapsed=0, mode="welcome";
  const root=new THREE.Group();root.rotation.z=THREE.MathUtils.degToRad(23.44);root.position.set(home.earth_x ?? 0,home.earth_y ?? .9,0);scene.add(root);
  const sunDirection=new THREE.Vector3(-.56,.28,.78).normalize();
  const empty=new THREE.DataTexture(new Uint8Array([0,0,0,255]),1,1);empty.needsUpdate=true;
  const uniforms={dayMap:{value:empty},nightMap:{value:empty},cloudMap:{value:empty},sunDirection:{value:sunDirection},nightReady:{value:0},cloudReady:{value:0},uOpacity:{value:1}};
  const vertex=`varying vec2 vUv; varying vec3 vNormalWorld; varying vec3 vPositionWorld;
    void main(){vUv=uv;vec4 world=modelMatrix*vec4(position,1.);vPositionWorld=world.xyz;
      vNormalWorld=normalize(mat3(modelMatrix)*normal);gl_Position=projectionMatrix*viewMatrix*world;}`;
  const finish=`\n#include <tonemapping_fragment>\n#include <colorspace_fragment>\n`;
  const earthMaterial=new THREE.ShaderMaterial({uniforms,vertexShader:vertex,fragmentShader:`
    uniform sampler2D dayMap,nightMap,cloudMap;
    uniform vec3 sunDirection; uniform float nightReady,cloudReady,uOpacity;
    varying vec2 vUv;varying vec3 vNormalWorld,vPositionWorld;
    void main(){
      vec3 n=normalize(vNormalWorld),v=normalize(cameraPosition-vPositionWorld);
      float d=dot(n,sunDirection),day=smoothstep(-.10,.12,d);
      vec3 ground=texture2D(dayMap,vUv).rgb;
      float cloud=texture2D(cloudMap,vUv+vec2(.0018,.0008)).g*cloudReady;
      vec3 lit=ground*(.11+.94*pow(max(d,0.),.72))*(1.-cloud*.12);
      vec3 dark=ground*.008+texture2D(nightMap,vUv).rgb*nightReady*.85;
      vec3 colour=mix(dark,lit,day);
      colour+=vec3(.025,.08,.15)*pow(1.-max(0.,dot(n,v)),4.)*smoothstep(-.2,.5,d)*.22;
      gl_FragColor=vec4(colour,uOpacity);
      ${finish}
    }`});
  const earth=new THREE.Mesh(new THREE.SphereGeometry(R,112,80),earthMaterial);root.add(earth);
  const cloudUniforms={cloudMap:uniforms.cloudMap,sunDirection:uniforms.sunDirection,cloudReady:uniforms.cloudReady,uOpacity:{value:1}};
  const clouds=new THREE.Mesh(new THREE.SphereGeometry(home.cloud_radius,96,64),new THREE.ShaderMaterial({
    uniforms:cloudUniforms,vertexShader:vertex,transparent:true,depthWrite:false,fragmentShader:`
      uniform sampler2D cloudMap;uniform vec3 sunDirection;uniform float cloudReady,uOpacity;
      varying vec2 vUv;varying vec3 vNormalWorld;
      void main(){float coverage=texture2D(cloudMap,vUv).g*cloudReady;
        float d=dot(normalize(vNormalWorld),sunDirection),light=smoothstep(-.08,.18,d);
        vec3 colour=mix(vec3(.018,.033,.056),vec3(.86,.9,.95),light)*(.3+.7*max(d,0.));
        gl_FragColor=vec4(colour,coverage*.87*uOpacity);${finish}}
    `}));clouds.renderOrder=1;root.add(clouds);
  const atmosphere=new THREE.Mesh(new THREE.SphereGeometry(home.atmosphere_radius,96,64),new THREE.ShaderMaterial({
    uniforms:{sunDirection:uniforms.sunDirection,uOpacity:{value:1}},vertexShader:vertex,transparent:true,depthWrite:false,side:THREE.BackSide,blending:THREE.AdditiveBlending,
    fragmentShader:`uniform vec3 sunDirection;uniform float uOpacity;varying vec3 vNormalWorld,vPositionWorld;
      void main(){vec3 n=normalize(vNormalWorld),v=normalize(cameraPosition-vPositionWorld);
        float d=dot(n,sunDirection),rim=pow(1.-abs(dot(n,v)),4.5);
        float daylight=smoothstep(-.28,.48,d);vec3 colour=mix(vec3(.015,.04,.09),vec3(.1,.35,.64),daylight);
        gl_FragColor=vec4(colour,rim*mix(.045,.37,daylight)*uOpacity);${finish}}`
  }));atmosphere.renderOrder=2;root.add(atmosphere);
  const ambient=new THREE.HemisphereLight(0xb4c9e2,0x111720,.65),sun=new THREE.DirectionalLight(home.sun_colour,3.4);
  sun.position.copy(sunDirection).multiplyScalar(12);scene.add(ambient,sun);

  let seed=config.space.star_seed;
  const random=()=>{seed=seed*16807%2147483647;return(seed-1)/2147483646;};
  const count=home.star_count ?? 3800,positions=new Float32Array(count*3),colours=new Float32Array(count*3),sizes=new Float32Array(count);
  for(let i=0;i<count;i++){
    const radius=35+random()*70,theta=random()*Math.PI*2,y=random()*2-1,ring=Math.sqrt(1-y*y),m=random();
    positions.set([Math.cos(theta)*ring*radius,y*radius,Math.sin(theta)*ring*radius],i*3);
    new THREE.Color(m>.97?0xffdfb8:0xc6d8eb).multiplyScalar(.3+.7*m*m*m).toArray(colours,i*3);sizes[i]=m>.985?1.9:m>.88?1.15:.65;
  }
  const geometry=new THREE.BufferGeometry();geometry.setAttribute("position",new THREE.BufferAttribute(positions,3));geometry.setAttribute("color",new THREE.BufferAttribute(colours,3));geometry.setAttribute("starScale",new THREE.BufferAttribute(sizes,1));
  const starMaterial=new THREE.PointsMaterial({size:1.05,sizeAttenuation:false,vertexColors:true,transparent:true,opacity:.85,depthWrite:false});
  starMaterial.onBeforeCompile=shader=>{
    shader.vertexShader="attribute float starScale;\n"+shader.vertexShader.replace("gl_PointSize = size;","gl_PointSize = size * starScale;");
    shader.fragmentShader=shader.fragmentShader.replace("#include <alphatest_fragment>","diffuseColor.a *= (1.-smoothstep(.12,.5,length(gl_PointCoord-vec2(.5))));\n#include <alphatest_fragment>");
  };
  const stars=new THREE.Points(geometry,starMaterial);scene.add(stars);

  const markers=new THREE.Group(),pins=new Map();root.add(markers);markers.visible=false;
  function normal(lat,lon){const a=THREE.MathUtils.degToRad(lat),b=THREE.MathUtils.degToRad(lon);return new THREE.Vector3(Math.cos(a)*Math.cos(b),Math.sin(a),-Math.cos(a)*Math.sin(b));}
  for(const item of config.environments.filter(e=>e.id!=="space")){
    const direction=normal(item.latitude,item.longitude),pin=new THREE.Group();pin.position.copy(direction).multiplyScalar(2.43);pin.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),direction);
    const ring=new THREE.Mesh(new THREE.RingGeometry(.037,.046,32),new THREE.MeshBasicMaterial({color:0xe6e2d9,side:THREE.DoubleSide,transparent:true,opacity:.8}));
    const dot=new THREE.Mesh(new THREE.CircleGeometry(.013,16),new THREE.MeshBasicMaterial({color:0xe6e2d9,side:THREE.DoubleSide}));dot.position.z=.005;pin.add(ring,dot);markers.add(pin);pins.set(item.id,{pin,ring,dot,direction});
  }
  const orbits=[];
  function fallbackSatellite(){
    const model=new THREE.Group(),foil=new THREE.MeshStandardMaterial({color:0xb79855,metalness:.75,roughness:.4}),panel=new THREE.MeshStandardMaterial({color:0x173450,metalness:.3,roughness:.35});
    const bus=new THREE.Mesh(new THREE.BoxGeometry(.13,.15,.17),foil);model.add(bus);
    for(const sign of [-1,1])for(let k=0;k<3;k++){
      const plate=new THREE.Mesh(new THREE.BoxGeometry(.095,.26,.004),panel);plate.position.set(sign*(.15+k*.1),0,0);model.add(plate);
      const rail=new THREE.Mesh(new THREE.BoxGeometry(.32,.004,.008),foil);rail.position.set(sign*.24,.13,0);model.add(rail);
    }
    return model;
  }
  for(let i=0;i<2;i++){
    const orbit=new THREE.Group(),satellite=new THREE.Group();orbit.rotation.set(i?1.87:1.39,i?.12:-.2,i?-.12:.15);satellite.add(fallbackSatellite());orbit.add(satellite);root.add(orbit);
    orbits.push({orbit,satellite,phase:i?3.3:-.05,radius:i?3.5:3.25,speed:i?-.009:.013,kind:i?"station":"satellite"});
  }
  async function spacecraft(entry,url,span){
    try{
      const {scene:model}=await new GLTFLoader().loadAsync(url),bounds=new THREE.Box3().setFromObject(model),size=bounds.getSize(new THREE.Vector3());
      model.position.sub(bounds.getCenter(new THREE.Vector3()));const holder=new THREE.Group();holder.add(model);holder.scale.setScalar(span/Math.max(size.x,size.y,size.z));holder.userData.authoredAsset=url;
      if(entry.kind==="satellite" && home.satellite_overview){
        const lod=new THREE.LOD();lod.addLevel(holder,0);
        try{const {scene:low}=await new GLTFLoader().loadAsync(home.satellite_overview),box=new THREE.Box3().setFromObject(low),dimensions=box.getSize(new THREE.Vector3());low.position.sub(box.getCenter(new THREE.Vector3()));const far=new THREE.Group();far.add(low);far.scale.setScalar(span/Math.max(dimensions.x,dimensions.y,dimensions.z));far.userData.authoredAsset=home.satellite_overview;lod.addLevel(far,13.5,.08);}catch(error){console.warn("Satellite overview unavailable",error.message);}
        entry.satellite.clear();entry.satellite.add(lod);entry.lod=lod;
      }else{entry.satellite.clear();entry.satellite.add(holder);}
      layerState[entry.kind]=true;
    }catch(error){console.warn("Optional orbital asset unavailable",url,error.message);}
  }
  async function load(){
    const loader=new THREE.TextureLoader();
    const [day,night,cloud]=await Promise.all([loader.loadAsync(config.assets.globe.day_map),loader.loadAsync(config.assets.globe.night_lights).catch(()=>null),loader.loadAsync(config.assets.globe.clouds).catch(()=>null)]);
    day.colorSpace=THREE.SRGBColorSpace;day.anisotropy=4;uniforms.dayMap.value=day;layerState.day=true;
    if(night){night.colorSpace=THREE.SRGBColorSpace;uniforms.nightMap.value=night;uniforms.nightReady.value=1;layerState.night=true;}
    if(cloud){uniforms.cloudMap.value=cloud;uniforms.cloudReady.value=1;layerState.clouds=true;}
    await Promise.all([spacecraft(orbits[0],home.satellite_model,home.satellite_span),spacecraft(orbits[1],config.visuals.orbit.model,home.station_span)]);
    update(0,0,false);
  }
  function update(time,delta,rotate=true){
    elapsed+=delta;if(rotate)earth.rotation.y+=delta*.018;
    clouds.rotation.y=earth.rotation.y+.006*Math.sin(elapsed*.025);markers.rotation.y=earth.rotation.y;
    root.updateMatrixWorld(true);
    for(const entry of orbits){
      const t=elapsed*entry.speed+entry.phase;entry.satellite.position.set(Math.cos(t)*entry.radius,Math.sin(t)*entry.radius,0);
      const localSun=sunDirection.clone().applyQuaternion(entry.orbit.getWorldQuaternion(new THREE.Quaternion()).invert());
      entry.satellite.quaternion.setFromUnitVectors(new THREE.Vector3(0,entry.kind==="satellite"?1:0,entry.kind==="satellite"?0:1),localSun);entry.satellite.rotateZ(entry.kind==="station"?.4:-.25);
    }
  }
  function highlight(id){markers.visible=true;for(const [key,entry] of pins){entry.ring.material.color.set(key===id?0x8fbdf0:0xe6e2d9);entry.pin.scale.setScalar(key===id?1.8:1);}}
  function position(id){return pins.get(id)?.pin.getWorldPosition(new THREE.Vector3());}
  function visible(value){root.visible=value;ambient.visible=sun.visible=value;stars.visible=value&&mode==="welcome";orbits.forEach(e=>e.orbit.visible=value&&mode==="welcome");}
  function setMode(value){mode=value;markers.visible=value==="select";root.position.set(value==="welcome"?(home.earth_x??0):0,value==="welcome"?(home.earth_y??.9):0,0);visible(true);}
  return {root,earth,sun,stars,load,update,highlight,position,visible,normal,mode:setMode,lod(camera){for(const entry of orbits)if(entry.lod&&entry.orbit.visible)entry.lod.update(camera);},
    diagnostics(){return {layers:{...layerState},mode,elapsed,rootPosition:root.position.toArray(),rootScale:root.scale.toArray(),earthRotation:earth.rotation.y,sunDirection:sunDirection.toArray(),stationSpan:home.station_span,spacecraft:orbits.map(e=>({kind:e.kind,position:e.satellite.getWorldPosition(new THREE.Vector3()).toArray(),bounds:(()=>{const box=new THREE.Box3().setFromObject(e.satellite);return{min:box.min.toArray(),max:box.max.toArray()};})(),visible:e.orbit.visible})),pins:[...pins].map(([id,e])=>({id,normal:e.direction.toArray(),world:e.pin.getWorldPosition(new THREE.Vector3()).toArray()}))};}
  };
}
