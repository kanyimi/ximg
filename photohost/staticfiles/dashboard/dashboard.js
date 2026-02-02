(function () {
  const shell = document.getElementById("dashboardShell");
  const content = document.getElementById("dashContent");
  const toggle = document.getElementById("dashToggle");
  const navLinks = document.querySelectorAll(".dash-nav .dash-link[data-route]");

  const partialMap = {
    stats: "/dashboard/partials/stats/",
    sections: "/dashboard/partials/sections/",
    files: "/dashboard/partials/files/",
    secret_notes: "/dashboard/partials/secret-notes/",
    twofa: "/dashboard/partials/2fa/",
  };

  function setActive(route) {
    navLinks.forEach((a) => {
      a.classList.toggle("active", a.dataset.route === route);
    });
  }

  function prettyUrlFor(route) {
    if (route === "stats") return "/dashboard/stats/";
    if (route === "sections") return "/dashboard/sections/";
    if (route === "files") return "/dashboard/files/";
    if (route === "secret_notes") return "/dashboard/secret-notes/";
    if (route === "twofa") return "/dashboard/2fa/";
    return "/dashboard/stats/";
  }

  async function loadRoute(route, params = {}, push = true) {
    const partial = partialMap[route];
    if (!partial) {
      content.innerHTML = `<div class="dash-error">Unknown route: ${route}</div>`;
      return;
    }

    const url = new URL(partial, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).length) url.searchParams.set(k, v);
    });

    setActive(route);
    content.innerHTML = `<div class="dash-loading">Loading...</div>`;

    const res = await fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });

    if (!res.ok) {
      content.innerHTML = `<div class="dash-error">Failed to load (${res.status}).</div>`;
      return;
    }

    content.innerHTML = await res.text();

    if (push) {
      const newUrl = new URL(prettyUrlFor(route), window.location.origin);

      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && String(v).length) newUrl.searchParams.set(k, v);
      });

      history.pushState({ route, params }, "", newUrl.toString());
    }

    wireDynamicForms(route);
  }

  function getCsrfToken() {
    // Django CSRF token (works if your base template includes {% csrf_token %} in forms)
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : "";
  }

  async function postAndReload(route, postUrl, formEl) {
    const fd = new FormData(formEl);
    const csrf = getCsrfToken();

    const res = await fetch(postUrl, {
      method: "POST",
      body: fd,
      headers: csrf ? { "X-CSRFToken": csrf } : {},
      credentials: "same-origin",
    });

    if (!res.ok) {
      // Try to show server errors if returned as html
      const txt = await res.text();
      content.innerHTML = txt || `<div class="dash-error">Action failed (${res.status}).</div>`;
      // Re-wire because content changed
      wireDynamicForms(route);
      return;
    }

    // Reload the same route to refresh status
    await loadRoute(route, {}, false);
  }

  function wireDynamicForms(route) {
    // Stats range form
    if (route === "stats") {
      const form = document.getElementById("statsRangeForm");
      if (form) {
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const fd = new FormData(form);
          loadRoute("stats", { start: fd.get("start"), end: fd.get("end") });
        });
      }
    }

    // Sections search
    if (route === "sections") {
      const form = document.getElementById("sectionsSearchForm");
      if (form) {
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const fd = new FormData(form);
          loadRoute("sections", { q: fd.get("q") });
        });
      }
    }

    // Files search
    if (route === "files") {
      const form = document.getElementById("filesSearchForm");
      if (form) {
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const fd = new FormData(form);
          loadRoute("files", { q: fd.get("q") });
        });
      }
    }

    // Secret notes: search + tabs + modal
    if (route === "secret_notes") {
      // Search
      const form = document.getElementById("notesSearchForm");
      if (form) {
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const fd = new FormData(form);
          loadRoute("secret_notes", { q: fd.get("q") });
        });
      }

      // Tabs (Active / Retention / Flagged)
      const tabActiveBtn = document.getElementById("tab-active-btn");
      const tabRetentionBtn = document.getElementById("tab-retention-btn");
      const tabFlaggedBtn = document.getElementById("tab-flagged-btn");

      const tabActive = document.getElementById("tab-active");
      const tabRetention = document.getElementById("tab-retention");
      const tabFlagged = document.getElementById("tab-flagged");

      const tabs = [
        { key: "active", btn: tabActiveBtn, pane: tabActive },
        { key: "retention", btn: tabRetentionBtn, pane: tabRetention },
        { key: "flagged", btn: tabFlaggedBtn, pane: tabFlagged },
      ].filter((t) => t.btn && t.pane);

      const setTab = (key) => {
        tabs.forEach((t) => {
          const isOn = t.key === key;
          t.btn.classList.toggle("is-active", isOn);
          t.pane.classList.toggle("is-active", isOn);
          t.btn.setAttribute("aria-selected", isOn ? "true" : "false");
        });
      };

      tabs.forEach((t) => t.btn.addEventListener("click", () => setTab(t.key)));
      if (tabs.length) setTab(tabs[0].key);

      // Modal (shared)
      const modal = document.getElementById("retentionModal");
      const modalId = document.getElementById("retentionModalId");
      const modalText = document.getElementById("retentionModalText");
      const copyBtn = document.getElementById("retentionCopyBtn");

      function openModal(noteId, plaintext) {
        if (!modal) return;
        if (modalId) modalId.textContent = noteId || "";
        if (modalText) modalText.value = plaintext || "";
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
      }

      function closeModal() {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
      }

      // Bind view buttons (your class)
      document.querySelectorAll(".js-view-note").forEach((btn) => {
        btn.addEventListener("click", () => {
          const noteId = btn.getAttribute("data-note-id") || "";
          const plaintext = btn.getAttribute("data-plaintext") || "";
          openModal(noteId, plaintext);

          const pane = btn.closest(".dash-tabpane");
          if (pane?.id === "tab-retention") setTab("retention");
          if (pane?.id === "tab-flagged") setTab("flagged");
        });
      });

      // Close handlers
      if (modal) {
        modal.querySelectorAll("[data-close='1']").forEach((el) => {
          el.addEventListener("click", closeModal);
        });

        if (!document.__dashModalEscBound) {
          document.__dashModalEscBound = true;
          document.addEventListener("keydown", (e) => {
            const m = document.getElementById("retentionModal");
            if (e.key === "Escape" && m && m.classList.contains("is-open")) closeModal();
          });
        }
      }

      // Copy plaintext
      if (copyBtn && modalText) {
        copyBtn.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(modalText.value || "");
            copyBtn.innerHTML = `<i class="fa-solid fa-check"></i> Copied`;
            setTimeout(() => {
              copyBtn.innerHTML = `<i class="fa-regular fa-copy"></i> Copy`;
            }, 1200);
          } catch {
            modalText.focus();
            modalText.select();
            document.execCommand("copy");
          }
        });
      }
    }

    // ✅ 2FA settings partial: enable/disable without leaving shell
    if (route === "twofa") {
      // If your 2FA partial includes forms, wire them here.
      // Expected:
      // - form#twofaEnableForm action="/dashboard/2fa/enable/" (or whatever you use)
      // - form#twofaDisableForm action="/dashboard/2fa/disable/"
      const enableForm = document.getElementById("twofaEnableForm");
      if (enableForm) {
        enableForm.addEventListener("submit", (e) => {
          e.preventDefault();
          postAndReload("twofa", enableForm.action, enableForm);
        });
      }

      const disableForm = document.getElementById("twofaDisableForm");
      if (disableForm) {
        disableForm.addEventListener("submit", (e) => {
          e.preventDefault();
          postAndReload("twofa", disableForm.action, disableForm);
        });
      }
    }
  }

  // Sidebar collapse
  if (shell && window.matchMedia("(max-width: 768px)").matches) {
    shell.classList.add("is-collapsed");
  }
  if (toggle && shell) {
    toggle.addEventListener("click", () => shell.classList.toggle("is-collapsed"));
  }

  // Intercept SPA nav clicks (only data-route links)
  navLinks.forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      loadRoute(a.dataset.route);
    });
  });

  // Back/forward buttons
  window.addEventListener("popstate", (e) => {
    const st = e.state;
    if (st && st.route) loadRoute(st.route, st.params || {}, false);
  });

  // Initial route based on URL path
  const path = window.location.pathname;

  const initial =
    path.includes("/dashboard/sections/") ? "sections" :
    path.includes("/dashboard/files/") ? "files" :
    path.includes("/dashboard/secret-notes/") ? "secret_notes" :
    path.includes("/dashboard/2fa/") ? "twofa" :
    (shell?.dataset.initialRoute || "stats");

  // Preserve query params
  const params = Object.fromEntries(new URL(window.location.href).searchParams.entries());
  loadRoute(initial, params, false);
})();
