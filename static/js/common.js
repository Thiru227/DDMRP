window.DDMRP = (function () {
  const fmt = {
    num(v, digits = 1) {
      if (v === null || v === undefined || v === "") return "–";
      const n = Number(v);
      if (!Number.isFinite(n)) return "–";
      return n.toLocaleString(undefined, { maximumFractionDigits: digits });
    },
    int(v) { return this.num(v, 0); },
    date(s) { return s || "–"; },
  };

  async function api(path, opts = {}) {
    const r = await fetch(path, { headers: { "Accept": "application/json" }, ...opts });
    if (!r.ok) {
      let body; try { body = await r.json(); } catch { body = { error: r.statusText }; }
      const err = new Error(body.error || `HTTP ${r.status}`);
      err.status = r.status; err.body = body;
      throw err;
    }
    return r.json();
  }

  function setSnapshotStatus(date) {
    const el = document.getElementById("snapshot-status");
    if (el) el.textContent = date ? `Snapshot: ${date}` : "No data yet";
  }

  function highlightNav() {
    const path = location.pathname;
    document.querySelectorAll("nav a[data-nav]").forEach((a) => {
      const matches =
        (a.dataset.nav === "dashboard" && path === "/") ||
        (a.dataset.nav === "planning"  && path.startsWith("/planning")) ||
        (a.dataset.nav === "upload"    && path.startsWith("/upload") && !path.startsWith("/uploads")) ||
        (a.dataset.nav === "alerts"    && path.startsWith("/alerts")) ||
        (a.dataset.nav === "history"   && path.startsWith("/uploads/history"));
      if (matches) a.classList.add("active");
    });
  }

  function alertPill(level) {
    return `<span class="alert-pill ${level}">${level}</span>`;
  }

  function poll(fn, ms = 5000) {
    fn();
    return setInterval(fn, ms);
  }

  document.addEventListener("DOMContentLoaded", highlightNav);

  return { api, fmt, setSnapshotStatus, alertPill, poll };
})();
