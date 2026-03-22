import React, { useState, useRef, useEffect, useCallback } from "react";

const INITIAL_FORM = {
  first_name: "",
  last_name: "",
  mrn: "",
  date_of_birth: "",
  provider_name: "",
  provider_npi: "",
  primary_diagnosis: "",
  medication_name: "",
  additional_diagnoses: "",
  medication_history: "",
  patient_records: "",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("form"); // "form" | "list"

  // ── 表单相关 state（不动） ──────────────────────────────
  const [form, setForm] = useState(INITIAL_FORM);
  const [status, setStatus] = useState("idle");
  const [carePlan, setCarePlan] = useState("");
  const [orderId, setOrderId] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [warningMsg, setWarningMsg] = useState("");
  const [pendingConfirm, setPendingConfirm] = useState(false);
  const intervalRef = useRef(null);

  // ── 列表相关 state ──────────────────────────────────────
  const [orders, setOrders] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    patient_name: "",
    page: 1,
    page_size: 20,
  });
  const [totalCount, setTotalCount] = useState(0);

  // ── 表单逻辑（不动） ────────────────────────────────────
  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function startPolling(careplanId) {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/careplan/${careplanId}/status/`);
        const data = await res.json();
        if (data.status === "completed") {
          clearInterval(intervalRef.current);
          setCarePlan(data.content);
          setStatus("done");
        } else if (data.status === "failed") {
          clearInterval(intervalRef.current);
          setErrorMsg("Care plan generation failed. Please try again.");
          setStatus("error");
        }
      } catch (err) {
        clearInterval(intervalRef.current);
        setErrorMsg("Network error: " + err.message);
        setStatus("error");
      }
    }, 3000);
  }

  async function handleSubmit(confirm = false) {
    setStatus("loading");
    setCarePlan("");
    setErrorMsg("");
    setWarningMsg("");
    try {
      const response = await fetch("/api/orders/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, confirm }),
      });
      const data = await response.json();
      if (response.ok) {
        if (data.type === "warning") {
          setWarningMsg(data.message);
          setPendingConfirm(true);
          setStatus("idle");
        } else {
          setPendingConfirm(false);
          setOrderId(data.id);
          startPolling(data.id);
        }
      } else {
        setErrorMsg(data.message || "Something went wrong");
        setStatus("error");
      }
    } catch (err) {
      setErrorMsg("Network error: " + err.message);
      setStatus("error");
    }
  }

  function handleDownload() {
    const blob = new Blob([carePlan], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `careplan-${orderId}.txt`;
    a.click();
  }

  // ── 列表逻辑 ────────────────────────────────────────────
  const fetchOrders = useCallback(async () => {
    setListLoading(true);
    setListError("");
    try {
      // 把 filters 拼成 query string，空值不传
      const params = new URLSearchParams();
      if (filters.status) params.append("status", filters.status);
      if (filters.patient_name) params.append("patient_name", filters.patient_name);
      params.append("page", filters.page);
      params.append("page_size", filters.page_size);

      const res = await fetch(`/api/orders/list/?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch orders");
      const data = await res.json();
      setOrders(data.results);
      setTotalCount(data.count);
    } catch (err) {
      setListError(err.message);
    } finally {
      setListLoading(false);
    }
  }, [filters]);

  // 切到 list tab 或 filters 变化时自动拉数据
  useEffect(() => {
    if (activeTab === "list") {
      fetchOrders();
    }
  }, [activeTab, fetchOrders]);

  function handleFilterChange(e) {
    // 改筛选条件时重置到第 1 页
    setFilters({ ...filters, [e.target.name]: e.target.value, page: 1 });
  }

  const totalPages = Math.ceil(totalCount / filters.page_size);

  // ── 渲染 ────────────────────────────────────────────────
  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Care Plan Generator</h1>
      <p style={styles.subtitle}>CVS Specialty Pharmacy</p>

      {/* Tab 切换 */}
      <div style={styles.tabs}>
        <button
          onClick={() => setActiveTab("form")}
          style={activeTab === "form" ? styles.tabActive : styles.tab}
        >
          New Order
        </button>
        <button
          onClick={() => setActiveTab("list")}
          style={activeTab === "list" ? styles.tabActive : styles.tab}
        >
          Orders List
        </button>
      </div>

      {/* ── Tab 1: 表单（原来的内容，完全不动） ── */}
      {activeTab === "form" && (
        <>
          <div style={styles.card}>
            <Section title="Patient Information">
              <div style={styles.row}>
                <Field label="First Name *" name="first_name" value={form.first_name} onChange={handleChange} />
                <Field label="Last Name *" name="last_name" value={form.last_name} onChange={handleChange} />
              </div>
              <div style={styles.row}>
                <Field label="MRN (6 digits) *" name="mrn" value={form.mrn} onChange={handleChange} placeholder="e.g. 001234" />
                <Field label="Date of Birth *" name="date_of_birth" value={form.date_of_birth} onChange={handleChange} placeholder="e.g. 1979-06-08" />
              </div>
              <div style={styles.row}>
                <Field label="Primary Diagnosis (ICD-10) *" name="primary_diagnosis" value={form.primary_diagnosis} onChange={handleChange} placeholder="e.g. G70.01" />
                <Field label="Medication Name *" name="medication_name" value={form.medication_name} onChange={handleChange} placeholder="e.g. IVIG" />
              </div>
              <div style={styles.row}>
                <Field label="Additional Diagnoses" name="additional_diagnoses" value={form.additional_diagnoses} onChange={handleChange} placeholder="e.g. I10, K21.0" />
                <div style={styles.fieldWrapper} />
              </div>
            </Section>

            <Section title="Provider Information">
              <div style={styles.row}>
                <Field label="Provider Name *" name="provider_name" value={form.provider_name} onChange={handleChange} />
                <Field label="Provider NPI (10 digits) *" name="provider_npi" value={form.provider_npi} onChange={handleChange} placeholder="e.g. 1234567890" />
              </div>
            </Section>

            <Section title="Clinical Notes">
              <TextArea label="Medication History" name="medication_history" value={form.medication_history} onChange={handleChange} placeholder="e.g. Pyridostigmine 60mg, Prednisone 10mg..." />
              <TextArea label="Patient Records" name="patient_records" value={form.patient_records} onChange={handleChange} placeholder="Paste clinical notes, recent history..." rows={6} />
            </Section>

            <button
              onClick={() => handleSubmit(false)}
              disabled={status === "loading"}
              style={status === "loading" ? styles.buttonDisabled : styles.button}
            >
              {status === "loading" ? "⏳ Submitting..." : "Generate Care Plan"}
            </button>

            {status === "loading" && (
              <p style={styles.loadingNote}>
                ℹ️ Order submitted! Generating care plan in the background...
              </p>
            )}
          </div>

          {pendingConfirm && (
            <div style={styles.warningBox}>
              <strong>⚠️ Warning:</strong> {warningMsg}
              <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                <button onClick={() => handleSubmit(true)} style={styles.confirmButton}>Yes, proceed anyway</button>
                <button onClick={() => { setPendingConfirm(false); setWarningMsg(""); }} style={styles.cancelButton}>Cancel</button>
              </div>
            </div>
          )}

          {status === "error" && (
            <div style={styles.errorBox}><strong>Error:</strong> {errorMsg}</div>
          )}

          {status === "done" && (
            <div style={styles.resultCard}>
              <div style={styles.resultHeader}>
                <h2 style={{ margin: 0 }}>✅ Care Plan Generated</h2>
                <span style={styles.orderId}>Order ID: {orderId}</span>
              </div>
              <pre style={styles.carePlanText}>{carePlan}</pre>
              <button onClick={handleDownload} style={styles.downloadButton}>⬇️ Download as .txt</button>
            </div>
          )}
        </>
      )}

      {/* ── Tab 2: 订单列表 ── */}
      {activeTab === "list" && (
        <div style={styles.card}>
          {/* 筛选栏 */}
          <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
            <div style={styles.fieldWrapper}>
              <label style={styles.label}>Filter by Status</label>
              <select
                name="status"
                value={filters.status}
                onChange={handleFilterChange}
                style={styles.input}
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div style={styles.fieldWrapper}>
              <label style={styles.label}>Search by Patient Name</label>
              <input
                name="patient_name"
                value={filters.patient_name}
                onChange={handleFilterChange}
                placeholder="e.g. Smith"
                style={styles.input}
              />
            </div>

            <div style={styles.fieldWrapper}>
              <label style={styles.label}>Per Page</label>
              <select
                name="page_size"
                value={filters.page_size}
                onChange={handleFilterChange}
                style={styles.input}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button onClick={fetchOrders} style={styles.button}>🔄 Refresh</button>
            </div>
          </div>

          {/* 状态提示 */}
          {listLoading && <p style={{ color: "#666" }}>Loading...</p>}
          {listError && <div style={styles.errorBox}>{listError}</div>}

          {/* 表格 */}
          {!listLoading && !listError && (
            <>
              <p style={{ color: "#666", fontSize: 13, marginBottom: 8 }}>
                {totalCount} orders found
              </p>
              <table style={styles.table}>
                <thead>
                  <tr style={styles.tableHeader}>
                    <th style={styles.th}>ID</th>
                    <th style={styles.th}>Patient</th>
                    <th style={styles.th}>Medication</th>
                    <th style={styles.th}>Status</th>
                    <th style={styles.th}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: "center", padding: 24, color: "#999" }}>
                        No orders found
                      </td>
                    </tr>
                  ) : (
                    orders.map((order) => (
                      <tr key={order.id} style={styles.tableRow}>
                        <td style={styles.td}>{order.id}</td>
                        <td style={styles.td}>{order.patient_name}</td>
                        <td style={styles.td}>{order.medication_name}</td>
                        <td style={styles.td}>
                          <StatusBadge status={order.status} />
                        </td>
                        <td style={styles.td}>
                          {new Date(order.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>

              {/* 分页控制 */}
              {totalPages > 1 && (
                <div style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center" }}>
                  <button
                    onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                    disabled={filters.page <= 1}
                    style={filters.page <= 1 ? styles.buttonDisabled : styles.button}
                  >
                    ← Prev
                  </button>
                  <span style={{ fontSize: 13, color: "#666" }}>
                    Page {filters.page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                    disabled={filters.page >= totalPages}
                    style={filters.page >= totalPages ? styles.buttonDisabled : styles.button}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// status 对应的颜色
function StatusBadge({ status }) {
  const colorMap = {
    pending:    { bg: "#fef3c7", color: "#92400e" },
    processing: { bg: "#dbeafe", color: "#1e40af" },
    completed:  { bg: "#d1fae5", color: "#065f46" },
    failed:     { bg: "#fee2e2", color: "#991b1b" },
  };
  const style = colorMap[status] || { bg: "#f3f4f6", color: "#374151" };
  return (
    <span style={{
      background: style.bg,
      color: style.color,
      padding: "2px 8px",
      borderRadius: 4,
      fontSize: 12,
      fontWeight: 500,
    }}>
      {status}
    </span>
  );
}

// 小组件（不动）
function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={styles.sectionTitle}>{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, name, value, onChange, placeholder }) {
  return (
    <div style={styles.fieldWrapper}>
      <label style={styles.label}>{label}</label>
      <input name={name} value={value} onChange={onChange} placeholder={placeholder || ""} style={styles.input} />
    </div>
  );
}

function TextArea({ label, name, value, onChange, placeholder, rows = 3 }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={styles.label}>{label}</label>
      <textarea name={name} value={value} onChange={onChange} placeholder={placeholder || ""} rows={rows} style={styles.textarea} />
    </div>
  );
}

const styles = {
  container: { maxWidth: 800, margin: "0 auto", padding: "24px 16px", fontFamily: "system-ui, sans-serif" },
  title: { fontSize: 28, fontWeight: "bold", marginBottom: 4 },
  subtitle: { color: "#666", marginBottom: 24 },
  tabs: { display: "flex", gap: 0, marginBottom: 24, borderBottom: "2px solid #e5e7eb" },
  tab: { padding: "10px 24px", background: "none", border: "none", cursor: "pointer", fontSize: 14, color: "#6b7280", borderBottom: "2px solid transparent", marginBottom: -2 },
  tabActive: { padding: "10px 24px", background: "none", border: "none", cursor: "pointer", fontSize: 14, color: "#2563eb", fontWeight: 600, borderBottom: "2px solid #2563eb", marginBottom: -2 },
  card: { background: "#fff", border: "1px solid #e0e0e0", borderRadius: 8, padding: 24, marginBottom: 24 },
  sectionTitle: { fontSize: 16, fontWeight: "600", color: "#333", marginBottom: 12, marginTop: 0 },
  row: { display: "flex", gap: 16, marginBottom: 0 },
  fieldWrapper: { flex: 1, marginBottom: 16 },
  label: { display: "block", fontSize: 13, fontWeight: "500", marginBottom: 4, color: "#444" },
  input: { width: "100%", padding: "8px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 14, boxSizing: "border-box" },
  textarea: { width: "100%", padding: "8px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 14, resize: "vertical", boxSizing: "border-box" },
  button: { padding: "10px 24px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, cursor: "pointer", fontWeight: "500" },
  buttonDisabled: { padding: "10px 24px", background: "#93c5fd", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, cursor: "not-allowed", fontWeight: "500" },
  loadingNote: { marginTop: 12, color: "#92400e", background: "#fef3c7", padding: "8px 12px", borderRadius: 4, fontSize: 13 },
  errorBox: { background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 6, padding: 16, marginBottom: 24, color: "#991b1b" },
  warningBox: { background: "#fef3c7", border: "1px solid #f59e0b", borderRadius: 6, padding: 16, marginBottom: 24, color: "#92400e" },
  confirmButton: { padding: "8px 16px", background: "#d97706", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14 },
  cancelButton: { padding: "8px 16px", background: "#fff", color: "#374151", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 14 },
  resultCard: { background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: 24 },
  resultHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  orderId: { fontSize: 12, color: "#666", background: "#e5e7eb", padding: "2px 8px", borderRadius: 4 },
  carePlanText: { whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 13, lineHeight: 1.6, background: "#fff", padding: 16, borderRadius: 4, border: "1px solid #d1fae5", maxHeight: 500, overflowY: "auto" },
  downloadButton: { marginTop: 16, padding: "8px 20px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 14 },
  tableHeader: { background: "#f9fafb" },
  th: { padding: "10px 12px", textAlign: "left", fontWeight: 600, color: "#374151", borderBottom: "1px solid #e5e7eb" },
  tableRow: { borderBottom: "1px solid #f3f4f6" },
  td: { padding: "10px 12px", color: "#374151" },
};
