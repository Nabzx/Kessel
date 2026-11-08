import * as THREE from "three";
import { texture, seeded } from "./scene-utils.js";

// Closed rock bodies. Every contour stays inside its authored clearance bounds.
export function rockGeometry(size, seed = 1, relief = 0.8) {
  const [w, h, d] = size, random = seeded(seed), count = 32, layers = 4;
  const vertices = [], indices = [];
  const contour = [];
  for (let i = 0; i < count; i++) {
    const angle = i / count * Math.PI * 2;
    // Rounded rectangle, with small inward fractures rather than route intrusion.
    const c = Math.cos(angle), s = Math.sin(angle), exponent = 0.3;
    contour.push([Math.sign(c) * Math.pow(Math.abs(c), exponent) * w / 2,
      Math.sign(s) * Math.pow(Math.abs(s), exponent) * d / 2]);
  }
  for (let layer = 0; layer < layers; layer++) {
    for (const [x, z] of contour) {
      const inset = Math.min(w,d)*.07*(.5+.5*Math.sin(vertices.length/3%count*2.718+seed)) + random() * Math.min(relief, Math.min(w, d) * 0.12);
      vertices.push(x - Math.sign(x) * inset, -h / 2 + h * layer / (layers - 1), z - Math.sign(z) * inset);
    }
  }
  for (let layer = 0; layer < layers - 1; layer++) {
    for (let i = 0; i < count; i++) {
      const a = layer * count + i, b = layer * count + (i + 1) % count, c = b + count, e = a + count;
      // Contour travels anticlockwise in XZ. Faces point outwards.
      indices.push(a, e, c, a, c, b);
    }
  }
  const capStart = indices.length;
  const bottom = vertices.length / 3;
  vertices.push(0, -h / 2, 0, 0, h / 2, 0);
  for (let i = 0; i < count; i++) {
    const next = (i + 1) % count, top = (layers - 1) * count;
    indices.push(bottom, i, next, bottom + 1, top + next, top + i);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.clearGroups();
  geometry.addGroup(0, capStart, 0);
  geometry.addGroup(capStart, indices.length - capStart, 1);
  geometry.computeVertexNormals();
  // Keep actual fractured facets; the texture supplies fine detail.
  const faceted = geometry.toNonIndexed();
  faceted.computeVertexNormals();
  geometry.dispose();
  return faceted;
}

export async function rockMaterial(spec) {
  const [colour, normal, roughness, ao] = await Promise.all([
    texture(spec.diff), texture(spec.normal, 1, false), texture(spec.roughness, 1, false), texture(spec.ao, 1, false),
  ]);
  const material = new THREE.MeshStandardMaterial({ color: spec.tint || "#b8b4a6", roughness: 0.95 });
  Object.assign(material.userData, { colour, normal, roughness, ao, physicalRepeatM: spec.repeat_m });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, { rockColour: { value: colour }, rockNormal: { value: normal },
      rockRough: { value: roughness }, rockAO: { value: ao }, rockRepeat: { value: spec.repeat_m } });
    shader.vertexShader = "varying vec3 rockPosition; varying vec3 rockWorldNormal;\n" + shader.vertexShader.replace(
      "#include <begin_vertex>", "#include <begin_vertex>\nrockPosition=(modelMatrix*vec4(position,1.0)).xyz; rockWorldNormal=normalize(mat3(modelMatrix)*normal);",
    );
    shader.fragmentShader = `varying vec3 rockPosition; varying vec3 rockWorldNormal;
      uniform sampler2D rockColour, rockNormal, rockRough, rockAO; uniform float rockRepeat;
      vec4 rockSample(sampler2D tex, vec3 p, vec3 weights) {
        vec3 q=p+vec3(sin(p.z*.31),sin(p.x*.27),sin(p.y*.35))*.19;
        vec3 r=vec3(q.x*.83-q.z*.56,q.y*1.17,q.x*.56+q.z*.83)*1.17+vec3(.37,.61,.23);
        vec4 a=texture2D(tex,q.zy)*weights.x+texture2D(tex,q.xz)*weights.y+texture2D(tex,q.xy)*weights.z;
        vec4 b=texture2D(tex,r.zy)*weights.x+texture2D(tex,r.xz)*weights.y+texture2D(tex,r.xy)*weights.z;
        return mix(a,b,.48);
      }\n` + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace("#include <map_fragment>", `
      vec3 rockP=rockPosition/rockRepeat;
      vec3 rockN=normalize(rockWorldNormal);
      vec3 rockW=pow(abs(rockN),vec3(6.0)); rockW/=max(dot(rockW,vec3(1.0)),.001);
      vec3 rockTex=rockSample(rockColour,rockP,rockW).rgb;
      float strata=sin(rockPosition.y*2.3+sin(rockPosition.x*.13)+sin(rockPosition.z*.09));
      diffuseColor.rgb*=rockTex*mix(.96,1.04,smoothstep(-.6,.6,strata));
      diffuseColor.rgb*=mix(.65,1.0,rockSample(rockAO,rockP,rockW).r);
    `).replace("#include <roughnessmap_fragment>", `
      #include <roughnessmap_fragment>
      roughnessFactor=clamp(rockSample(rockRough,rockP,rockW).r,.55,1.0);
    `).replace("#include <normal_fragment_maps>", `
      #include <normal_fragment_maps>
      vec3 nx=texture2D(rockNormal,rockP.zy).xyz*2.0-1.0;
      vec3 ny=texture2D(rockNormal,rockP.xz).xyz*2.0-1.0;
      vec3 nz=texture2D(rockNormal,rockP.xy).xyz*2.0-1.0;
      vec3 mapped=normalize(vec3(nx.z*sign(rockN.x),nx.y,nx.x)*rockW.x+
        vec3(ny.x,ny.z*sign(rockN.y),ny.y)*rockW.y+
        vec3(nz.x,nz.y,nz.z*sign(rockN.z))*rockW.z);
      normal=normalize(mix(normal,mat3(viewMatrix)*mapped,.28));
    `);
  };
  material.customProgramCacheKey = () => "kessel-rock-triplanar-v2";
  return material;
}

