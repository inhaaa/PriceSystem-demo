"""Reviewed presentation-only helpers; no business or authentication dependencies."""

import json
from html import escape
import re


def page_header_html(title: object, description: object, eyebrow: object) -> str:
    """Build an escaped semantic page heading."""

    return (
        '<header class="page-header">'
        '<div class="page-header__body">'
        f'<div class="page-header__eyebrow">{escape(str(eyebrow))}</div>'
        f'<h1 class="page-header__title">{escape(str(title))}</h1>'
        f'<p class="page-header__description">{escape(str(description))}</p>'
        "</div>"
        "</header>"
    )


def sidebar_brand_html() -> str:
    """Build the static PriceSystem demo sidebar identity."""

    return (
        '<div class="sidebar-brand">'
        '<img class="sidebar-brand__mark" src="/app/static/login-diamond-mini.svg" '
        'width="43" height="43" alt="" aria-hidden="true" decoding="async">'
        '<div class="sidebar-brand__copy">'
        '<div class="sidebar-brand__name" style="font-size:1.15rem;letter-spacing:.02em">PriceSystem</div>'
        '<div class="sidebar-brand__tagline">입찰가격 분석 <span class="demo-badge">DEMO</span></div>'
        "</div>"
        "</div>"
    )


def login_panel_html(wordmark: object, tagline: object, phrase: object) -> str:
    """Build a masthead and an in-flow diamond stage above the sign-in form."""

    particles = "".join(
        '<span class="login-atmosphere__particle" '
        f'style="--x:{(i * 37 + 7) % 100}%;--y:{(i * 29 + 11) % 100}%;'
        f'--delay:{-i * 1.7}s;--duration:{18 + i % 7 * 3}s;'
        f'--size:{1 + i % 3}px"></span>'
        for i in range(18)
    )
    return (
        '<div class="login-atmosphere" hidden aria-hidden="true">'
        '<img class="login-atmosphere__architecture" src="/app/static/diamond-chamber.svg" '
        'alt="" draggable="false" decoding="async"/>'
        '<div class="login-atmosphere__light"></div>'
        f'<div class="login-atmosphere__field">{particles}</div>'
        '<span class="login-panel__cursor"></span>'
        '</div>'
        '<header class="login-masthead">'
        '<div class="login-panel__identity">'
        '<svg class="login-panel__symbol" width="21" height="21" '
        'viewBox="0 0 32 32" aria-hidden="true">'
        '<path d="M7 6h18l6 9-15 17L1 15Z M1 15h30 M7 6l9 26L25 6 M7 6l9 9 9-9" '
        'fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>'
        '</svg>'
        f'<p class="login-panel__wordmark">{escape(str(wordmark))}</p>'
        '</div>'
        f'<p class="login-panel__tagline">{escape(str(tagline))}</p>'
        '</header>'
        '<section class="login-panel" aria-label="회전하는 다이아몬드">'
        '<span class="login-panel__axis" aria-hidden="true"></span>'
        '<span class="login-panel__halo" aria-hidden="true"></span>'
        '<div class="login-gem" hidden aria-hidden="true">'
        '<div class="login-gem__stage"><div class="login-gem__spin">'
        '<div class="login-gem__crown"><i></i><i></i><i></i><i></i></div>'
        '<div class="login-gem__pavilion"><i></i><i></i><i></i><i></i></div>'
        '</div></div></div>'
        '<div class="login-panel__caption">'
        '<p class="login-panel__interaction">'
        '<span aria-hidden="true">↔</span> 드래그하여 다른 각도로 바라보세요</p>'
        '</div>'
        '</section>'
    )


def _material_icon_name(icon: object) -> str:
    """Return a safe Material Symbols icon name from Streamlit icon syntax."""

    match = re.fullmatch(r":material/([A-Za-z0-9_]+):", str(icon or ""))
    return match.group(1) if match else "arrow_forward"


def home_action_card_html(
    title: object,
    description: object,
    icon: object,
    featured: bool = False,
) -> str:
    """Build an escaped display-only action card."""

    content_class = "home-action-card__content"
    if featured:
        content_class += " home-action-card__content--featured"
    return (
        '<article class="home-action-card">'
        f'<div class="{content_class}">'
        f'<span class="material-symbols-rounded" aria-hidden="true">{_material_icon_name(icon)}</span>'
        f'<h3 class="home-action-card__title">{escape(str(title))}</h3>'
        f'<p class="home-action-card__description">{escape(str(description))}</p>'
        "</div>"
        "</article>"
    )


def login_cursor_glow_script() -> str:
    """Mount viewport-wide, input-safe water and crystal interactions."""

    return """
<script type="module">
(async () => {
  const KEY = "__psLoginPanelGlow";
  if (typeof window[KEY] === "function") window[KEY]();
  let disposed = false;
  let detach = null;
  let observer = null;
  let timeout = 0;
  const cleanup = () => {
    disposed = true;
    if (detach) detach();
    if (observer) observer.disconnect();
    clearTimeout(timeout);
  };
  window[KEY] = cleanup;
  let mountLoginAtmosphere;
  try {
    ({ mountLoginAtmosphere } = await import("/app/static/login-atmosphere.js?v=2"));
  } catch (error) {
    cleanup();
    return;
  }
  if (disposed) return;
  const attach = () => {
    const panel = document.querySelector(".login-panel");
    const layer = document.querySelector(".login-atmosphere");
    const root = panel && panel.closest('[data-testid="stAppViewContainer"]');
    if (!root || !layer) return false;
    detach = mountLoginAtmosphere({ root, panel, layer });
    return true;
  };
  if (attach()) return;
  observer = new MutationObserver(() => {
    if (!disposed && attach()) {
      observer.disconnect();
      clearTimeout(timeout);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  timeout = setTimeout(cleanup, 8000);
})();
</script>
"""


