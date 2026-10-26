import { useState, useEffect, useCallback } from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from "recharts";
import { BASE } from "../api";
import { useAppContext } from "../context/AppContext";

const API = BASE;


// Human-readable labels for the 12 category codes
const CATEGORY_LABELS = {
  DSA:  "Data Structures & Algo",
  COD:  "Coding / Languages",
  OOD:  "Object-Oriented Design",
  APTI: "Aptitude",
  COMM: "Communication",
  AI:   "AI / ML / Data",
  CLOUD:"Cloud & DevOps",
  SQL:  "Databases / SQL",
  SWE:  "Software Engineering",
  SYSD: "System Design",
  NETW: "Networking",
  OS:   "Operating Systems",
};


// Colour palette (cool blues / purples for radar + a vibrant orange for gaps)
const COLORS = {
  candidate: "#6366f1",   // indigo
  required:  "#94a3b8",   // slate
  gap:       "#f97316",   // orange
  bar:       ["#6366f1", "#06b6d4", "#10b981", "#f59e0b"],
};

function scoreColor(score) {
  if (score >= 70) return "#10b981";  // green
  if (score >= 45) return "#f59e0b";  // amber
  return "#ef4444";                   // red
}

// ── Readiness dial (big number with ring) ──────────────────────────────────
function ReadinessDial({ score }) {
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const dash = (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div className="dial-wrapper" aria-label={`Readiness score: ${score}%`}>
      <svg width="180" height="180" viewBox="0 0 180 180">
        {/* track */}
        <circle cx="90" cy="90" r={radius} fill="none" stroke="#1e293b" strokeWidth="16" />
        {/* filled arc */}
        <circle
          cx="90" cy="90" r={radius} fill="none"
          stroke={color} strokeWidth="16"
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeLinecap="round"
          transform="rotate(-90 90 90)"
          style={{ transition: "stroke-dasharray 0.8s ease" }}
        />
        <text x="90" y="84" textAnchor="middle" fontSize="34" fontWeight="700" fill={color}>{score}</text>
        <text x="90" y="106" textAnchor="middle" fontSize="13" fill="#94a3b8">/ 100</text>
      </svg>
      <div className="dial-label" style={{ color }}>
        {score >= 70 ? "🟢 Strong fit" : score >= 45 ? "🟡 Partial fit" : "🔴 Significant gaps"}
      </div>
    </div>
  );
}

