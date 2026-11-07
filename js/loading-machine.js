import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export async function createLoadingMachine(config, drawPoint) {
  const gltf=await new GLTFLoader().loadAsync(config.model);
  const model=gltf.scene;
  const bones=[];
  model.traverse(object=>{
    if(object.isBone) bones.push(object);
    if(object.isMesh) { object.frustumCulled=false; object.castShadow=true; object.receiveShadow=true; }
  });
  model.updateMatrixWorld(true);
  const bounds=new THREE.Box3().setFromObject(model);
  const size=bounds.getSize(new THREE.Vector3());
  model.scale.multiplyScalar(config.length_m/Math.max(size.x,size.z));
  // Point the bucket towards the truck; use the documented rig joints rather
  // than inferring forward from the glTF root's arbitrary export rotation.
  const bucket=config.bucket_bone_name?bones.find(b=>b.name===config.bucket_bone_name):bones[config.bucket_bone_index], tracks=config.tracks_bone_name?bones.find(b=>b.name===config.tracks_bone_name):bones[9]||bones[0];
  if(!bucket||!tracks)throw new Error("Excavator joint mapping unavailable");
  const direction=bucket.getWorldPosition(new THREE.Vector3()).sub(tracks.getWorldPosition(new THREE.Vector3()));
  const targetHeading=config.target_offset_m
    ? Math.atan2(config.target_offset_m[0]-config.offset_m[0],config.target_offset_m[2]-config.offset_m[2])
    : -Math.PI/2;
  model.rotation.y += targetHeading-Math.atan2(direction.x,direction.z);
  model.updateMatrixWorld(true);
  bounds.setFromObject(model);
  const centre=bounds.getCenter(new THREE.Vector3());
  model.position.x-=centre.x; model.position.z-=centre.z; model.position.y-=bounds.min.y;
  const root=new THREE.Group(); root.name="licensed-loading-excavator";root.userData.authoredAsset=config.model;
  root.position.fromArray(drawPoint.position_m).add(new THREE.Vector3(...config.offset_m));
  root.add(model);
  const boom=config.boom_bone_name?bones.find(b=>b.name===config.boom_bone_name):bones[config.boom_bone_index];
  if(!boom)throw new Error("Excavator boom mapping unavailable");
  const boomBase=boom.quaternion.clone(),bucketBase=bucket.quaternion.clone();
  const axis=new THREE.Vector3(1,0,0),rotation=new THREE.Quaternion();
  let boomAngle=0,bucketAngle=0;
  return {root,bucketPosition(target){return bucket.getWorldPosition(target);},update(entry,delta=0){
    const loading=entry?.phase==="loading";
    const phase=loading?entry.load*Math.PI*2:0;
    boomAngle=THREE.MathUtils.damp(boomAngle,loading?Math.sin(phase)*.2:0,5,delta);
    bucketAngle=THREE.MathUtils.damp(bucketAngle,loading?Math.sin(phase+.6)*.3:0,5,delta);
    boom.quaternion.copy(boomBase).multiply(rotation.setFromAxisAngle(axis,boomAngle));
    bucket.quaternion.copy(bucketBase).multiply(rotation.setFromAxisAngle(axis,bucketAngle));
  }};
}
