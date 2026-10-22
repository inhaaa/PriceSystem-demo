"""PriceSystem workspace shell; native Streamlit themes own all sheet colors."""

import streamlit as st


def workspace_theme_marker_html(initial_theme: str | None = "light") -> str:
    """Seed the first frame from the submit context until the native bridge mounts."""
    initial_theme = "dark" if initial_theme == "dark" else "light"
    return f'<span class="workspace-theme-marker" data-initial-theme="{initial_theme}" hidden aria-hidden="true"></span>'


# Public v2 component theme variables update with the native Settings selector.
# Copy only sheet tokens, not theme state: no global server config, polling,
# database preference, React internals, or second theme selector to get out of sync.
SHEET_THEME_BRIDGE_JS = """
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
  const observer = new MutationObserver(sync);
  // The official wrapper owns the inherited --st-* properties. Observe only
  // this component's ancestor attributes, never the whole document subtree.
  let wrapper = probe.parentElement;
  while (wrapper && wrapper !== document.body) {
    observer.observe(wrapper, {attributes: true, attributeFilter: ['style', 'class']});
    wrapper = wrapper.parentElement;
  }
  return () => {
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
  --ps-canvas: #111514;
  --ps-surface: #171b1a;
  --ps-surface-muted: #202a25;
  --ps-surface-subtle: #1b211e;
  --ps-text: #e9eeeb;
  --ps-muted: #a6b2ac;
  --ps-text-muted: #a6b2ac;
  --ps-border: #333c37;
  --ps-border-strong: #56645c;
  --ps-border-accent: #6a8976;
  --ps-primary: #ccdfca;
  --ps-primary-hover: #e5f0dd;
  --ps-primary-soft: #253d33;
  --ps-action: #2f624c;
  --ps-action-hover: #386d54;
  --ps-action-ink: #ffffff;
  --ps-accent: #d4ed76;
  --ps-focus-outline: #d4ed76;
  --ps-focus-color: #d4ed7633;
  --ps-success: #bbd9be;
  --ps-success-bg: #253d33;
  --ps-warning: #ead4a4;
  --ps-warning-bg: #423a28;
  --ps-danger: #f1b3aa;
  --ps-danger-bg: #482f2b;
  --ps-info: #b9d5cd;
  --ps-info-bg: #263c34;
  --ps-sheet: #141414;
  --ps-sheet-input: #191919;
  --ps-sheet-ink: #f4f3ef;
  --ps-sheet-border: #4e584f;
  --ps-sheet-grid: #3c443d;
  --ps-sheet-head: #202820;
  background: var(--ps-canvas);
  color-scheme: dark;
}
__LIGHT__ {
  --ps-canvas: #f5f6f5;
  --ps-surface: #ffffff;
  --ps-surface-muted: #f0f3f1;
  --ps-surface-subtle: #f8faf9;
  --ps-text: #242a28;
  --ps-muted: #68716d;
  --ps-text-muted: #68716d;
  --ps-border: #e0e6e2;
  --ps-border-strong: #b9c4be;
  --ps-border-accent: #9cb5a7;
  --ps-primary: #204e3e;
  --ps-primary-hover: #173e30;
  --ps-primary-soft: #edf4ef;
  --ps-action: #204e3e;
  --ps-action-hover: #173e30;
  --ps-action-ink: #ffffff;
  --ps-accent: #d4ed76;
  --ps-focus-outline: #315b43;
  --ps-focus-color: #315b4326;
  --ps-success: #245b3d;
  --ps-success-bg: #eaf0e8;
  --ps-warning: #7e5719;
  --ps-warning-bg: #f7efdb;
  --ps-danger: #a1392c;
  --ps-danger-bg: #faebe6;
  --ps-info: #245448;
  --ps-info-bg: #eaf0e8;
  --ps-sheet: #ffffff;
  --ps-sheet-input: #f8faf9;
  --ps-sheet-ink: #242a28;
  --ps-sheet-border: #b9c4be;
  --ps-sheet-grid: #e0e6e2;
  --ps-sheet-head: #f0f3f1;
  color-scheme: light;
}
__SCOPE__ [data-testid="stElementContainer"]:has(.workspace-theme-marker),
__SCOPE__ .st-key-workspace_sheet_theme { display: none; }
__SCOPE__ [data-testid="stAppViewContainer"],
__SCOPE__ [data-testid="stMain"] { min-width: 0; background: var(--ps-canvas); }
__SCOPE__ [data-testid="stHeader"] {
  color: var(--ps-text); background: var(--ps-canvas); border-bottom: 1px solid var(--ps-border);
}
__SCOPE__ [data-testid="stHeader"] button { color: var(--ps-text); }
__SCOPE__ [data-testid="stMainBlockContainer"] {
  box-sizing: border-box; width: calc(100% - 56px); max-width: 1500px; min-width: 0;
  margin: 64px auto 28px; padding: 0; color: var(--ps-text);
}
__SCOPE__ [data-testid="stMainBlockContainer"] > div,
__SCOPE__ [data-testid="stColumn"],
__SCOPE__ [data-testid="stLayoutWrapper"] { min-width: 0; }
__SCOPE__ .st-key-workspace_surface,
__SCOPE__ .st-key-workspace_qa_surface {
  min-width: 0; padding: 22px; background: var(--ps-surface);
  border: 1px solid var(--ps-border); border-radius: 6px;
}
__SCOPE__ .st-key-workspace_surface:has(.st-key-daily_workspace),
__SCOPE__ .st-key-workspace_surface:has(.st-key-notice_workbench),
__SCOPE__ .st-key-workspace_surface:has(.st-key-interest_registration) {
  padding: 0; background: transparent; border: 0;
}
__SCOPE__ .st-key-workspace_home { min-width: 0; gap: 20px; }
__SCOPE__ .st-key-workspace_surface [data-testid="stElementContainer"]:has(.page-header) { display: none; }
__SCOPE__ .st-key-workspace_masthead { gap: 0; }
__SCOPE__ .st-key-workspace_masthead .page-header {
  padding: 2px 0 20px; margin: 0; border: 0;
}
__SCOPE__ .st-key-workspace_masthead .page-header__title {
  margin: 0; font-size: 1.5rem; font-weight: 650; letter-spacing: -.04em;
}
__SCOPE__ .workspace-tabbar-spacer { display: none; }
__SCOPE__ .st-key-internal_tab_bar {
  padding: 0 0 10px; margin-bottom: 16px; border-bottom: 1px solid var(--ps-border);
}
__SCOPE__ div[class*="st-key-workspace_tab_"] {
  border: 1px solid var(--ps-border); border-radius: 5px; background: var(--ps-surface);
}
__SCOPE__ div[class*="st-key-workspace_tab_"]:has(button[kind="primary"]) {
  border-color: var(--ps-primary); background: var(--ps-primary-soft); box-shadow: inset 0 -2px var(--ps-primary);
}
__SCOPE__ div[class*="st-key-workspace_tab_"] button,
__SCOPE__ div[class*="st-key-workspace_tab_"] button[kind="primary"]:not(:disabled) {
  min-height: 2.3rem; color: var(--ps-text); background: transparent; border: 0; border-radius: 0; box-shadow: none;
}
__SCOPE__ div[class*="st-key-workspace_tab_"] button:hover { color: var(--ps-text); background: var(--ps-surface-muted); }
__SCOPE__ [data-testid="stSidebar"] {
  --ps-text: #f5f4ed;
  --ps-muted: #c1d1c5;
  --ps-text-muted: #c1d1c5;
  --ps-surface: #153d32;
  --ps-surface-muted: #214b3c;
  --ps-border: #436354;
  --ps-border-strong: #7c9982;
  --ps-primary: #d4ed76;
  --ps-primary-hover: #e4f3ac;
  color: var(--ps-text); background: #153d32; border: 0;
  border-right: 1px solid #274e3e; border-radius: 0; margin: 0; height: 100svh;
}
__SCOPE__ [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] { gap: 7px; }
__SCOPE__ [data-testid="stSidebar"] .sidebar-brand {
  gap: 12px; padding: 8px 2px 25px; margin: 0 0 14px; border-bottom: 1px solid #436354;
}
__SCOPE__ .sidebar-brand__mark {
  display: block; width: 37px; height: 37px; flex: 0 0 37px; object-fit: contain;
  background: transparent; border-radius: 0;
}
__SCOPE__ .sidebar-brand__name { color: #f5f4ed; font-size: 1.2rem; font-weight: 750; letter-spacing: -.04em; }
__SCOPE__ .sidebar-brand__tagline { color: #c1d1c5; font-size: .67rem; }
__SCOPE__ .sidebar-nav-title { margin: 18px 2px 8px; color: #c1d1c5; font-size: .65rem; letter-spacing: .1em; }
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button {
  min-height: 2.55rem; padding: .55rem .7rem; color: #f5f4ed; background: transparent;
  border: 1px solid transparent; border-radius: 3px; font-size: .83rem;
}
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button[kind="primary"] {
  color: #f5f4ed; background: #2a5141; border-color: #5c7c61; box-shadow: inset 3px 0 #d4ed76;
}
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button:hover {
  color: #ffffff; background: #2a5141;
}
__SCOPE__ [data-testid="stSidebar"] [data-testid="stButton"] button > div { justify-content: flex-start; }
__SCOPE__ [data-testid="stSidebar"] .st-key-sidebar_logout button { color: #c1d1c5; background: transparent; border-color: transparent; }
__SCOPE__ [data-testid="stSidebar"] button:focus-visible { outline: 2px solid #d4ed76; outline-offset: 2px; }
__SCOPE__ [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] { color: #f5f4ed; }
__SCOPE__ [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
__SCOPE__ [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"] { color: var(--ps-text); }
__SCOPE__ [data-testid="stSidebarCollapsedControl"] { background: var(--ps-canvas); border: 1px solid var(--ps-border); border-radius: 3px; }
__SCOPE__ [data-testid="stMarkdownContainer"] { color: var(--ps-text); }
__SCOPE__ button [data-testid="stMarkdownContainer"] { color: inherit; }
__SCOPE__ [data-testid="stCaptionContainer"] { color: var(--ps-muted); opacity: 1; }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) { --ps-text: var(--ps-info); }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { --ps-text: var(--ps-success); }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { --ps-text: var(--ps-warning); }
__SCOPE__ [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { --ps-text: var(--ps-danger); }
__SCOPE__ [data-testid="stButton"] button[kind="primary"]:not(:disabled),
__SCOPE__ [data-testid="stFormSubmitButton"] button:is([kind="primary"], [kind="primaryFormSubmit"]):not(:disabled) {
  color: var(--ps-action-ink); background: var(--ps-action); border-color: var(--ps-action);
}
__SCOPE__ [data-testid="stButton"] button[kind="primary"]:not(:disabled):hover,
__SCOPE__ [data-testid="stFormSubmitButton"] button:is([kind="primary"], [kind="primaryFormSubmit"]):not(:disabled):hover {
  color: var(--ps-action-ink); background: var(--ps-action-hover); border-color: var(--ps-action-hover);
}
/* Sidebar and tab controls retain their own selected-state colors. */
__SCOPE__ [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button[kind="primary"]:not(:disabled) {
  color: #f5f4ed; background: #2a5141; border-color: #5c7c61;
}
__SCOPE__ div[class*="st-key-workspace_tab_"] [data-testid="stButton"] button[kind="primary"]:not(:disabled) {
  color: var(--ps-text); background: transparent; border: 0;
}
__SCOPE__ .st-key-daily_controls {
  padding: 20px; background: var(--ps-surface); border: 0; border-top: 1px solid var(--ps-border); border-radius: 0;
}
__SCOPE__ .st-key-daily_result_panel {
  padding: 20px; background: var(--ps-surface); border: 0; border-radius: 0;
}
@media (max-width: 1024px) {
  __SCOPE__ [data-testid="stMainBlockContainer"] { width: calc(100% - 40px); }
}
@media (max-width: 768px) {
  __SCOPE__ [data-testid="stMainBlockContainer"] { width: calc(100% - 24px); margin: 62px auto 20px; }
  __SCOPE__ .st-key-workspace_surface, __SCOPE__ .st-key-workspace_qa_surface { padding: 18px 12px; }
  __SCOPE__ [data-testid="stSidebar"] { background: #153d32; margin: 0; height: 100svh; }
  __SCOPE__ [data-testid="stHeader"] { background: var(--ps-canvas); }
  __SCOPE__ :is(input, textarea, select) { font-size: 16px; }
}
""".replace(
    "__LIGHT__",
    'body:is([data-ps-theme="light"], :not([data-ps-theme]):has(.workspace-theme-marker[data-initial-theme="light"])):has(.workspace-theme-marker):not(:has(#login-card-root))',
).replace("__SCOPE__", "body:has(.workspace-theme-marker):not(:has(#login-card-root))")
