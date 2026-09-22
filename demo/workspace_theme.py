"""Authenticated Diamond space; native Streamlit themes own all sheet colors."""

from pathlib import Path

import streamlit as st


def workspace_theme_marker_html(initial_theme: str | None = "light") -> str:
    """Seed the first frame from the submit context until the native bridge mounts."""
    initial_theme = "dark" if initial_theme == "dark" else "light"
    return f'<span class="workspace-theme-marker" data-initial-theme="{initial_theme}" hidden aria-hidden="true"></span>'


# Public v2 component theme variables update with the native Settings selector.
# Copy only sheet tokens, not theme state: no global server config, polling,
# database preference, React internals, or second theme selector to get out of sync.
SHEET_THEME_BRIDGE_JS = Path(__file__).with_name("workspace_glimmer.js").read_text(encoding="utf-8") + """
export default function({ parentElement }) {
  const probe = parentElement.querySelector('.workspace-theme-probe');
  const target = document.body;
  const mapping = {
    '--ps-sheet': '--st-background-color',
    '--ps-sheet-input': '--st-secondary-background-color',
    '--ps-sheet-ink': '--st-text-color',
    '--ps-sheet-border': '--st-border-color',
    '--ps-sheet-grid': '--st-dataframe-border-color',
    '--ps-sheet-head': '--st-dataframe-header-background-color'
  };
  const sync = () => {
    const values = getComputedStyle(probe);
    for (const [key, source] of Object.entries(mapping)) {
      const value = values.getPropertyValue(source).trim();
      if (value) target.style.setProperty(key, value);
    }
    // st.context.theme.type is documented as unreliable on first load and right
    // after a switch, so read the palette the browser already resolved instead.
    // Assigning to color makes the engine normalise any notation to rgb().
    const background = values.getPropertyValue('--st-background-color').trim();
    if (!background) return;
    probe.style.color = background;
    const channels = (getComputedStyle(probe).color.match(/[\\d.]+/g) || []).map(Number);
    if (channels.length < 3) return;
    const [red, green, blue] = channels;
    target.dataset.psTheme =
      red * 0.299 + green * 0.587 + blue * 0.114 < 128 ? 'dark' : 'light';
  };
  sync();
  const disposeGlimmer = mountWorkspaceGlimmer();
  const observer = new MutationObserver(sync);
  // The official wrapper owns the inherited --st-* properties. Observe only
  // this component's ancestor attributes, never the whole document subtree.
  let wrapper = probe.parentElement;
  while (wrapper && wrapper !== document.body) {
    observer.observe(wrapper, {attributes: true, attributeFilter: ['style', 'class']});
    wrapper = wrapper.parentElement;
  }
  return () => {
    disposeGlimmer();
    observer.disconnect();
    for (const key of Object.keys(mapping)) target.style.removeProperty(key);
    delete target.dataset.psTheme;
  };
}
"""

def render_sheet_theme_bridge() -> None:
    """Mount in the main area so the sidebar palette cannot override sheets."""
    # Register against the current runtime (also supports fresh AppTest runtimes).
    bridge = st.components.v2.component(
        "workspace_sheet_theme",
        html='<span class="workspace-theme-probe" hidden aria-hidden="true"></span>',
        js=SHEET_THEME_BRIDGE_JS,
        isolate_styles=False,
    )
    bridge(key="workspace_sheet_theme", height=0)


