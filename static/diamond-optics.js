// Local, deterministic optical material for the rotating login diamond.
// All intersections use the same convex boundary that is rasterized on screen.
export function buildFacetPlanes(positions) {
  if (!positions.length || positions.length % 9) {
    throw new Error("Expected non-indexed triangles");
  }
  const planes = [];
  for (let i = 0; i < positions.length; i += 9) {
    const a = Array.from(positions.slice(i, i + 3));
    const u = [0, 1, 2].map(k => positions[i + 3 + k] - a[k]);
    const v = [0, 1, 2].map(k => positions[i + 6 + k] - a[k]);
    const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const length = Math.hypot(...n);
    if (length < 1e-9) throw new Error("Degenerate optical facet");
    let plane = [...n.map(x => x / length), n.reduce((s, x, k) => s + x * a[k], 0) / length];
    if (plane[3] < 0) plane = plane.map(x => -x);
    if (!planes.some(p => p.every((x, k) => Math.abs(x - plane[k]) < 1e-5))) planes.push(plane);
  }
  if (planes.length > 128) throw new Error("Optical facet budget exceeded");
  for (const p of planes) {
    for (let i = 0; i < positions.length; i += 3) {
      if (p[0] * positions[i] + p[1] * positions[i + 1] + p[2] * positions[i + 2] - p[3] > 1e-4) {
        throw new Error("Optical boundary must be convex and contain the origin");
      }
    }
  }
  return planes;
}

function studioTexture(THREE) {
  const width = 768, height = 384;
  const data = new Uint16Array(width * height * 4);
  // Broad photographic softboxes separated by black flags. Small HDR pinlights
  // create isolated flashes without washing every facet into a white surface.
  const boxes = [
    [0.10, 0.27, 0.23, 0.27, 1.5, 0.94, 0.97, 1],
    [0.40, 0.17, 0.24, 0.23, 2.1, 1, 0.99, 0.96],
    [0.68, 0.30, 0.20, 0.32, 1.35, 0.92, 0.96, 1],
    [0.91, 0.20, 0.16, 0.20, 1.7, 1, 1, 1],
    [0.29, 0.62, 0.25, 0.28, 0.85, 1, 0.98, 0.93],
    [0.59, 0.73, 0.30, 0.20, 1.1, 0.93, 0.97, 1],
    [0.88, 0.66, 0.15, 0.24, 0.6, 1, 1, 1],
  ];
  const pins = [[0.18, 0.31], [0.45, 0.12], [0.64, 0.39], [0.81, 0.17], [0.34, 0.67], [0.93, 0.59]];
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const u = (x + 0.5) / width, v = (y + 0.5) / height;
      const c = [0.010, 0.012, 0.017];
      for (const b of boxes) {
        const du = Math.min(Math.abs(u - b[0]), 1 - Math.abs(u - b[0]));
        const edge = Math.min((b[2] * 0.5 - du) * width, (b[3] * 0.5 - Math.abs(v - b[1])) * height);
        const mask = Math.max(0, Math.min(1, edge / 1.5));
        const value = mask * b[4] * (0.65 + 0.35 * v);
        for (let k = 0; k < 3; k++) c[k] += value * b[5 + k];
      }
      for (const pin of pins) {
        const du = Math.min(Math.abs(u - pin[0]), 1 - Math.abs(u - pin[0]));
        const d2 = (du / 0.005) ** 2 + ((v - pin[1]) / 0.009) ** 2;
        const value = 16 * Math.exp(-d2 * 2);
        for (let k = 0; k < 3; k++) c[k] += value;
      }
      const offset = (y * width + x) * 4;
      for (let k = 0; k < 3; k++) data[offset + k] = THREE.DataUtils.toHalfFloat(c[k]);
      data[offset + 3] = THREE.DataUtils.toHalfFloat(1);
    }
  }
  const texture = new THREE.DataTexture(data, width, height, THREE.RGBAFormat, THREE.HalfFloatType);
  texture.minFilter = texture.magFilter = THREE.LinearFilter;
  texture.wrapS = THREE.RepeatWrapping;
  texture.colorSpace = THREE.LinearSRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

