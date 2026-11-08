import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
const loader=new GLTFLoader(),cache=new Map();
export async function authoredAsset(spec) {
  if(!spec?.path)return null;
  if(!cache.has(spec.path))cache.set(spec.path,loader.loadAsync(spec.path+"?v="+encodeURIComponent(document.querySelector('meta[name="kessel-presentation"]')?.content||"local")).catch(error=>{cache.delete(spec.path);throw error;}));
  const asset=await cache.get(spec.path),root=asset.scene.clone(true);
  root.name=spec.id||root.name;
  const materials=new Map();
  const own=material=>{if(!materials.has(material))materials.set(material,material.clone());return materials.get(material);};
  root.traverse(object=>{if(object.isMesh){object.castShadow=true;object.receiveShadow=true;object.material=Array.isArray(object.material)?object.material.map(own):own(object.material);}});
  root.userData.assetPath=spec.path;
  root.userData.source='Original Blender authoring; synthetic/proposed geometry';
  return root;
}
