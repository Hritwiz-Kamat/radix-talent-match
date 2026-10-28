import { useState, useEffect } from "react";
import { BASE } from "../api";
import { useAppContext } from "../context/AppContext";

const MATCH_TYPE_BADGES = {
  exact: { label: "Exact Match", bg: "#10b981", color: "#fff" },
  alias: { label: "Alias Match", bg: "#06b6d4", color: "#fff" },
  fuzzy: { label: "Fuzzy Match", bg: "#8b5cf6", color: "#fff" },
  semantic: { label: "Semantic Match", bg: "#f59e0b", color: "#fff" },
};

export default function SkillMatching() {
  const { currentCandidate, currentJD } = useAppContext();
  const [candidates, setCandidates] = useState([]);
  const [jdList, setJdList] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(
    currentCandidate?.candidate_id || currentCandidate?.id || ""
  );
  const [selectedJD, setSelectedJD] = useState(
    currentJD?.source_file || ""
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [matchResult, setMatchResult] = useState(null);

  // Matrix view state
  const [viewTab, setViewTab] = useState("match"); // "match" | "matrix"
  const [matrixData, setMatrixData] = useState([]);
  const [loadingMatrix, setLoadingMatrix] = useState(false);

  // Load candidate list and dynamic JD list from backend
  useEffect(() => {
    fetch(`${BASE}/api/profile`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setCandidates(data);
        const preferred = currentCandidate?.candidate_id || currentCandidate?.id;
        if (preferred && data.some((c) => (c.candidate_id || c.id) === preferred)) {
          setSelectedCandidate(preferred);
        } else if (data.length > 0 && !selectedCandidate) {
          const defaultCand = data.find((c) => (c.candidate_id || c.id) === "sameer-singla") || data[0];
          setSelectedCandidate(defaultCand.candidate_id || defaultCand.id);
        }
      })
      .catch(() => {});

    fetch(`${BASE}/api/jd-analytics/list`)
      .then((r) => (r.ok ? r.json() : []))
      .then((items) => {
        setJdList(items);
        if (currentJD?.source_file) {
          setSelectedJD(currentJD.source_file);
        } else if (items.length > 0 && !selectedJD) {
          setSelectedJD(items[0].source_file);
        }
      })
      .catch(() => {});
  }, []);

  // Update candidate when shared context changes
  useEffect(() => {
    const cid = currentCandidate?.candidate_id || currentCandidate?.id;
    if (cid) {
      setSelectedCandidate(cid);
    }
  }, [currentCandidate]);

  // Update JD when shared context changes
  useEffect(() => {
    if (currentJD?.source_file) {
      setSelectedJD(currentJD.source_file);
    }
  }, [currentJD]);

  const handleRunMatch = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${BASE}/api/skill-match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: selectedCandidate,
          jd_source_file: selectedJD,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server error (HTTP ${res.status})`);
      }

      const data = await res.json();
      setMatchResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadMatrix = async () => {
    setViewTab("matrix");
    setLoadingMatrix(true);
    try {
      const res = await fetch(`${BASE}/api/skill-match/matrix`);
      if (res.ok) {
        const data = await res.json();
        setMatrixData(data.matrix || []);
      }
    } catch (e) {
      // ignore
    } finally {
      setLoadingMatrix(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 70) return "#10b981";
    if (score >= 45) return "#f59e0b";
    return "#ef4444";
  };

  return (
    <section className="page" style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: "0 0 6px 0", color: "#111827" }}>
            Skill Matching Engine
          </h1>
          <p style={{ margin: 0, color: "#64748b", fontSize: 14 }}>
            Multi-tier algorithm: Exact → Canonical Alias → RapidFuzz → Semantic LLM Adjudication.
          </p>
        </div>

        {/* Tab switcher */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setViewTab("match")}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid #cbd5e1",
              background: viewTab === "match" ? "#4f46e5" : "#fff",
              color: viewTab === "match" ? "#fff" : "#475569",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Candidate Match
          </button>
          <button
            onClick={loadMatrix}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid #cbd5e1",
              background: viewTab === "matrix" ? "#4f46e5" : "#fff",
              color: viewTab === "matrix" ? "#fff" : "#475569",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Saved Results Matrix
          </button>
        </div>
      </header>

      {viewTab === "match" ? (
        <>
          {/* Selector Card */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              padding: 20,
              marginBottom: 24,
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 220 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                  Select Candidate Profile
                </label>
                <select
                  value={selectedCandidate}
                  onChange={(e) => setSelectedCandidate(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 8,
                    border: "1px solid #cbd5e1",
                    fontSize: 14,
                    background: "#f8fafc",
                  }}
                >
                  {candidates.map((c) => {
                    const cid = c.candidate_id || c.id;
                    return (
                      <option key={cid} value={cid}>
                        {c.name} ({cid})
                      </option>
                    );
                  })}
                </select>
              </div>

              <div style={{ flex: 1, minWidth: 260 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                  Select Job Description
                </label>
                <select
                  value={selectedJD}
                  onChange={(e) => setSelectedJD(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 8,
                    border: "1px solid #cbd5e1",
                    fontSize: 14,
                    background: "#f8fafc",
                  }}
                >
                  {jdList.map((j) => (
                    <option key={j.source_file} value={j.source_file}>
                      {j.title} {j.is_analyzed ? `✓ (${j.skills_count} skills)` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleRunMatch}
                disabled={loading || !selectedCandidate || !selectedJD}
                style={{
                  padding: "10px 24px",
                  background: loading ? "#94a3b8" : "#4f46e5",
                  color: "#fff",
                  border: 0,
                  borderRadius: 8,
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: loading || !selectedCandidate || !selectedJD ? "not-allowed" : "pointer",
                }}
              >
                {loading ? "Matching..." : "Execute Match"}
              </button>
            </div>

            {error && (
              <div
                style={{
                  marginTop: 14,
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
          </div>

          {/* Results View */}
          {matchResult && (
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Score Card */}
              <div
                style={{
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: 24,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                  flexWrap: "wrap",
                  gap: 16,
                }}
              >
                <div>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Evaluation Result
                  </span>
                  <h2 style={{ fontSize: 20, fontWeight: 700, margin: "4px 0 0 0", color: "#111827" }}>
                    Match for {matchResult.candidate_id} against {matchResult.jd_source_file}
                  </h2>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div
                    style={{
                      width: 80,
                      height: 80,
                      borderRadius: "50%",
                      background: `${getScoreColor(matchResult.match_score)}15`,
                      border: `3px solid ${getScoreColor(matchResult.match_score)}`,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <span style={{ fontSize: 24, fontWeight: 800, color: getScoreColor(matchResult.match_score), lineHeight: 1 }}>
                      {matchResult.match_score}%
                    </span>
                    <span style={{ fontSize: 10, fontWeight: 600, color: "#64748b", marginTop: 2 }}>MATCH</span>
                  </div>
                </div>
              </div>

              {/* Matched Skills List */}
              <div
                style={{
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: 24,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                }}
              >
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: "#10b981" }}>✓</span> Matched Competencies ({matchResult.matched_skills.length})
                </h3>

                {matchResult.matched_skills.length === 0 ? (
                  <p style={{ color: "#64748b", fontSize: 14, margin: 0 }}>No direct competency matches identified.</p>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
                    {matchResult.matched_skills.map((m, i) => (
                      <div
                        key={i}
                        style={{
                          border: "1px solid #e2e8f0",
                          borderRadius: 8,
                          padding: 12,
                          background: "#f8fafc",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14, color: "#1e293b" }}>{m.jd_skill}</div>
                          {m.candidate_skill !== m.jd_skill && (
                            <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                              Satisfied by: <em>{m.candidate_skill}</em>
                            </div>
                          )}
                        </div>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "4px 8px",
                            borderRadius: 6,
                            background: MATCH_TYPE_BADGES[m.match_type]?.bg || "#64748b",
                            color: "#fff",
                            textTransform: "uppercase",
                          }}
                        >
                          {MATCH_TYPE_BADGES[m.match_type]?.label || m.match_type}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Missing Skills List */}
              <div
                style={{
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: 24,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                }}
              >
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: "#ef4444" }}>✗</span> Missing Competencies & Actionable Recommendations ({matchResult.missing_skills.length})
                </h3>

                {matchResult.missing_skills.length === 0 ? (
                  <p style={{ color: "#10b981", fontSize: 14, margin: 0, fontWeight: 500 }}>
                    Candidate covers all requirements identified in the job description!
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {matchResult.missing_skills.map((s, i) => (
                      <div
                        key={i}
                        style={{
                          border: "1px solid #fee2e2",
                          borderRadius: 8,
                          padding: 14,
                          background: "#fff5f5",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          <span style={{ fontWeight: 700, fontSize: 14, color: "#991b1b" }}>{s.skill_name}</span>
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 700,
                              textTransform: "uppercase",
                              padding: "2px 8px",
                              borderRadius: 4,
                              background: s.importance === "required" ? "#ef4444" : "#f59e0b",
                              color: "#fff",
                            }}
                          >
                            {s.importance || "Preferred"}
                          </span>
                        </div>
                        {s.suggestion && (
                          <div style={{ fontSize: 13, color: "#4b5563" }}>
                            <strong>Recommendation:</strong> {s.suggestion}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        /* Matrix View */
        <div
          style={{
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 12,
            padding: 24,
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#1e293b" }}>
              Candidate x Job Description Match Matrix
            </h2>
            <button
              onClick={loadMatrix}
              disabled={loadingMatrix}
              style={{
                padding: "8px 14px",
                border: "1px solid #cbd5e1",
                borderRadius: 6,
                background: "#f8fafc",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {loadingMatrix ? "Refreshing..." : "↻ Refresh Matrix"}
            </button>
          </div>

          {matrixData.length === 0 ? (
            <p style={{ color: "#64748b", fontSize: 14 }}>
              No matches calculated yet. Run Candidate Match above to generate entries.
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "10px 14px", fontSize: 13, color: "#475569" }}>Candidate ID</th>
                    <th style={{ padding: "10px 14px", fontSize: 13, color: "#475569" }}>Job Description</th>
                    <th style={{ padding: "10px 14px", fontSize: 13, color: "#475569" }}>Match Score</th>
                  </tr>
                </thead>
                <tbody>
                  {matrixData.map((m, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "10px 14px", fontWeight: 600, fontSize: 13, color: "#1e293b" }}>
                        {m.candidate_id}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "#475569" }}>
                        {m.jd_source_file}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <span
                          style={{
                            fontWeight: 700,
                            fontSize: 13,
                            color: getScoreColor(m.match_score),
                            background: `${getScoreColor(m.match_score)}15`,
                            padding: "3px 8px",
                            borderRadius: 4,
                          }}
                        >
                          {m.match_score}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
