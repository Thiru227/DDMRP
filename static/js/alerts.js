(function () {
  const { api, fmt, setSnapshotStatus, alertPill } = window.DDMRP;
  let allBranches = new Set();

  async function refresh() {
    const sev = document.getElementById("filter-severity").value;
    const br  = document.getElementById("filter-branch").value;
    const qs = new URLSearchParams();
    if (sev) qs.set("severity", sev);
    if (br)  qs.set("branch", br);

    try {
      const data = await api(`/api/alerts/?${qs}`);
      setSnapshotStatus(data.snapshot_date);
      document.querySelector('[data-count="red"]').textContent    = fmt.int(data.counts.red);
      document.querySelector('[data-count="yellow"]').textContent = fmt.int(data.counts.yellow);

      data.alerts.forEach((a) => allBranches.add(a.branch_code));
      const sel = document.getElementById("filter-branch");
      const cur = sel.value;
      sel.innerHTML = `<option value="">All branches</option>` +
        [...allBranches].sort().map((b) => `<option value="${b}">${b}</option>`).join("");
      sel.value = cur;

      document.querySelector("#alerts-table tbody").innerHTML = data.alerts.map((a) => `
        <tr>
          <td title="${escapeAttr(a.msku_code)}">${truncate(a.msku_code, 40)}</td>
          <td>${a.branch_code}</td>
          <td>${alertPill(a.alert_level)}</td>
          <td class="num">${fmt.num(a.net_flow)}</td>
          <td class="num">${fmt.num(a.red_zone)}</td>
          <td class="num">${fmt.num(a.toy)}</td>
          <td class="num">${fmt.num(a.tog)}</td>
          <td class="num">${fmt.num(a.order_recommendation, 0)}</td>
          <td class="num">${fmt.num(a.planning_priority, 2)}</td>
        </tr>`).join("") || `<tr><td colspan="9" class="hint">No active alerts.</td></tr>`;
    } catch (e) { console.error(e); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("filter-severity").addEventListener("change", refresh);
    document.getElementById("filter-branch").addEventListener("change", refresh);
    document.getElementById("refresh-now").addEventListener("click", refresh);
    refresh();
    setInterval(refresh, 10000);
  });

  function truncate(s, n) { return s && s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function escapeAttr(s) { return String(s ?? "").replace(/"/g, "&quot;"); }
})();