// ── Gap table ──────────────────────────────────────────────────────────────
function GapTable({ gaps }) {
  const sorted = [...gaps].sort((a, b) => b.gap_size - a.gap_size);
  return (
    <div className="gap-table-wrapper">
      <h3>Skill Gaps (sorted by size)</h3>
      <table className="gap-table">
        <thead>
          <tr>
            <th>Category</th>
            <th>You</th>
            <th>Required</th>
            <th>Gap</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((g) => (
            <tr key={g.category_code} className={g.gap ? "row-gap" : "row-ok"}>
              <td>
                {CATEGORY_LABELS[g.category_code] ?? g.category_code}
                {g.candidate_level === 0 && g.explanation === "no evidence" && (
                  <span className="not-assessable" title="Resume contains no evidence for this category">
                    Not assessable from resume
                  </span>
                )}
              </td>
              <td className="num">
                {g.candidate_level === 0 && g.explanation === "no evidence"
                  ? <span className="na-dash" title="No resume evidence">–</span>
                  : g.candidate_level}
              </td>
              <td className="num">{g.required_level}</td>
              <td className="num" style={{ color: g.gap_size > 0 ? COLORS.gap : "#10b981", fontWeight: 700 }}>
                {g.gap_size > 0 ? `−${g.gap_size}` : "✓"}
              </td>
              <td>
                <div
                  className="bar-fill"
                  style={{
                    width: `${Math.min(100, (g.candidate_level / Math.max(g.required_level, 1)) * 100)}%`,
                    background: g.gap ? COLORS.gap : "#10b981",
                  }}
                />
              </td>
            </tr>

          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Radar chart ────────────────────────────────────────────────────────────
function SkillRadar({ gaps }) {
  const data = gaps.map((g) => ({
    category: CATEGORY_LABELS[g.category_code]?.split(" ")[0] ?? g.category_code,
    Candidate: g.candidate_level,
    Required: g.required_level,
  }));

  return (
    <div className="chart-card">
      <h3>Skill Radar</h3>
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data}>
          <PolarGrid stroke="#1e293b" />
          <PolarAngleAxis dataKey="category" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 10]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <Radar name="Candidate" dataKey="Candidate" stroke={COLORS.candidate} fill={COLORS.candidate} fillOpacity={0.35} />
          <Radar name="Required"  dataKey="Required"  stroke={COLORS.required}  fill={COLORS.required}  fillOpacity={0.15} />
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Compare bar chart ──────────────────────────────────────────────────────
function CompareChart({ results, candidates }) {
  const data = results.map((r) => ({
    name: candidates.find((c) => c.id === r.candidate_id)?.name ?? r.candidate_id,
    score: r.readiness_score,
  }));

  return (
    <div className="chart-card">
      <h3>All Candidates — Readiness Comparison</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barCategoryGap="30%">
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
          <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8" }} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Bar dataKey="score" radius={[6, 6, 0, 0]} name="Readiness %">
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS.bar[i % COLORS.bar.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Scoring explanation panel ──────────────────────────────────────────────
function ScoringPanel({ method, gaps }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="scoring-panel">
      <button className="explain-btn" onClick={() => setOpen((v) => !v)}>
        {open ? "▲ Hide" : "▼ Why this score?"}
      </button>
      {open && (
        <div className="explain-body">
          <p className="formula">{method}</p>
          <h4>Per-category explanation</h4>
          <ul>
            {gaps.map((g) => (
              <li key={g.category_code}>
                <strong>{CATEGORY_LABELS[g.category_code] ?? g.category_code}:</strong>{" "}
                {g.explanation ?? "no evidence"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function TalentCheck() {
  const { currentCandidate } = useAppContext();
  const [companiesData, setCompaniesData] = useState(null);
  const [candidates, setCandidates]       = useState([]);   // [{id, name}] — from /api/talent-check/candidates
  const [selectedCompany, setSelectedCompany] = useState("");
  const [selectedRole, setSelectedRole]    = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [result, setResult]   = useState(null);
  const [compare, setCompare] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  // Sync selectedCandidate if AppContext provides currentCandidate
  useEffect(() => {
    if (currentCandidate?.id && candidates.some((c) => c.id === currentCandidate.id)) {
      setSelectedCandidate(currentCandidate.id);
    }
  }, [currentCandidate, candidates]);

  // Fetch companies AND candidates on mount (two fast reads, parallel)
  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/talent-check/companies`).then((r) => r.json()),
      fetch(`${API}/api/talent-check/candidates`).then((r) => r.json()),
    ])
      .then(([companiesJson, candidatesJson]) => {
        setCompaniesData(companiesJson);
        const first = companiesJson.companies?.[0] ?? "";
        setSelectedCompany(first);
        setSelectedRole(companiesJson.roles_by_company?.[first]?.[0] ?? "");
        setCandidates(candidatesJson);
        // Default to the first candidate returned by the API
        if (candidatesJson.length > 0) setSelectedCandidate(candidatesJson[0].id);
      })
      .catch(() => setError("Cannot reach backend. Is the server running on :8000?"));
  }, []);

  // Update role when company changes
  useEffect(() => {
    if (!companiesData || !selectedCompany) return;
    const roles = companiesData.roles_by_company?.[selectedCompany] ?? [];
    setSelectedRole(roles[0] ?? "");
    setResult(null);
    setCompare(null);
  }, [selectedCompany, companiesData]);

  const runCheck = useCallback(async () => {
    if (!selectedCompany || !selectedRole || !selectedCandidate) return;
    setLoading(true);
    setError(null);
    try {
      const [checkRes, compareRes] = await Promise.all([
        fetch(`${API}/api/talent-check`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            candidate_id: selectedCandidate,
            company:      selectedCompany,
            role:         selectedRole,
          }),
        }),
        fetch(`${API}/api/talent-check/compare?company=${encodeURIComponent(selectedCompany)}&role=${encodeURIComponent(selectedRole)}`),
      ]);
      if (!checkRes.ok) {
        const err = await checkRes.json();
        throw new Error(err.detail ?? "Unknown error");
      }
      setResult(await checkRes.json());
      if (compareRes.ok) setCompare(await compareRes.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [selectedCompany, selectedRole, selectedCandidate]);

  const roles = companiesData?.roles_by_company?.[selectedCompany] ?? [];

  return (
    <div className="tc-page talent-check">
      {/* ── Header ── */}
      <header className="tc-header">
        <h1>Talent Check</h1>
        <p className="tc-subtitle">
          How ready is a candidate for a specific role? Powered by pure scoring — no AI, fully explainable.
        </p>
      </header>

      {/* ── Selector row ── */}
      <section className="tc-selectors">
        <div className="sel-group">
          <label htmlFor="company-select">Company</label>
          <select
            id="company-select"
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
          >
            {(companiesData?.companies ?? []).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="sel-group">
          <label htmlFor="role-select">Role</label>
          <select
            id="role-select"
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
          >
            {roles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <div className="sel-group">
          <label htmlFor="candidate-select">Candidate</label>
          <select
            id="candidate-select"
            value={selectedCandidate}
            onChange={(e) => setSelectedCandidate(e.target.value)}
          >
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <button
          id="run-check-btn"
          className="run-btn"
          onClick={runCheck}
          disabled={loading || !selectedCompany || !selectedRole}
        >
          {loading ? "Checking…" : "Run Talent Check"}
        </button>
      </section>

      {error && <div className="tc-error">⚠️ {error}</div>}

      {/* ── Results ── */}
      {result && (
        <section className="tc-results">
          <div className="results-top">
            <ReadinessDial score={result.readiness_score} />
            <div className="results-meta">
              <h2>{candidates.find((c) => c.id === result.candidate_id)?.name ?? result.candidate_id}</h2>
              <div className="meta-pill">{result.company}</div>
              <div className="meta-pill role-pill">{selectedRole}</div>
            </div>
          </div>

          <ScoringPanel method={result.scoring_method} gaps={result.skillset_gap} />

          <div className="two-col">
            <SkillRadar gaps={result.skillset_gap} />
            {compare && <CompareChart results={compare} candidates={candidates} />}
          </div>

          <GapTable gaps={result.skillset_gap} />
        </section>
      )}

      {!result && !loading && !error && (
        <div className="tc-placeholder">
          <span>👆 Select a company, role, and candidate then click <strong>Run Talent Check</strong></span>
        </div>
      )}
    </div>
  );
}
