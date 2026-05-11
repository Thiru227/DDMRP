(function () {
  const { api, fmt, setSnapshotStatus, alertPill } = window.DDMRP;

  const EDITABLE = {
    on_hand_qty: 0, on_order_qty: 0, qualified_demand_qty: 0,
    moq: 0, dlt: 1, ltf: 3, vf: 3, doc: 1,
  };

  let allRows = [];
  let pollHandle = null;

  function rowHtml(r) {
    const flagged = r.flagged_diff ? ' title="Engine vs source diff flagged"' : "";
    const fld = (key) => {
      const digits = EDITABLE[key];
      const val = r[key];
      const display = (val === null || val === undefined) ? "" : Number(val).toFixed(digits);
      return `<td class="editable num"><input data-field="${key}" value="${display}"></td>`;
    };
    const num = (v, d = 1) => `<td class="num">${fmt.num(v, d)}</td>`;
    return `
      <tr data-msku="${escapeAttr(r.msku_code)}" data-branch="${escapeAttr(r.branch_code)}"${flagged}>
        <td title="${escapeAttr(r.msku_code)}">${truncate(r.msku_code, 36)}</td>
        <td>${r.branch_code}</td>
        <td>${alertPill(r.alert_level)}</td>
        ${fld("on_hand_qty")}${fld("on_order_qty")}${fld("qualified_demand_qty")}
        ${num(r.adu, 2)}${num(r.red_zone)}${num(r.yellow_zone)}${num(r.green_zone)}${num(r.tog)}
        ${num(r.net_flow)}${num(r.planning_priority, 2)}${num(r.order_recommendation, 0)}
        ${fld("moq")}${fld("dlt")}${fld("ltf")}${fld("vf")}${fld("doc")}
      </tr>`;
  }

  function render() {
    const branch = document.getElementById("filter-branch").value;
    const alert  = document.getElementById("filter-alert").value;
    const q = document.getElementById("filter-search").value.trim().toLowerCase();
    let rows = allRows;
    if (branch) rows = rows.filter((r) => r.branch_code === branch);
    if (alert)  rows = rows.filter((r) => r.alert_level === alert);
    if (q)      rows = rows.filter((r) => (r.msku_code || "").toLowerCase().includes(q));
    document.querySelector("#planning-table tbody").innerHTML =
      rows.map(rowHtml).join("") || `<tr><td colspan="19" class="hint">No matching rows.</td></tr>`;
  }

  function populateBranches() {
    const sel = document.getElementById("filter-branch");
    const cur = sel.value;
    const branches = [...new Set(allRows.map((r) => r.branch_code))].sort();
    sel.innerHTML = `<option value="">All branches</option>` +
      branches.map((b) => `<option value="${b}">${b}</option>`).join("");
    if (branches.includes(cur)) sel.value = cur;
  }

  async function refresh() {
    try {
      const data = await api("/api/planning/snapshot");
      setSnapshotStatus(data.snapshot_date);
      allRows = data.items;
      populateBranches();
      render();
    } catch (e) { console.error(e); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("filter-search").addEventListener("input", render);
    document.getElementById("filter-branch").addEventListener("change", render);
    document.getElementById("filter-alert").addEventListener("change", render);
    document.getElementById("refresh-now").addEventListener("click", refresh);

    document.querySelector("#planning-table tbody").addEventListener("change", async (ev) => {
      const input = ev.target.closest("input[data-field]");
      if (!input) return;
      const tr = input.closest("tr");
      const msku = tr.dataset.msku, branch = tr.dataset.branch;
      const field = input.dataset.field;
      const value = parseFloat(input.value);
      if (Number.isNaN(value)) return;
      tr.classList.add("saving");
      try {
        const updated = await api(
          `/api/planning/${encodeURIComponent(msku)}/${encodeURIComponent(branch)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ [field]: value }),
          }
        );
        const idx = allRows.findIndex((r) => r.msku_code === msku && r.branch_code === branch);
        if (idx >= 0) {
          allRows[idx] = { ...allRows[idx], [field]: value, ...updated };
          render();
          const newRow = document.querySelector(`tr[data-msku="${cssEscape(msku)}"][data-branch="${branch}"]`);
          if (newRow) newRow.classList.add("flash");
        }
      } catch (e) {
        alert("Save failed: " + e.message);
      } finally {
        tr.classList.remove("saving");
      }
    });

    refresh();
    pollHandle = setInterval(refresh, 10000);
  });

  function truncate(s, n) { return s && s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function escapeAttr(s) { return String(s ?? "").replace(/"/g, "&quot;"); }
  function cssEscape(s) { return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/"/g, '\\"'); }
})();
