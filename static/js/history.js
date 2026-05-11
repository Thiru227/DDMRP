(function () {
  const { api, fmt } = window.DDMRP;

  async function refresh() {
    try {
      const data = await api("/api/uploads/history");
      document.querySelector("#history-table tbody").innerHTML = data.jobs.map((j) => `
        <tr>
          <td>${j.filename}</td>
          <td>${j.format}</td>
          <td>${j.status}</td>
          <td class="num">${fmt.int(j.total_rows)}</td>
          <td class="num">${fmt.int(j.valid_rows)}</td>
          <td class="num">${fmt.int(j.invalid_rows)}</td>
          <td>${j.uploaded_at || ""}</td>
          <td>${j.committed_at || ""}</td>
        </tr>`).join("") || `<tr><td colspan="8" class="hint">No uploads yet.</td></tr>`;
    } catch (e) { console.error(e); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    refresh();
    setInterval(refresh, 10000);
  });
})();