def login_gem_webgl_script(
    module_url: str = "/app/static/vendor/three.module.min.js",
) -> str:
    """Upgrade the login panel gem to a refracting WebGL diamond when possible.

    The legacy CSS gem remains hidden, including during loading. The static
    facet background preserves the scene when WebGL is unavailable or motion
    is reduced. Animation pauses outside the viewport, and narrow screens use
    a smaller render budget.
    """

    source = json.dumps(str(module_url), ensure_ascii=False).translate(
        {
            ord("<"): r"\u003c",
            ord(">"): r"\u003e",
            ord("&"): r"\u0026",
            0x2028: r"\u2028",
            0x2029: r"\u2029",
        }
    )
    return """
<script type="module">
(async () => {
  const KEY = "__psLoginGem";
  if (typeof window[KEY] === "function") {
    window[KEY]();
    window[KEY] = null;
  }
  const mark = (state) => {
    window.__psLoginGemState = state;
  };
  mark("start");
  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const mobileQuery = window.matchMedia("(max-width: 768px)");
  if (motionQuery.matches) {
    mark("skip:reduced-motion");
    return;
  }
  // Claim ownership before awaiting DOM/modules so a rerun can cancel this mount.
  let disposed = false;
  let cancelPanelWait = () => {};
  let releaseScene = () => {};
  const cleanup = () => {
    if (disposed) return;
    disposed = true;
    cancelPanelWait();
    releaseScene();
    if (window[KEY] === cleanup) window[KEY] = null;
  };
  window[KEY] = cleanup;

  // type="module" 은 defer 실행이라 Streamlit 이 패널을 마운트하기 전에 돈다.
  const waitForPanel = () =>
    new Promise((resolve) => {
      const existing = document.querySelector(".login-panel");
      if (existing) {
        resolve(existing);
        return;
      }
      let timeout = 0;
      const finish = (found) => {
        observer.disconnect();
        clearTimeout(timeout);
        cancelPanelWait = () => {};
        resolve(found);
      };
      const observer = new MutationObserver(() => {
        const found = document.querySelector(".login-panel");
        if (found) finish(found);
      });
      observer.observe(document.body, { childList: true, subtree: true });
      cancelPanelWait = () => finish(null);
      timeout = setTimeout(() => finish(null), 10000);
    });

  const panel = await waitForPanel();
  if (disposed) return;
  if (!panel) {
    cleanup();
    mark("skip:no-panel");
    return;
  }
  if (panel.querySelector(".login-panel__canvas")) {
    cleanup();
    mark("skip:already-mounted");
    return;
  }
  mark("panel-ready");
  // Streamlit can replace the stylesheet before pruning stale scene nodes.
  const sceneIsAttached = () => panel.isConnected &&
    window.getComputedStyle(panel).getPropertyValue("--ps-login-scene").trim() === "1";

  let THREE;
  let createDiamondOptics;
  try {
    [THREE, { createDiamondOptics }] = await Promise.all([
      import(__MODULE_URL__),
      import("/app/static/diamond-optics.js?v=1"),
    ]);
  } catch (error) {
    if (disposed) return;
    cleanup();
    mark("fail:import " + String(error).slice(0, 120));
    return;
  }
  if (disposed) return;
  if (!sceneIsAttached()) {
    cleanup();
    return;
  }
  mark("three-loaded");

  const canvas = document.createElement("canvas");
  canvas.className = "login-panel__canvas";
  canvas.setAttribute("aria-hidden", "true");

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
    });
  } catch (error) {
    cleanup();
    mark("fail:webgl " + String(error).slice(0, 120));
    return;
  }

  const size = () => ({
    width: Math.max(panel.clientWidth, 1),
    height: Math.max(panel.clientHeight, 1),
  });
  let view = size();
  let mobile = mobileQuery.matches;
  const pixelRatio = () => Math.min(window.devicePixelRatio || 1,
    mobile ? 1 : 1.5);
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(view.width, view.height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  // 노출을 올리면 더 많은 패싯이 ACES 숄더를 넘어 흰색으로 클리핑된다.
  // 배경도 같이 밝아지므로 backgroundIntensity 로 정확히 상쇄한다.
  // 둘 다 톤매핑 전 선형 배수라 곱(EXPOSURE * BG_INTENSITY = 1.45)이 같으면
  // 판 밝기는 이전과 수학적으로 동일하다.
  const EXPOSURE = 3.8;
  const PANEL_GAIN = 1.45;
  renderer.toneMappingExposure = EXPOSURE;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    30,
    view.width / view.height,
    0.1,
    100
  );
  camera.position.set(0, 0.7, 4.9);
  camera.lookAt(0, -0.05, 0);
  let cameraScroll = 0;
  let baseZoom = 1;
  const updateScrollCamera = (delta) => {
    const scroll = Number(window.__psLoginScene?.scroll);
    const wanted = Number.isFinite(scroll) ? Math.max(0, Math.min(1, scroll)) : 0;
    if (mobile || motionQuery.matches) cameraScroll = 0;
    else cameraScroll += (wanted - cameraScroll) * (1 - Math.exp(-delta * 3));
    camera.zoom = baseZoom * (1 + cameraScroll * 0.035);
    camera.position.set(0, 0.7 + cameraScroll * 0.045, 4.9 - cameraScroll * 0.04);
    camera.lookAt(0, -0.05, 0);
    camera.updateProjectionMatrix();
  };
  // Keep the same optical material, fitting its presentation to a compact stage.
  const fitCamera = () => {
    camera.aspect = view.width / view.height;
    baseZoom = Math.min(1.8, camera.aspect * 1.7);
    updateScrollCamera(0);
  };
  fitCamera();

  // 굴절할 실체가 되는 배경. 판의 CSS 그라디언트와 같은 톤으로 맞춰 이음선을 없앤다.
  const bgCanvas = document.createElement("canvas");
  bgCanvas.width = 512;
  bgCanvas.height = 1024;
  const bg = bgCanvas.getContext("2d");
  const base = bg.createLinearGradient(0, 0, 512, 1024);
  base.addColorStop(0, "#111315");
  base.addColorStop(0.46, "#0b0d0f");
  base.addColorStop(1, "#08090a");
  bg.fillStyle = base;
  bg.fillRect(0, 0, 512, 1024);
  const wash = (x, y, radius, color) => {
    const gradient = bg.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, color);
    gradient.addColorStop(1, "rgba(0,0,0,0)");
    bg.fillStyle = gradient;
    bg.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  };
  wash(60, -40, 420, "rgba(230,232,234,0.025)");
  wash(500, 1080, 360, "rgba(192,196,200,0.018)");
  // Optical lighting lives inside the gem's studio map, not in the visible panel.
  const bgTexture = new THREE.CanvasTexture(bgCanvas);
  bgTexture.colorSpace = THREE.SRGBColorSpace;
  scene.background = bgTexture;
  scene.backgroundIntensity = PANEL_GAIN / EXPOSURE;

  // Canvas2D 는 #ffffff 를 넘을 수 없어 환경맵 전체가 linear 1.0 으로 클램프된다.
  // 흰 종이와 같은 값이라 아무리 증폭해도 "밝은 평면"이 될 뿐이다(= 우유).
  // half-float 로 코어를 25~60 linear 로 넣으면 catching/non-catching 패싯 비가
  // 10000:1 이 되고 ACES 가 그걸 선명한 명암 분할로 압축한다.
  const EW = 1024;
  const EH = 512;
  const GROUND = 0.002;
  const half = THREE.DataUtils.toHalfFloat;
  const envData = new Uint16Array(EW * EH * 4);
  const groundHalf = half(GROUND);
  const oneHalf = half(1);
  for (let i = 0; i < EW * EH; i += 1) {
    envData[i * 4] = groundHalf;
    envData[i * 4 + 1] = groundHalf;
    envData[i * 4 + 2] = groundHalf;
    envData[i * 4 + 3] = oneHalf;
  }
  // 작고 거의 하드엣지인 코어. 넓고 부드러우면 모든 패싯이 항상 조금씩 밝아
  // 반짝임이 아니라 헤이즈로 읽힌다.
  const core = (u, v, radius, peak, tr, tg, tb) => {
    const cx = u * EW;
    const cy = v * EH;
    const plateau = radius * 0.45;
    const top = Math.max(0, Math.floor(cy - radius));
    const bottom = Math.min(EH, Math.ceil(cy + radius));
    for (let y = top; y < bottom; y += 1) {
      for (let x = Math.floor(cx - radius); x < Math.ceil(cx + radius); x += 1) {
        const dx = x - cx;
        const dy = y - cy;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d > radius) continue;
        let k = d <= plateau ? 1 : 1 - (d - plateau) / (radius - plateau);
        k *= k;
        const xi = ((x % EW) + EW) % EW;
        const o = (y * EW + xi) * 4;
        envData[o] = half(GROUND + peak * k * tr);
        envData[o + 1] = half(GROUND + peak * k * tg);
        envData[o + 2] = half(GROUND + peak * k * tb);
      }
    }
  };
  // 이웃 패싯이 전혀 다른 값을 잡아야 사진 같은 모자이크가 된다. 그래서 코어
  // 개수를 늘려 공간 주파수를 올린다. 반경은 9~24px 로 작게 유지한다 — 넓히면
  // 모든 패싯이 항상 조금씩 밝아져 대비가 아니라 헤이즈가 된다. 지면은 0.002 로
  // 두므로 거부됐던 라이트 추가와 달리 바닥이 올라가지 않는다.
  // roughness 0 이라 젬은 PMREM mip 0 을 타서 이 디테일이 그대로 보인다.
  const CORES = [
    [0.06, 0.18, 24, 56, 1, 1, 1],
    [0.13, 0.29, 11, 34, 0.92, 0.96, 1],
    [0.19, 0.11, 15, 44, 1, 1, 1],
    [0.25, 0.36, 9, 26, 0.86, 0.93, 1],
    [0.31, 0.2, 18, 50, 1, 1, 1],
    [0.37, 0.08, 10, 30, 1, 0.97, 0.9],
    [0.43, 0.31, 13, 36, 1, 0.98, 0.94],
    [0.49, 0.16, 9, 24, 0.9, 0.95, 1],
    [0.54, 0.27, 16, 46, 0.95, 0.98, 1],
    [0.6, 0.06, 11, 28, 1, 0.94, 0.88],
    [0.66, 0.34, 14, 38, 1, 1, 1],
    [0.71, 0.19, 9, 22, 0.88, 0.94, 1],
    [0.78, 0.1, 20, 52, 1, 1, 1],
    [0.84, 0.3, 12, 32, 0.9, 0.95, 1],
    [0.9, 0.22, 15, 40, 1, 0.97, 0.92],
    [0.96, 0.35, 10, 26, 0.93, 0.96, 1],
    [0.04, 0.47, 12, 24, 0.85, 0.92, 1],
    [0.16, 0.58, 16, 32, 0.9, 0.95, 1],
    [0.27, 0.5, 9, 20, 1, 0.96, 0.9],
    [0.37, 0.66, 14, 27, 1, 0.95, 0.9],
    [0.47, 0.54, 10, 22, 0.92, 0.96, 1],
    [0.57, 0.63, 13, 25, 1, 1, 1],
    [0.67, 0.49, 9, 19, 0.88, 0.94, 1],
    [0.76, 0.6, 15, 30, 0.93, 0.96, 1],
    [0.86, 0.52, 10, 21, 1, 0.93, 0.86],
    [0.94, 0.64, 12, 24, 0.9, 0.95, 1],
    [0.1, 0.76, 11, 20, 0.86, 0.92, 1],
    [0.29, 0.82, 14, 23, 0.88, 0.93, 1],
    [0.44, 0.74, 9, 17, 1, 0.96, 0.92],
    [0.58, 0.86, 13, 21, 0.9, 0.95, 1],
    [0.72, 0.77, 10, 18, 1, 0.94, 0.88],
    [0.88, 0.84, 12, 20, 0.92, 0.96, 1],
  ];
  for (let i = 0; i < CORES.length; i += 1) {
    const spec = CORES[i];
    core(spec[0], spec[1], spec[2], spec[3], spec[4], spec[5], spec[6]);
  }

  const envTexture = new THREE.DataTexture(
    envData,
    EW,
    EH,
    THREE.RGBAFormat,
    THREE.HalfFloatType
  );
  envTexture.mapping = THREE.EquirectangularReflectionMapping;
  envTexture.colorSpace = THREE.LinearSRGBColorSpace;
  envTexture.needsUpdate = true;
  let pmrem;
  let environmentTarget;
  try {
    pmrem = new THREE.PMREMGenerator(renderer);
    environmentTarget = pmrem.fromEquirectangular(envTexture);
  } catch (error) {
    // The scene disposer is not installed until initialization has completed.
    bgTexture.dispose();
    renderer.dispose();
    if (renderer.forceContextLoss) renderer.forceContextLoss();
    cleanup();
    mark("fail:environment " + String(error).slice(0, 120));
    return;
  } finally {
    if (pmrem) pmrem.dispose();
    envTexture.dispose();
  }
  const environment = environmentTarget.texture;
  scene.environment = environment;

  // transmission 은 diffuse 만 mix 한다. totalSpecular 와 clearcoat 는 그 뒤에
  // 더해지므로 punctual light 스페큘러는 transmission=1 에서도 온전히 남는다.
  // 광원은 배경 픽셀에 아무 영향이 없다 — 젬만 밝아진다.
  const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
  keyLight.position.set(2.2, 3.4, 2.6);
  const coolLight = new THREE.DirectionalLight(0xcfe0ff, 1.7);
  coolLight.position.set(-2.6, 1.2, 1.8);
  const rimLight = new THREE.DirectionalLight(0xffe6c2, 2.4);
  rimLight.position.set(-1.4, -0.8, -3);
  scene.add(keyLight, coolLight, rimLight);
  const LIGHTS = [
    [keyLight, 3.2],
    [coolLight, 1.7],
    [rimLight, 2.4],
  ];

  // ---- 표준 라운드 브릴리언트 57면 ----
  // 8회 대칭. 비율은 girdle 반경 1 기준 표준값.
  const R_TABLE = 0.53;
  const H_CROWN = 0.324;
  const R_STAR = 0.8;
  const Y_STAR = 0.152;
  const Y_GIRDLE = 0.016;
  const R_LOWER = 0.24;
  const Y_LOWER = -0.665;
  const Y_CULET = -0.862;

  // Eightfold brilliant boundary; non-planar quads retain their triangle facets.
  const buildBrilliant = (N) => {
  const at = (radius, y, turns) => {
    const angle = turns * Math.PI * 2;
    return new THREE.Vector3(
      Math.cos(angle) * radius,
      y,
      Math.sin(angle) * radius
    );
  };
  const T = [];
  const S = [];
  const MU = [];
  const ML = [];
  const VU = [];
  const VL = [];
  const LG = [];
  for (let k = 0; k < N; k += 1) {
    const main = k / N;
    const mid = (k + 0.5) / N;
    T.push(at(R_TABLE, H_CROWN, main));
    S.push(at(R_STAR, Y_STAR, mid));
    MU.push(at(1, Y_GIRDLE, main));
    ML.push(at(1, -Y_GIRDLE, main));
    VU.push(at(1, Y_GIRDLE, mid));
    VL.push(at(1, -Y_GIRDLE, mid));
    LG.push(at(R_LOWER, Y_LOWER, mid));
  }
  const tableCenter = new THREE.Vector3(0, H_CROWN, 0);
  const culet = new THREE.Vector3(0, Y_CULET, 0);

  const positions = [];
  const emit = (a, b, c) => {
    positions.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
  };
  // 원점이 입체 내부에 있으므로 무게중심·법선 내적으로 바깥 방향을 판정한다.
  const face = (a, b, c) => {
    const ux = b.x - a.x;
    const uy = b.y - a.y;
    const uz = b.z - a.z;
    const vx = c.x - a.x;
    const vy = c.y - a.y;
    const vz = c.z - a.z;
    const nx = uy * vz - uz * vy;
    const ny = uz * vx - ux * vz;
    const nz = ux * vy - uy * vx;
    const cx = (a.x + b.x + c.x) / 3;
    const cy = (a.y + b.y + c.y) / 3;
    const cz = (a.z + b.z + c.z) / 3;
    if (nx * cx + ny * cy + nz * cz < 0) {
      emit(a, c, b);
    } else {
      emit(a, b, c);
    }
  };
  const quad = (a, b, c, d) => {
    face(a, b, c);
    face(a, c, d);
  };

  for (let k = 0; k < N; k += 1) {
    const n = (k + 1) % N;
    const p = (k + N - 1) % N;

    // 테이블 (1면) — 팔각형 팬
    face(tableCenter, T[k], T[n]);
    // 스타 (8면)
    face(T[k], T[n], S[k]);
    // 베젤/카이트 (8면)
    quad(T[k], S[k], MU[k], S[p]);
    // 어퍼거들 (16면)
    face(S[k], MU[k], VU[k]);
    face(S[k], VU[k], MU[n]);
    // 거들 밴드 — 57면에는 안 들어가지만 사진의 밝은 거들 선을 만든다
    quad(MU[k], VU[k], VL[k], ML[k]);
    quad(VU[k], MU[n], ML[n], VL[k]);
    // 파빌리온 메인 (8면)
    quad(ML[k], LG[k], culet, LG[p]);
    // 로워거들 (16면)
    face(LG[k], ML[k], VL[k]);
    face(LG[k], VL[k], ML[n]);
  }

  const built = new THREE.BufferGeometry();
  built.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3)
  );
  built.computeVertexNormals();
  return built;
  };

  const geometry = buildBrilliant(8);
  // Match each rasterized facet with the same boundary used for internal rays.
  const optics = createDiamondOptics(THREE, geometry);
  const material = optics.material;
  const GEM_SCALE = 0.64;
  const gem = new THREE.Mesh(geometry, material);
  gem.scale.setScalar(GEM_SCALE);
  scene.add(gem);

  // ---- 바닥 ----
  // 큘릿은 geometry y=-1.02 → world -1.02*0.48 = -0.49. 그게 접촉점이다.
  const FLOOR_Y = Y_CULET * GEM_SCALE;

  // (a) 반사. transmission 0 + 판 남색이라 몸체는 배경에 묻히고 글린트만 남는다.
  //     roughness 0.26 이 더 흐린 PMREM mip 을 타서 반사 블러를 공짜로 준다.
  const mirrorMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x0a1122,
    metalness: 0,
    roughness: 0.62,
    transmission: 0,
    envMapIntensity: 1.4,
    flatShading: true,
    side: THREE.BackSide,
    transparent: true,
    opacity: 0.018,
    depthWrite: false,
  });
  const mirror = new THREE.Mesh(geometry, mirrorMaterial);
  const MIRROR_SQUASH = 0.58;
  mirror.scale.set(GEM_SCALE, -GEM_SCALE * MIRROR_SQUASH, GEM_SCALE);
  const MIRROR_Y = FLOOR_Y + Y_CULET * GEM_SCALE * MIRROR_SQUASH;
  scene.add(mirror);

  // (b) 접촉 그림자. 렌즈라서 가운데가 오히려 밝다 — destination-out 으로 구멍을 뚫는다.
  const shadowCanvas = document.createElement("canvas");
  shadowCanvas.width = 256;
  shadowCanvas.height = 256;
  const sh = shadowCanvas.getContext("2d");
  sh.clearRect(0, 0, 256, 256);
  sh.save();
  sh.translate(128, 138);
  sh.scale(1, 0.72);
  const shadowGrad = sh.createRadialGradient(0, 0, 0, 0, 0, 120);
  shadowGrad.addColorStop(0, "rgba(4,7,18,0.62)");
  shadowGrad.addColorStop(0.45, "rgba(4,7,18,0.3)");
  shadowGrad.addColorStop(1, "rgba(4,7,18,0)");
  sh.fillStyle = shadowGrad;
  sh.beginPath();
  sh.arc(0, 0, 120, 0, Math.PI * 2);
  sh.fill();
  sh.restore();
  sh.globalCompositeOperation = "destination-out";
  const holeGrad = sh.createRadialGradient(128, 134, 0, 128, 134, 34);
  holeGrad.addColorStop(0, "rgba(0,0,0,0.55)");
  holeGrad.addColorStop(1, "rgba(0,0,0,0)");
  sh.fillStyle = holeGrad;
  sh.fillRect(94, 100, 68, 68);
  sh.globalCompositeOperation = "source-over";
  const shadowTexture = new THREE.CanvasTexture(shadowCanvas);
  shadowTexture.colorSpace = THREE.SRGBColorSpace;
  const shadowPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(1.5, 1.5),
    new THREE.MeshBasicMaterial({
      map: shadowTexture,
      transparent: true,
      depthWrite: false,
      toneMapped: false,
    })
  );
  // 카메라 하강각이 10.5° 뿐이라 수평 쿼드는 화면에서 선이 된다.
  // 사진들처럼 "바로 아래로 눌린" 형태가 되도록 카메라 정면 빌보드로 둔다.
  shadowPlane.position.set(0, FLOOR_Y - 0.055, -0.02);
  shadowPlane.scale.set(1, 0.26, 1);
  shadowPlane.renderOrder = 1;
  scene.add(shadowPlane);

  // (c) 코스틱 스플래시. 가산이라 검정은 무시된다 → 알파 마스크 불필요.
  //     발자국을 젬 지름의 1.6배 안으로 묶는다. 넘으면 거부됐던 스포트라이트가 된다.
  const causticCanvas = document.createElement("canvas");
  causticCanvas.width = 512;
  causticCanvas.height = 512;
  const cs = causticCanvas.getContext("2d");
  cs.fillStyle = "#000000";
  cs.fillRect(0, 0, 512, 512);
  const causticCore = cs.createRadialGradient(256, 256, 0, 256, 256, 52);
  causticCore.addColorStop(0, "rgba(255,255,255,0.95)");
  causticCore.addColorStop(1, "rgba(0,0,0,0)");
  cs.fillStyle = causticCore;
  cs.fillRect(204, 204, 104, 104);
  const SPOKES = [
    [0.0, 150, 0.42, "255,255,255"],
    [0.55, 116, 0.3, "127,228,255"],
    [1.15, 136, 0.34, "255,255,255"],
    [1.75, 102, 0.26, "255,208,138"],
    [2.35, 128, 0.32, "255,255,255"],
    [2.95, 110, 0.24, "255,155,224"],
    [3.55, 140, 0.34, "255,255,255"],
    [4.15, 106, 0.25, "127,228,255"],
    [4.75, 122, 0.3, "255,255,255"],
    [5.35, 112, 0.26, "255,208,138"],
  ];
  for (let i = 0; i < SPOKES.length; i += 1) {
    const s = SPOKES[i];
    cs.save();
    cs.translate(256, 256);
    cs.rotate(s[0]);
    cs.scale(1, 0.085);
    const spoke = cs.createRadialGradient(0, 0, 0, 0, 0, s[1]);
    spoke.addColorStop(0, "rgba(" + s[3] + "," + s[2] + ")");
    spoke.addColorStop(1, "rgba(0,0,0,0)");
    cs.fillStyle = spoke;
    cs.beginPath();
    cs.arc(0, 0, s[1], 0, Math.PI * 2);
    cs.fill();
    cs.restore();
  }
  const causticTexture = new THREE.CanvasTexture(causticCanvas);
  causticTexture.colorSpace = THREE.SRGBColorSpace;
  causticTexture.center.set(0.5, 0.5);
  const causticMaterial = new THREE.MeshBasicMaterial({
    map: causticTexture,
    color: 0xc8dcff,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
    opacity: 0.5,
  });
  const causticPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(1.55, 1.55),
    causticMaterial
  );
  causticPlane.position.set(0, FLOOR_Y - 0.045, -0.01);
  causticPlane.scale.set(1, 0.3, 1);
  causticPlane.renderOrder = 2;
  scene.add(causticPlane);

  // ---- 블룸 후처리 ----
  // r170 은 렌더 타깃에 그릴 때 톤매핑을 끈다(WebGLPrograms 의
  // toneMapped && (target !== null && !target.isXRRenderTarget || (p = toneMapping))).
  // 그래서 소스 타깃에는 ACES 이전 HDR 선형값이 담기고, 판 남색(선형 0.003~0.026)과
  // 터진 패싯(선형 1 이상)의 차이가 수백 배라 임계값 분리가 깨끗하다.
  //
  // 본 렌더는 캔버스에 그대로 두고 블룸만 가산 오버레이로 얹는다. 씬을 타깃에
  // 그려서 합성하면 toneMapped:false 로 맞춰둔 그림자·코스틱의 밝기가 달라지므로,
  // 이미 확정된 판 밝기를 지키려면 이 순서여야 한다.
  const glContext = renderer.getContext();
  const canFloatTarget =
    !!glContext.getExtension("EXT_color_buffer_float") ||
    !!glContext.getExtension("EXT_color_buffer_half_float");

  let draw = () => renderer.render(scene, camera);
  let resizeBloom = () => {};
  let disposeBloom = () => {};
  let bloomReady = false;

  const createBloom = () => {
    if (bloomReady || !canFloatTarget) return;
    const makeTarget = (depth) =>
      new THREE.WebGLRenderTarget(1, 1, {
        type: THREE.HalfFloatType,
        format: THREE.RGBAFormat,
        colorSpace: THREE.LinearSRGBColorSpace,
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        wrapS: THREE.ClampToEdgeWrapping,
        wrapT: THREE.ClampToEdgeWrapping,
        depthBuffer: depth,
        stencilBuffer: false,
        samples: depth ? 4 : 0,
      });
    // 소스만 깊이 버퍼와 MSAA 가 필요하다. 나머지는 어차피 blur 된다.
    const srcTarget = makeTarget(true);
    const mips = [
      { a: makeTarget(false), b: makeTarget(false) },
      { a: makeTarget(false), b: makeTarget(false) },
      { a: makeTarget(false), b: makeTarget(false) },
    ];

    // 전체화면 삼각형. 클립 좌표를 직접 쓰므로 카메라 행렬이 필요 없다.
    const quadGeometry = new THREE.BufferGeometry();
    quadGeometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3)
    );
    quadGeometry.setAttribute(
      "uv",
      new THREE.Float32BufferAttribute([0, 0, 2, 0, 0, 2], 2)
    );
    const quadCamera = new THREE.Camera();
    const quadScene = new THREE.Scene();

    const VERTEX = [
      "varying vec2 vUv;",
      "void main() {",
      "  vUv = uv;",
      "  gl_Position = vec4(position.xy, 0.0, 1.0);",
      "}",
    ].join("\\n");
    const BOX_TAPS = [
      "vec3 box(sampler2D tex, vec2 uv, vec2 texel) {",
      "  vec3 c = texture2D(tex, uv + vec2(-texel.x, -texel.y)).rgb;",
      "  c += texture2D(tex, uv + vec2(texel.x, -texel.y)).rgb;",
      "  c += texture2D(tex, uv + vec2(-texel.x, texel.y)).rgb;",
      "  c += texture2D(tex, uv + vec2(texel.x, texel.y)).rgb;",
      "  return c * 0.25;",
      "}",
    ].join("\\n");

    // bright-pass: 소프트 니 임계값 + 4탭 다운샘플을 한 번에.
    // ceiling 이 없으면 선형 50 짜리 패싯 하나가 화면 전체를 흰 덩어리로 만든다.
    const brightMaterial = new THREE.ShaderMaterial({
      uniforms: {
        tSrc: { value: srcTarget.texture },
        texel: { value: new THREE.Vector2(1, 1) },
        threshold: { value: 1.8 },
        knee: { value: 0.45 },
        ceiling: { value: 3 },
      },
      vertexShader: VERTEX,
      fragmentShader: [
        "uniform sampler2D tSrc;",
        "uniform vec2 texel;",
        "uniform float threshold;",
        "uniform float knee;",
        "uniform float ceiling;",
        "varying vec2 vUv;",
        BOX_TAPS,
        "void main() {",
        "  vec3 c = min(box(tSrc, vUv, texel), vec3(ceiling));",
        "  float lum = max(c.r, max(c.g, c.b));",
        "  float soft = clamp(lum - threshold + knee, 0.0, 2.0 * knee);",
        "  soft = soft * soft / (4.0 * knee + 1.0e-4);",
        "  float gain = max(soft, lum - threshold) / max(lum, 1.0e-4);",
        "  gl_FragColor = vec4(c * gain, 1.0);",
        "}",
      ].join("\\n"),
      depthTest: false,
      depthWrite: false,
    });

    const downMaterial = new THREE.ShaderMaterial({
      uniforms: {
        tSrc: { value: null },
        texel: { value: new THREE.Vector2(1, 1) },
      },
      vertexShader: VERTEX,
      fragmentShader: [
        "uniform sampler2D tSrc;",
        "uniform vec2 texel;",
        "varying vec2 vUv;",
        BOX_TAPS,
        "void main() {",
        "  gl_FragColor = vec4(box(tSrc, vUv, texel), 1.0);",
        "}",
      ].join("\\n"),
      depthTest: false,
      depthWrite: false,
    });

    // 선형 샘플링을 이용한 5탭 가우시안. 분리형이라 H/V 두 번에 9탭 품질이 난다.
    const blurMaterial = new THREE.ShaderMaterial({
      uniforms: {
        tSrc: { value: null },
        dir: { value: new THREE.Vector2(0, 0) },
      },
      vertexShader: VERTEX,
      fragmentShader: [
        "uniform sampler2D tSrc;",
        "uniform vec2 dir;",
        "varying vec2 vUv;",
        "void main() {",
        "  vec2 o1 = dir * 1.3846153846;",
        "  vec2 o2 = dir * 3.2307692308;",
        "  vec3 c = texture2D(tSrc, vUv).rgb * 0.227027;",
        "  c += (texture2D(tSrc, vUv + o1).rgb",
        "      + texture2D(tSrc, vUv - o1).rgb) * 0.3162162162;",
        "  c += (texture2D(tSrc, vUv + o2).rgb",
        "      + texture2D(tSrc, vUv - o2).rgb) * 0.0702702703;",
        "  gl_FragColor = vec4(c, 1.0);",
        "}",
      ].join("\\n"),
      depthTest: false,
      depthWrite: false,
    });

    // Streamlit 은 st.html 을 DOMPurify 로 통과시킨다. DOMPurify 3.x 의
    // SAFE_FOR_XML(기본 on)은 여는 꺾쇠 바로 뒤에 단어문자나 슬래시가 오는 내용을
    // 가진 엘리먼트를 mXSS 방어로 통째 제거한다. GLSL 의 #include 지시문이 정확히
    // 여기 걸려 스크립트가 DOM 에서 통째로 사라진다.
    // 그래서 꺾쇠를 런타임에 조립해 HTML 소스에는 남기지 않는다.
    const chunk = (name) =>
      "  #include " + String.fromCharCode(60) + name + ">";

    // 합성. toneMapped 를 켜두면 three 가 렌더러의 ACES + 노출 3.8 을 그대로
    // 주입하므로 블룸도 본 렌더와 같은 곡선을 타고 부드럽게 눌린다.
    const compositeMaterial = new THREE.ShaderMaterial({
      uniforms: {
        tMip0: { value: mips[0].a.texture },
        tMip1: { value: mips[1].a.texture },
        tMip2: { value: mips[2].a.texture },
        weights: { value: new THREE.Vector3(1, 0.55, 0.25) },
        strength: { value: 0.2 },
      },
      vertexShader: VERTEX,
      fragmentShader: [
        "uniform sampler2D tMip0;",
        "uniform sampler2D tMip1;",
        "uniform sampler2D tMip2;",
        "uniform vec3 weights;",
        "uniform float strength;",
        "varying vec2 vUv;",
        "void main() {",
        "  vec3 c = texture2D(tMip0, vUv).rgb * weights.x",
        "    + texture2D(tMip1, vUv).rgb * weights.y",
        "    + texture2D(tMip2, vUv).rgb * weights.z;",
        "  gl_FragColor = vec4(c * strength, 1.0);",
        chunk("tonemapping_fragment"),
        chunk("colorspace_fragment"),
        "}",
      ].join("\\n"),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthTest: false,
      depthWrite: false,
    });

    const quad = new THREE.Mesh(quadGeometry, brightMaterial);
    quad.frustumCulled = false;
    quadScene.add(quad);

    resizeBloom = () => {
      const dpr = renderer.getPixelRatio();
      // 소스는 절반 해상도다. 굴절 패스도 뷰포트를 따라가므로 추가 비용이
      // 본 프레임의 1/4 수준으로 떨어진다.
      let w = Math.max(2, Math.round(view.width * dpr * 0.5));
      let h = Math.max(2, Math.round(view.height * dpr * 0.5));
      srcTarget.setSize(w, h);
      for (let i = 0; i < mips.length; i += 1) {
        w = Math.max(2, Math.floor(w / 2));
        h = Math.max(2, Math.floor(h / 2));
        mips[i].a.setSize(w, h);
        mips[i].b.setSize(w, h);
      }
    };
    resizeBloom();

    const runPass = (material, target) => {
      quad.material = material;
      renderer.setRenderTarget(target);
      renderer.render(quadScene, quadCamera);
    };

    draw = () => {
      // (1) 블룸 소스. 렌더 타깃이라 톤매핑이 적용되지 않아 HDR 이 그대로 남는다.
      renderer.setRenderTarget(srcTarget);
      renderer.render(scene, camera);

      // (2) bright-pass → 3단 분리 가우시안
      brightMaterial.uniforms.tSrc.value = srcTarget.texture;
      brightMaterial.uniforms.texel.value.set(
        1 / srcTarget.width,
        1 / srcTarget.height
      );
      runPass(brightMaterial, mips[0].a);
      for (let i = 0; i < mips.length; i += 1) {
        if (i > 0) {
          const prev = mips[i - 1].a;
          downMaterial.uniforms.tSrc.value = prev.texture;
          downMaterial.uniforms.texel.value.set(1 / prev.width, 1 / prev.height);
          runPass(downMaterial, mips[i].a);
        }
        const level = mips[i];
        blurMaterial.uniforms.tSrc.value = level.a.texture;
        blurMaterial.uniforms.dir.value.set(1 / level.a.width, 0);
        runPass(blurMaterial, level.b);
        blurMaterial.uniforms.tSrc.value = level.b.texture;
        blurMaterial.uniforms.dir.value.set(0, 1 / level.a.height);
        runPass(blurMaterial, level.a);
      }

      // (3) 본 렌더. 캔버스로 직접 그리므로 판 밝기는 이전과 동일하다.
      renderer.setRenderTarget(null);
      renderer.render(scene, camera);

      // (4) 블룸만 가산으로 얹는다.
      quad.material = compositeMaterial;
      const keepAutoClear = renderer.autoClear;
      renderer.autoClear = false;
      renderer.render(quadScene, quadCamera);
      renderer.autoClear = keepAutoClear;
    };

    disposeBloom = () => {
      srcTarget.dispose();
      for (let i = 0; i < mips.length; i += 1) {
        mips[i].a.dispose();
        mips[i].b.dispose();
      }
      quadGeometry.dispose();
      brightMaterial.dispose();
      downMaterial.dispose();
      blurMaterial.dispose();
      compositeMaterial.dispose();
    };
    bloomReady = true;
  };
  let presented = false;
  const applyRenderBudget = () => {
    mobile = mobileQuery.matches;
    renderer.setPixelRatio(pixelRatio());
    if (!presented || mobile || !canFloatTarget) {
      disposeBloom();
      bloomReady = false;
      disposeBloom = () => {};
      resizeBloom = () => {};
      draw = () => renderer.render(scene, camera);
      panel.dataset.bloom = "off";
    } else {
      createBloom();
      resizeBloom();
      panel.dataset.bloom = "on";
    }
  };
  applyRenderBudget();

  const RAD = Math.PI / 180;
  const TURN = (Math.PI * 2) / 26;
  let spin = 0;
  let envSpin = 0;
  let hover = 0;
  let tiltX = 0;
  let tiltY = 0;
  let last = null;
  let frame = 0;
  const panelInViewport = () => {
    const rect = panel.getBoundingClientRect();
    return rect.bottom > 0 && rect.right > 0 &&
      rect.top < window.innerHeight && rect.left < window.innerWidth;
  };
  let inViewport = panelInViewport();
  const canAnimate = () => !disposed && !document.hidden &&
    !motionQuery.matches && inViewport;

  // ---- 드래그 회전 ----
  let dragging = false;
  let dragId = null;
  let dragLastX = 0;
  let dragLastY = 0;
  let yawManual = 0;
  let pitchManual = 0;
  let yawVel = 0;
  const onPointerDown = (event) => {
    if (!event.isPrimary || !canAnimate()) return;
    dragging = true;
    dragId = event.pointerId;
    dragLastX = event.clientX;
    dragLastY = event.clientY;
    yawVel = 0;
    panel.dataset.drag = "on";
    // 캡처 실패는 치명적이지 않다 (합성 이벤트 등에서 InvalidPointerId 가 날 수 있다)
    try {
      if (panel.setPointerCapture) panel.setPointerCapture(event.pointerId);
    } catch (error) {
      /* 무시 */
    }
  };
  const onPointerDrag = (event) => {
    if (!dragging || event.pointerId !== dragId) return;
    const dx = event.clientX - dragLastX;
    const dy = event.clientY - dragLastY;
    dragLastX = event.clientX;
    dragLastY = event.clientY;
    yawManual += dx * 0.009;
    yawVel = dx * 0.009;
    pitchManual = Math.max(-0.55, Math.min(0.55, pitchManual + dy * 0.006));
  };
  const endDrag = (event) => {
    if (!dragging || (event && event.pointerId !== dragId)) return;
    const pointerId = dragId;
    dragging = false;
    dragId = null;
    delete panel.dataset.drag;
    try {
      if (panel.hasPointerCapture?.(pointerId)) panel.releasePointerCapture(pointerId);
    } catch (error) {
      /* A detached panel may already have lost its pointer capture. */
    }
  };
  panel.addEventListener("pointerdown", onPointerDown);
  panel.addEventListener("pointermove", onPointerDrag);
  panel.addEventListener("pointerup", endDrag);
  panel.addEventListener("pointercancel", endDrag);
  panel.addEventListener("lostpointercapture", endDrag);

  const onResize = () => {
    if (disposed) return;
    if (!sceneIsAttached()) {
      cleanup();
      return;
    }
    view = size();
    applyRenderBudget();
    renderer.setSize(view.width, view.height, false);
    fitCamera();
    inViewport = panelInViewport();
    syncVisibility();
  };
  window.addEventListener("resize", onResize);
  const resizeObserver = typeof ResizeObserver === "function"
    ? new ResizeObserver(onResize) : null;
  if (resizeObserver) resizeObserver.observe(panel);

  let shaderFailed = false;
  renderer.debug.onShaderError = () => { shaderFailed = true; };

  const tick = (now) => {
    frame = 0;
    if (!sceneIsAttached()) {
      cleanup();
      return;
    }
    if (!canAnimate()) {
      last = null;
      return;
    }
    // Keep only one RAF pending; narrow viewports draw no more than 30 fps.
    if (mobile && last !== null && now - last < 1000 / 30) {
      frame = requestAnimationFrame(tick);
      return;
    }
    const delta = last === null ? 0 : Math.max(0, Math.min((now - last) / 1000, 0.05));
    last = now;
    updateScrollCamera(delta);

    // 커서가 판 위에 있으면 표면 반짝임만 끌어올린다. 배경 밝기는 건드리지 않는다.
    const wanted = panel.dataset.glow === "on" ? 1 : 0;
    hover += (wanted - hover) * Math.min(delta * 3.4, 1);

    // 드래그 중에는 자전을 멈추고, 놓으면 관성으로 감쇠하며 자전으로 복귀한다.
    if (!dragging) {
      spin += delta * TURN * (1 + hover * 0.55);
      yawManual += yawVel;
      yawVel *= 0.94;
      if (Math.abs(yawVel) < 0.00005) yawVel = 0;
    }
    // 환경맵을 돌리면 광이 패싯을 차례로 스친다 = 반짝임
    // HDR 환경에서 envMapIntensity 를 크게 올리면 전체가 흰색으로 클리핑되어
    // 패싯 분할이 사라진다. 호버는 밝기가 아니라 "섬광 빈도"를 올린다.
    envSpin += delta * (0.1 + hover * 0.8);
    scene.environmentRotation.y = envSpin;
    for (let i = 0; i < LIGHTS.length; i += 1) {
      LIGHTS[i][0].intensity = LIGHTS[i][1] * (1 + hover * 1.2);
    }

    const pointer = window.__psLoginPointer || { tiltX: 0, tiltY: 0 };
    const pointerEase = 1 - Math.exp(-delta * 3.7);
    tiltX += (pointer.tiltX - tiltX) * pointerEase;
    tiltY += (pointer.tiltY - tiltY) * pointerEase;
    gem.rotation.set(
      tiltY * RAD + pitchManual,
      spin + tiltX * RAD + yawManual,
      0
    );
    gem.position.y = Math.sin(spin * 1.7) * 0.045;
    optics.update(gem, camera, envSpin, hover);
    mirror.rotation.copy(gem.rotation);
    mirror.position.set(
      gem.position.x,
      MIRROR_Y - gem.position.y * MIRROR_SQUASH,
      gem.position.z
    );
    mirrorMaterial.envMapIntensity = 1.4 + hover * 1.1;
    // 스플래시가 젬과 반대로 돌면 스포크가 살아 움직인다
    causticTexture.rotation = -spin * 0.8;
    causticMaterial.opacity =
      (0.34 + 0.12 * Math.sin(spin * 7) + 0.07 * Math.sin(spin * 11.3)) *
      (1 + hover * 0.8);
    try {
      // Let the first real diamond reach the screen before compiling bloom passes.
      if (presented && !mobile && canFloatTarget && !bloomReady) applyRenderBudget();
      draw();
      if (shaderFailed) throw new Error("shader compilation failed");
    } catch (error) {
      cleanup();
      mark("fail:shader " + String(error).slice(0, 120));
      return;
    }
    presented = true;
    // Reveal the real diamond only after a successful, visible draw.
    if (panel.dataset.gem !== "webgl") {
      canvas.style.display = "";
      panel.dataset.gem = "webgl";
      mark("live");
    }
    frame = requestAnimationFrame(tick);
  };
  const syncVisibility = () => {
    if (disposed) return;
    if (!sceneIsAttached()) {
      cleanup();
      return;
    }
    if (!canAnimate()) {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      last = null;
      endDrag();
      yawVel = 0;
      if (motionQuery.matches) {
        canvas.style.display = "none";
        delete panel.dataset.gem;
        updateScrollCamera(0);
      }
      return;
    }
    if (!frame) {
      last = null;
      frame = requestAnimationFrame(tick);
    }
  };
  const onViewportScroll = () => {
    inViewport = panelInViewport();
    syncVisibility();
  };
  const intersectionObserver = typeof IntersectionObserver === "function"
    ? new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === panel) inViewport = entry.isIntersecting;
      }
      syncVisibility();
    }, { threshold: 0 }) : null;
  if (intersectionObserver) intersectionObserver.observe(panel);
  else window.addEventListener("scroll", onViewportScroll, { passive: true, capture: true });
  // Detached DOM must be released even while there is no animation frame.
  const detachObserver = new MutationObserver(() => {
    if (!sceneIsAttached()) cleanup();
  });
  detachObserver.observe(document.body, { childList: true, subtree: true });
  document.addEventListener("visibilitychange", syncVisibility);
  motionQuery.addEventListener("change", syncVisibility);
  mobileQuery.addEventListener("change", onResize);
  const onContextLost = (event) => {
    event.preventDefault();
    cleanup();
    mark("fail:context-lost");
  };
  canvas.addEventListener("webglcontextlost", onContextLost);
  releaseScene = () => {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    last = null;
    endDrag();
    canvas.removeEventListener("webglcontextlost", onContextLost);
    window.removeEventListener("resize", onResize);
    window.removeEventListener("scroll", onViewportScroll, true);
    document.removeEventListener("visibilitychange", syncVisibility);
    motionQuery.removeEventListener("change", syncVisibility);
    mobileQuery.removeEventListener("change", onResize);
    if (resizeObserver) resizeObserver.disconnect();
    if (intersectionObserver) intersectionObserver.disconnect();
    detachObserver.disconnect();
    panel.removeEventListener("pointerdown", onPointerDown);
    panel.removeEventListener("pointermove", onPointerDrag);
    panel.removeEventListener("pointerup", endDrag);
    panel.removeEventListener("pointercancel", endDrag);
    panel.removeEventListener("lostpointercapture", endDrag);
    delete panel.dataset.drag;
    disposeBloom();
    delete panel.dataset.bloom;
    geometry.dispose();
    optics.dispose();
    mirrorMaterial.dispose();
    shadowPlane.geometry.dispose();
    shadowPlane.material.dispose();
    shadowTexture.dispose();
    causticPlane.geometry.dispose();
    causticMaterial.dispose();
    causticTexture.dispose();
    environmentTarget.dispose();
    bgTexture.dispose();
    renderer.dispose();
    if (renderer.forceContextLoss) renderer.forceContextLoss();
    canvas.remove();
    delete panel.dataset.gem;
  };

  canvas.style.display = "none";
  panel.insertBefore(canvas, panel.firstChild);
  syncVisibility();
})();
</script>
""".replace("__MODULE_URL__", source)


