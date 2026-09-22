// Fixed viewport positions {x, y, size, nav, id}, identical to approved v11.
function placeBling(width, height, navRect, blockers, navBlockers) {
  const inside = (x,y,r,pad=0) => x>=r.left-pad && x<=r.right+pad && y>=r.top-pad && y<=r.bottom+pad;
  const navVisible = navRect && navRect.right>20 && navRect.left < width && navRect.right-navRect.left>20;
  const columns = width < 720 ? 4 : 7;
  const seeds = [];
  for (let row=0; row < 6; row++) for (let col=0; col < columns; col++) {
    const i=row*columns+col;
    seeds.push({x:(col+.22+(i*7%9)/16)/columns*width, y:(row+.24+(i*5%7)/13)/6*height, nav:false});
  }
  if (navVisible) for (const y of [.12,.36,.62,.88]) for (const x of [.16,.82]) {
    seeds.push({x:navRect.left+x*(navRect.right-navRect.left),y:navRect.top+y*(navRect.bottom-navRect.top),nav:true});
  }
  const points=[];
  seeds.forEach((seed,id)=>{
    const size=20+(id%3)*6, radius=size/2+5;
    const obstacles=seed.nav ? navBlockers : blockers;
    for (const [dx,dy] of [[0,0],[24,0],[-24,0],[0,28],[0,-28],[22,24],[-22,-24]]) {
      const x=seed.x+dx, y=seed.y+dy;
      if (x < radius || x>width-radius || y < radius || y>height-radius) continue;
      if (seed.nav ? !inside(x,y,navRect,-radius) : navVisible&&inside(x,y,navRect,radius)) continue;
      if (obstacles.some(r=>inside(x,y,r,radius))) continue;
      if (points.some(p=>Math.hypot(x-p.x,y-p.y) < 48)) continue;
      points.push({x,y,size,nav:seed.nav,id});
      break;
    }
  });
  return points;
}

function mountWorkspaceGlimmer() {
  // Component reruns can overlap. Each mount releases only its own reference.
  const existing = document.querySelector('.prism-bling');
  if (existing?.retainWorkspaceGlimmer) return existing.retainWorkspaceGlimmer();
  const layer = document.createElement('div');
  layer.className = 'prism-bling';
  layer.setAttribute('aria-hidden', 'true');
  layer.style.visibility = 'hidden';
  document.body.append(layer);

  const controls = 'button,input,textarea,select,label,a,table,[role="button"],[role="grid"],[contenteditable="true"],[data-testid="stDataFrame"],.material-symbols-rounded,[role="dialog"],[aria-modal="true"],[data-testid="stDialog"],[data-testid="stPopoverBody"],[role="listbox"],[role="menu"]';
  const nonContent = 'script,style,noscript,template,.prism-bling';
  let timer, disposed = false, owners = 0, observed = [];

  function obstacles(scene, sidebar) {
    const blockers = [], navBlockers = [];
    const add = (element, rects) => {
      const targets = sidebar.contains(element) ? [navBlockers]
        : scene.contains(element) ? [blockers] : [blockers, navBlockers];
      for (const rect of rects) {
        if (rect.width && rect.height && rect.bottom > 0 && rect.top < window.innerHeight && rect.right > 0 && rect.left < window.innerWidth) {
          for (const target of targets) target.push(rect);
        }
      }
    };
    for (const element of document.body.querySelectorAll(controls)) {
      add(element, element.getClientRects());
    }
    // Text Ranges protect glyph lines, leaving empty space in wide containers.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const parent = node.parentElement;
      if (!node.nodeValue?.trim() || !parent || parent.closest(nonContent + ',' + controls)) continue;
      range.selectNodeContents(node);
      add(parent, range.getClientRects());
    }
    return [blockers, navBlockers];
  }

  function layout() {
    timer = undefined;
    if (disposed || document.hidden) return;
    const scene = document.querySelector('[data-testid="stAppViewContainer"]');
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    const content = scene?.querySelector('[data-testid="stMainBlockContainer"]');
    const targets = [scene, sidebar, content].filter(Boolean);
    if (targets.length !== observed.length || targets.some((target, index) => target !== observed[index])) {
      resizeObserver.disconnect();
      targets.forEach(target => resizeObserver.observe(target));
      observed = targets;
    }
    if (!scene || !sidebar || !document.querySelector('.workspace-theme-marker') || document.querySelector('#login-card-root')) {
      layer.style.visibility = 'hidden';
      return;
    }
    const [blockers, navBlockers] = obstacles(scene, sidebar);
    const points = placeBling(window.innerWidth, window.innerHeight, sidebar.getBoundingClientRect(), blockers, navBlockers);
    // Reuse nodes so ordinary layout updates retain their CSS animation phase.
    while (layer.children.length < points.length) layer.append(document.createElement('i'));
    [...layer.children].forEach((element, index) => {
      const point = points[index];
      element.hidden = !point;
      if (!point) return;
      element.dataset.surface = point.nav ? 'nav' : 'scene';
      element.style.cssText = `left:${point.x}px;top:${point.y}px;--size:${point.size}px;--duration:${2.8+(point.id%7)*.26}s;--delay:${-(point.id*.47)}s`;
    });
    layer.style.visibility = '';
  }

  function schedule() {
    if (disposed) return;
    layer.style.visibility = 'hidden';
    clearTimeout(timer);
    timer = undefined;
    if (!document.hidden) timer = setTimeout(layout, 60);
  }
  function visibility() {
    layer.dataset.paused = String(document.hidden);
    schedule();
  }
  const resizeObserver = new ResizeObserver(schedule);
  const mutationObserver = new MutationObserver(records => {
    if (records.some(record => {
      const target = record.target.nodeType === 3 ? record.target.parentElement : record.target;
      return target && !layer.contains(target) && !target.closest?.(nonContent);
    })) schedule();
  });
  // Body observation also catches a sidebar/scene that mounts after this bridge.
  // Ignore our own style/child updates to avoid a render-observe feedback loop.
  mutationObserver.observe(document.body, {
    childList: true, subtree: true, characterData: true, attributes: true,
    attributeFilter: ['class', 'style', 'hidden', 'open', 'aria-expanded', 'value', 'type', 'disabled'],
  });
  window.addEventListener('resize', schedule);
  const events = ['scroll', 'input', 'change', 'transitionend'];
  events.forEach(event => document.addEventListener(event, schedule, {capture: true, passive: true}));
  document.addEventListener('visibilitychange', visibility);
  document.fonts?.addEventListener('loadingdone', schedule);
  document.fonts?.ready.then(schedule);
  layer.dataset.paused = String(document.hidden);
  layout();

  layer.retainWorkspaceGlimmer = () => {
    owners++;
    let released = false;
    return () => {
      if (released) return;
      released = true;
      if (--owners) return;
      disposed = true;
      clearTimeout(timer);
      resizeObserver.disconnect();
      mutationObserver.disconnect();
      window.removeEventListener('resize', schedule);
      events.forEach(event => document.removeEventListener(event, schedule, true));
      document.removeEventListener('visibilitychange', visibility);
      document.fonts?.removeEventListener('loadingdone', schedule);
      layer.remove();
      delete layer.retainWorkspaceGlimmer;
    };
  };
  return layer.retainWorkspaceGlimmer();
}

if (typeof module !== 'undefined') module.exports = {placeBling, mountWorkspaceGlimmer};