export function createDiamondOptics(THREE, geometry) {
  const planes = buildFacetPlanes(geometry.attributes.position.array);
  const environment = studioTexture(THREE);
  const material = new THREE.ShaderMaterial({
    defines: { FACET_COUNT: planes.length },
    uniforms: {
      facets: { value: planes.map(p => new THREE.Vector4(...p)) },
      studio: { value: environment },
      localCamera: { value: new THREE.Vector3() },
      localToWorld: { value: new THREE.Matrix3() },
      environmentAngle: { value: 0 },
      brilliance: { value: 1 },
    },
    vertexShader: `
      varying vec3 surfacePosition;
      varying vec3 surfaceNormal;
      void main() {
        surfacePosition = position;
        surfaceNormal = normal;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      precision highp float;
      uniform vec4 facets[FACET_COUNT];
      uniform sampler2D studio;
      uniform vec3 localCamera;
      uniform mat3 localToWorld;
      uniform float environmentAngle;
      uniform float brilliance;
      varying vec3 surfacePosition;
      varying vec3 surfaceNormal;
      const float EPS = 0.00015;
      const float PI = 3.14159265359;

      vec3 illumination(vec3 direction) {
        vec3 d = normalize(localToWorld * direction);
        float c = cos(environmentAngle), s = sin(environmentAngle);
        d.xz = mat2(c, -s, s, c) * d.xz;
        vec2 uv = vec2(atan(d.z, d.x) / (2.0 * PI) + 0.5, asin(clamp(d.y, -1.0, 1.0)) / PI + 0.5);
        return texture2D(studio, uv).rgb * brilliance;
      }

      float fresnel(float cosine, float etaI, float etaT) {
        float sinT2 = pow(etaI / etaT, 2.0) * (1.0 - cosine * cosine);
        if (sinT2 >= 1.0) return 1.0;
        float cosT = sqrt(1.0 - sinT2);
        float rs = (etaI * cosine - etaT * cosT) / (etaI * cosine + etaT * cosT);
        float rp = (etaT * cosine - etaI * cosT) / (etaT * cosine + etaI * cosT);
        return 0.5 * (rs * rs + rp * rp);
      }

      // The mesh is convex: the next exit is the nearest forward supporting plane.
      float intersectBoundary(vec3 origin, vec3 direction, out vec3 hitNormal) {
        float nearest = 1.0e5;
        hitNormal = vec3(0.0, 1.0, 0.0);
        for (int i = 0; i < FACET_COUNT; i++) {
          vec4 p = facets[i];
          float denominator = dot(p.xyz, direction);
          if (denominator > 0.00001) {
            float distance = (p.w - dot(p.xyz, origin)) / denominator;
            if (distance > EPS * 0.25 && distance < nearest) {
              nearest = distance;
              hitNormal = p.xyz;
            }
          }
        }
        return nearest;
      }

      vec3 traceInside(vec3 incident, vec3 normal, float ior) {
        vec3 direction = refract(incident, normal, 1.0 / ior);
        vec3 origin = surfacePosition - normal * EPS;
        vec3 radiance = vec3(0.0);
        float throughput = 1.0;
        for (int bounce = 0; bounce < 7; bounce++) {
          vec3 hitNormal;
          float distance = intersectBoundary(origin, direction, hitNormal);
          if (distance > 1.0e4) break;
          vec3 hit = origin + direction * distance;
          float reflectance = fresnel(clamp(dot(direction, hitNormal), 0.0, 1.0), ior, 1.0);
          if (reflectance < 0.9999) {
            vec3 outgoing = refract(direction, -hitNormal, ior);
            radiance += throughput * (1.0 - reflectance) * illumination(outgoing);
          }
          throughput *= reflectance * exp(-distance * 0.006);
          if (throughput < 0.015) break;
          direction = reflect(direction, hitNormal);
          origin = hit - hitNormal * EPS;
        }
        return radiance;
      }

      void main() {
        vec3 incident = normalize(surfacePosition - localCamera);
        vec3 normal = normalize(surfaceNormal);
        float entry = fresnel(clamp(-dot(incident, normal), 0.0, 1.0), 1.0, 2.42);
        // Separate optical paths, not a rainbow coating: fire appears at facet boundaries.
        vec3 red = traceInside(incident, normal, 2.407);
        vec3 green = traceInside(incident, normal, 2.420);
        vec3 blue = traceInside(incident, normal, 2.438);
        vec3 transmitted = vec3(red.r, green.g, blue.b);
        vec3 reflected = illumination(reflect(incident, normal));
        vec3 color = reflected * entry + transmitted * (1.0 - entry);
        gl_FragColor = vec4(color, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const inverse = new THREE.Matrix4();
  const cameraWorld = new THREE.Vector3();
  return {
    material,
    update(mesh, camera, angle, hover) {
      mesh.updateMatrixWorld();
      camera.getWorldPosition(cameraWorld);
      inverse.copy(mesh.matrixWorld).invert();
      material.uniforms.localCamera.value.copy(cameraWorld).applyMatrix4(inverse);
      material.uniforms.localToWorld.value.setFromMatrix4(mesh.matrixWorld);
      material.uniforms.environmentAngle.value = angle;
      material.uniforms.brilliance.value = 0.85 + hover * 0.12;
    },
    dispose() {
      material.dispose();
      environment.dispose();
    },
  };
}
