import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
export function createGlobe(scene, config) {
  const mobile = false;
  const home = config.visuals.home;
  let elapsed = 0;
  const layerState = {day:false,night:false,clouds:false,station:false};
  const cloudShadow = {map:{value:null},ready:{value:0}};
  const earthRoot = new THREE.Group();
  earthRoot.rotation.z = THREE.MathUtils.degToRad(23.44);
  earthRoot.position.set(0, 1.4, 0);
  scene.add(earthRoot);
  const earthGeometry = new THREE.SphereGeometry(
    2.38,
    mobile ? 72 : 112,
    mobile ? 48 : 80,
  );
  const earthMaterial = new THREE.MeshStandardMaterial({
    roughness: .94,
    metalness: 0,
    color: 0xffffff,
  });
  earthMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.cloudShadowMap=cloudShadow.map;shader.uniforms.cloudReady=cloudShadow.ready;
    shader.fragmentShader="uniform sampler2D cloudShadowMap; uniform float cloudReady;\n"+shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <map_fragment>",
        `#include <map_fragment>
float ocean=smoothstep(0.0,.018,diffuseColor.b-diffuseColor.r)*smoothstep(-.003,.012,diffuseColor.b-diffuseColor.g*.8)*(1.0-smoothstep(.015,.1,dot(diffuseColor.rgb,vec3(.299,.587,.114))));
 diffuseColor.rgb*=mix(vec3(1.0),vec3(.72,.9,1.04),ocean*.3);
 #ifdef USE_MAP
 if(cloudReady>.5){float shade=texture2D(cloudShadowMap,vMapUv+vec2(.002,.001)).g;diffuseColor.rgb*=mix(1.0,.89,shade);}
 #endif`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        "#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,.32,ocean);",
      );
  };
  const earth = new THREE.Mesh(earthGeometry, earthMaterial);
  earth.rotation.y = 0;
  earthRoot.add(earth);

  const nightUniforms = {
    nightMap: { value: null },
    sunDirection: { value: new THREE.Vector3(-5.5, 3.8, 7.5).normalize() },
  };
  const nightMaterial = new THREE.ShaderMaterial({
    uniforms: nightUniforms,
    vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormalWorld;
    void main() {
      vUv = uv;
      vNormalWorld = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
    fragmentShader: `
    uniform sampler2D nightMap;
    uniform vec3 sunDirection;
    varying vec2 vUv;
    varying vec3 vNormalWorld;
    void main() {
      float daylight = dot(normalize(vNormalWorld), normalize(sunDirection));
      float night = 1.0 - smoothstep(-0.13, 0.12, daylight);
      float cityLight = dot(texture2D(nightMap, vUv).rgb, vec3(0.299, 0.587, 0.114));
      vec3 glow = vec3(1.0, 0.56, 0.24) * cityLight * night * 1.35;
      gl_FragColor = vec4(glow, night);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1,
  });
  const nightEarth = new THREE.Mesh(
    new THREE.SphereGeometry(home.night_radius, mobile ? 72 : 112, mobile ? 48 : 80),
    nightMaterial,
  );
  nightEarth.rotation.y = earth.rotation.y;
  nightEarth.visible = false;
  nightEarth.renderOrder = 1;
  earthRoot.add(nightEarth);

  const cloudMaterial = new THREE.MeshStandardMaterial({
    color: 0xf2f2ec,
    roughness: 1,
    transparent: true,
    opacity: 0.62,
    alphaTest: 0.025,
    depthWrite: false,
  });
  const cloudEarth = new THREE.Mesh(
    new THREE.SphereGeometry(home.cloud_radius, mobile ? 72 : 112, mobile ? 48 : 80),
    cloudMaterial,
  );
  cloudEarth.rotation.y = earth.rotation.y;
  cloudEarth.visible = false;
  cloudEarth.renderOrder = 2;
  earthRoot.add(cloudEarth);

  const surfaceMarkers = new THREE.Group();
  earthRoot.add(surfaceMarkers);

  const atmosphereMaterial = new THREE.ShaderMaterial({
    uniforms: { sunDirection: nightUniforms.sunDirection },
    vertexShader: `
    varying vec3 vNormalWorld;
    varying vec3 vPositionWorld;
    void main() {
      vec4 worldPosition = modelMatrix * vec4(position, 1.0);
      vPositionWorld = worldPosition.xyz;
      vNormalWorld = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * viewMatrix * worldPosition;
    }
  `,
    fragmentShader: `
    varying vec3 vNormalWorld;
    varying vec3 vPositionWorld;
    uniform vec3 sunDirection;
    void main() {
      vec3 viewDirection = normalize(cameraPosition - vPositionWorld);
      float rim = pow(1.0 - abs(dot(normalize(vNormalWorld), viewDirection)), 3.2);
      float daylight = max(dot(normalize(vNormalWorld), normalize(sunDirection)), 0.0);
      vec3 hue = mix(vec3(0.035, 0.12, 0.29), vec3(0.15, 0.47, 0.74), daylight);
      float twilight=exp(-pow(dot(normalize(vNormalWorld),normalize(sunDirection))/.16,2.0));
      hue=mix(hue,vec3(.67,.3,.15),twilight*.13);
      gl_FragColor = vec4(hue, rim * mix(.09,.32,daylight));
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `,
    side: THREE.BackSide,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const atmosphere = new THREE.Mesh(
    new THREE.SphereGeometry(home.atmosphere_radius, mobile ? 72 : 112, mobile ? 48 : 80),
    atmosphereMaterial,
  );
  atmosphere.renderOrder = 3;
  earthRoot.add(atmosphere);

  const ambient = new THREE.AmbientLight(0x6d90a8, home.ambient_intensity);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(home.sun_colour, home.sun_intensity);
  sun.position.set(-5.5, 3.8, 7.5);
  scene.add(sun);

  const starsGeometry = new THREE.BufferGeometry();
  const starPositions = new Float32Array(config.space.star_count * 3);
  let seed = config.space.star_seed;
  function random() {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  }
  for (let i = 0; i < starPositions.length; i += 3) {
    const radius = 13 + random() * 35;
    const theta = random() * Math.PI * 2;
    const y = random() * 2 - 1;
    const ring = Math.sqrt(1 - y * y);
    starPositions[i] = Math.cos(theta) * ring * radius;
    starPositions[i + 1] = y * radius;
    starPositions[i + 2] = Math.sin(theta) * ring * radius;
  }
  starsGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(starPositions, 3),
  );
  const starColours=new Float32Array(config.space.star_count*3),starScales=new Float32Array(config.space.star_count);
  for(let i=0;i<config.space.star_count;i++){
    const magnitude=random(),brightness=.32+magnitude*magnitude*.68;
    const colour=new THREE.Color(magnitude>.97?0xffe6c5:0xc1d8ed).multiplyScalar(brightness);
    colour.toArray(starColours,i*3);starScales[i]=home.star_sizes[magnitude>.95?2:magnitude>.6?1:0]/home.star_sizes[1];
  }
  starsGeometry.setAttribute("color",new THREE.BufferAttribute(starColours,3));
  starsGeometry.setAttribute("starScale",new THREE.BufferAttribute(starScales,1));
  const stars = new THREE.Points(
    starsGeometry,
    new THREE.PointsMaterial({
      color: 0xffffff,
      vertexColors:true,
      size: home.star_sizes[1],
      depthWrite:false,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.78,
    }),
  );
  stars.material.onBeforeCompile=shader=>{
    shader.vertexShader="attribute float starScale;\n"+shader.vertexShader.replace("gl_PointSize = size;","gl_PointSize = size * starScale;");
  };
  scene.add(stars);

  const pins = new Map();
  function normal(lat, lon) {
    const a = THREE.MathUtils.degToRad(lat),
      b = THREE.MathUtils.degToRad(lon);
    return new THREE.Vector3(
      Math.cos(a) * Math.cos(b),
      Math.sin(a),
      -Math.cos(a) * Math.sin(b),
    );
  }
  for (const environment of config.environments.filter(
    (item) => item.id !== "space",
  )) {
    const direction = normal(environment.latitude, environment.longitude);
    const pin = new THREE.Group();
    pin.position.copy(direction).multiplyScalar(2.43);
    pin.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), direction);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.037, 0.046, 40),
      new THREE.MeshBasicMaterial({
        color: 0xe6e2d9,
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide,
      }),
    );
    const dot = new THREE.Mesh(
      new THREE.CircleGeometry(0.013, 20),
      new THREE.MeshBasicMaterial({ color: 0xe6e2d9, side: THREE.DoubleSide }),
    );
    dot.position.z = 0.005;
    pin.add(ring, dot);
    surfaceMarkers.add(pin);
    pins.set(environment.id, { pin, ring, dot, direction });
  }
  surfaceMarkers.visible = false;
  const orbits = [];
  const satelliteMaterial = new THREE.MeshStandardMaterial({
    color: 0xc4b58e,
    metalness: 0.65,
    roughness: 0.38,
  });
  const solarMaterial = new THREE.MeshStandardMaterial({
    color: 0x102439,
    metalness: 0,
    roughness: 0.42,
  });
  for (let index = 0; index < config.space.satellites; index++) {
    const orbit = new THREE.Group();
    orbit.rotation.z = index ? -0.55 : 0.48;
    const satellite = new THREE.Group();
    satellite.add(
      new THREE.Mesh(
        new THREE.BoxGeometry(0.11, 0.11, 0.13),
        satelliteMaterial,
      ),
    );
    for (const side of [-1, 1]) {
      const panel = new THREE.Mesh(
        new THREE.BoxGeometry(0.2, 0.013, 0.18),
        solarMaterial,
      );
      panel.position.x = side * 0.16;
      satellite.add(panel);
    }
    const antenna=new THREE.Mesh(new THREE.CylinderGeometry(.003,.003,.15,6),satelliteMaterial);
    antenna.position.set(.04,.12,0);satellite.add(antenna);
    orbit.add(satellite);
    earthRoot.add(orbit);
    orbits.push({
      orbit,
      satellite,
      phase: index * 2.8,
      radius: 3.2 + index * 0.25,
    });
  }
  const rocks = [];
  for (const [x, y, z, size] of config.space.asteroids) {
    const geometry = new THREE.IcosahedronGeometry(size * home.asteroid_scale, 2),
      positions = geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      const k = 1 + 0.16 * Math.sin(i * 12.43);
      positions.setXYZ(
        i,
        positions.getX(i) * k,
        positions.getY(i) * k,
        positions.getZ(i) * k,
      );
    }
    geometry.computeVertexNormals();
    const rock = new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({ color: 0x484640, roughness: 1 }),
    );
    rock.position.set(x, y, z);
    scene.add(rock);
    rocks.push(rock);
  }
  const moon = new THREE.Mesh(
    new THREE.SphereGeometry(0.47, 32, 24),
    new THREE.MeshStandardMaterial({ color: 0x8b8d89, roughness: 1 }),
  );
  moon.position.set(4.1, 0.8, -1);
  moon.visible = false;
  earthRoot.add(moon);
  const assets = new THREE.TextureLoader();
  async function load() {
    const [texture,nightResult,cloudResult] = await Promise.all([
      assets.loadAsync(config.assets.globe.day_map),
      assets.loadAsync(config.assets.globe.night_lights).then(value=>({value})).catch(()=>({value:null})),
      assets.loadAsync(config.assets.globe.clouds).then(value=>({value})).catch(()=>({value:null})),
    ]);
    layerState.day=true;
    texture.colorSpace = THREE.SRGBColorSpace;
    if (typeof createImageBitmap === "function") {
      try {
        texture.image = await createImageBitmap(texture.image, {
          resizeWidth: 4096,
          resizeHeight: 2048,
          imageOrientation: "flipY",
          premultiplyAlpha: "none",
        });
      } catch {}
    }
    texture.anisotropy = 4;
    earthMaterial.map = texture;
    earthMaterial.needsUpdate = true;
    // NASA structure only, in a decorative presentation orbit. Keep the original
    // satellite in place if the optional silhouette cannot load.
    new GLTFLoader().loadAsync(config.visuals.orbit.model).then(({scene: station}) => {
      const bounds = new THREE.Box3().setFromObject(station), size = bounds.getSize(new THREE.Vector3());
      const model = new THREE.Group();
      station.position.sub(bounds.getCenter(new THREE.Vector3())); model.add(station);
      model.scale.setScalar(home.station_span / Math.max(size.x, size.y, size.z));
      const orbital = orbits[0].satellite;
      for(const child of [...orbital.children]) { orbital.remove(child); child.geometry?.dispose(); }
      orbital.add(model); layerState.station=true; orbital.userData.source = config.visuals.orbit.credit;
    }).catch(() => {});
    if(nightResult.value){nightUniforms.nightMap.value=nightResult.value;nightEarth.visible=true;layerState.night=true;}
    if(cloudResult.value){
      cloudMaterial.alphaMap=cloudResult.value;cloudMaterial.needsUpdate=true;cloudEarth.visible=true;
      cloudShadow.map.value=cloudResult.value;cloudShadow.ready.value=1;layerState.clouds=true;
    }
    Promise.all([assets.loadAsync(config.visuals.rock.diff),assets.loadAsync(config.visuals.rock.normal)])
      .then(([map,normal])=>{
        map.colorSpace=THREE.SRGBColorSpace;
        for(const rock of rocks){rock.material.map=map;rock.material.normalMap=normal;rock.material.normalScale=new THREE.Vector2(.2,.2);rock.material.needsUpdate=true;}
      }).catch(()=>{});
  }
  function update(time, delta, rotate = true) {
    elapsed+=delta;
    if (rotate) earth.rotation.y += delta * 0.022;
    nightEarth.rotation.y = earth.rotation.y;
    cloudEarth.rotation.y = earth.rotation.y + 0.008 * Math.sin(elapsed * .02);
    surfaceMarkers.rotation.y = earth.rotation.y;
    for (const entry of orbits) {
      const t = elapsed * .12 + entry.phase;
      entry.satellite.position.set(
        Math.cos(t) * entry.radius,
        Math.sin(t) * entry.radius,
        Math.sin(t) * 0.4,
      );
      entry.satellite.rotation.y = t;
    }
    for (const rock of rocks) {
      rock.rotation.x += delta * 0.014;
      rock.rotation.y += delta * 0.019;
    }
    nightUniforms.sunDirection.value
      .copy(sun.position)
      .sub(sun.target.position)
      .normalize();
  }
  function highlight(id) {
    surfaceMarkers.visible = true;
    moon.visible = id === "space";
    for (const [key, entry] of pins) {
      entry.ring.material.color.set(key === id ? 0xd5ac6c : 0xe6e2d9);
      entry.pin.scale.setScalar(key === id ? 1.8 : 1);
    }
  }
  function position(id) {
    if (id === "space") return moon.getWorldPosition(new THREE.Vector3());
    const entry = pins.get(id);
    return entry?.pin.getWorldPosition(new THREE.Vector3());
  }
  function visible(value) {
    earthRoot.visible = value;
    ambient.visible = sun.visible = value;
    stars.visible = value;
    for (const rock of rocks) rock.visible = value;
  }
  return {
    root: earthRoot,
    earth,
    sun,
    stars,
    load,
    update,
    highlight,
    position,
    visible,
    normal,
    diagnostics(){return {layers:{...layerState},earthRotation:earth.rotation.y,sunDirection:nightUniforms.sunDirection.value.toArray(),stationSpan:home.station_span,pins:[...pins].map(([id,e])=>({id,normal:e.direction.toArray(),world:e.pin.getWorldPosition(new THREE.Vector3()).toArray()}))};},
  };
}
