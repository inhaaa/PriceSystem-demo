export default function({ parentElement, data = {} }) {
  const anchor = parentElement.querySelector('.ps-login-scene-anchor');
  if (!anchor) return () => {};
  if (!anchor.sceneTemplate) {
    anchor.sceneTemplate = parentElement.querySelector('.ps-login-art');
    anchor.sceneTemplate?.remove();
  }
  document.body.psLoginSceneDispose?.();
  const root = anchor.sceneTemplate?.cloneNode(true);
  if (!root) return () => {};
  const visual = root.querySelector('.ps-login-visual');
  if (!visual) return () => {};
  root.dataset.sceneState = 'loading';
  root.dataset.renderer = 'loading';
  root.dataset.composition = 'price-bands';
  root.dataset.phase = 'gather';
  // The mobile artwork must share the native form's scrolling container.
  (document.querySelector('[data-testid="stMain"]') || document.body).append(root);

  let disposed = false;
  let renderer, scene, camera, sculpture, key, environment, projectedLabel, projectedSelection, selectionPoint;
  let accent, tint, porcelain, referenceMaterial, markerMaterial, selectedBase, pointCoreMaterial, pointCollarMaterial;
  let selectionStrength = 0;
  let raf = 0, previousFrame = 0, elapsed = 0, diagnosticTime = -1, distance = 18, contextLost = false;
  const bands = [], guideX = 1.5;
  const referenceLabel = visual.querySelector('.ps-login-reference-label');
  const selectionLabel = visual.querySelector('.ps-login-selection-label');
  const pointer = {x: 0, y: 0};
  const easedPointer = {x: 0, y: 0};
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = matchMedia('(max-width: 767px)');
  const palettes = {
    '초록색': {action: '#204e3e', deep: '#153d32'},
    '파란색': {action: '#315780', deep: '#203650'},
    '핑크색': {action: '#944761', deep: '#4f2839'},
    '검정색': {action: '#25282c', deep: '#191c20'},
  };
  const canAnimate = () => !disposed && !contextLost && !motion.matches && !mobile.matches && !document.hidden;
  const positionSelectionLabel = (x, y, strength) => {
    if (!selectionLabel) return;
    selectionLabel.hidden = strength <= 0.001;
    selectionLabel.style.opacity = strength.toFixed(3);
    if (selectionLabel.hidden) return;
    const visible = root.getBoundingClientRect(), rect = visual.getBoundingClientRect();
    const leftEdge = Math.max(0, visible.left - rect.left) + 12;
    const rightEdge = Math.min(rect.width, visible.right - rect.left) - 12;
    const width = selectionLabel.offsetWidth;
    let left = x + 12;
    if (left + width > rightEdge) left = x - 12 - width;
    selectionLabel.style.left = `${Math.max(leftEdge, Math.min(left, rightEdge - width))}px`;
    selectionLabel.style.top = `${y}px`;
  };
  const syncSelectionLabel = () => {
    if (!selectionLabel || disposed || !root.isConnected) return;
    if (root.dataset.renderer === 'fallback') {
      const point = visual.querySelector('.ps-login-fallback-point');
      if (!point) return;
      const dot = point.getBoundingClientRect(), rect = visual.getBoundingClientRect();
      positionSelectionLabel(dot.left + dot.width / 2 - rect.left, dot.top + dot.height / 2 - rect.top, 1);
    } else if (selectionPoint && projectedSelection && camera) {
      selectionPoint.getWorldPosition(projectedSelection);
      projectedSelection.project(camera);
      positionSelectionLabel((projectedSelection.x + 1) * visual.clientWidth / 2, (1 - projectedSelection.y) * visual.clientHeight / 2, selectionStrength);
    }
  };
  const render = () => {
    if (!disposed && renderer && !contextLost && root.isConnected) {
      renderer.render(scene, camera);
      if (referenceLabel && projectedLabel && sculpture) {
        sculpture.localToWorld(projectedLabel.set(guideX, 3.05, 0.4));
        projectedLabel.project(camera);
        referenceLabel.style.left = `${(projectedLabel.x + 1) * visual.clientWidth / 2}px`;
        referenceLabel.style.top = `${(1 - projectedLabel.y) * visual.clientHeight / 2}px`;
      }
    }
    syncSelectionLabel();
  };
  const applyPalette = () => {
    if (!accent) return;
    const name = document.body.dataset.psColor === '하늘색' ? '파란색' : document.body.dataset.psColor;
    const palette = data?.paletteMap?.[name] || palettes[name] || palettes['초록색'];
    const css = getComputedStyle(root);
    const actionColor = css.getPropertyValue('--ps-login-action').trim() || palette.action;
    const deepColor = css.getPropertyValue('--ps-login-deep').trim() || palette.deep;
    const Color = accent.color.constructor;
    const white = new Color('#f2f2e9');
    selectedBase.set(actionColor).lerp(white, 0.53);
    accent.emissive.set(actionColor);
    tint.color.set(actionColor).lerp(white, 0.29);
    porcelain.color.set(actionColor).lerp(white, 0.83);
    markerMaterial.color.set(deepColor).lerp(white, 0.08);
    referenceMaterial.color.set(css.getPropertyValue('--ps-login-accent').trim() || '#e4ebdb');
    accent.color.copy(selectedBase).lerp(referenceMaterial.color, selectionStrength * 0.3);
    pointCoreMaterial.color.copy(referenceMaterial.color);
    pointCollarMaterial.color.set(deepColor);
    root.dataset.sceneColor = name || '초록색';
    render();
  };
  const resize = () => {
    if (disposed) return;
    if (!renderer || contextLost) {
      syncSelectionLabel();
      return;
    }
    const {width, height} = visual.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile.matches ? 1 : 1.5));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    distance = Math.max(14.6, 12.6 / camera.aspect);
    camera.position.set(distance * 0.27, distance * 0.19, distance * 0.96);
    camera.lookAt(0.3, 0.1, 0);
    camera.updateProjectionMatrix();
    render();
  };

  const smooth = value => {
    const t = Math.max(0, Math.min(1, value));
    return t * t * t * (t * (t * 6 - 15) + 10);
  };
  const pose = (time, delta = 0) => {
    const cycle = time % 18;
    let alignment = 0;
    for (const [index, band] of bands.entries()) {
      const amount = cycle < 11.8 ? smooth((cycle - 1 - index * 0.32) / 3.2) : 1 - smooth((cycle - 11.8 - index * 0.22) / 3.6);
      const free = 1 - amount;
      const x = guideX + (band.offset + Math.sin(time * 0.32 + index) * 0.13) * free;
      const y = band.y + Math.sin(time * 0.45 + index * 0.9) * 0.045 * free;
      band.mesh.position.set(x, y, Math.sin(time * 0.3 + index) * 0.04 * free);
      band.mesh.rotation.set(Math.sin(time * 0.24 + index) * 0.02 * free, band.tilt * free, band.tilt * 0.18 * free);
      band.marker.position.set(x, y, 0.265 + band.mesh.position.z);
      band.marker.rotation.copy(band.mesh.rotation);
      alignment += amount;
    }
    const selection = smooth((cycle - 5.4) / 0.9) * (1 - smooth((cycle - 11.8) / 1.2));
    selectionStrength = selection;
    accent.color.copy(selectedBase).lerp(referenceMaterial.color, selection * 0.3);
    accent.emissiveIntensity = selection * 0.12;
    selectionPoint.visible = selection > 0.001;
    selectionPoint.scale.setScalar(0.82 + selection * 0.18);
    pointCoreMaterial.opacity = pointCollarMaterial.opacity = selection;
    const damping = 1 - Math.exp(-delta * 3.2);
    easedPointer.x += (pointer.x - easedPointer.x) * damping;
    easedPointer.y += (pointer.y - easedPointer.y) * damping;
    sculpture.rotation.set(0.055 + easedPointer.y * 0.055 + Math.sin(time * 0.24) * 0.008, -0.22 + easedPointer.x * 0.1 + Math.sin(time * 0.21 + 0.8) * 0.008, -0.045 - easedPointer.x * 0.022);
    camera.position.set(distance * 0.27 + easedPointer.x * 0.45, distance * 0.19 - easedPointer.y * 0.28, distance * 0.96);
    camera.lookAt(0.3, 0.1, 0);
    key.position.x = -5 + easedPointer.x * 1.5 + Math.sin(time * 0.22) * 0.2;
    if (Math.abs(time - diagnosticTime) >= 0.25 || delta === 0) {
      diagnosticTime = time;
      root.dataset.phase = cycle < 1 || cycle >= 16.8 ? 'gather' : cycle < 5.8 ? 'align' : cycle < 11.8 ? 'hold' : 'release';
      root.dataset.alignment = (alignment / bands.length).toFixed(3);
      root.dataset.selection = selection.toFixed(3);
      root.dataset.point = selection.toFixed(3);
    }
  };
  const animate = now => {
    raf = 0;
    if (!canAnimate()) return;
    if (!previousFrame || now - previousFrame >= 1000 / 30) {
      const delta = previousFrame ? Math.min((now - previousFrame) / 1000, 0.1) : 0;
      previousFrame = now;
      elapsed += delta;
      pose(elapsed, delta);
      render();
    }
    raf = requestAnimationFrame(animate);
  };
  const syncMotion = () => {
    cancelAnimationFrame(raf);
    raf = 0;
    previousFrame = 0;
    if (disposed || !renderer) return;
    root.dataset.motion = document.hidden ? 'hidden' : motion.matches ? 'reduced' : mobile.matches ? 'mobile' : 'animated';
    if (!document.hidden && (motion.matches || mobile.matches)) {
      pointer.x = pointer.y = easedPointer.x = easedPointer.y = 0;
      elapsed = 8;
      pose(elapsed);
    }
    render();
    if (canAnimate()) raf = requestAnimationFrame(animate);
  };
  const onPointer = event => {
    const rect = visual.getBoundingClientRect();
    const visible = root.getBoundingClientRect();
    const inside = event.clientX >= Math.max(rect.left, visible.left) && event.clientX <= Math.min(rect.right, visible.right) && event.clientY >= Math.max(rect.top, visible.top) && event.clientY <= Math.min(rect.bottom, visible.bottom);
    pointer.x = inside ? Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1)) : 0;
    pointer.y = inside ? Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1)) : 0;
  };
  const resetPointer = () => { pointer.x = pointer.y = 0; };
  const onContextLost = event => {
    event.preventDefault();
    contextLost = true;
    root.dataset.sceneState = 'fallback';
    root.dataset.renderer = 'fallback';
    cancelAnimationFrame(raf);
    syncSelectionLabel();
  };
  const onContextRestored = () => {
    if (disposed) return;
    contextLost = false;
    root.dataset.sceneState = 'ready';
    root.dataset.renderer = 'three';
    syncMotion();
  };
  const resizeObserver = new ResizeObserver(resize);
  const paletteObserver = new MutationObserver(applyPalette);
  paletteObserver.observe(document.body, {attributes: true, attributeFilter: ['data-ps-color', 'data-ps-theme', 'data-scene-color']});
  resizeObserver.observe(visual);
  document.addEventListener('visibilitychange', syncMotion);
  document.addEventListener('pointermove', onPointer, {passive: true});
  document.addEventListener('pointerleave', resetPointer);
  window.addEventListener('blur', resetPointer);
  motion.addEventListener('change', syncMotion);
  mobile.addEventListener('change', syncMotion);

  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(raf);
    resizeObserver.disconnect();
    paletteObserver.disconnect();
    document.removeEventListener('visibilitychange', syncMotion);
    document.removeEventListener('pointermove', onPointer);
    document.removeEventListener('pointerleave', resetPointer);
    window.removeEventListener('blur', resetPointer);
    motion.removeEventListener('change', syncMotion);
    mobile.removeEventListener('change', syncMotion);
    renderer?.domElement.removeEventListener('webglcontextlost', onContextLost);
    renderer?.domElement.removeEventListener('webglcontextrestored', onContextRestored);
    const geometries = new Set(), materials = new Set();
    scene?.traverse(object => {
      if (object.geometry) geometries.add(object.geometry);
      if (object.material) for (const material of [].concat(object.material)) materials.add(material);
      object.shadow?.map?.dispose();
    });
    geometries.forEach(geometry => geometry.dispose());
    materials.forEach(material => material.dispose());
    environment?.dispose();
    renderer?.dispose();
    renderer?.forceContextLoss();
    root.remove();
    if (anchor.sceneDispose === dispose) delete anchor.sceneDispose;
    if (document.body.psLoginSceneDispose === dispose) delete document.body.psLoginSceneDispose;
  };
  anchor.sceneDispose = dispose;
  document.body.psLoginSceneDispose = dispose;

  (async () => {
    try {
      const THREE = await import(new URL('/app/static/vendor/three.module.min.js', location.origin).href);
      if (disposed || !root.isConnected) return;
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
      renderer = new THREE.WebGLRenderer({alpha: true, antialias: true, powerPreference: 'low-power'});
      renderer.setClearColor(0x000000, 0);
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.04;
      renderer.domElement.className = 'ps-login-canvas';
      renderer.domElement.setAttribute('aria-hidden', 'true');
      renderer.domElement.style.cssText = 'display:block;width:100%;height:100%;pointer-events:none';
      renderer.domElement.addEventListener('webglcontextlost', onContextLost);
      renderer.domElement.addEventListener('webglcontextrestored', onContextRestored);
      visual.append(renderer.domElement);

      // Broad studio reflections describe the curvature without external HDR assets.
      const studio = document.createElement('canvas');
      studio.width = 512;
      studio.height = 256;
      const context = studio.getContext('2d');
      const gradient = context.createLinearGradient(0, 0, studio.width, 0);
      for (const [stop, color] of [[0, '#343a3c'], [0.18, '#969b9d'], [0.27, '#fffef5'], [0.37, '#bdc4c6'], [0.55, '#4c5255'], [0.74, '#ced3d6'], [0.82, '#fffef7'], [1, '#454c50']]) gradient.addColorStop(stop, color);
      context.fillStyle = gradient;
      context.fillRect(0, 0, studio.width, studio.height);
      const texture = new THREE.CanvasTexture(studio);
      texture.mapping = THREE.EquirectangularReflectionMapping;
      texture.colorSpace = THREE.SRGBColorSpace;
      const pmrem = new THREE.PMREMGenerator(renderer);
      environment = pmrem.fromEquirectangular(texture);
      scene.environment = environment.texture;
      texture.dispose();
      pmrem.dispose();

      scene.add(new THREE.HemisphereLight('#f5f6ef', '#2e3934', 1.1));
      key = new THREE.DirectionalLight('#fffaf0', 3.3);
      key.position.set(-5, 9, 5);
      key.castShadow = true;
      key.shadow.mapSize.set(1024, 1024);
      Object.assign(key.shadow.camera, {left: -9, right: 9, top: 6, bottom: -6, near: 0.5, far: 35});
      key.shadow.normalBias = 0.03;
      key.shadow.bias = -0.0001;
      key.shadow.radius = 4;
      scene.add(key);
      const rim = new THREE.DirectionalLight('#e7f0f2', 2);
      rim.position.set(6, 3, -7);
      scene.add(rim);
      sculpture = new THREE.Group();
      sculpture.name = 'price-band-sculpture';
      scene.add(sculpture);
      projectedLabel = new THREE.Vector3();
      projectedSelection = new THREE.Vector3();
      const satin = {metalness: 0.35, roughness: 0.34, clearcoat: 0.45, clearcoatRoughness: 0.35, side: THREE.DoubleSide};
      accent = new THREE.MeshPhysicalMaterial(satin);
      selectedBase = new THREE.Color();
      tint = new THREE.MeshPhysicalMaterial(satin);
      porcelain = new THREE.MeshPhysicalMaterial({...satin, metalness: 0.18, roughness: 0.4});
      const specifications = [
        {width: 6.7, offset: -2.25, material: porcelain},
        {width: 8.3, offset: 1.25, material: tint},
        {width: 5.7, offset: -1.45, material: porcelain},
        {width: 7.8, offset: 1.8, material: accent},
        {width: 8.6, offset: -1.05, material: tint},
        {width: 6.2, offset: 0.85, material: porcelain},
      ];
      markerMaterial = new THREE.MeshBasicMaterial();
      referenceMaterial = new THREE.MeshBasicMaterial({transparent: true, opacity: 0.8});
      for (const [index, specification] of specifications.entries()) {
        const {width, offset, material} = specification;
        const geometry = new THREE.BoxGeometry(width, 0.42, 0.3, 64, 6, 6);
        const positions = geometry.attributes.position, normals = geometry.attributes.normal;
        const radius = 0.065, vector = new THREE.Vector3(), core = new THREE.Vector3();
        // Rounded sides and a shallow bow give each price interval a satin highlight.
        for (let i = 0; i < positions.count; i++) {
          vector.fromBufferAttribute(positions, i);
          core.set(Math.max(-width / 2 + radius, Math.min(width / 2 - radius, vector.x)), Math.max(-0.21 + radius, Math.min(0.21 - radius, vector.y)), Math.max(-0.15 + radius, Math.min(0.15 - radius, vector.z)));
          vector.sub(core).normalize();
          const normal = vector.clone();
          vector.multiplyScalar(radius).add(core);
          const slope = -0.06 * Math.PI / width * Math.sin(vector.x * Math.PI / width);
          vector.z += 0.06 * Math.cos(vector.x * Math.PI / width);
          normal.set(normal.x - slope * normal.z, normal.y, normal.z).normalize();
          positions.setXYZ(i, vector.x, vector.y, vector.z);
          normals.setXYZ(i, normal.x, normal.y, normal.z);
        }
        const mesh = new THREE.Mesh(geometry, material);
        mesh.name = `price-band-${index}`;
        mesh.castShadow = mesh.receiveShadow = true;
        sculpture.add(mesh);
        const marker = new THREE.Mesh(new THREE.BoxGeometry(0.032, 0.29, 0.016), markerMaterial);
        marker.name = `price-center-${index}`;
        sculpture.add(marker);
        bands.push({mesh, marker, offset, y: (2.5 - index) * 0.86, tilt: (index % 2 ? 1 : -1) * 0.035});
      }
      const reference = new THREE.Mesh(new THREE.BoxGeometry(0.013, 5.4, 0.013), referenceMaterial);
      reference.name = 'price-reference';
      reference.position.set(guideX, 0, 0.265);
      sculpture.add(reference);
      selectionPoint = new THREE.Group();
      selectionPoint.name = 'price-selection-point';
      selectionPoint.position.set(guideX, bands[3].y, 0.282);
      pointCoreMaterial = new THREE.MeshBasicMaterial({transparent: true, opacity: 0});
      pointCollarMaterial = new THREE.MeshBasicMaterial({transparent: true, opacity: 0});
      const pointCore = new THREE.Mesh(new THREE.CircleGeometry(0.06, 32), pointCoreMaterial);
      pointCore.name = 'price-selection-core';
      const pointCollar = new THREE.Mesh(new THREE.RingGeometry(0.062, 0.095, 32), pointCollarMaterial);
      pointCollar.name = 'price-selection-collar';
      selectionPoint.add(pointCore, pointCollar);
      sculpture.add(selectionPoint);
      root.dataset.sceneState = 'ready';
      root.dataset.renderer = 'three';
      pose(0);
      applyPalette();
      resize();
      syncMotion();
    } catch (_) {
      // A decorative GPU failure must never block the native login form.
      if (!disposed) {
        root.dataset.sceneState = 'fallback';
        root.dataset.renderer = 'fallback';
        renderer?.domElement.remove();
        environment?.dispose();
        environment = undefined;
        renderer?.dispose();
        renderer = undefined;
        syncSelectionLabel();
      }
    }
  })();
  return dispose;
}
