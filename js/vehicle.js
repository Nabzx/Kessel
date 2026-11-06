import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

// The geometry and articulation are authored in the vehicle asset, in metres.
export function createVehicle(id, model, textures = {}) {
  const root = new THREE.Group();
  root.name = id;
  root.userData.vehicleId = id;
  const materials = Object.fromEntries(Object.entries(model.materials).map(([name, spec]) => [name, new THREE.MeshStandardMaterial({ color: spec.colour, roughness: spec.roughness ?? .8, metalness: spec.metalness ?? 0, emissive: spec.emissive || 0 })]));
  // Painted steel and rubber are dielectrics; only exposed fittings use metal.
  materials.body.metalness = 0;
  materials.body.roughness = .66;
  materials.dark.metalness = 0;
  materials.dark.roughness = .95;
  materials.glass.metalness = 0;
  materials.glass.roughness = .16;
  materials.body.onBeforeCompile = shader => {
    shader.vertexShader = "varying vec3 panelPosition;\n" + shader.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\npanelPosition=position;");
    shader.fragmentShader = "varying vec3 panelPosition;\n" + shader.fragmentShader.replace("#include <color_fragment>", `
      #include <color_fragment>
      float grit=.5+.5*sin(panelPosition.x*63.0)*sin(panelPosition.z*79.0);
      diffuseColor.rgb*=mix(.78,1.0,smoothstep(-.5,.1,panelPosition.y))*(.97+.03*grit);
    `);
  };
  materials.cargo.map = textures.oreMap || null;
  materials.cargo.normalMap = textures.oreNormal || null;
  materials.lamp = new THREE.MeshBasicMaterial({ color: model.materials.lamp.colour, toneMapped: false });
  const box = new THREE.BoxGeometry(1, 1, 1);
  const bodyBox = new RoundedBoxGeometry(1, 1, 1, 1, .035);
  const transform = new THREE.Object3D();
  function boxes(parts, parent) {
    for (const name of new Set(parts.map(part => part.material))) {
      const specs = parts.filter(part => part.material === name);
      const mesh = new THREE.InstancedMesh(name === "body" ? bodyBox : box, materials[name], specs.length);
      mesh.userData.vehicleId = id;
      specs.forEach((part, i) => {
        transform.position.fromArray(part.position_m);
        transform.scale.fromArray(part.size_m);
        transform.rotation.set(...(part.rotation || [0, 0, 0]));
        transform.updateMatrix();
        mesh.setMatrixAt(i, transform.matrix);
      });
      mesh.computeBoundingSphere();
      parent.add(mesh);
    }
  }
  boxes([...model.parts, ...(model.detail_parts || [])], root);
  const dumpBed = new THREE.Group();
  dumpBed.position.fromArray(model.dump_bed.position_m);
  root.add(dumpBed);
  boxes([{ material: "body", position_m: model.dump_bed.body_position_m, size_m: model.dump_bed.body_size_m }, ...model.dump_bed.panels], dumpBed);
  const cargo = new THREE.Group();
  dumpBed.add(cargo);
  const cargoMesh = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), materials.cargo, model.dump_bed.cargo_rocks.length);
  model.dump_bed.cargo_rocks.forEach((rock, i) => {
    transform.position.fromArray(rock.position_m);
    transform.scale.setScalar(rock.radius_m);
    transform.rotation.set(i * .7, i * 1.3, i * .4);
    transform.updateMatrix();
    cargoMesh.setMatrixAt(i, transform.matrix);
  });
  cargo.add(cargoMesh);
  const wheels = [];
  const spec = model.wheels;
  const tyreGeometry = new THREE.CylinderGeometry(spec.radius_m, spec.radius_m, spec.width_m, spec.segments);
  const hubGeometry = new THREE.CylinderGeometry(spec.hub_radius_m, spec.hub_radius_m, .08, 12);
  for (const side of [-1, 1]) {
    for (const z of spec.axle_z_m) {
      const wheel = new THREE.Group();
      wheel.position.set(side * spec.side_offset_m, spec.centre_y_m, z);
      const tyre = new THREE.Mesh(tyreGeometry, materials.dark);
      tyre.rotation.z = Math.PI / 2;
      wheel.add(tyre);
      const hub = new THREE.Mesh(hubGeometry, materials.body);
      hub.rotation.z = Math.PI / 2;
      hub.position.x = side * (spec.width_m / 2 - .06);
      wheel.add(hub);
      const tread = Array.from({ length: 20 }, (_, i) => {
        const a = i / 20 * Math.PI * 2;
        return { material: "dark", size_m: [spec.width_m * .92, .07, .13], position_m: [0, Math.cos(a) * spec.radius_m, Math.sin(a) * spec.radius_m], rotation: [a, 0, .12 * side] };
      });
      boxes(tread, wheel);
      root.add(wheel);
      wheels.push(wheel);
    }
    const lamp = new THREE.Mesh(new THREE.SphereGeometry(model.headlights.radius_m, 8, 6), materials.lamp);
    lamp.position.set(side * model.headlights.side_offset_m, ...model.headlights.position_m);
    root.add(lamp);
  }
  const badgeCanvas=document.createElement("canvas");badgeCanvas.width=256;badgeCanvas.height=64;
  const badgeContext=badgeCanvas.getContext("2d");badgeContext.fillStyle="#17262c";badgeContext.fillRect(0,0,256,64);
  badgeContext.font="500 22px monospace";badgeContext.fillStyle="#d5e8ed";badgeContext.fillText(`KESSEL / ${id.slice(-2)}`,14,40);
  const badge=new THREE.Mesh(new THREE.PlaneGeometry(.85,.21),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(badgeCanvas),side:THREE.DoubleSide}));
  badge.position.set(0,.77,-3.82);badge.rotation.y=Math.PI;root.add(badge);
  // Small contact shadow, without adding a second render pass or shadow maps.
  const shadowCanvas = document.createElement("canvas");
  shadowCanvas.width = shadowCanvas.height = 32;
  const context = shadowCanvas.getContext("2d");
  const gradient = context.createRadialGradient(16, 16, 0, 16, 16, 16);
  gradient.addColorStop(0, "rgba(0,0,0,.65)");
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = gradient; context.fillRect(0, 0, 32, 32);
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 9), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(shadowCanvas), transparent: true, depthWrite: false }));
  shadow.name = "contact-shadow";
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = .09;
  root.add(shadow);
  const detail=new THREE.Group();detail.name="inspection-detail";
  for(const child of [...root.children]) detail.add(child);
  root.add(detail);
  const overview=new THREE.Group();overview.name="overview-vehicle";
  const dimensions=model.dimensions_m;
  const proxyBody=new THREE.InstancedMesh(box,new THREE.MeshBasicMaterial({color:model.materials.body.colour}),2);
  const bodySpecs=[{size:[dimensions.width*.9,dimensions.height*.4,dimensions.length],position:[0,dimensions.height*.35,0]},{size:[dimensions.width*.9,dimensions.height*.5,dimensions.length*.23],position:[0,dimensions.height*.73,dimensions.length*.31]}];
  bodySpecs.forEach((part,index)=>{transform.position.fromArray(part.position);transform.scale.fromArray(part.size);transform.rotation.set(0,0,0);transform.updateMatrix();proxyBody.setMatrixAt(index,transform.matrix);});overview.add(proxyBody);
  const proxyWheels=new THREE.InstancedMesh(tyreGeometry,new THREE.MeshBasicMaterial({color:model.materials.dark.colour}),4);
  wheels.forEach((wheel,index)=>{transform.position.copy(wheel.position);transform.scale.setScalar(1);transform.rotation.set(0,0,Math.PI/2);transform.updateMatrix();proxyWheels.setMatrixAt(index,transform.matrix);});overview.add(proxyWheels);
  const proxyCargo=new THREE.Mesh(new THREE.BoxGeometry(dimensions.width*.8,dimensions.height*.15,dimensions.length*.52),new THREE.MeshBasicMaterial({color:model.materials.cargo.colour}));proxyCargo.position.set(0,dimensions.height*.68,-dimensions.length*.15);overview.add(proxyCargo);
  root.add(overview);detail.visible=false;
  root.traverse(object => { if (object.isMesh) object.userData.vehicleId = id; });
  return { root, detail, overview, proxyCargo, dumpBed, cargo, wheels, forward: new THREE.Vector3(...model.forward_axis) };
}