def workspace_tab_scroll_script(active_tab: object) -> str:
    """Reveal the active workspace tab after Streamlit mounts the tab row."""

    active_tab_json = json.dumps(str(active_tab or ""), ensure_ascii=False).translate(
        {
            ord("<"): r"\u003c",
            ord(">"): r"\u003e",
            ord("&"): r"\u0026",
            0x2028: r"\u2028",
            0x2029: r"\u2029",
        }
    )
    return f"""
<script>
(() => {{
  const activeTab = {active_tab_json};
  if (!activeTab) return;
  requestAnimationFrame(() => {{
    const tabbar = document.querySelector(".st-key-internal_tab_bar");
    if (!tabbar) return;
    const activeButton = tabbar.querySelector(
      'div[class*="st-key-tab_activate_"] button[kind="primary"]'
    );
    const activeWrapper = activeButton?.closest(
      'div[class*="st-key-workspace_tab_"]'
    );
    if (!activeWrapper) return;
    const tabbarRect = tabbar.getBoundingClientRect();
    const activeRect = activeWrapper.getBoundingClientRect();
    let nextLeft = tabbar.scrollLeft;
    if (activeRect.left < tabbarRect.left) {{
      nextLeft -= tabbarRect.left - activeRect.left;
    }} else if (activeRect.right > tabbarRect.right) {{
      nextLeft += activeRect.right - tabbarRect.right;
    }}
    if (nextLeft === tabbar.scrollLeft) return;
    tabbar.scrollTo({{ left: nextLeft, behavior: "instant" }});
  }});
}})();
</script>
"""
