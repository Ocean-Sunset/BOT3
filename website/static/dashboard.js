(() => {
  "use strict";

  const SIDEBAR_KEY = "prowl_sidebar";
  const SIDEBAR_MIN = 220;
  const SIDEBAR_MAX = 420;
  const SIDEBAR_DEFAULT = 280;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ========================= SIDEBAR: INIT WIDTH (no transition) =========================

  function initSidebarWidth() {
    const sidebar = $("#sidebar");
    const toggle = $("#sidebar-toggle");
    const html = document.documentElement;
    const saved = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");

    // Remove the no-transition snapshot class so is-collapsed takes over
    html.classList.remove("sidebar-start-collapsed");
    sidebar.style.transition = "none";
    if (saved.collapsed) {
      sidebar.classList.add("is-collapsed");
      const icon = toggle.querySelector('[data-lucide]');
      if (icon) { icon.setAttribute('data-lucide', 'panel-left'); lucide.createIcons(); }
    }
    sidebar.offsetHeight;
    sidebar.style.transition = "";
  }

  // ========================= SIDEBAR: TOGGLE =========================

  function initSidebarToggle() {
    const sidebar = $("#sidebar");
    const toggle = $("#sidebar-toggle");
    const saved = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");

    toggle.addEventListener("click", () => {
      const isCollapsed = sidebar.classList.toggle("is-collapsed");
      if (!isCollapsed) {
        sidebar.style.width = (saved.width || SIDEBAR_DEFAULT) + "px";
      }
      localStorage.setItem(SIDEBAR_KEY, JSON.stringify({ ...saved, collapsed: isCollapsed }));
      const icon = toggle.querySelector('[data-lucide]');
      if (icon) {
        icon.setAttribute('data-lucide', isCollapsed ? 'panel-left' : 'panel-left-close');
        lucide.createIcons();
      }
    });
  }

  // ========================= SIDEBAR: RESIZE =========================

  function initSidebarResize() {
    const sidebar = $("#sidebar");
    const toggle = $("#sidebar-toggle");
    const handle = $("#sidebar-resize");
    const saved = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");

    let dragging = false;
    handle.addEventListener("mousedown", (e) => {
      sidebar.style.transition = "none";
      if (sidebar.classList.contains("is-collapsed")) {
        sidebar.classList.remove("is-collapsed");
        saved.collapsed = false;
        sidebar.style.width = SIDEBAR_DEFAULT + "px";
        localStorage.setItem(SIDEBAR_KEY, JSON.stringify({ ...saved, width: SIDEBAR_DEFAULT }));
        const icon = toggle?.querySelector('[data-lucide]');
        if (icon) { icon.setAttribute('data-lucide', 'panel-left-close'); lucide.createIcons(); }
      }
      dragging = true;
      handle.classList.add("is-dragging");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      let w = e.clientX;
      w = Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, w));
      sidebar.style.width = w + "px";
    });

    document.addEventListener("mouseup", () => {
      if (!dragging) return;
      dragging = false;
      handle.classList.remove("is-dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      sidebar.style.transition = "";
      const w = sidebar.offsetWidth;
      localStorage.setItem(SIDEBAR_KEY, JSON.stringify({ collapsed: false, width: w }));
    });
  }

  // ========================= USER POPOVER =========================

  function initUserPopover() {
    const btn = $("#user-menu-btn");
    const pop = $("#user-popover");
    if (!btn || !pop) return;

    function positionPopover() {
      const rect = btn.getBoundingClientRect();
      pop.style.left = rect.left + "px";
      pop.style.bottom = (window.innerHeight - rect.top + 4) + "px";
    }

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = pop.classList.contains("hidden");
      pop.classList.toggle("hidden");
      if (isOpen) positionPopover();
    });

    document.addEventListener("click", () => {
      pop.classList.add("hidden");
    });

    window.addEventListener("resize", () => {
      if (!pop.classList.contains("hidden")) positionPopover();
    });
  }

  // ========================= TOOLTIP =========================

  function initTooltips() {
    const el = document.createElement("div");
    el.id = "prowl-tooltip";
    document.body.appendChild(el);

    let timer;
    document.addEventListener("mouseover", (e) => {
      const target = e.target.closest("[data-tooltip]");
      if (!target) { el.style.display = "none"; return; }
      clearTimeout(timer);
      timer = setTimeout(() => {
        el.textContent = target.getAttribute("data-tooltip");
        el.style.display = "block";
        position(e);
      }, 400);
    });

    document.addEventListener("mouseout", (e) => {
      if (e.target.closest("[data-tooltip]")) {
        clearTimeout(timer);
        el.style.display = "none";
      }
    });

    document.addEventListener("mousemove", (e) => {
      if (el.style.display === "block") position(e);
    });

    function position(e) {
      const mx = e.clientX, my = e.clientY;
      let x = mx + 12, y = my + 12;
      const w = el.offsetWidth, h = el.offsetHeight;
      if (x + w > window.innerWidth) x = mx - w - 8;
      if (y + h > window.innerHeight) y = my - h - 8;
      el.style.left = x + "px";
      el.style.top = y + "px";
    }
  }

  // ========================= SIDEBAR: SCROLL POSITION =========================

  function initSidebarScroll() {
    const nav = $(".sidebar-nav");
    if (!nav) return;

    // Restore scroll position
    const saved = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");
    if (saved.scrollTop != null) {
      nav.scrollTop = saved.scrollTop;
    }

    // Save scroll position before page unload (debounced - sync localStorage on scroll is janky)
    let scrollTimer = null;
    nav.addEventListener("scroll", () => {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(() => {
        const data = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");
        data.scrollTop = nav.scrollTop;
        localStorage.setItem(SIDEBAR_KEY, JSON.stringify(data));
      }, 150);
    });
  }

  // ========================= MASONRY (.md-row) =========================
  // Places each card into the currently-shortest column so a tall block on
  // one side doesn't push the next block below it (Pinterest-style), with no
  // row stretching.

  function initMasonry() {
    const rows = document.querySelectorAll(".md-row");
    if (!rows.length) return;
    const GAP = 12;     // column gap (0.75rem)
    const ROW_GAP = 24; // section margin-bottom (1.5rem)

    function layout() {
      const twoCol = window.innerWidth >= 900;
      rows.forEach((row) => {
        const items = Array.from(row.children);
        if (!twoCol || !items.length) {
          items.forEach((el) => { el.style.position = ""; el.style.top = ""; el.style.left = ""; el.style.width = ""; });
          row.style.position = ""; row.style.height = "";
          return;
        }
        const cw = (row.clientWidth - GAP) / 2;
        if (!(cw > 0)) return; // not laid out yet - retry on next mutation
        const colH = [0, 0];
        items.forEach((el) => {
          const i = colH[0] <= colH[1] ? 0 : 1;
          el.style.width = cw + "px";
          el.style.position = "absolute";
          el.style.left = (i === 0 ? 0 : cw + GAP) + "px";
          el.style.top = colH[i] + "px";
          colH[i] += el.offsetHeight + ROW_GAP;
        });
        row.style.position = "relative";
        row.style.height = Math.max(colH[0], colH[1]) + "px";
      });
    }

    layout();
    let timer = null;
    // Watch content/class changes only - NOT 'style', because layout() itself
    // writes inline styles and would otherwise trigger an infinite relayout loop.
    const onMut = () => { clearTimeout(timer); timer = setTimeout(layout, 80); };
    rows.forEach((row) => {
      try {
        const obs = new MutationObserver(onMut);
        obs.observe(row, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
      } catch (e) {}
    });
    window.addEventListener("resize", () => { clearTimeout(timer); timer = setTimeout(layout, 120); });
    window.addEventListener("load", () => { clearTimeout(timer); timer = setTimeout(layout, 150); });
    window.relayoutMasonry = layout;
  }

  // ========================= QUICK LINKS USAGE =========================
  // Count how often a user visits each panel so Quick Links can reorder by usage.
  function initUsageTracking() {
    const panel = window.__ACTIVE_PANEL;
    if (!panel) return;
    try {
      const key = "prowl_usage";
      const u = JSON.parse(localStorage.getItem(key) || "{}");
      u[panel] = (u[panel] || 0) + 1;
      localStorage.setItem(key, JSON.stringify(u));
    } catch (e) {}
  }

  // ========================= MODAL SCROLL-FADE =========================
  // Adds .is-scrollable to any scrollable .md-modal so the CSS gradient
  // "invisible borders" appear at the top/bottom of long popups (custom embed
  // builders, image-card editors, etc.). Applies to every dashboard page.
  function initModalScrollFades() {
    function refresh(overlay) {
      const m = overlay && overlay.querySelector(".md-modal");
      if (m) m.classList.toggle("is-scrollable", m.scrollHeight > m.clientHeight + 2);
    }
    function watch(overlay) {
      if (overlay.__fadeWatched) return;
      overlay.__fadeWatched = true;
      new MutationObserver(() => {
        if (overlay.classList.contains("is-open")) requestAnimationFrame(() => refresh(overlay));
      }).observe(overlay, { attributes: true, attributeFilter: ["class"] });
      const m = overlay.querySelector(".md-modal");
      if (m) new MutationObserver(() => refresh(overlay)).observe(m, { childList: true, subtree: true });
      refresh(overlay);
    }
    function scan() { document.querySelectorAll(".md-modal-overlay").forEach(watch); }
    scan();
    // Modals injected after initial load still get wired up.
    new MutationObserver(scan).observe(document.body, { childList: true, subtree: false });
    window.addEventListener("resize", () => {
      document.querySelectorAll(".md-modal-overlay.is-open").forEach(refresh);
    });
  }

  // ========================= INIT =========================

  function init() {
    initSidebarWidth();
    initSidebarToggle();
    initSidebarResize();
    initSidebarScroll();
    initUserPopover();
    initTooltips();
    initMasonry();
    initUsageTracking();
    initModalScrollFades();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // ========================= SAVE-BAR STATE MACHINE =========================
  // Single source of truth for settings edit/save/discard across ALL dashboard
  // pages. Centralizing here is what keeps the recurring "discard reverts to the
  // pre-save value" bug from coming back: every page enforces the same rules.
  //
  //   on markChanged(k, v): store original[k] (first edit only), set pending[k]
  //                         and SNAP[k], show the bar.
  //   on save:             LOADED[k] = pending[k]; delete original[k];
  //                         delete pending[k]   (per key).
  //   on discard:          reverted = {...LOADED}; overlay original for keys still
  //                         pending; clear pending + original; re-render from there.
  //
  // Pages supply: render()  -> apply window.SETTINGS_SNAPSHOT to the DOM
  //                  saveOne(k, v) -> Promise that persists one changed key
  window.ProwlSettings = (function () {
    window.SETTINGS_SNAPSHOT = window.SETTINGS_SNAPSHOT || {};
    window.LOADED = window.LOADED || {};
    window._ps_original = window._ps_original || {};
    window._ps_pending = window._ps_pending || {};

    let _render = function () {};
    let _saveOne = async function () {};
    let _bound = false;

    function _bar() { return document.getElementById("save-bar"); }
    function showBar() { const b = _bar(); if (b) b.classList.remove("is-closed"); }
    function hideBar() { const b = _bar(); if (b) b.classList.add("is-closed"); }

    function markChanged(key, value) {
      if (!(key in window._ps_original)) {
        window._ps_original[key] = (key in window.SETTINGS_SNAPSHOT)
          ? window.SETTINGS_SNAPSHOT[key]
          : !value;
      }
      window._ps_pending[key] = value;
      window.SETTINGS_SNAPSHOT[key] = value;
      showBar();
    }

    async function saveChanges() {
      const keys = Object.keys(window._ps_pending);
      if (!keys.length) { hideBar(); return; }
      const btn = document.getElementById("save-btn");
      if (btn) btn.disabled = true;
      try {
        for (const key of keys) {
          await _saveOne(key, window._ps_pending[key]);
          window.LOADED[key] = window._ps_pending[key];
          delete window._ps_original[key];
          delete window._ps_pending[key];
        }
      } catch (e) {
        if (typeof window.showToast === "function") {
          window.showToast("Some changes failed to save.", "error");
        }
      } finally {
        if (btn) btn.disabled = false;
        hideBar();
      }
    }

    function discardChanges() {
      const reverted = Object.assign({}, window.LOADED);
      for (const k of Object.keys(window._ps_pending)) {
        if (k in window._ps_original) reverted[k] = window._ps_original[k];
        delete window._ps_pending[k];
      }
      for (const k of Object.keys(window._ps_original)) delete window._ps_original[k];
      window.SETTINGS_SNAPSHOT = reverted;
      _render();
      hideBar();
    }

    function load(settings) {
      window.SETTINGS_SNAPSHOT = Object.assign({}, settings);
      window.LOADED = Object.assign({}, settings);
      window._ps_original = {};
      window._ps_pending = {};
      _render();
      hideBar();
    }

    function init(opts) {
      _render = (opts && opts.render) ? opts.render : _render;
      _saveOne = (opts && opts.saveOne) ? opts.saveOne : _saveOne;
      if (!_bound) {
        const sb = document.getElementById("save-btn");
        const db = document.getElementById("discard-btn");
        if (sb) sb.addEventListener("click", saveChanges);
        if (db) db.addEventListener("click", discardChanges);
        _bound = true;
      }
    }

    // Bare-name aliases so existing page code calling markChanged()/saveChanges()
    // without the ProwlSettings prefix keeps working during migration.
    window.markChanged = markChanged;
    window.saveChanges = saveChanges;
    window.discardChanges = discardChanges;

    return { init, markChanged, saveChanges, discardChanges, load, showBar, hideBar };
  })();
})();
