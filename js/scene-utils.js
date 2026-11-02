import * as THREE from "three";
export async function texture(path, repeat = 1, colour = true) {
  const map = await new THREE.TextureLoader().loadAsync(path);
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.repeat.set(repeat, repeat);
  map.anisotropy = 4;
  if (colour) map.colorSpace = THREE.SRGBColorSpace;
  return map;
}
export function box(size, position, material, parent) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.fromArray(position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  if (parent) parent.add(mesh);
  return mesh;
}
export function lightRig(root, extent = 180) {
  root.add(new THREE.HemisphereLight(0xe1ecea, 0x454442, 2.8));
  const key = new THREE.DirectionalLight(0xf1f3e8, 3.4);
  key.position.set(-extent, extent * 1.7, extent * 0.7);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, {
    left: -extent,
    right: extent,
    top: extent,
    bottom: -extent,
    near: 1,
    far: extent * 6,
  });
  key.shadow.bias = -0.0005;
  key.shadow.normalBias = 0.08;
  root.add(key);
  return key;
}
export function dispose(root) {
  const geometries = new Set(),
    materials = new Set(),
    textures = new Set();
  root.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    for (const material of Array.isArray(object.material)
      ? object.material
      : [object.material])
      if (material) {
        materials.add(material);
        for (const value of [
          ...Object.values(material),
          ...Object.values(material.userData || {}),
        ])
          if (value?.isTexture) textures.add(value);
        for (const uniform of Object.values(material.uniforms || {}))
          if (uniform.value?.isTexture) textures.add(uniform.value);
      }
  });
  geometries.forEach((item) => item.dispose());
  materials.forEach((item) => item.dispose());
  textures.forEach((item) => item.dispose());
  root.parent?.remove(root);
}
export function seeded(seed) {
  return () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}
export function line(points, colour, opacity = 1) {
  return new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(
      points.map((point) => new THREE.Vector3(...point)),
    ),
    new THREE.LineBasicMaterial({
      color: colour,
      transparent: opacity < 1,
      opacity,
    }),
  );
}

// Original studio lighting, prepared once and stored as a half-float CubeUV map.
export async function studioEnvironment(config) {
  const response = await fetch(config.path);
  if (!response.ok) throw new Error("Kit lighting unavailable");
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength !== config.width * config.height * 8)
    throw new Error("Invalid kit lighting");
  const map = new THREE.DataTexture(
    new Uint16Array(bytes),
    config.width,
    config.height,
    THREE.RGBAFormat,
    THREE.HalfFloatType,
  );
  map.mapping = THREE.CubeUVReflectionMapping;
  map.minFilter = map.magFilter = THREE.LinearFilter;
  map.generateMipmaps = false;
  map.needsUpdate = true;
  return map;
}