export function rockBody(spec, material, parent, seed = 1, relief = 0.8) {
  const section = material.userData.sectionMaterial ||= new THREE.MeshStandardMaterial({ color: 0x88867a, roughness: 0.98 });
  section.onBeforeCompile=shader=>{
    shader.uniforms.sectionRock={value:material.userData.colour};
    shader.vertexShader="varying vec3 sectionPosition;\n"+shader.vertexShader.replace("#include <begin_vertex>","#include <begin_vertex>\nsectionPosition=(modelMatrix*vec4(position,1.0)).xyz;");
    shader.fragmentShader="uniform sampler2D sectionRock; varying vec3 sectionPosition;\n"+shader.fragmentShader.replace("#include <color_fragment>",`#include <color_fragment>
      float strata=sin(sectionPosition.x*.18+sectionPosition.z*.24+sin(sectionPosition.z*.1)*2.0);
      float grain=sin(sectionPosition.x*11.2)*sin(sectionPosition.z*15.7);
      vec3 cutTexture=texture2D(sectionRock,sectionPosition.xz/12.0).rgb;float cutGrey=dot(cutTexture,vec3(.2126,.7152,.0722));
      diffuseColor.rgb*=mix(vec3(sqrt(cutGrey)*.85),cutTexture,.18)*mix(.88,1.08,smoothstep(-.6,.6,strata))*(.98+.02*grain);`);
  };
  const mesh = new THREE.Mesh(rockGeometry(spec.size, seed, relief), [material, section]);
  mesh.position.fromArray(spec.position);
  mesh.castShadow = mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}
