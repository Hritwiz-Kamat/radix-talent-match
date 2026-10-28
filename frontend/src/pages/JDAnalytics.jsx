import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { BASE } from "../api";
import { useAppContext } from "../context/AppContext";

const CATEGORY_COLORS = {
  DSA: "#6366f1",
  COD: "#3b82f6",
  OOD: "#8b5cf6",
  APTI: "#ec4899",
  COMM: "#10b981",
  AI: "#f59e0b",
  CLOUD: "#06b6d4",
  SQL: "#14b8a6",
  SWE: "#64748b",
  SYSD: "#84cc16",
  NETW: "#0ea5e9",
  OS: "#a855f7",
  OTHER: "#94a3b8",
};

export default function JDAnalytics() {
  const navigate = useNavigate();
  const { currentJD, setCurrentJD } = useAppContext();
  const [jdList, setJdList] = useState([]);
  const [selectedFile, setSelectedFile] = useState(currentJD?.source_file || "");
  const [uploadFile, setUploadFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(currentJD || null);
  const [statusMsg, setStatusMsg] = useState("");

  const loadJdList = async () => {
    try {
      const res = await fetch(`${BASE}/api/jd-analytics/list`);
      if (res.ok) {
        const items = await res.json();
        setJdList(items);
        if (items.length > 0 && !selectedFile) {
          const initial = currentJD?.source_file || items[0].source_file;
          setSelectedFile(initial);
        }
      }
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    loadJdList();
  }, []);

  const handleParse = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setError(null);
    setStatusMsg("");

    try {
      const res = await fetch(
        `${BASE}/api/jd-analytics/parse-jd?filename=${encodeURIComponent(
          selectedFile
        )}`,
        { method: "POST" }
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }

      const result = await res.json();
      setData(result);
      setCurrentJD(result);
      setStatusMsg("✓ Successfully parsed and saved to workspace storage");
      loadJdList();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadJD = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    setUploading(true);
    setError(null);
    setStatusMsg("");

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const res = await fetch(`${BASE}/api/jd-analytics/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload failed (HTTP ${res.status})`);
      }

      const result = await res.json();
      setData(result);
      setCurrentJD(result);
      setSelectedFile(result.source_file);
      setStatusMsg(`✓ Custom JD '${uploadFile.name}' uploaded and analyzed successfully!`);
      setUploadFile(null);
      loadJdList();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Compute category counts
  const categoryCounts = (data?.skills || []).reduce((acc, s) => {
    acc[s.category_code] = (acc[s.category_code] || 0) + 1;
    return acc;
  }, {});

  return (
    <section className="page" style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: "0 0 6px 0", color: "#111827" }}>
          JD Analytics
        </h1>
        <p style={{ margin: 0, color: "#64748b", fontSize: 14 }}>
          Analyze and extract required/preferred technical competencies from Job Descriptions.
        </p>
      </header>

      {/* Grid of 2 Input Options */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, marginBottom: 24 }}>
        {/* Option 1: Choose Existing JD */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 12,
            padding: 20,
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 12px 0", color: "#1e293b" }}>
            Option 1: Choose Existing Job Description
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <select
              value={selectedFile}
              onChange={(e) => setSelectedFile(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                fontSize: 14,
                background: "#f8fafc",
                color: "#1e293b",
              }}
            >
              {jdList.map((j) => (
                <option key={j.source_file} value={j.source_file}>
                  {j.title} {j.is_analyzed ? `✓ (${j.skills_count} skills)` : "(not analyzed)"}
                </option>
              ))}
            </select>

            <button
              onClick={handleParse}
              disabled={loading || !selectedFile}
              style={{
                padding: "10px 18px",
                background: loading ? "#94a3b8" : "#4f46e5",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                cursor: loading || !selectedFile ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Analyzing Document..." : "Analyze & Load Selected JD"}
            </button>
          </div>
        </div>

        {/* Option 2: Upload Custom JD */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 12,
            padding: 20,
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 12px 0", color: "#1e293b" }}>
            Option 2: Upload Custom Job Description
          </h2>
          <form onSubmit={handleUploadJD} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setUploadFile(e.target.files[0] || null)}
              style={{
                padding: "8px",
                borderRadius: 8,
                border: "1px dashed #cbd5e1",
                fontSize: 13,
                background: "#f8fafc",
              }}
            />
            <button
              type="submit"
              disabled={uploading || !uploadFile}
              style={{
                padding: "10px 18px",
                background: !uploadFile || uploading ? "#94a3b8" : "#0284c7",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                cursor: !uploadFile || uploading ? "not-allowed" : "pointer",
              }}
            >
              {uploading ? "Analyzing Upload..." : "Upload & Analyze Custom JD"}
            </button>
          </form>
        </div>
      </div>

      {statusMsg && (
        <div
          style={{
            marginBottom: 20,
            padding: "10px 14px",
            borderRadius: 6,
            background: "#ecfdf5",
            color: "#065f46",
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {statusMsg}
        </div>
      )}

      {error && (
        <div
          style={{
            marginBottom: 20,
            padding: "10px 14px",
            borderRadius: 6,
            background: "#fef2f2",
            color: "#991b1b",
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Main Results View */}
      {data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Metadata Card */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              padding: 24,
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: "#6366f1",
                  background: "#eef2ff",
                  padding: "4px 8px",
                  borderRadius: 4,
                }}
              >
                {data.company || "Company Specified in JD"}
              </span>
              <h2 style={{ fontSize: 22, fontWeight: 700, margin: "8px 0 4px 0", color: "#111827" }}>
                {data.role || Path(data.source_file).stem}
              </h2>
              <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>
                Source: <code>{data.source_file}</code> · {data.skills?.length || 0} extracted competencies
              </p>
            </div>

            <button
              onClick={() => navigate("/skill-matching")}
              style={{
                padding: "10px 20px",
                background: "#0284c7",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Proceed to Skill Matching 🔗
            </button>
          </div>

          {/* Competency Badges Bar */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              padding: 20,
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#475569", margin: "0 0 12px 0" }}>
              Category Distribution
            </h3>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {Object.entries(categoryCounts).map(([cat, count]) => (
                <div
                  key={cat}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 10px",
                    borderRadius: 6,
                    background: "#f1f5f9",
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: CATEGORY_COLORS[cat] || "#94a3b8",
                    }}
                  />
                  <span>{cat}</span>
                  <span style={{ color: "#64748b", fontWeight: 600 }}>({count})</span>
                </div>
              ))}
            </div>
          </div>

          {/* Skills Table */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              overflow: "hidden",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                  <th style={{ padding: "12px 16px", fontSize: 13, color: "#475569" }}>Competency</th>
                  <th style={{ padding: "12px 16px", fontSize: 13, color: "#475569" }}>Category</th>
                  <th style={{ padding: "12px 16px", fontSize: 13, color: "#475569" }}>Importance</th>
                  <th style={{ padding: "12px 16px", fontSize: 13, color: "#475569" }}>Evidence / Context</th>
                </tr>
              </thead>
              <tbody>
                {data.skills?.map((skill, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: idx === data.skills.length - 1 ? "none" : "1px solid #f1f5f9",
                    }}
                  >
                    <td style={{ padding: "12px 16px", fontWeight: 600, color: "#1e293b", fontSize: 14 }}>
                      {skill.skill_name}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: 4,
                          color: CATEGORY_COLORS[skill.category_code] || "#475569",
                          background: `${CATEGORY_COLORS[skill.category_code] || "#94a3b8"}15`,
                        }}
                      >
                        {skill.category_code}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          textTransform: "capitalize",
                          padding: "2px 8px",
                          borderRadius: 4,
                          background: skill.importance === "required" ? "#fee2e2" : "#fef3c7",
                          color: skill.importance === "required" ? "#991b1b" : "#92400e",
                        }}
                      >
                        {skill.importance || "unspecified"}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", fontSize: 13, color: "#64748b", maxWidth: 450 }}>
                      "{skill.evidence}"
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
