(function () {
  const { api, fmt } = window.DDMRP;
  let currentJob = null;

  const dz = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const status = document.getElementById("upload-status");
  const previewCard = document.getElementById("preview-card");

  ["dragenter", "dragover"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("dragover"); }));
  dz.addEventListener("drop", (e) => {
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", (e) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  });

  async function handleFile(file) {
    setStatus(`Uploading ${file.name}…`, "");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const data = await api("/api/uploads/stock", { method: "POST", body: fd });
      currentJob = data.job_id;
      setStatus(`Parsed ${data.total_rows} rows from ${data.filename}.`, "ok");
      showPreview(data);
    } catch (e) {
      currentJob = null;
      previewCard.hidden = true;
      const missing = e.body?.missing_fields ? ` Missing: ${e.body.missing_fields.join(", ")}` : "";
      setStatus(`Upload failed: ${e.message}.${missing}`, "error");
    }
  }

  function showPreview(data) {
    previewCard.hidden = false;
    document.getElementById("preview-total").textContent = fmt.int(data.total_rows);
    document.getElementById("preview-valid").textContent = fmt.int(data.valid_rows);
    document.getElementById("preview-warnings").textContent = fmt.int(data.warnings?.length || 0);
    const tbody = document.querySelector("#preview-table tbody");
    tbody.innerHTML = data.preview.map((r) => `
      <tr>
        <td>${truncate(r.msku_code || "", 36)}</td>
        <td>${r.branch_code || ""}</td>
        <td class="num">${fmt.num(r.on_hand_qty, 0)}</td>
        <td class="num">${fmt.num(r.on_order_qty, 0)}</td>
        <td class="num">${fmt.num(r.qualified_demand_qty, 0)}</td>
        <td class="num">${fmt.num(r.sales_90d, 0)}</td>
        <td class="num">${fmt.num(r.adu_days, 0)}</td>
        <td class="num">${fmt.num(r.moq, 0)}</td>
        <td class="num">${fmt.num(r.dlt, 1)}</td>
        <td class="num">${fmt.num(r.ltf, 2)}</td>
        <td class="num">${fmt.num(r.vf, 2)}</td>
        <td class="num">${fmt.num(r.doc, 1)}</td>
      </tr>`).join("");
  }

  document.getElementById("commit-btn").addEventListener("click", async () => {
    if (!currentJob) return;
    setStatus("Committing…", "");
    try {
      const data = await api(`/api/uploads/${currentJob}/commit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      setStatus(`Committed: ${data.inventory_rows} inventory + ${data.planning_rows} planning rows for ${data.snapshot_date}.`, "ok");
      previewCard.hidden = true;
      currentJob = null;
      input.value = "";
    } catch (e) {
      setStatus(`Commit failed: ${e.message}`, "error");
    }
  });

  document.getElementById("cancel-btn").addEventListener("click", () => {
    previewCard.hidden = true;
    currentJob = null;
    input.value = "";
    setStatus("Cancelled.", "");
  });

  function setStatus(msg, cls) {
    status.className = "status-line" + (cls ? " " + cls : "");
    status.textContent = msg;
  }
  function truncate(s, n) { return s && s.length > n ? s.slice(0, n - 1) + "…" : s; }
})();
