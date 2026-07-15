(() => {
  "use strict";

  // ========================= CONFIG =========================

  const POLL_INTERVAL = 30000;
  const SIDEBAR_KEY = "prowl_sidebar";
  const QUICK_LINKS_KEY = "prowl_quick_links";
  const SIDEBAR_MIN = 220;
  const SIDEBAR_MAX = 420;
  const SIDEBAR_DEFAULT = 280;

  const GUILD_ID = window.__GUILD_ID;
  const ACTIVE_PANEL = window.__ACTIVE_PANEL;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ========================= LOADING BAR =========================

  const bar = $("#loading-bar");
  let barTimer;

  function showBar() {
    clearTimeout(barTimer);
    bar.style.width = "0%";
    bar.classList.add("is-visible");
    requestAnimationFrame(() => { bar.style.width = "60%"; });
  }

  function hideBar() {
    bar.style.width = "100%";
    barTimer = setTimeout(() => {
      bar.classList.remove("is-visible");
      bar.style.width = "0%";
    }, 300);
  }

  // ========================= SIDEBAR: TOGGLE =========================

  function initSidebarToggle() {
    const sidebar = $("#sidebar");
    const toggle = $("#sidebar-toggle");
    const shell = $("#app-shell");
    const saved = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");

    if (saved.collapsed) {
      sidebar.classList.add("is-collapsed");
      shell.style.gridTemplateColumns = "72px 1fr";
    }

    toggle.addEventListener("click", () => {
      const isCollapsed = sidebar.classList.toggle("is-collapsed");
      shell.style.gridTemplateColumns = isCollapsed ? "72px 1fr" : `${sidebar.offsetWidth}px 1fr`;
      localStorage.setItem(SIDEBAR_KEY, JSON.stringify({ ...saved, collapsed: isCollapsed }));
    });
  }

  // ========================= SIDEBAR: RESIZE =========================

  function initSidebarResize() {
    const sidebar = $("#sidebar");
    const handle = $("#sidebar-resize");
    const shell = $("#app-shell");
    const saved = JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "{}");

    if (saved.width && !sidebar.classList.contains("is-collapsed")) {
      sidebar.style.width = saved.width + "px";
      shell.style.gridTemplateColumns = saved.width + "px 1fr";
    }

    let dragging = false;
    handle.addEventListener("mousedown", (e) => {
      if (sidebar.classList.contains("is-collapsed")) return;
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
      shell.style.gridTemplateColumns = w + "px 1fr";
    });

    document.addEventListener("mouseup", () => {
      if (!dragging) return;
      dragging = false;
      handle.classList.remove("is-dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      const w = sidebar.offsetWidth;
      localStorage.setItem(SIDEBAR_KEY, JSON.stringify({ collapsed: false, width: w }));
    });
  }

  // ========================= USER POPOVER =========================

  function initUserPopover() {
    const btn = $("#user-menu-btn");
    const pop = $("#user-popover");
    if (!btn || !pop) return;

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      pop.classList.toggle("hidden");
    });

    document.addEventListener("click", () => {
      pop.classList.add("hidden");
    });
  }

  // ========================= QUICK SETUP BANNER =========================

  function initQuickSetup() {
    const key = `prowl_setup_done_${GUILD_ID}`;
    if (!localStorage.getItem(key)) {
      $("#quick-setup-banner")?.classList.remove("hidden");
    }

    $$(".nav-item[data-panel]").forEach((item) => {
      if (item.dataset.panel === "quick-setup") {
        item.addEventListener("click", () => {
          localStorage.setItem(key, "1");
          $("#quick-setup-banner")?.classList.add("hidden");
        });
      }
    });
  }

  // ========================= QUICK LINKS =========================

  function getQuickLinks() {
    try {
      return JSON.parse(localStorage.getItem(QUICK_LINKS_KEY) || "{}");
    } catch { return {}; }
  }

  function trackVisit(panel) {
    if (panel === "overview" || panel === "quick-setup" || panel === "settings") return;
    const links = getQuickLinks();
    links[panel] = (links[panel] || 0) + 1;
    localStorage.setItem(QUICK_LINKS_KEY, JSON.stringify(links));
  }

  function renderQuickLinks(container) {
    const links = getQuickLinks();
    const sorted = Object.entries(links)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    if (sorted.length < 2) return;

    const PANEL_META = {
      ai: { icon: "sparkles", label: "AI" },
      welcomer: { icon: "hand-wave", label: "Welcomer" },
      verification: { icon: "shield-check", label: "Verification" },
      roles: { icon: "palette", label: "Roles" },
      leveling: { icon: "trending-up", label: "Leveling" },
      commands: { icon: "terminal", label: "Commands" },
      lideration: { icon: "shield", label: "Lideration" },
      logs: { icon: "scroll-text", label: "Logs" },
      statistics: { icon: "bar-chart-3", label: "Statistics" },
      music: { icon: "music", label: "Music" },
    };

    const cards = sorted.map(([panel, count]) => {
      const meta = PANEL_META[panel] || { icon: "circle", label: panel };
      return `
        <a href="/guild/${GUILD_ID}/${panel}" data-nav-panel="${panel}"
           class="flex items-center gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.08]
                  hover:bg-white/[0.05] hover:border-brand/25 hover:-translate-y-[2px]
                  hover:shadow-[0_6px_18px_rgba(0,0,0,0.25)]
                  transition-all duration-200 cursor-pointer group">
          <div class="w-10 h-10 rounded-xl grid place-items-center bg-brand/10 shrink-0 group-hover:bg-brand/15 transition-colors">
            <i data-lucide="${meta.icon}" class="w-5 h-5 text-brand-light"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-[13px] font-bold truncate">${meta.label}</div>
            <div class="text-[11px] text-white/40 font-semibold">${count} visit${count !== 1 ? "s" : ""}</div>
          </div>
        </a>`;
    }).join("");

    container.innerHTML = `
      <div class="mb-5 anim-fade-in-up" style="animation-delay:.05s">
        <h2 class="text-sm font-extrabold uppercase tracking-[0.08em] text-white/40 mb-3">Quick Links</h2>
        <div class="grid grid-cols-5 gap-3 max-xl:grid-cols-3 max-md:grid-cols-2 max-sm:grid-cols-1">${cards}</div>
      </div>`;

    lucide.createIcons();

    container.querySelectorAll("[data-nav-panel]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        navigateTo(el.dataset.navPanel);
      });
    });
  }

  // ========================= PAGE CONTENT =========================

  const PANEL_TITLES = {
    overview: "Overview",
    ai: "AI",
    welcomer: "Welcomer",
    verification: "Verification",
    roles: "Roles",
    leveling: "Leveling",
    commands: "Slash Commands",
    lideration: "Lideration",
    logs: "Logs",
    statistics: "Statistics",
    music: "Music",
    settings: "Settings",
    "quick-setup": "Quick Setup",
  };

  function overviewHTML() {
    return `
      <div class="mb-5 anim-fade-in-up" style="animation-delay:.05s">
        <h1 class="text-[26px] font-black tracking-tight leading-tight">Overview</h1>
        <p class="text-white/50 text-sm font-semibold mt-0.5">Live stats from your bot</p>
      </div>
      <div id="quick-links-area" class="mb-2"></div>
      <div class="grid grid-cols-4 gap-3.5 mb-4 max-lg:grid-cols-2 max-sm:grid-cols-1">
        ${statCard("globe", "Servers", "stat-guilds", 0.1)}
        ${statCard("users", "Users", "stat-users", 0.15)}
        ${statCard("clock", "Uptime", "stat-uptime", 0.2)}
        ${statCard("hard-drive", "Memory", "stat-memory", 0.25)}
      </div>
      <div class="grid grid-cols-4 gap-3.5 max-lg:grid-cols-2 max-sm:grid-cols-1 anim-fade-in-up" style="animation-delay:.3s">
        ${detailCard("Channels", "stat-channels")}
        ${detailCard("Roles", "stat-roles")}
        ${detailCard("Emojis", "stat-emojis")}
        ${detailCard("CPU", "stat-cpu")}
      </div>`;
  }

  function statCard(icon, label, id, delay) {
    return `
      <div class="flex items-center gap-3.5 p-4 rounded-2xl bg-white/[0.025] border border-white/[0.08]
                  transition-all duration-250 hover:-translate-y-[3px] hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] hover:border-brand/25
                  anim-fade-in-up" style="animation-delay:${delay}s">
        <div class="w-12 h-12 rounded-[14px] grid place-items-center bg-brand/10 shrink-0">
          <i data-lucide="${icon}" class="w-6 h-6 text-brand-light"></i>
        </div>
        <div class="flex flex-col gap-0.5">
          <div class="text-[24px] font-black tracking-tight" data-counter="0" id="${id}">—</div>
          <div class="text-[11.5px] text-white/50 font-bold uppercase tracking-[0.04em]">${label}</div>
        </div>
      </div>`;
  }

  function detailCard(label, id) {
    return `
      <div class="p-3.5 px-4 rounded-[10px] bg-white/[0.02] border border-white/[0.08] transition-all duration-250 hover:-translate-y-[2px] hover:shadow-[0_6px_18px_rgba(0,0,0,0.25)]">
        <div class="text-[11px] text-white/50 font-extrabold uppercase tracking-[0.04em] mb-1">${label}</div>
        <div class="text-xl font-black" id="${id}">—</div>
      </div>`;
  }

  function placeholderHTML(title) {
    return `
      <div class="mb-5 anim-fade-in-up" style="animation-delay:.05s">
        <h1 class="text-[26px] font-black tracking-tight leading-tight">${title}</h1>
      </div>
      <div class="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.03] to-white/[0.015]
                  shadow-[0_14px_40px_rgba(0,0,0,0.45)] p-5 anim-fade-in-up" style="animation-delay:.1s">
        <p class="text-white/40 text-sm font-semibold py-16 text-center">Coming soon.</p>
      </div>`;
  }

  function commandsHTML() {
    return `
      <div class="mb-5 anim-fade-in-up" style="animation-delay:.05s">
        <h1 class="text-[26px] font-black tracking-tight leading-tight">Slash Commands</h1>
        <p class="text-white/50 text-sm font-semibold mt-0.5">Registered application commands</p>
      </div>
      <div class="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.03] to-white/[0.015]
                  shadow-[0_14px_40px_rgba(0,0,0,0.45)] p-5 anim-fade-in-up" style="animation-delay:.1s">
        <div class="overflow-x-auto">
          <table class="w-full border-separate border-spacing-y-1.5" id="commands-table">
            <thead><tr>
              <th class="text-left py-2.5 px-3.5 text-[11px] text-white/50 font-extrabold uppercase tracking-[0.04em]">Command</th>
              <th class="text-left py-2.5 px-3.5 text-[11px] text-white/50 font-extrabold uppercase tracking-[0.04em]">Source Cog</th>
            </tr></thead>
            <tbody id="commands-tbody">
              <tr><td colspan="2"><div class="skeleton-row h-10 rounded-[10px]"></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>`;
  }

  function quickSetupHTML() {
    return `
      <div class="mb-5 anim-fade-in-up" style="animation-delay:.05s">
        <h1 class="text-[26px] font-black tracking-tight leading-tight">Quick Setup</h1>
        <p class="text-white/50 text-sm font-semibold mt-0.5">Get Prowl running in your server in minutes</p>
      </div>
      <div class="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.03] to-white/[0.015]
                  shadow-[0_14px_40px_rgba(0,0,0,0.45)] p-6 anim-fade-in-up" style="animation-delay:.1s">
        <div class="space-y-4">
          ${setupStep(1, "Create a #logs channel", "Prowl needs a channel named #logs for audit logging.")}
          ${setupStep(2, "Create a #welcome channel", "New members will be greeted here.")}
          ${setupStep(3, "Set up verification", "Configure a verification role and channel.")}
          ${setupStep(4, "Enable leveling", "Let members earn XP and level up.")}
        </div>
        <button id="finish-setup-btn"
                class="mt-6 w-full py-3 rounded-xl bg-brand hover:bg-brand/80 text-white font-bold text-sm transition-colors">
          I'm done — hide this
        </button>
      </div>`;
  }

  function setupStep(num, title, desc) {
    return `
      <div class="flex items-start gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <div class="w-8 h-8 rounded-lg grid place-items-center bg-brand/15 text-brand-light font-bold text-sm shrink-0">${num}</div>
        <div>
          <div class="text-sm font-bold">${title}</div>
          <div class="text-xs text-white/40 font-semibold mt-0.5">${desc}</div>
        </div>
      </div>`;
  }

  const PAGE_RENDERERS = {
    overview: overviewHTML,
    ai: () => placeholderHTML("AI"),
    welcomer: () => placeholderHTML("Welcomer"),
    verification: () => placeholderHTML("Verification"),
    roles: () => placeholderHTML("Roles"),
    leveling: () => placeholderHTML("Leveling"),
    commands: commandsHTML,
    lideration: () => placeholderHTML("Lideration"),
    logs: () => placeholderHTML("Logs"),
    statistics: () => placeholderHTML("Statistics"),
    music: () => placeholderHTML("Music"),
    settings: () => placeholderHTML("Settings"),
    "quick-setup": quickSetupHTML,
  };

  // ========================= NAVIGATION =========================

  let currentPanel = ACTIVE_PANEL;

  function initNav() {
    $$(".nav-item[data-panel]").forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const panel = item.dataset.panel;
        if (panel === currentPanel) return;
        navigateTo(panel);
      });
    });
  }

  function navigateTo(panel) {
    const url = `/guild/${GUILD_ID}/${panel}`;
    showBar();
    history.pushState({ panel }, "", url);

    // track quick links
    trackVisit(panel);
    setActiveNav(panel);
    renderPage(panel);

    // lazy load data
    if (panel === "overview") loadOverviewData();
    if (panel === "commands") loadCommands();

    setTimeout(hideBar, 350);
    currentPanel = panel;
  }

  function setActiveNav(panel) {
    $$(".nav-item").forEach((n) => n.classList.remove("is-active"));
    const target = $(`.nav-item[data-panel="${panel}"]`);
    if (target) target.classList.add("is-active");
  }

  function renderPage(panel) {
    const content = $("#app-content");
    const renderer = PAGE_RENDERERS[panel] || (() => placeholderHTML(PANEL_TITLES[panel] || panel));
    content.innerHTML = `<div class="anim-page-in">${renderer()}</div>`;
    lucide.createIcons();

    if (panel === "overview") {
      const qlArea = $("#quick-links-area");
      if (qlArea) renderQuickLinks(qlArea);
    }
  }

  // Handle browser back/forward
  window.addEventListener("popstate", (e) => {
    const panel = e.state?.panel || extractPanelFromURL() || "overview";
    setActiveNav(panel);
    renderPage(panel);
    if (panel === "overview") loadOverviewData();
    if (panel === "commands") loadCommands();
    currentPanel = panel;
  });

  function extractPanelFromURL() {
    const parts = window.location.pathname.split("/");
    return parts[parts.length - 1] || "overview";
  }

  // ========================= DATA LOADING =========================

  function animateCounter(el, target, duration = 800) {
    if (!el) return;
    const start = parseInt(el.textContent) || 0;
    if (start === target) return;
    const diff = target - start;
    const startTime = performance.now();
    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      el.textContent = Math.round(start + diff * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  async function pollStatus() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      const dot = $("#status-dot");
      const text = $("#status-text");
      const version = $("#bot-version");
      if (!dot) return;
      const isOnline = data.status === "online";
      dot.className = "w-2.5 h-2.5 rounded-full transition-colors duration-300 " + (isOnline ? "is-online" : "is-offline");
      text.textContent = isOnline ? "Online" : "Offline";
      version.textContent = data.version || "v—";

      if (currentPanel === "overview") updateOverviewStats(data);
    } catch {}
  }

  function loadOverviewData() {
    pollStatus();
  }

  function updateOverviewStats(data) {
    animateCounter($("#stat-guilds"), parseInt(data.guilds) || 0);
    animateCounter($("#stat-users"), parseInt(data.users) || 0);
    const up = $("#stat-uptime"); if (up) up.textContent = data.uptime || "—";
    const mem = $("#stat-memory"); if (mem) mem.textContent = data.memory_mb !== "N/A" ? `${data.memory_mb} MB` : "—";
    const ch = $("#stat-channels"); if (ch) ch.textContent = data.channels || "—";
    const rl = $("#stat-roles"); if (rl) rl.textContent = data.roles || "—";
    const em = $("#stat-emojis"); if (em) em.textContent = data.emojis || "—";
    const cp = $("#stat-cpu"); if (cp) cp.textContent = data.cpu_percent !== "N/A" ? `${data.cpu_percent}%` : "—";
  }

  async function loadCommands() {
    const tbody = $("#commands-tbody");
    if (!tbody) return;
    try {
      const res = await fetch("/api/commands");
      const json = await res.json();
      const commands = json.commands || [];
      const cogs = json.cogs || [];
      if (commands.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-white/50 text-sm font-semibold py-10 text-center">No commands registered.</td></tr>';
        return;
      }
      tbody.innerHTML = commands.map((cmd) => {
        const cog = cogs.find((c) => cmd.toLowerCase().includes(c.toLowerCase())) || "—";
        return `<tr class="bg-white/[0.02] transition-colors duration-150 hover:bg-white/[0.04]">
          <td class="py-3 px-3.5 font-extrabold text-sm rounded-l-[10px]">/${esc(cmd)}</td>
          <td class="py-3 px-3.5 text-white/50 text-sm rounded-r-[10px]">${esc(cog)}</td></tr>`;
      }).join("");
    } catch {
      tbody.innerHTML = '<tr><td colspan="2" class="text-white/50 text-sm py-10 text-center">Failed to load commands.</td></tr>';
    }
  }

  // ========================= INIT =========================

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
  }

  function initQuickSetupBtn() {
    document.addEventListener("click", (e) => {
      if (e.target.id === "finish-setup-btn") {
        localStorage.setItem(`prowl_setup_done_${GUILD_ID}`, "1");
        $("#quick-setup-banner")?.classList.add("hidden");
        navigateTo("overview");
      }
    });
  }

  async function init() {
    initSidebarToggle();
    initSidebarResize();
    initUserPopover();
    initQuickSetup();
    initQuickSetupBtn();
    initNav();

    // render initial page
    renderPage(currentPanel);
    if (currentPanel === "overview") loadOverviewData();
    if (currentPanel === "commands") loadCommands();

    await pollStatus();
    setInterval(pollStatus, POLL_INTERVAL);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
