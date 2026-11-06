// Usage: node scripts/prepare-orbit.mjs <isolated npm tool directory> <NASA source.glb>
// npm install --prefix <tool directory> @gltf-transform/cli@4.4.0
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import path from 'node:path';
const require=createRequire(path.resolve(process.argv[2],'package.json'));
const {NodeIO}=await import(pathToFileURL(require.resolve('@gltf-transform/core')));
const {dedup,prune,weld,simplify,flatten,join}=await import(pathToFileURL(require.resolve('@gltf-transform/functions')));
const {MeshoptSimplifier}=await import(pathToFileURL(require.resolve('meshoptimizer')));
import fs from 'node:fs';
import crypto from 'node:crypto';
const source=process.argv[3];
const io=new NodeIO();const doc=await io.read(source);
for(const mat of doc.getRoot().listMaterials()) {
 for(const slot of ['baseColor','metallicRoughness','normal','occlusion','emissive']) {
  const fn='set'+slot[0].toUpperCase()+slot.slice(1)+'Texture';if(mat[fn])mat[fn](null);
 }
 mat.setEmissiveFactor([0,0,0]);mat.setMetallicFactor(.35);mat.setRoughnessFactor(.65);
}
for(const texture of doc.getRoot().listTextures())texture.dispose();
const grey=doc.createMaterial('unmarked-station-metal').setBaseColorFactor([.62,.64,.62,1]).setMetallicFactor(.35).setRoughnessFactor(.65);
const panel=doc.createMaterial('unmarked-solar-arrays').setBaseColorFactor([.08,.12,.19,1]).setMetallicFactor(.25).setRoughnessFactor(.55);
for(const mesh of doc.getRoot().listMeshes())for(const p of mesh.listPrimitives()){
 const name=(p.getMaterial()?.getName()||'').toLowerCase();p.setMaterial(name.includes('solar')?panel:grey);
 for(const semantic of p.listSemantics())if(semantic!=='POSITION')p.setAttribute(semantic,null);
}
await MeshoptSimplifier.ready;
await doc.transform(flatten(),join(),dedup(),weld(),simplify({simplifier:MeshoptSimplifier,ratio:.025,error:.1}),prune());
const out=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../assets/models/iss');fs.mkdirSync(out,{recursive:true});await io.write(out+'/iss.glb',doc);
let triangles=0;for(const mesh of doc.getRoot().listMeshes())for(const p of mesh.listPrimitives())triangles+=(p.getIndices()?.getCount()||p.getAttribute('POSITION').getCount())/3;
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.writeFileSync(out+'/manifest.json',JSON.stringify({source_url:'https://science.nasa.gov/resource/international-space-station-3d-model/',download_url:'https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/i/ISS_stationary.glb',credit:'NASA / Visualization Technology Applications and Development (VTAD)',notice:'NASA polygon data; NASA media usage guidance applies. No endorsement. All source textures and markings removed.',source_sha256:hash(source),source_bytes:fs.statSync(source).size,path:'assets/models/iss/iss.glb',sha256:hash(out+'/iss.glb'),bytes:fs.statSync(out+'/iss.glb').size,triangles,units:'source units retained; runtime normalised to presentation span, not physical or orbital scale',conversion:'glTF Transform 4.4.0; remove textures and non-position attributes; two neutral materials; flatten; join; dedup; weld; MeshoptSimplifier ratio .025 error .1; prune. Uncompressed glTF 2.0, no runtime decoder.'},null,2)+'\n');console.log({triangles,bytes:fs.statSync(out+'/iss.glb').size});
