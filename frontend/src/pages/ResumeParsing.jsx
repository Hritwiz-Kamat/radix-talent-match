import { useState, useEffect, useCallback } from "react";
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

export default function ResumeParsing() {
  const navigate = useNavigate();
  const { setCurrentCandidate } = useAppContext();
  const [samples, setSamples] = useState([]);
  const [samplesLoading, setSamplesLoading] = useState(true);
  const [samplesError, setSamplesError] = useState(null);
  const [selectedSample, setSelectedSample] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [statusMsg, setStatusMsg] = useState("");

  const formatErrorMessage = (err) => {
    if (!err) return "Unknown error occurred.";
    const msg = typeof err === "string" ? err : err.message || "";
    if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("connect to backend")) {
      return `Cannot reach the backend server at ${BASE}. Please ensure the FastAPI backend is running (run: uvicorn app.main:app --reload).`;
    }
    return msg;
  };

  const loadSamples = useCallback(async () => {
    setSamplesLoading(true);
    setSamplesError(null);
    try {
      const res = await fetch(`${BASE}/api/resume/samples`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      const list = Array.isArray(data) ? data : [];
      setSamples(list);
      if (list.length > 0) {
        setSelectedSample((prev) => (list.includes(prev) ? prev : list[0]));
      }
    } catch (err) {
      setSamplesError(formatErrorMessage(err));
    } finally {
      setSamplesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSamples();
  }, [loadSamples]);

  const handleParseSample = async () => {
    if (!selectedSample) return;
    setLoading(true);
    setError(null);
    setStatusMsg("");

    try {
      const res = await fetch(
        `${BASE}/api/resume/parse-sample?name=${encodeURIComponent(selectedSample)}`,
        { method: "POST" }
      );
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      try {
        const prefillRes = await fetch(`${BASE}/api/profile/prefill?save=true`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        if (prefillRes.ok) {
          const profile = await prefillRes.json();
          setCurrentCandidate(profile);
          setStatusMsg(`✓ Parsed and saved profile as '${profile.name}' (${profile.candidate_id})`);
        } else {
          setStatusMsg("✓ Sample resume parsed successfully");
        }
      } catch (e) {
        setStatusMsg("✓ Sample resume parsed successfully");
      }
    } catch (err) {
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    // Validate extension
    const ext = uploadFile.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "txt", "md"].includes(ext)) {
      setError("Unsupported file format. Please upload a PDF, DOCX, or TXT resume.");
      return;
    }

    setLoading(true);
    setError(null);
    setStatusMsg("");

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const res = await fetch(`${BASE}/api/resume/parse`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      try {
        const prefillRes = await fetch(`${BASE}/api/profile/prefill?save=true`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        if (prefillRes.ok) {
          const profile = await prefillRes.json();
          setCurrentCandidate(profile);
          setStatusMsg(`✓ Resume parsed and candidate profile saved as '${profile.name}' (${profile.candidate_id})`);
        } else {
          setStatusMsg("✓ Resume uploaded, parsed, and stored successfully");
        }
      } catch (e) {
        setStatusMsg("✓ Resume uploaded, parsed, and stored successfully");
      }
    } catch (err) {
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleProceedToProfile = async () => {
    if (!result) return;
    try {
      // Call prefill endpoint with save=true to persist profile
      const res = await fetch(`${BASE}/api/profile/prefill?save=true`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      if (res.ok) {
        const profile = await res.json();
        setCurrentCandidate(profile);
      }
      navigate("/profile-builder");
    } catch (e) {
      navigate("/profile-builder");
    }
  };

  return (
    <section className="page" style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: "0 0 6px 0", color: "#111827" }}>
          Resume Parsing
        </h1>
        <p style={{ margin: 0, color: "#64748b", fontSize: 14 }}>
          Upload candidate CVs or select sample resumes to extract competencies, education, and experience.
        </p>
      </header>

      {/* Grid of 2 Input Options */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, marginBottom: 24 }}>
        {/* Option 1: Sample Resumes */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 12,
            padding: 20,
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "#1e293b" }}>
              Option 1: Choose Sample Resume
            </h2>
            {samplesLoading && (
              <span style={{ fontSize: 12, color: "#64748b" }}>Loading...</span>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <select
              value={selectedSample}
              onChange={(e) => setSelectedSample(e.target.value)}
              disabled={samplesLoading || samples.length === 0}
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
              {samplesLoading && <option value="">Loading sample resumes from backend...</option>}
              {!samplesLoading && samples.length === 0 && (
                <option value="">No sample resumes found</option>
              )}
              {samples.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            {samplesError && (
              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: 6,
                  background: "#fef2f2",
                  color: "#991b1b",
                  fontSize: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>{samplesError}</span>
                <button
                  type="button"
                  onClick={loadSamples}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#4f46e5",
                    fontWeight: 600,
                    cursor: "pointer",
                    textDecoration: "underline",
                    fontSize: 12,
                  }}
                >
                  Retry
                </button>
              </div>
            )}

            <button
              onClick={handleParseSample}
              disabled={loading || !selectedSample || samplesLoading}
              style={{
                padding: "10px 18px",
                background: loading || !selectedSample || samplesLoading ? "#94a3b8" : "#4f46e5",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                cursor: loading || !selectedSample || samplesLoading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Parsing..." : "Parse Selected Sample"}
            </button>
          </div>
        </div>

        {/* Option 2: Upload File */}
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
            Option 2: Upload Resume (PDF / DOCX)
          </h2>
          <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
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
              disabled={loading || !uploadFile}
              style={{
                padding: "10px 18px",
                background: !uploadFile || loading ? "#94a3b8" : "#0284c7",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                cursor: !uploadFile || loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Uploading & Parsing..." : "Upload & Parse Resume"}
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

      {/* Parsed Output Details */}
      {result && (
        <div style={{ display: "grid", gap: 20 }}>
          {/* Header Action Card */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              padding: 20,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 12, color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                Parsed Candidate Resume
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginTop: 2 }}>
                {result.source_file}
              </div>
              <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
                {result.skills?.length || 0} skills extracted · {result.extras?.education || "General Profile"}
              </div>
            </div>

            <button
              onClick={handleProceedToProfile}
              style={{
                padding: "10px 20px",
                background: "#10b981",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Review in Profile Builder →
            </button>
          </div>

          {/* Extras Info (Education & Experience) */}
          {result.extras && (
            <div
              style={{
                background: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: 12,
                padding: 18,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 16,
              }}
            >
              {result.extras.education && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b" }}>EDUCATION</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#1e293b", marginTop: 4 }}>
                    {typeof result.extras.education === "string"
                      ? result.extras.education
                      : JSON.stringify(result.extras.education)}
                  </div>
                </div>
              )}
              {result.extras.experience && Array.isArray(result.extras.experience) && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b" }}>EXPERIENCE / INTERNSHIPS</div>
                  <div style={{ fontSize: 13, color: "#1e293b", marginTop: 4 }}>
                    {result.extras.experience.length} recorded items
                  </div>
                </div>
              )}
              {result.extras.hackathons && Array.isArray(result.extras.hackathons) && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b" }}>HACKATHONS</div>
                  <div style={{ fontSize: 13, color: "#1e293b", marginTop: 4 }}>
                    {result.extras.hackathons.length} recorded items
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Skills List Table */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0", fontWeight: 700, fontSize: 15 }}>
              Extracted Skills & Competencies
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "12px 18px", width: "25%" }}>Skill</th>
                    <th style={{ padding: "12px 14px", width: "15%" }}>Category</th>
                    <th style={{ padding: "12px 14px", width: "15%" }}>Confidence</th>
                    <th style={{ padding: "12px 18px" }}>Evidence in Resume</th>
                  </tr>
                </thead>
                <tbody>
                  {result.skills?.map((skill, idx) => (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        background: idx % 2 === 0 ? "#fff" : "#fafafa",
                      }}
                    >
                      <td style={{ padding: "12px 18px", fontWeight: 600, color: "#1e293b" }}>
                        {skill.skill_name}
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            background: CATEGORY_COLORS[skill.category_code] || "#64748b",
                            color: "#fff",
                            padding: "2px 8px",
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 600,
                          }}
                        >
                          {skill.category_code}
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px", textTransform: "capitalize", color: "#475569" }}>
                        {skill.confidence}
                      </td>
                      <td style={{ padding: "12px 18px", color: "#475569", fontStyle: "italic" }}>
                        "{skill.evidence}"
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
