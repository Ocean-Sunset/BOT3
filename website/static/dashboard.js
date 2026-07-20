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
    Object.assign(el.style, {
      position: "fixed",
      padding: "4px 8px",
      fontSize: "11px",
      fontWeight: "600",
      color: "#ccc",
      background: "#1a1a1a",
      border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: "4px",
      fontFamily: "'Lexend', system-ui, sans-serif",
      whiteSpace: "nowrap",
      pointerEvents: "none",
      zIndex: "99999",
      display: "none",
    });
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

    // Save scroll position before page unload
    nav.addEventListener("scroll", () => {
      const data = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");
      data.scrollTop = nav.scrollTop;
      localStorage.setItem(SIDEBAR_KEY, JSON.stringify(data));
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
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
