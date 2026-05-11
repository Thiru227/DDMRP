(function () {
  const { api, fmt, setSnapshotStatus } = window.DDMRP;

  async function refresh() {
    try {
      const data = await api("/api/dashboard/summary");
      setSnapshotStatus(data.kpis.snapshot_date);
      for (const [k, v] of Object.entries(data.kpis)) {
        const el = document.querySelector(`[data-kpi="${k}"]`);
        if (el) el.textContent = (k === "order_recommendation_total") ? fmt.num(v, 0) : fmt.int(v);
      }

      const bbody = document.querySelector("#branches-table tbody");
      bbody.innerHTML = data.branches.map((b) => `
        <tr>
          <td>${b.branch_code}</td>
          <td class="num">${fmt.int(b.skus)}</td>
          <td class="num" style="color:var(--red)">${fmt.int(b.red)}</td>
          <td class="num" style="color:var(--yellow)">${fmt.int(b.yellow)}</td>
          <td class="num" style="color:var(--green)">${fmt.int(b.healthy)}</td>
          <td class="num">${fmt.num(b.order_total, 0)}</td>
        </tr>`).join("") || `<tr><td colspan="6" class="hint">No branch data yet — upload a CSV to get started.</td></tr>`;

      const ubody = document.querySelector("#uploads-table tbody");
      ubody.innerHTML = data.recent_uploads.map((u) => `
        <tr>
          <td>${u.filename}</td>
          <td>${u.status}</td>
          <td class="num">${fmt.int(u.total_rows)}</td>
          <td>${u.uploaded_at}</td>
        </tr>`).join("") || `<tr><td colspan="4" class="hint">No uploads yet.</td></tr>`;
    } catch (e) {
      console.error(e);
    }
  }

  window.DDMRP.poll(refresh, 5000);
})();