WORKSPACE_THEME_CSS = """
__SCOPE__ {
  --ps-canvas: #0a0a0a;
  --ps-text: #eeede9;
  --ps-muted: #b4b2ac;
  --ps-text-muted: #aaa8a2;
  --ps-surface: #20201f;
  --ps-surface-muted: #292927;
  --ps-surface-subtle: #1b1b1a;
  --ps-border: #d2d0c924;
  --ps-border-strong: #d2d0c94a;
  --ps-border-accent: #d2d0c938;
  --ps-primary: #dedbd3;
  --ps-primary-hover: #ffffff;
  --ps-primary-soft: #d2d0c915;
  --ps-action: #292824;
  --ps-action-hover: #3c3a35;
  --ps-focus-outline: #aaa69c;
  --ps-focus-color: #bfb9ae33;
  --ps-radius-card: 10px;
  --ps-shadow-card: none;
  --ps-shadow-card-hover: none;
  --ps-sheet: #141414;
  --ps-sheet-input: #191919;
  --ps-sheet-ink: #f4f3ef;
  --ps-sheet-border: #d2d0c924;
  --ps-sheet-grid: #3c3c38;
  --ps-sheet-head: #202020;
  --ps-glass: linear-gradient(128deg, #d6d6d60c, #15151580 56%, #e1e1e106);
  background: var(--ps-canvas);
}
__SCOPE__ [data-testid="stElementContainer"]:has(.workspace-theme-marker),
__SCOPE__ .st-key-workspace_sheet_theme { display: none; }
__SCOPE__ [data-testid="stAppViewContainer"] {
  isolation: isolate;
  background: radial-gradient(ellipse at 50% 24%, #202020, transparent 65%), #0a0a0a;
}
__SCOPE__ [data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: url("/app/static/diamond-chamber.svg") center / 100% 100% no-repeat;
  opacity: 0.96;
  filter: grayscale(1) brightness(1.65);
}
__SCOPE__ [data-testid="stAppViewContainer"]:has(.st-key-workspace_home)::after {
  /* One decorative layer; only opacity and transform change between frames. */
  content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    radial-gradient(ellipse 7px 3px at 18.6% 34%, #ffffffb3, #ffffff26 35%, transparent 100%),
    radial-gradient(ellipse 4px 7px at 83.6% 36.9%, #ffffffa6, #ffffff1a 35%, transparent 100%),
    radial-gradient(ellipse 6px 3px at 73.1% 83.6%, #ffffff80, transparent 100%),
    radial-gradient(ellipse 40% 32% at 85% 32%, #ffffff0d, transparent 72%),
    linear-gradient(124deg, transparent 32%, #ffffff0d 32.06%, transparent 32.18%, transparent 76%, #ffffff12 76.06%, transparent 76.18%);
  opacity: .2;
  animation: prism-home-glimmer 18s ease-in-out infinite;
}
@keyframes prism-home-glimmer {
  0%, 100% { opacity: .2; transform: translateY(0); }
  50% { opacity: .44; transform: translateY(-3px); }
}
__SCOPE__ [data-testid="stMain"] { min-width: 0; background: transparent; }
__SCOPE__ [data-testid="stMainBlockContainer"] {
  position: relative; box-sizing: border-box; flex: 0 0 auto; height: auto;
  width: calc(100% - 48px); max-width: 1540px; min-width: 0; min-height: 0;
  margin: 70px auto 28px; padding: 0;
  color: var(--ps-text); background: transparent; border: 0; border-radius: 0; box-shadow: none;
}
__SCOPE__ [data-testid="stMainBlockContainer"] > div,
__SCOPE__ [data-testid="stColumn"],
__SCOPE__ [data-testid="stLayoutWrapper"] { min-width: 0; }
__SCOPE__ .st-key-workspace_surface,
__SCOPE__ .st-key-workspace_qa_surface {
  min-width: 0; padding: 24px; background: var(--ps-glass);
  border: 1px solid var(--ps-border); border-radius: 10px;
  box-shadow: inset 0 1px 0 #ebebeb09;
}
__SCOPE__ .st-key-workspace_surface [data-testid="stElementContainer"]:has(.page-header) { display: none; }
__SCOPE__ .st-key-workspace_masthead { color: var(--ps-text); gap: 0; }
__SCOPE__ .st-key-workspace_masthead .page-header { padding: 10px 2px 22px; margin: 0; border: 0; }
__SCOPE__ .st-key-workspace_masthead .page-header__title {
  color: #eeede9; font-size: clamp(1.5rem, 2vw, 2rem); font-weight: 550;
  letter-spacing: -0.045em; margin: 0 0 8px; padding: 0; line-height: 1.3;
}
__SCOPE__ .page-header__eyebrow { color: #aaa8a2; letter-spacing: 0.13em; font-size: .68rem; }
__SCOPE__ .page-header__description { color: #b4b2ac; font-size: .875rem; line-height: 1.6; }
__SCOPE__ .workspace-tabbar-spacer { display: none; }
__SCOPE__ .st-key-internal_tab_bar { margin: 0 0 14px; padding-bottom: 12px; border-bottom: 1px solid var(--ps-border); }
__SCOPE__ div[class*="st-key-workspace_tab_"] { border: 1px solid transparent; border-radius: 5px; }
__SCOPE__ div[class*="st-key-workspace_tab_"]:has(button[kind="primary"]) { border-color: var(--ps-border); background: #d2d0c910; box-shadow: inset 0 -1px #bfb9ae; }
__SCOPE__ div[class*="st-key-workspace_tab_"] button {
  min-height: 2.2rem; color: #b4b2ac; background: transparent; border: 0; border-radius: 4px; box-shadow: none;
}
__SCOPE__ div[class*="st-key-workspace_tab_"] button[kind="primary"] { color: #f4f3ef; }
__SCOPE__ div[class*="st-key-workspace_tab_"] button:hover { color: #fff; background: #d2d0c912; }
__SCOPE__ .st-key-workspace_home .home-launcher { margin: 8px 0 10px; padding-bottom: 18px; border-bottom: 1px solid var(--ps-border); }
__SCOPE__ .st-key-workspace_home .home-launcher h2 { color: #eeede9; font-weight: 550; letter-spacing: -.03em; }
__SCOPE__ .st-key-workspace_home .home-launcher p { color: #b4b2ac; font-size: .9rem; line-height: 1.6; margin: 0; }
__SCOPE__ div[class*="st-key-home_featured_"],
__SCOPE__ div[class*="st-key-home_secondary_"]:not([class*="st-key-home_secondary_grid"]) {
  position: relative; background: var(--ps-glass); border: 1px solid var(--ps-border);
  border-radius: 10px; padding: 24px; box-shadow: inset 0 1px 0 #ebebeb09;
  transition: border-color 140ms ease;
}
__SCOPE__ div[class*="st-key-home_featured_"]:hover,
__SCOPE__ div[class*="st-key-home_secondary_"]:not([class*="st-key-home_secondary_grid"]):hover {
  transform: none; border-color: #d2d0c950; box-shadow: none;
}
__SCOPE__ .home-action-card__content .material-symbols-rounded { color: #dedbd3; background: #d2d0c90c; border: 1px solid var(--ps-border); border-radius: 8px; }
__SCOPE__ [data-testid="stHeader"] { color: #dedbd3; background: #0a0a0ae6; border-bottom: 1px solid var(--ps-border); }
__SCOPE__ [data-testid="stHeader"] button { color: #dedbd3; }
__SCOPE__ [data-testid="stSidebar"] {
  isolation: isolate; color: #eeede9; background: var(--ps-glass);
  border: 1px solid var(--ps-border); border-radius: 12px;
  margin: 66px 0 18px 18px; height: calc(100svh - 84px);
}
__SCOPE__ [data-testid="stSidebar"]::before {
  content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none;
  background: url("/app/static/diamond-chamber.svg") left center / auto 100% no-repeat;
  opacity: 0.65; filter: grayscale(1) brightness(1.6); border-radius: inherit;
}
__SCOPE__ [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
__SCOPE__ [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
__SCOPE__ [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"] { color: #dedbd3; }
__SCOPE__ [data-testid="stSidebarCollapsedControl"] { background: #171717; border-radius: 6px; }
__SCOPE__ [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] { gap: 8px; }
__SCOPE__ .sidebar-brand { gap: 11px; padding-bottom: 18px; margin-bottom: 14px; border-bottom: 1px solid var(--ps-border); }
__SCOPE__ .sidebar-brand__mark { display: block; width: 43px; height: 43px; flex: 0 0 43px; object-fit: contain; background: transparent; border-radius: 0; }
__SCOPE__ .sidebar-brand__name { font-size: 1.5rem; color: #f0f0ec; letter-spacing: .14em; }
__SCOPE__ .sidebar-brand__tagline { font-size: .62rem; color: #b2b2b2; }
__SCOPE__ .sidebar-nav-title { margin-top: 1.1rem; font-size: .68rem; letter-spacing: .05em; }
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button { min-height: 2.5rem; border-radius: 5px; transition: background-color 140ms ease; }
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button[kind="primary"] { color: #f4f3ef; background: linear-gradient(95deg, #e2e2e221, #dfdfdf09); border-color: var(--ps-border); box-shadow: inset 2px 0 #d3d3d3; }
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button > div { justify-content: flex-start; }
__SCOPE__ [data-testid="stMetric"] { border-radius: 8px; }
__SCOPE__ [data-testid="stMetricValue"],
__SCOPE__ [data-testid="stMetricValue"] > div { color: var(--ps-text); }
__SCOPE__ [data-testid="stMarkdownContainer"] { color: var(--ps-text); }
__SCOPE__ button [data-testid="stMarkdownContainer"] { color: inherit; }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) { --ps-text: var(--ps-info); }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { --ps-text: var(--ps-success); }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { --ps-text: var(--ps-warning); }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { --ps-text: var(--ps-danger); }
__SCOPE__ [data-testid="stCaptionContainer"] { color: var(--ps-muted); opacity: 1; }
__SCOPE__ [data-testid="stExpander"] details { border-color: var(--ps-border); }
__SCOPE__ [data-testid="stForm"] { background: transparent; border: 1px solid var(--ps-border); border-radius: 8px; }
__SCOPE__ [data-testid="stFileUploader"] {
  --ps-text: var(--ps-sheet-ink); --ps-surface: var(--ps-sheet-input);
  --ps-surface-muted: var(--ps-sheet-head); --ps-border-strong: var(--ps-sheet-border);
  padding: 16px; background: var(--ps-sheet); color: var(--ps-sheet-ink);
  border: 1px solid var(--ps-sheet-border); border-radius: 8px;
}
__SCOPE__ [data-testid="stFileUploader"] section { color: var(--ps-sheet-ink); background: transparent; border: 1px dashed var(--ps-sheet-grid); border-radius: 4px; }
__SCOPE__ [data-testid="stFileUploader"] :is(p, small, span) { color: inherit; }
__SCOPE__ [data-testid="stFileUploader"] [data-testid="stWidgetLabel"] { color: var(--ps-sheet-ink); }
__SCOPE__ [data-testid="stMain"] :is([data-baseweb="input"], [data-baseweb="textarea"]),
__SCOPE__ [data-testid="stMain"] [data-baseweb="select"] > div,
__SCOPE__ :is([data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"]),
__SCOPE__ [data-testid="stSelectbox"] .react-aria-ComboBox > [role="group"] {
  color: var(--ps-sheet-ink); background: var(--ps-sheet-input);
  border: 1px solid var(--ps-sheet-border); border-radius: 6px;
}
__SCOPE__ :is(input, textarea, select) { color: var(--ps-sheet-ink); font-weight: 500; }
__SCOPE__ input:not([type="checkbox"]):not([type="radio"]),
__SCOPE__ textarea,
__SCOPE__ [data-baseweb="input"] > div,
__SCOPE__ [data-baseweb="textarea"] {
  color: var(--ps-sheet-ink); background: var(--ps-sheet-input);
}
__SCOPE__ :is([data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"]):focus-within { border-color: var(--ps-focus-outline); }
__SCOPE__ :is([data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"]):has(input:disabled) { opacity: .65; }
__SCOPE__ [aria-invalid="true"] { border-color: var(--ps-danger); outline-color: var(--ps-danger); }
__SCOPE__ input:disabled, __SCOPE__ textarea:disabled { cursor: not-allowed; }
__SCOPE__ [data-testid="stTabs"] .react-aria-SelectionIndicator { background: #c7c5bf; }
__SCOPE__ [data-testid="stTabs"] [role="tab"] { color: #b4b2ac; }
__SCOPE__ [data-testid="stTabs"] [role="tab"] p { color: inherit; }
__SCOPE__ [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #f4f3ef; border-bottom-color: #c7c5bf; }
__SCOPE__ [data-testid="stTabs"] [role="tab"]:focus-visible { outline: 2px solid var(--ps-focus-outline); outline-offset: 2px; }
__SCOPE__ [data-testid="stTable"] {
  max-width: 100%; min-width: 0; overflow-x: auto; color: var(--ps-sheet-ink);
  background: var(--ps-sheet); border: 1px solid var(--ps-sheet-border); border-radius: 6px;
}
__SCOPE__ [data-testid="stTable"] table { color: var(--ps-sheet-ink); background: var(--ps-sheet); border-collapse: collapse; font-weight: 500; }
__SCOPE__ [data-testid="stTable"] :is(th, td) { border: 1px solid var(--ps-sheet-grid); }
__SCOPE__ [data-testid="stTable"] th { background: var(--ps-sheet-head); color: var(--ps-sheet-ink); }
/* Glide owns canvas colors (config.toml), keyboard editing, and its horizontal
   scrollbar. Never wrap/replace the grid or clip the floating toolbar. */
__SCOPE__ [data-testid="stDataFrame"] { max-width: 100%; min-width: 0; overflow: visible; border: 0; background: var(--ps-sheet); }
__SCOPE__ [data-testid="stDataFrame"]:focus-within { outline: 2px solid var(--ps-focus-outline); outline-offset: 2px; }
__SCOPE__ :is([data-testid="stDialog"] [role="dialog"], [data-testid="stPopoverBody"], [role="listbox"], [data-baseweb="calendar"]) {
  --ps-text: var(--ps-sheet-ink); --ps-muted: var(--ps-sheet-ink);
  --ps-surface: var(--ps-sheet-input); --ps-surface-muted: var(--ps-sheet-head);
  --ps-border-strong: var(--ps-sheet-border);
  color: var(--ps-sheet-ink); background: var(--ps-sheet);
  border: 1px solid var(--ps-sheet-border); border-radius: 8px;
}
__SCOPE__ [role="option"][aria-selected="true"], __SCOPE__ [role="option"]:hover { background: var(--ps-sheet-head); color: var(--ps-sheet-ink); }
__SCOPE__ [data-testid="stButton"] button[kind="primary"],
__SCOPE__ [data-testid="stFormSubmitButton"] button[kind="primary"] { color: #f4f3ef; background: #292824; border-color: #69665e; }
__SCOPE__ [data-testid="stButton"] button:focus-visible { outline: 2px solid var(--ps-focus-outline); outline-offset: 2px; }
__SCOPE__ div[class*="st-key-home_featured_"] div[class*="st-key-home_open_"] button {
  width: auto; padding: .55rem .9rem; margin-top: 12px;
}
__SCOPE__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button {
  width: auto; padding: .55rem .9rem; margin-top: 12px;
  color: #191918; background: #dedbd3; border: 1px solid #eeeae2;
  border-radius: 6px; font-weight: 600; box-shadow: none;
  transition: background-color 140ms ease, border-color 140ms ease;
}
__SCOPE__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button:hover {
  color: #191918; background: #eeeae2; border-color: #ffffff;
}
__SCOPE__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button:focus-visible {
  outline: 2px solid #eeeae2; outline-offset: 3px; box-shadow: none;
}
@media (max-width: 1024px) {
  __SCOPE__ [data-testid="stMainBlockContainer"] { width: calc(100% - 32px); }
}
@media (max-width: 768px) {
  __SCOPE__ [data-testid="stAppViewContainer"]:has(.st-key-workspace_home)::after { animation: none; display: none; }
  __SCOPE__ [data-testid="stMainBlockContainer"] { width: calc(100% - 20px); margin: 64px auto 12px; }
  __SCOPE__ .st-key-workspace_surface, __SCOPE__ .st-key-workspace_qa_surface { padding: 16px 12px; }
  __SCOPE__ [data-testid="stSidebar"] { background-color: #111; margin: 58px 0 0; height: calc(100svh - 58px); }
  __SCOPE__ :is(input, textarea, select) { font-size: 16px; }
}
@media (max-width: 480px) {
  __SCOPE__ .st-key-workspace_surface, __SCOPE__ .st-key-workspace_qa_surface { padding-inline: 6px; }
}
@media (prefers-reduced-motion: reduce) {
  __SCOPE__ [data-testid="stAppViewContainer"]:has(.st-key-workspace_home)::after { animation: none; display: none; }
  __SCOPE__ [data-testid="stButton"] button,
  __SCOPE__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button,
  __SCOPE__ div[class*="st-key-home_featured_"],
  __SCOPE__ div[class*="st-key-home_secondary_"] { transition: none; }
}

/* ---- Crystal: the approved stationary light room ----
   The submit context supplies the initial palette; the live bridge overrides it.
   Keep sheet colors, geometry, spacing and radii; change only the room and light. */
__LIGHT__ {
  --ps-canvas: #eaeef3;
  --ps-sheet: #ffffff;
  --ps-sheet-input: #eef2f7;
  --ps-sheet-ink: #10171f;
  --ps-sheet-border: #c3cfdb;
  --ps-sheet-grid: #dbe3ec;
  --ps-sheet-head: #eef2f7;
  --ps-text: #10171f;
  --ps-muted: #5d6a77;
  --ps-text-muted: #5d6a77;
  --ps-surface: #ffffff;
  --ps-surface-muted: #eef2f7;
  --ps-surface-subtle: #f7fafc;
  --ps-border: #0e21361f;
  --ps-border-strong: #0e213645;
  --ps-border-accent: #0e213630;
  --ps-primary: #1d2a36;
  --ps-primary-hover: #0b1219;
  --ps-primary-soft: #0e21360f;
  --ps-action: #e8edf3;
  --ps-action-hover: #dce5ee;
  --ps-focus-outline: #2f6f96;
  --ps-focus-color: #2f6f9636;
  --ps-glass: linear-gradient(128deg, #ffffffee, #ffffffb8 56%, #dfeaf4a8);
}
__LIGHT__ [data-testid="stAppViewContainer"] {
  background: #f5f6f5;
}
/* One static optical surface continues behind the header and sidebar. */
__LIGHT__ [data-testid="stAppViewContainer"]::before {
  inset: -12px;
  background: url("/app/static/workspace-crystal.svg") center / 100% 100% no-repeat;
  filter: grayscale(1) contrast(.98) brightness(1.01);
  opacity: .9;
  transform: none; transition: none; animation: none;
}
__LIGHT__ [data-testid="stSidebar"]::before { display: none; }
__LIGHT__ [data-testid="stAppViewContainer"]:has(.st-key-workspace_home)::after {
  display: none; transform: none; transition: none; animation: none;
}
__LIGHT__ [data-testid="stHeader"] { color: #1d2a36; background: transparent; border-bottom-color: transparent; }
__LIGHT__ [data-testid="stHeader"] button { color: #1d2a36; }
__LIGHT__ [data-testid="stSidebar"] { color: #1a222b; background: linear-gradient(128deg, #ffffff70, #ffffff18 56%, #ffffff48); }
__LIGHT__ [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
__LIGHT__ [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
__LIGHT__ [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"] { color: #1d2a36; }
__LIGHT__ [data-testid="stSidebarCollapsedControl"] { background: #ffffff; }
__LIGHT__ .sidebar-brand__name { color: #10171f; }
__LIGHT__ .sidebar-brand__tagline { color: #6b7683; }
/* The mini diamond is a flat image, so it cannot follow the tokens; invert it
   like the chamber or it vanishes into a white sidebar. */
__LIGHT__ .sidebar-brand__mark { filter: invert(1) grayscale(1) brightness(1.06); }
__LIGHT__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button[kind="primary"] {
  color: #0f1620; background: linear-gradient(95deg, #2f6f9614, #2f6f9603); box-shadow: inset 2px 0 #4d90b8;
}
__LIGHT__ .st-key-workspace_masthead .page-header__title { color: #10171f; }
__LIGHT__ .page-header__eyebrow { color: #6b7683; }
__LIGHT__ .page-header__description { color: #5d6a77; }
/* The tab strip sits inside the generic button rule below, so it has to restate
   the transparent fill too. Colour alone leaves dark text on a dark chip. */
__LIGHT__ div[class*="st-key-workspace_tab_"] button { color: #5d6a77; background: transparent; }
__LIGHT__ div[class*="st-key-workspace_tab_"] button[kind="primary"] { color: #10171f; background: transparent; }
__LIGHT__ div[class*="st-key-workspace_tab_"]:has(button[kind="primary"]) {
  background: #0e21360a; box-shadow: inset 0 -1px #2f6f96;
}
__LIGHT__ div[class*="st-key-workspace_tab_"] button:hover { color: #0b1219; background: #0e213610; }
__LIGHT__ .st-key-workspace_home .home-launcher h2 { color: #10171f; }
__LIGHT__ .st-key-workspace_home .home-launcher p { color: #5d6a77; }
__LIGHT__ .home-action-card__content .material-symbols-rounded { color: #2f6f96; background: #2f6f9610; }
__LIGHT__ div[class*="st-key-home_featured_"]:hover,
__LIGHT__ div[class*="st-key-home_secondary_"]:not([class*="st-key-home_secondary_grid"]):hover { border-color: #0e213652; }
__LIGHT__ [data-testid="stButton"] button[kind="primary"],
__LIGHT__ [data-testid="stFormSubmitButton"] button[kind="primary"] { color: #f6f9fb; background: #1d2a36; border-color: #101a24; }
/* The filled CTA has to flip: a pale button on white reads as unclickable. */
__LIGHT__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button {
  color: #f6f9fb; background: #1d2a36; border: 1px solid #101a24;
}
__LIGHT__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button:hover {
  color: #ffffff; background: #0f1a24; border-color: #0b1219;
}
__LIGHT__ .st-key-workspace_home :is(.st-key-home_open_daily_recommend, .st-key-home_open_data_upload) button:focus-visible {
  outline: 2px solid #2f6f96;
}
@media (max-width: 768px) {
  __LIGHT__ [data-testid="stSidebar"] { background-color: transparent; }
}
@media (max-width: 768px), (pointer: coarse) {
  __LIGHT__ [data-testid="stAppViewContainer"]::before {
    background-size: calc((100dvh + 24px) * 1.6) 100%; background-position: 18% center;
  }
}
/* One non-interactive foreground plane above the native sidebar (999991).
   Its default is hidden: login and dark theme never inherit these glints. */
.prism-bling { display: none; position: fixed; inset: 0; z-index: 999992; pointer-events: none; overflow: hidden; }
__LIGHT__ .prism-bling { display: block; }
__LIGHT__ .prism-bling > i {
  position: absolute; width: calc(var(--size) * .65); height: calc(var(--size) * .65); margin: calc(var(--size) * -.325);
  pointer-events: none; opacity: 0;
  background:
    radial-gradient(ellipse 48% 8% at 50% 48%, #fff 18%, #ffffffcc 38%, transparent 88%),
    radial-gradient(ellipse 2.4px 1.7px at 50% 44%, #fff 55%, #ffffffdd 80%, transparent 100%),
    radial-gradient(ellipse 36% 27% at 50% 56%, #52676d99 10%, #72848b70 42%, #93a1a526 72%, transparent 100%);
  animation: prism-surface-bling calc(var(--duration) * 3) ease-in-out infinite;
  animation-delay: calc(var(--delay) * 3);
}
.prism-bling > i[hidden] { display: none; }
@keyframes prism-surface-bling {
  0%, 36%, 58%, 88%, 100% { opacity: 0; }
  10% { opacity: 1; }
  18% { opacity: .7; }
  27% { opacity: .18; }
  68% { opacity: .9; }
  76% { opacity: .4; }
  82% { opacity: .1; }
}
__LIGHT__ .prism-bling[data-paused="true"] > i { animation-play-state: paused; }
__LIGHT__:has(:is([role="dialog"], [role="menu"], [role="listbox"], [data-testid="stPopoverBody"], [data-baseweb="calendar"])) .prism-bling { display: none; }
@media (prefers-reduced-motion: reduce) {
  __LIGHT__ .prism-bling { display: none; }
  __LIGHT__ .prism-bling > i { animation: none; }
}
""".replace(
    "__LIGHT__",
    'body:is([data-ps-theme="light"], :not([data-ps-theme]):has(.workspace-theme-marker[data-initial-theme="light"])):has(.workspace-theme-marker):not(:has(#login-card-root))',
).replace("__SCOPE__", "body:has(.workspace-theme-marker):not(:has(#login-card-root))")
