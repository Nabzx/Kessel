import * as THREE from "three";

// Include visible visual geometry, not hidden fallback bodies or collision guides.
export function visibleBounds(root, target = new THREE.Box3()) {
  target.makeEmpty();
  root.updateMatrixWorld(true);
  function visit(object) {
    if (!object.visible) return;
    if (object.isMesh && object.geometry) {
      if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
      target.union(object.geometry.boundingBox.clone().applyMatrix4(object.matrixWorld));
    }
    for (const child of object.children) visit(child);
  }
  visit(root);
  return target;
}

export function boxCorners(bounds) {
  return [0, 1, 2, 3, 4, 5, 6, 7].map(i => new THREE.Vector3(
    i & 1 ? bounds.max.x : bounds.min.x,
    i & 2 ? bounds.max.y : bounds.min.y,
    i & 4 ? bounds.max.z : bounds.min.z));
}

export function fitReplay(camera, bounds, panel, headerBottom = 84) {
  const width = innerWidth, height = innerHeight;
  const safe = {left:32, right:Math.min(width - 32, panel.left - 28), top:headerBottom + 28, bottom:height - 88};
  const centre = bounds.getCenter(new THREE.Vector3());
  const direction = new THREE.Vector3(21, 20.5, 28).normalize();
  const points = boxCorners(bounds);
  camera.aspect = width / height;
  camera.setViewOffset(width, height, width/2 - (safe.left+safe.right)/2, height/2 - (safe.top+safe.bottom)/2, width, height);
  const project = distance => {
    camera.position.copy(centre).addScaledVector(direction, distance);
    camera.lookAt(centre);camera.updateMatrixWorld(true);camera.updateProjectionMatrix();
    const p = points.map(v => v.clone().project(camera));
    return {left:Math.min(...p.map(v=>(v.x+1)*width/2)), right:Math.max(...p.map(v=>(v.x+1)*width/2)), top:Math.min(...p.map(v=>(1-v.y)*height/2)), bottom:Math.max(...p.map(v=>(1-v.y)*height/2))};
  };
  let low = Math.max(4,bounds.getSize(new THREE.Vector3()).length()/2), high = 150;
  for(let i=0;i<32;i++) {
    const mid=(low+high)/2, p=project(mid);
    if(p.left>=safe.left&&p.right<=safe.right&&p.top>=safe.top&&p.bottom<=safe.bottom)high=mid;else low=mid;
  }
  const projected=project(high);
  return {target:centre, safe, projected, distance:high};
}
