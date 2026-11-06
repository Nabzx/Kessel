import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
export function createGlobe(scene, config) {
  const mobile = false;
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
    roughness: 1,
    metalness: 0,
    color: 0xffffff,
  });
  earthMaterial.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <map_fragment>",
        `#include <map_fragment>
float ocean=1.0-smoothstep(.012,.028,dot(diffuseColor.rgb,vec3(.299,.587,.114)));
diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.006,.025,.05),ocean*.8);`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        "#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,.46,ocean);",
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
      gl_FragColor = vec4(glow, cityLight * night);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const nightEarth = new THREE.Mesh(
    new THREE.SphereGeometry(2.386, mobile ? 72 : 112, mobile ? 48 : 80),
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
    opacity: 0.48,
    alphaTest: 0.025,
    depthWrite: false,
  });
  const cloudEarth = new THREE.Mesh(
    new THREE.SphereGeometry(2.405, mobile ? 72 : 112, mobile ? 48 : 80),
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
      vec3 hue = mix(vec3(0.06, 0.25, 0.5), vec3(0.16, 0.62, 0.84), daylight);
      gl_FragColor = vec4(hue, rim * mix(.12,.42,daylight));
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
    new THREE.SphereGeometry(2.44, mobile ? 72 : 112, mobile ? 48 : 80),
    atmosphereMaterial,
  );
  atmosphere.renderOrder = 3;
  earthRoot.add(atmosphere);

  const ambient = new THREE.AmbientLight(0x6d90a8, 0.24);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xfff2da, 3.0);
  sun.position.set(-5.5, 3.8, 7.5);
  scene.add(sun);

  const starsGeometry = new THREE.BufferGeometry();
  const starPositions = new Float32Array(config.space.star_count * 3);
  let seed = 741;
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
  const stars = new THREE.Points(
    starsGeometry,
    new THREE.PointsMaterial({
      color: 0xa8cfe2,
      size: 0.055,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.78,
    }),
  );
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
      new THREE.RingGeometry(0.025, 0.047, 32),
      new THREE.MeshBasicMaterial({
        color: 0xe6e2d9,
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide,
      }),
    );
    const dot = new THREE.Mesh(
      new THREE.CircleGeometry(0.017, 16),
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
    color: 0xc4c5bd,
    metalness: 0.65,
    roughness: 0.38,
  });
  const solarMaterial = new THREE.MeshStandardMaterial({
    color: 0x172b40,
    metalness: 0.6,
    roughness: 0.3,
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
    const geometry = new THREE.IcosahedronGeometry(size, 1),
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
    const texture = await assets.loadAsync(config.assets.globe.day_map);
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
      model.scale.setScalar(.72 / Math.max(size.x, size.y, size.z));
      const orbital = orbits[0].satellite;
      for(const child of [...orbital.children]) { orbital.remove(child); child.geometry?.dispose(); }
      orbital.add(model); orbital.userData.source = config.visuals.orbit.credit;
    }).catch(() => {});
    Promise.all([
      assets.loadAsync(config.assets.globe.night_lights),
      assets.loadAsync(config.assets.globe.clouds),
    ])
      .then(([night, cloud]) => {
        nightUniforms.nightMap.value = night;
        nightEarth.visible = true;
        cloudMaterial.alphaMap = cloud;
        cloudMaterial.needsUpdate = true;
        cloudEarth.visible = true;
      })
      .catch(() => {});
  }
  function update(time, delta, rotate = true) {
    if (rotate) earth.rotation.y += delta * 0.022;
    nightEarth.rotation.y = earth.rotation.y;
    cloudEarth.rotation.y = earth.rotation.y + 0.008 * Math.sin(time * 0.00002);
    surfaceMarkers.rotation.y = earth.rotation.y;
    for (const entry of orbits) {
      const t = time * 0.00012 + entry.phase;
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
      .sub(earthRoot.position)
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
    return entry?.direction
      .clone()
      .multiplyScalar(2.45)
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), earth.rotation.y)
      .applyQuaternion(earthRoot.quaternion)
      .add(earthRoot.position);
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
  };
}
