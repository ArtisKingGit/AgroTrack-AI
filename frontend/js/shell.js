/**
 * AgroTrack AI Shared Shell & Navigation Controller
 * Manages the persistent sidebar, topbar, user profile, role switcher, and auth state.
 * Preserves authentic AgroFast visual identity and colours.
 * Development-only role switcher gating (hidden in production mode).
 */

(function () {
  const ROLES = [
    { id: "admin", label: "Organisation Administrator", badgeColor: "#22c55e", token: "mock-token-admin", name: "Sarah Mwangi" },
    { id: "manager", label: "Project Manager", badgeColor: "#14b8a6", token: "mock-token-manager", name: "David Kiprop" },
    { id: "field", label: "Field Officer", badgeColor: "#38bdf8", token: "mock-token-field", name: "Amina Otieno" },
    { id: "analyst", label: "Analyst", badgeColor: "#a855f7", token: "mock-token-analyst", name: "Brian Njoroge" },
    { id: "viewer", label: "Viewer", badgeColor: "#94a3b8", token: "mock-token-viewer", name: "Grace Wanjiku" }
  ];

  let clientConfig = {
    environment: "development",
    allowDevMockAuth: true
  };

  // Retrieve current active role from localStorage or default to Admin
  function getActiveRole() {
    const saved = localStorage.getItem("agrotrack-active-role");
    const found = ROLES.find(r => r.id === saved || r.label === saved);
    return found || ROLES[0];
  }

  function setActiveRole(roleId) {
    if (!clientConfig.allowDevMockAuth) {
      console.warn("Role switching is disabled in production mode.");
      return;
    }
    const found = ROLES.find(r => r.id === roleId);
    if (found) {
      localStorage.setItem("agrotrack-active-role", found.id);
      localStorage.setItem("agrotrack-auth-token", found.token);
      window.location.reload();
    }
  }

  // Detect current page from URL
  function getCurrentPage() {
    const path = window.location.pathname.split("/").pop();
    return path || "overview.html";
  }

  function renderSidebar(activePage, currentRole) {
    const sidebarEl = document.getElementById("appSidebar");
    if (!sidebarEl) return;

    sidebarEl.className = "app-sidebar";
    sidebarEl.innerHTML = `
      <a href="overview.html" class="sidebar-brand">
        <div class="brand-icon">
          <i class="fas fa-leaf"></i>
        </div>
        <div class="brand-text">
          <h1>AgroTrack AI</h1>
          <span>Agri-Intelligence Platform</span>
        </div>
      </a>

      <div class="sidebar-org">
        <div class="org-label">Active Organisation</div>
        <div class="org-card">
          <div class="org-badge">
            <i class="fas fa-building"></i>
          </div>
          <div class="org-info">
            <div class="org-name" id="shellOrgName">GreenValley AgTech</div>
            <div class="org-tier"><i class="fas fa-shield-halved"></i> Enterprise Tier</div>
          </div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section-title">Core Platform</div>
        
        <a href="overview.html" class="nav-item ${activePage === "overview.html" ? "active" : ""}">
          <i class="fas fa-chart-pie"></i>
          <span>Overview</span>
        </a>

        <div class="nav-section-title">Capabilities</div>

        <a href="track.html" class="nav-item ${activePage === "track.html" || activePage === "manage.html" || activePage === "dashboard.html" ? "active" : ""}">
          <i class="fas fa-seedling"></i>
          <span>AgroTrack</span>
          <span class="nav-tag tag-active">Active</span>
        </a>

        <a href="marketlens.html" class="nav-item ${activePage === "marketlens.html" ? "active" : ""}">
          <i class="fas fa-chart-line"></i>
          <span>MarketLens</span>
          <span class="nav-tag tag-active">Active</span>
        </a>

        <a href="impactos.html" class="nav-item ${activePage === "impactos.html" ? "active" : ""}">
          <i class="fas fa-hands-holding-circle"></i>
          <span>ImpactOS</span>
          <span class="nav-tag tag-active">Active</span>
        </a>

        <a href="analyst.html" class="nav-item ${activePage === "analyst.html" ? "active" : ""}">
          <i class="fas fa-brain"></i>
          <span>AI Analyst</span>
          <span class="nav-tag tag-active">Active</span>
        </a>

        <div class="nav-section-title">Administration</div>

        <a href="settings.html" class="nav-item ${activePage === "settings.html" ? "active" : ""}">
          <i class="fas fa-gear"></i>
          <span>Settings</span>
        </a>
      </nav>

      <div class="sidebar-footer">
        <div class="user-profile-widget">
          <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(currentRole.name)}&background=020617&color=22c55e" alt="Profile" class="user-avatar" id="shellUserAvatar">
          <div class="user-meta">
            <div class="user-name" id="shellUserName">${currentRole.name}</div>
            <span class="user-role-badge" style="background: rgba(34, 197, 94, 0.15); color: ${currentRole.badgeColor};">${currentRole.label}</span>
          </div>
          <button class="logout-btn" id="shellLogoutBtn" title="Log Out">
            <i class="fas fa-arrow-right-from-bracket"></i>
          </button>
        </div>
      </div>
    `;

    // Logout listener
    const logoutBtn = document.getElementById("shellLogoutBtn");
    if (logoutBtn) {
      logoutBtn.onclick = () => {
        localStorage.removeItem("agrotrack-auth-token");
        window.location.href = "login.html";
      };
    }
  }

  function renderTopbar(activePage, currentRole) {
    const topbarEl = document.getElementById("appTopbar");
    if (!topbarEl) return;

    const pageTitles = {
      "overview.html": "Platform Overview",
      "track.html": "AgroTrack — Farm & Field Operations",
      "marketlens.html": "MarketLens — Market Intelligence",
      "impactos.html": "ImpactOS — Projects & Impact",
      "analyst.html": "AI Analyst — Agri-Intelligence Layer",
      "settings.html": "Settings & Platform Config"
    };

    const title = pageTitles[activePage] || "AgroTrack AI";

    let roleControlHtml = "";
    if (clientConfig.allowDevMockAuth) {
      // Development mode: role switcher enabled for testing
      roleControlHtml = `
        <label for="roleSwitcher" style="font-size: 0.75rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
          <i class="fas fa-user-shield"></i> <span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; padding: 1px 5px; border-radius: 4px; font-size: 0.65rem; font-weight: 700;">DEV</span> Role:
        </label>
        <select id="roleSwitcher" class="role-switcher-select" title="Switch active role for development testing">
          ${ROLES.map(r => `<option value="${r.id}" ${r.id === currentRole.id ? "selected" : ""}>${r.label}</option>`).join("")}
        </select>
      `;
    } else {
      // Production mode: strictly read-only authenticated role display
      roleControlHtml = `
        <div style="display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: var(--text-secondary); background: rgba(15, 23, 42, 0.7); padding: 5px 12px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.08);">
          <i class="fas fa-shield-halved" style="color: #22c55e;"></i>
          <span style="font-weight: 600; color: #f1f5f9;">${currentRole.label}</span>
        </div>
      `;
    }

    topbarEl.className = "app-topbar";
    topbarEl.innerHTML = `
      <div class="topbar-left">
        <button class="mobile-menu-toggle" id="mobileMenuBtn" aria-label="Toggle menu">
          <i class="fas fa-bars"></i>
        </button>
        <div class="breadcrumbs">
          <span>AgroTrack AI</span> <i class="fas fa-chevron-right" style="font-size: 0.65rem; margin: 0 6px;"></i> <span class="current">${title}</span>
        </div>
      </div>

      <div class="topbar-right">
        <div id="shellSyncPill" class="sync-pill online" title="Platform connectivity: Online" style="cursor: pointer;" onclick="if(window.agrotrackOfflineSync) window.agrotrackOfflineSync.openSyncQueueModal();">
          <i class="fas fa-circle-check"></i> <span>Online</span>
        </div>

        ${roleControlHtml}

        <button class="topbar-action-btn" title="Notifications" id="notifyBellBtn">
          <i class="fas fa-bell"></i>
        </button>
      </div>
    `;

    // Role switcher listener (if in dev mode)
    const switcher = document.getElementById("roleSwitcher");
    if (switcher) {
      switcher.onchange = (e) => setActiveRole(e.target.value);
    }

    // Mobile menu toggle
    const mobileBtn = document.getElementById("mobileMenuBtn");
    const sidebar = document.getElementById("appSidebar");
    if (mobileBtn && sidebar) {
      mobileBtn.onclick = () => {
        sidebar.classList.toggle("open");
      };
    }
  }

  async function fetchClientConfig() {
    try {
      const resp = await fetch("/api/v1/config");
      if (resp.ok) {
        clientConfig = await resp.json();
      }
    } catch (_) {
      // Offline fallback: keep current config
    }
  }

  // Initialize Shell on DOM ready
  document.addEventListener("DOMContentLoaded", async () => {
    await fetchClientConfig();
    const activePage = getCurrentPage();
    const currentRole = getActiveRole();
    renderSidebar(activePage, currentRole);
    renderTopbar(activePage, currentRole);
    if (window.agrotrackOfflineSync) {
      window.agrotrackOfflineSync.updateUI();
    }
  });

  // Expose API helper
  window.AgroTrack = {
    getActiveRole,
    setActiveRole,
    getAuthToken: () => localStorage.getItem("agrotrack-auth-token") || getActiveRole().token,
    getConfig: () => clientConfig
  };
})();
