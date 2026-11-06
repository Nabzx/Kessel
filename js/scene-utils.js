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
export function lightRig(root, extent = 180, stage = "surface") {
  root.add(new THREE.HemisphereLight(0xc9d9df, 0x373a32, stage === "mine" ? 1.55 : 1.35));
  const key = new THREE.DirectionalLight(0xffe5bb, stage === "mine" ? 2.4 : 3.1);
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
  key.shadow.normalBias = 0.035;
  key.shadow.radius = 2;
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

// Blend two translated samples through a smooth, low-frequency field. This
// breaks the repeating photograph without a larger texture or extra draw call.
export function varyTexture(material) {
  const prepare = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    prepare.call(material, shader);
    shader.fragmentShader = shader.fragmentShader.replace("#include <map_fragment>", `
      #ifdef USE_MAP
        vec2 surfaceUV=vMapUv;
        float field=(sin(surfaceUV.x*.47)+sin(surfaceUV.y*.39+surfaceUV.x*.13))*2.0+4.0;
        float cell=floor(field), blend=smoothstep(.15,.85,fract(field));
        vec2 offsetA=sin(vec2(3.0,7.0)*cell), offsetB=sin(vec2(3.0,7.0)*(cell+1.0));
        vec4 texel=mix(texture2D(map,surfaceUV+offsetA),texture2D(map,surfaceUV+offsetB),blend);
        diffuseColor*=texel;
      #endif
    `);
    shader.fragmentShader=shader.fragmentShader.replace("#include <normal_fragment_maps>",
      THREE.ShaderChunk.normal_fragment_maps.replaceAll("texture2D( normalMap, vNormalMapUv )",
        "mix(texture2D(normalMap,vNormalMapUv+offsetA),texture2D(normalMap,vNormalMapUv+offsetB),blend)"));
  };
  material.customProgramCacheKey = () => "kessel-varied-surface-" + material.type;
  return material;
}
