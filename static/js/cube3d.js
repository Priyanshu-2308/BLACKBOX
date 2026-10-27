/**
 * BLACKBOX ARENA — 3D MONOLITH CONTROLLER (Three.js r128)
 * Single shared WebGL renderer, matte black material, dynamic canvas texture,
 * cursor tilt, soft ripples, split-cube solve animation, library runway.
 */

(function(global) {
  'use strict';

  let container, canvas;
  let scene, camera, renderer;
  let activeMode = 'today'; // 'today', 'probe', 'library', 'solved'
  let prefersReducedMotion = false;

  // Single Cube Objects
  let cubeMesh = null;
  let shadowMesh = null;
  let frontCanvas, frontCtx, frontTexture;

  // Split Cube Objects (Solved Mode)
  let splitGroup = null;
  let splitLeftMesh = null;
  let splitRightMesh = null;

  // Library Runway Objects
  let runwayGroup = null;
  let runwayCubes = [];
  let targetRunwayX = 0;

  // Interaction State
  let mouseX = 0, mouseY = 0;
  let targetRotX = 0.35, targetRotY = 0.55;
  let currentRotX = 0.35, currentRotY = 0.55;
  let isHovered = false;

  // Ripple Animation State
  let rippleActive = false;
  let rippleRadius = 0;
  let rippleAlpha = 0;
  let latestOutputText = "OUT: 0x00";
  let latestStatusText = "STIMULUS: AWAITING PROBE";

  // Check WebGL support
  function isWebGLAvailable() {
    try {
      const c = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl')));
    } catch (e) {
      return false;
    }
  }

  function init(containerEl) {
    container = containerEl;
    if (!isWebGLAvailable() || typeof THREE === 'undefined') {
      console.warn('WebGL or Three.js unavailable, falling back to CSS Monolith.');
      container.innerHTML = '<div class="fallback-css-monolith"><div class="css-cube"></div></div>';
      return;
    }

    prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {
      prefersReducedMotion = e.matches;
    });

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // 1. Scene & Camera
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.5);

    // 2. Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = false; // Using custom contact shadow for performance & crispness
    canvas = renderer.domElement;
    canvas.id = 'monolith-three-canvas';
    container.appendChild(canvas);

    // 3. Lighting (Soft key light + Sharp rim light)
    const ambient = new THREE.AmbientLight(0xffffff, 0.45);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xffffff, 0.95);
    keyLight.position.set(5, 7, 6);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0xdce7f5, 0.85);
    rimLight.position.set(-6, -4, -6);
    scene.add(rimLight);

    // 4. Setup Dynamic Front Texture
    setupFrontCanvasTexture();

    // 5. Setup Meshes
    setupSingleCube();
    setupContactShadow();
    setupSplitCube();
    setupRunway();

    // 6. Event Listeners
    window.addEventListener('resize', onWindowResize);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('touchmove', onTouchMove, { passive: true });

    // 7. Start Render Loop
    requestAnimationFrame(renderLoop);
  }

  function setupFrontCanvasTexture() {
    frontCanvas = document.createElement('canvas');
    frontCanvas.width = 512;
    frontCanvas.height = 512;
    frontCtx = frontCanvas.getContext('2d');
    drawFrontFace(latestStatusText, latestOutputText, 0, 0);

    frontTexture = new THREE.CanvasTexture(frontCanvas);
    frontTexture.anisotropy = 4;
  }

  function drawFrontFace(statusText, outText, rRadius, rAlpha) {
    if (!frontCtx) return;
    const ctx = frontCtx;
    ctx.clearRect(0, 0, 512, 512);

    // Matte dark graphite ground
    ctx.fillStyle = '#141416';
    ctx.fillRect(0, 0, 512, 512);

    // Etched hairline caliper grid
    ctx.strokeStyle = 'rgba(228, 226, 228, 0.12)';
    ctx.lineWidth = 1;
    for (let y = 60; y < 460; y += 40) {
      ctx.beginPath();
      ctx.moveTo(40, y);
      ctx.lineTo(472, y);
      ctx.stroke();
    }
    for (let x = 60; x < 460; x += 60) {
      ctx.beginPath();
      ctx.moveTo(x, 40);
      ctx.lineTo(x, 472);
      ctx.stroke();
    }

    // Expanding soft ripple wave
    if (rRadius > 0 && rAlpha > 0) {
      ctx.save();
      ctx.strokeStyle = `rgba(255, 181, 158, ${rAlpha})`;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(256, 256, rRadius, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = `rgba(207, 224, 242, ${rAlpha * 0.5})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(256, 256, rRadius * 0.65, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    // Top Caliper Bar
    ctx.fillStyle = '#e4e2e4';
    ctx.fillRect(48, 60, 416, 2);

    // Status Line
    ctx.font = '700 16px "Space Mono", monospace';
    ctx.fillStyle = '#919094';
    ctx.letterSpacing = '2px';
    ctx.fillText(statusText.toUpperCase(), 48, 100);

    // Main Embossed Output in Center
    ctx.font = '700 32px "Space Mono", monospace';
    ctx.fillStyle = '#ffffff';
    // Clean truncate for canvas
    const displayOut = outText.length > 22 ? outText.substring(0, 20) + '...' : outText;
    ctx.fillText(displayOut, 48, 170);

    // Secondary Telemetry
    ctx.fillStyle = '#ffb59e';
    ctx.font = '700 18px "Space Mono", monospace';
    ctx.fillText('// LATENCY: 0.00018s', 48, 215);

    // Specular Catchline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(48, 235);
    ctx.lineTo(160, 235);
    ctx.stroke();

    // Bottom datum mark
    ctx.font = '700 13px "Space Mono", monospace';
    ctx.fillStyle = 'rgba(145, 144, 148, 0.8)';
    ctx.fillText('STIMULUS PROTOCOL SECURE', 48, 440);

    if (frontTexture) frontTexture.needsUpdate = true;
  }

  function setupSingleCube() {
    const geo = new THREE.BoxGeometry(2.35, 2.35, 2.35);

    // 6 Materials: Right, Left, Top, Bottom, Front, Back
    const matteDark = new THREE.MeshStandardMaterial({
      color: 0x141416,
      roughness: 0.82,
      metalness: 0.08
    });

    const frontMat = new THREE.MeshStandardMaterial({
      map: frontTexture,
      roughness: 0.75,
      metalness: 0.05
    });

    const materials = [
      matteDark, // +X
      matteDark, // -X
      new THREE.MeshStandardMaterial({ color: 0x1c1b1d, roughness: 0.8, metalness: 0.1 }), // +Y Top face
      new THREE.MeshStandardMaterial({ color: 0x0b0b0c, roughness: 0.9, metalness: 0.05 }), // -Y Bottom
      frontMat,  // +Z Front face (with dynamic canvas texture)
      matteDark  // -Z Back
    ];

    cubeMesh = new THREE.Mesh(geo, materials);
    cubeMesh.position.set(0, 0.15, 0);
    cubeMesh.rotation.set(0.35, 0.55, 0);
    scene.add(cubeMesh);
  }

  function setupContactShadow() {
    // Soft contact occlusion disk
    const shadowCanvas = document.createElement('canvas');
    shadowCanvas.width = 128;
    shadowCanvas.height = 128;
    const sCtx = shadowCanvas.getContext('2d');

    const grad = sCtx.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0.55)');
    grad.addColorStop(0.4, 'rgba(0, 0, 0, 0.25)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    sCtx.fillStyle = grad;
    sCtx.fillRect(0, 0, 128, 128);

    const sTex = new THREE.CanvasTexture(shadowCanvas);
    const sGeo = new THREE.PlaneGeometry(3.6, 3.6);
    const sMat = new THREE.MeshBasicMaterial({
      map: sTex,
      transparent: true,
      depthWrite: false
    });

    shadowMesh = new THREE.Mesh(sGeo, sMat);
    shadowMesh.rotation.x = -Math.PI / 2;
    shadowMesh.position.set(0, -1.6, 0);
    scene.add(shadowMesh);
  }

  function setupSplitCube() {
    splitGroup = new THREE.Group();
    splitGroup.visible = false;

    const halfGeoLeft = new THREE.BoxGeometry(1.15, 2.35, 2.35);
    const halfGeoRight = new THREE.BoxGeometry(1.15, 2.35, 2.35);

    const outerMat = new THREE.MeshStandardMaterial({ color: 0x141416, roughness: 0.85, metalness: 0.08 });
    const innerVoidMat = new THREE.MeshBasicMaterial({ color: 0x0E0E10 });

    splitLeftMesh = new THREE.Mesh(halfGeoLeft, [innerVoidMat, outerMat, outerMat, outerMat, outerMat, outerMat]);
    splitRightMesh = new THREE.Mesh(halfGeoRight, [outerMat, innerVoidMat, outerMat, outerMat, outerMat, outerMat]);

    splitLeftMesh.position.set(-0.6, 0, 0);
    splitRightMesh.position.set(0.6, 0, 0);

    splitGroup.add(splitLeftMesh);
    splitGroup.add(splitRightMesh);
    splitGroup.rotation.set(0.35, 0.55, 0);
    scene.add(splitGroup);
  }

  function setupRunway() {
    runwayGroup = new THREE.Group();
    runwayGroup.visible = false;
    runwayCubes = [];

    const cubeGeo = new THREE.BoxGeometry(1.6, 1.6, 1.6);
    const mat = new THREE.MeshStandardMaterial({ color: 0x161618, roughness: 0.82, metalness: 0.08 });

    // 5 runway display cubes spaced along X
    for (let i = 0; i < 5; i++) {
      const c = new THREE.Mesh(cubeGeo, mat);
      c.position.set((i - 2) * 2.8, 0, 0);
      c.rotation.set(0.3 + (i * 0.05), 0.4 + (i * 0.15), 0);
      runwayGroup.add(c);
      runwayCubes.push(c);
    }

    scene.add(runwayGroup);
  }

  function setSceneMode(mode, data) {
    activeMode = mode;

    if (mode === 'solved') {
      if (cubeMesh) cubeMesh.visible = false;
      if (runwayGroup) runwayGroup.visible = false;
      if (splitGroup) {
        splitGroup.visible = true;
        // Reset and trigger split separation
        splitLeftMesh.position.set(-0.58, 0, 0);
        splitRightMesh.position.set(0.58, 0, 0);
      }
      if (shadowMesh) shadowMesh.visible = true;
    } else if (mode === 'library') {
      if (cubeMesh) cubeMesh.visible = false;
      if (splitGroup) splitGroup.visible = false;
      if (runwayGroup) runwayGroup.visible = true;
      if (shadowMesh) shadowMesh.visible = false;
    } else {
      // today or probe
      if (splitGroup) splitGroup.visible = false;
      if (runwayGroup) runwayGroup.visible = false;
      if (cubeMesh) cubeMesh.visible = true;
      if (shadowMesh) shadowMesh.visible = true;

      if (data && data.output) {
        latestOutputText = `OUT: ${JSON.stringify(data.output)}`;
        latestStatusText = `PROBE CHARGE: ${data.queries_used || 0}/30`;
        drawFrontFace(latestStatusText, latestOutputText, 0, 0);
      }
    }
  }

  function triggerRipple(outputValue) {
    latestOutputText = `OUT: ${JSON.stringify(outputValue)}`;
    latestStatusText = "TRANSMISSION VERIFIED";
    rippleActive = true;
    rippleRadius = 10;
    rippleAlpha = 1.0;
  }

  function cycleRunway(direction) {
    targetRunwayX += direction * -2.8;
  }

  function onMouseMove(e) {
    if (prefersReducedMotion) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    mouseX = (e.clientX / w) - 0.5;
    mouseY = (e.clientY / h) - 0.5;
    targetRotY = 0.55 + (mouseX * 0.5);
    targetRotX = 0.35 + (mouseY * -0.5);
    isHovered = true;
  }

  function onTouchMove(e) {
    if (prefersReducedMotion || !e.touches.length) return;
    const t = e.touches[0];
    const w = window.innerWidth;
    const h = window.innerHeight;
    mouseX = (t.clientX / w) - 0.5;
    mouseY = (t.clientY / h) - 0.5;
    targetRotY = 0.55 + (mouseX * 0.4);
    targetRotX = 0.35 + (mouseY * -0.4);
  }

  function onWindowResize() {
    if (!container || !renderer || !camera) return;
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  function renderLoop(time) {
    requestAnimationFrame(renderLoop);

    // Ripple expansion
    if (rippleActive) {
      rippleRadius += 6;
      rippleAlpha -= 0.025;
      if (rippleAlpha <= 0) {
        rippleActive = false;
        rippleRadius = 0;
        rippleAlpha = 0;
      }
      drawFrontFace(latestStatusText, latestOutputText, rippleRadius, rippleAlpha);
    }

    // Animation & Tilts
    if (!prefersReducedMotion) {
      // Gentle touch drift when idle
      const driftY = Math.sin(time * 0.001) * 0.05;
      const driftX = Math.cos(time * 0.0012) * 0.04;

      currentRotY += (targetRotY + driftY - currentRotY) * 0.08;
      currentRotX += (targetRotX + driftX - currentRotX) * 0.08;

      if (cubeMesh && cubeMesh.visible) {
        cubeMesh.rotation.y = currentRotY;
        cubeMesh.rotation.x = currentRotX;
      }

      if (splitGroup && splitGroup.visible) {
        splitGroup.rotation.y = currentRotY;
        splitGroup.rotation.x = currentRotX;

        // Smooth split separation animation along diagonal seam
        if (splitLeftMesh.position.x > -1.1) {
          splitLeftMesh.position.x -= 0.015;
          splitLeftMesh.position.y -= 0.008;
        }
        if (splitRightMesh.position.x < 1.1) {
          splitRightMesh.position.x += 0.015;
          splitRightMesh.position.y += 0.008;
        }
      }

      if (runwayGroup && runwayGroup.visible) {
        runwayGroup.position.x += (targetRunwayX - runwayGroup.position.x) * 0.1;
        runwayCubes.forEach((c, idx) => {
          c.rotation.y += 0.004 * (idx % 2 === 0 ? 1 : -1);
        });
      }
    }

    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  // Export public API
  global.Monolith3D = {
    init,
    setSceneMode,
    triggerRipple,
    cycleRunway,
    drawFrontFace
  };

})(window);
