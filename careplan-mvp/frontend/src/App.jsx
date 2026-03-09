import React, { useState } from "react";

// ============================================================
// MVP 前端 - 所有逻辑都在这一个文件里
// 和后端 views.py 一样，Day 7 才会拆分
// ============================================================

const INITIAL_FORM = {
  first_name: "",
  last_name: "",
  mrn: "",
  provider_name: "",
  provider_npi: "",
  primary_diagnosis: "",
  medication_name: "",
  additional_diagnoses: "",
  medication_history: "",
  patient_records: "",
};

export default function App() {
  const [form, setForm] = useState(INITIAL_FORM);

  // status: "idle" | "loading" | "done" | "error"
  const [status, setStatus] = useState("idle");
  const [carePlan, setCarePlan] = useState("");
  const [orderId, setOrderId] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // 处理表单字段变化
  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  // 提交表单 → POST /api/orders/
  // 现在是同步的：点提交后页面会卡住等 LLM 生成（10-30秒）
  // 这就是 Day 4 要解决的问题
  async function handleSubmit() {
    setStatus("loading");
    setCarePlan("");
    setErrorMsg("");

    try {
      const response = await fetch("/api/orders/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      const data = await response.json();

      if (response.ok) {
        setOrderId(data.id);
        setCarePlan(data.care_plan);
        setStatus("done");
      } else {
        setErrorMsg(data.error || "Something went wrong");
        setStatus("error");
      }
    } catch (err) {
      setErrorMsg("Network error: " + err.message);
      setStatus("error");
    }
  }

  // 下载 care plan 为 .txt 文件
  function handleDownload() {
    const blob = new Blob([carePlan], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `careplan-${orderId}.txt`;
    a.click();
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Care Plan Generator</h1>
      <p style={styles.subtitle}>CVS Specialty Pharmacy</p>

      {/* ---- 表单区域 ---- */}
      <div style={styles.card}>
        <h2 style={styles.sectionTitle}>Patient Information</h2>

        <div style={styles.row}>
          <Field label="First Name *" name="first_name" value={form.first_name} onChange={handleChange} />
          <Field label="Last Name *" name="last_name" value={form.last_name} onChange={handleChange} />
        </div>

        <div style={styles.row}>
          <Field label="MRN (6 digits) *" name="mrn" value={form.mrn} onChange={handleChange} placeholder="e.g. 001234" />
          <Field label="Primary Diagnosis (ICD-10) *" name="primary_diagnosis" value={form.primary_diagnosis} onChange={handleChange} placeholder="e.g. G70.01" />
        </div>

        <div style={styles.row}>
          <Field label="Medication Name *" name="medication_name" value={form.medication_name} onChange={handleChange} placeholder="e.g. IVIG" />
          <Field label="Additional Diagnoses" name="additional_diagnoses" value={form.additional_diagnoses} onChange={handleChange} placeholder="e.g. I10, K21.0" />
        </div>

        <h2 style={{ ...styles.sectionTitle, marginTop: 24 }}>Provider Information</h2>

        <div style={styles.row}>
          <Field label="Provider Name *" name="provider_name" value={form.provider_name} onChange={handleChange} />
          <Field label="Provider NPI (10 digits) *" name="provider_npi" value={form.provider_npi} onChange={handleChange} placeholder="e.g. 1234567890" />
        </div>

        <h2 style={{ ...styles.sectionTitle, marginTop: 24 }}>Clinical Notes</h2>

        <TextArea label="Medication History" name="medication_history" value={form.medication_history} onChange={handleChange}
          placeholder="e.g. Pyridostigmine 60mg, Prednisone 10mg..." />

        <TextArea label="Patient Records" name="patient_records" value={form.patient_records} onChange={handleChange}
          placeholder="Paste clinical notes, recent history..." rows={6} />

        {/* 提交按钮 */}
        <button
          onClick={handleSubmit}
          disabled={status === "loading"}
          style={status === "loading" ? styles.buttonDisabled : styles.button}
        >
          {status === "loading" ? "⏳ Generating Care Plan... (please wait)" : "Generate Care Plan"}
        </button>

        {/* 提示用户等待 - 这就是 Day 4 要解决的体验问题 */}
        {status === "loading" && (
          <p style={styles.loadingNote}>
            ℹ️ The LLM is generating your care plan. This takes 10-30 seconds.
            The page will appear frozen — this is the problem we'll fix in Day 4!
          </p>
        )}
      </div>

      {/* ---- 错误提示 ---- */}
      {status === "error" && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {errorMsg}
        </div>
      )}

      {/* ---- 结果显示 ---- */}
      {status === "done" && (
        <div style={styles.resultCard}>
          <div style={styles.resultHeader}>
            <h2 style={{ margin: 0 }}>✅ Care Plan Generated</h2>
            <span style={styles.orderId}>Order ID: {orderId}</span>
          </div>

          <pre style={styles.carePlanText}>{carePlan}</pre>

          <button onClick={handleDownload} style={styles.downloadButton}>
            ⬇️ Download as .txt
          </button>
        </div>
      )}
    </div>
  );
}

// ---- 小组件 ----

function Field({ label, name, value, onChange, placeholder }) {
  return (
    <div style={styles.fieldWrapper}>
      <label style={styles.label}>{label}</label>
      <input
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder || ""}
        style={styles.input}
      />
    </div>
  );
}

function TextArea({ label, name, value, onChange, placeholder, rows = 3 }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={styles.label}>{label}</label>
      <textarea
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder || ""}
        rows={rows}
        style={styles.textarea}
      />
    </div>
  );
}

// ---- 样式 ----

const styles = {
  container: { maxWidth: 800, margin: "0 auto", padding: "24px 16px", fontFamily: "system-ui, sans-serif" },
  title: { fontSize: 28, fontWeight: "bold", marginBottom: 4 },
  subtitle: { color: "#666", marginBottom: 24 },
  card: { background: "#fff", border: "1px solid #e0e0e0", borderRadius: 8, padding: 24, marginBottom: 24 },
  sectionTitle: { fontSize: 16, fontWeight: "600", color: "#333", marginBottom: 12, marginTop: 0 },
  row: { display: "flex", gap: 16, marginBottom: 0 },
  fieldWrapper: { flex: 1, marginBottom: 16 },
  label: { display: "block", fontSize: 13, fontWeight: "500", marginBottom: 4, color: "#444" },
  input: { width: "100%", padding: "8px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 14, boxSizing: "border-box" },
  textarea: { width: "100%", padding: "8px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 14, resize: "vertical", boxSizing: "border-box" },
  button: { marginTop: 8, padding: "10px 24px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 15, cursor: "pointer", fontWeight: "500" },
  buttonDisabled: { marginTop: 8, padding: "10px 24px", background: "#93c5fd", color: "#fff", border: "none", borderRadius: 6, fontSize: 15, cursor: "not-allowed", fontWeight: "500" },
  loadingNote: { marginTop: 12, color: "#92400e", background: "#fef3c7", padding: "8px 12px", borderRadius: 4, fontSize: 13 },
  errorBox: { background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 6, padding: 16, marginBottom: 24, color: "#991b1b" },
  resultCard: { background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: 24 },
  resultHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  orderId: { fontSize: 12, color: "#666", background: "#e5e7eb", padding: "2px 8px", borderRadius: 4 },
  carePlanText: { whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 13, lineHeight: 1.6, background: "#fff", padding: 16, borderRadius: 4, border: "1px solid #d1fae5", maxHeight: 500, overflowY: "auto" },
  downloadButton: { marginTop: 16, padding: "8px 20px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14 },
};
