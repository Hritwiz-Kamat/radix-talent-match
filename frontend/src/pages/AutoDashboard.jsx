import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BASE } from "../api";
import { useAppContext } from "../context/AppContext";

export default function AutoDashboard() {
  const { setCurrentCandidate, setCurrentJD } = useAppContext();
  const navigate = useNavigate();

  const [jdFile, setJdFile] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0: idle, 1: jd, 2: resume, 3: profile, 4: match, 5: score, 6: done
  const [error, setError] = useState(null);

  const [companiesData, setCompaniesData] = useState({ companies: [], roles_by_company: {} });
  const [selectedCompany, setSelectedCompany] = useState("");
  const [selectedRole, setSelectedRole] = useState("");

  const [pipelineResult, setPipelineResult] = useState(null);

  // Load companies and roles on mount to power the role selector
  useEffect(() => {
    fetch(`${BASE}/api/talent-check/companies`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setCompaniesData(data);
        if (data.companies && data.companies.length > 0) {
          const firstComp = data.companies[0];
          setSelectedCompany(firstComp);
          const roles = data.roles_by_company?.[firstComp] || [];
          setSelectedRole(roles[0] || "");
        }
      })
      .catch((err) => {
        console.error("Failed to fetch companies:", err);
      });
  }, []);

  // When JD file changes, pre-select company and role if matched by filename ("Company - Role")
  const handleJdFileChange = (e) => {
    const file = e.target.files?.[0] || null;
    setJdFile(file);
    setError(null);
    if (!file || !companiesData.companies || companiesData.companies.length === 0) return;

    const cleanName = file.name.replace(/\.[^/.]+$/, "");
    const parts = cleanName.split("-").map((p) => p.trim());
    if (parts.length > 0 && parts[0]) {
      const targetCompany = parts[0].toLowerCase();
      const matchedComp =
        companiesData.companies.find((c) => c.toLowerCase() === targetCompany) ||
        companiesData.companies.find((c) => c.toLowerCase().includes(targetCompany) || targetCompany.includes(c.toLowerCase()));

      if (matchedComp) {
        setSelectedCompany(matchedComp);
        const roles = companiesData.roles_by_company?.[matchedComp] || [];
        if (parts.length > 1 && parts[1]) {
          const targetRole = parts[1].toLowerCase();
          const matchedRole =
            roles.find((r) => r.toLowerCase() === targetRole) ||
            roles.find((r) => r.toLowerCase().includes(targetRole) || targetRole.includes(r.toLowerCase()));
          setSelectedRole(matchedRole || roles[0] || "");
        } else {
          setSelectedRole(roles[0] || "");
        }
      }
    }
  };

  const handleCompanyChange = (comp) => {
    setSelectedCompany(comp);
    const roles = companiesData.roles_by_company?.[comp] || [];
    setSelectedRole(roles[0] || "");
  };

  const runPipeline = async () => {
    if (!jdFile || !resumeFile) {
      setError("Please select both a Job Description and a Candidate Resume file.");
      return;
    }
    if (!selectedCompany || !selectedRole) {
      setError("Please select a target company and role for Talent Check.");
      return;
    }

    setLoading(true);
    setError(null);
    setPipelineResult(null);

    try {
      // Step 1: Upload & parse Job Description
      setCurrentStep(1);
      const jdFormData = new FormData();
      jdFormData.append("file", jdFile);

      const jdRes = await fetch(`${BASE}/api/jd-analytics/upload`, {
        method: "POST",
        body: jdFormData,
      });
      if (!jdRes.ok) {
        const errJson = await jdRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `JD upload failed with HTTP ${jdRes.status}`);
      }
      const jdSkillList = await jdRes.json();
      setCurrentJD(jdSkillList);

      // Step 2: Upload & parse Candidate Resume
      setCurrentStep(2);
      const resumeFormData = new FormData();
      resumeFormData.append("file", resumeFile);

      const resumeRes = await fetch(`${BASE}/api/resume/parse`, {
        method: "POST",
        body: resumeFormData,
      });
      if (!resumeRes.ok) {
        const errJson = await resumeRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `Resume parsing failed with HTTP ${resumeRes.status}`);
      }
      const resumeSkillList = await resumeRes.json();

      // Step 3: Prefill & persist Candidate Profile
      setCurrentStep(3);
      const profileRes = await fetch(`${BASE}/api/profile/prefill?save=true`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resumeSkillList),
      });
      if (!profileRes.ok) {
        const errJson = await profileRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `Profile creation failed with HTTP ${profileRes.status}`);
      }
      const savedProfile = await profileRes.json();
      setCurrentCandidate(savedProfile);

      // Step 4: Skill Matching (Candidate vs JD)
      setCurrentStep(4);
      const matchRes = await fetch(`${BASE}/api/skill-match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: savedProfile.candidate_id,
          jd_source_file: jdSkillList.source_file,
        }),
      });
      if (!matchRes.ok) {
        const errJson = await matchRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `Skill matching failed with HTTP ${matchRes.status}`);
      }
      const matchResult = await matchRes.json();

      // Step 5: Talent Check (Readiness evaluation vs company role)
      setCurrentStep(5);
      const tcRes = await fetch(`${BASE}/api/talent-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: savedProfile.candidate_id,
          company: selectedCompany,
          role: selectedRole,
        }),
      });
      if (!tcRes.ok) {
        const errJson = await tcRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `Talent Check evaluation failed with HTTP ${tcRes.status}`);
      }
      const tcResult = await tcRes.json();

      // Step 6: Complete
      setCurrentStep(6);
      setPipelineResult({
        profile: savedProfile,
        jd: jdSkillList,
        match: matchResult,
        talentCheck: tcResult,
      });
    } catch (err) {
      console.error("Pipeline failure:", err);
      setError(err.message || "An unexpected error occurred during pipeline execution.");
    } finally {
      setLoading(false);
    }
  };

  const availableRoles = companiesData.roles_by_company?.[selectedCompany] || [];

  return (
    <div style={{ padding: "2rem", maxWidth: "900px", margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
        <h1 style={{ fontSize: "2.2rem", color: "#1e293b", marginBottom: "0.5rem" }}>
          RADIX Talent Match Pipeline
        </h1>
        <p style={{ color: "#64748b", fontSize: "1rem" }}>
          Upload documents to run end-to-end extraction, profiling, skill matching, and company readiness evaluation.
        </p>
      </div>

      {/* Upload Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* JD Upload */}
        <div style={{ backgroundColor: "#f8fafc", border: "2px dashed #cbd5e1", borderRadius: "12px", padding: "1.5rem", textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🏢</div>
          <h3 style={{ margin: "0 0 0.5rem 0", color: "#334155" }}>1. Job Description</h3>
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            onChange={handleJdFileChange}
            style={{ width: "100%", cursor: "pointer" }}
            disabled={loading}
          />
          {jdFile && <p style={{ color: "#10b981", marginTop: "0.75rem", fontSize: "0.85rem", fontWeight: "bold" }}>✓ {jdFile.name}</p>}
        </div>

        {/* Resume Upload */}
        <div style={{ backgroundColor: "#f8fafc", border: "2px dashed #cbd5e1", borderRadius: "12px", padding: "1.5rem", textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📄</div>
          <h3 style={{ margin: "0 0 0.5rem 0", color: "#334155" }}>2. Candidate Resume</h3>
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            onChange={(e) => {
              setResumeFile(e.target.files?.[0] || null);
              setError(null);
            }}
            style={{ width: "100%", cursor: "pointer" }}
            disabled={loading}
          />
          {resumeFile && <p style={{ color: "#10b981", marginTop: "0.75rem", fontSize: "0.85rem", fontWeight: "bold" }}>✓ {resumeFile.name}</p>}
        </div>
      </div>

      {/* Company & Role Selector Confirmation */}
      <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "1.25rem", marginBottom: "1.5rem" }}>
        <h4 style={{ margin: "0 0 0.75rem 0", color: "#334155" }}>Target Evaluation Bar (Talent Check)</h4>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#64748b", marginBottom: "0.25rem" }}>
              Target Company
            </label>
            <select
              value={selectedCompany}
              onChange={(e) => handleCompanyChange(e.target.value)}
              disabled={loading}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              {(companiesData.companies || []).map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#64748b", marginBottom: "0.25rem" }}>
              Target Role
            </label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              disabled={loading}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              {availableRoles.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div style={{ textAlign: "center", marginBottom: "2rem" }}>
        <button
          onClick={runPipeline}
          disabled={loading || !jdFile || !resumeFile}
          style={{
            padding: "0.9rem 2.5rem",
            fontSize: "1.1rem",
            fontWeight: "bold",
            backgroundColor: loading || !jdFile || !resumeFile ? "#94a3b8" : "#4f46e5",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: loading || !jdFile || !resumeFile ? "not-allowed" : "pointer",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
          }}
        >
          {loading ? "Executing Pipeline..." : "Run End-to-End Pipeline"}
        </button>
      </div>

      {/* Progress Status Bar */}
      {loading && (
        <div style={{ background: "#f1f5f9", borderRadius: "8px", padding: "1rem", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#334155", marginBottom: "0.5rem" }}>
            Pipeline Progress:
          </div>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "0.9rem", color: "#475569" }}>
            <li style={{ color: currentStep >= 1 ? (currentStep > 1 ? "#10b981" : "#4f46e5") : "#94a3b8" }}>
              {currentStep > 1 ? "✓" : currentStep === 1 ? "⏳" : "○"} 1. Upload & parse Job Description
            </li>
            <li style={{ color: currentStep >= 2 ? (currentStep > 2 ? "#10b981" : "#4f46e5") : "#94a3b8" }}>
              {currentStep > 2 ? "✓" : currentStep === 2 ? "⏳" : "○"} 2. Upload & parse Candidate Resume
            </li>
            <li style={{ color: currentStep >= 3 ? (currentStep > 3 ? "#10b981" : "#4f46e5") : "#94a3b8" }}>
              {currentStep > 3 ? "✓" : currentStep === 3 ? "⏳" : "○"} 3. Create & persist Candidate Profile
            </li>
            <li style={{ color: currentStep >= 4 ? (currentStep > 4 ? "#10b981" : "#4f46e5") : "#94a3b8" }}>
              {currentStep > 4 ? "✓" : currentStep === 4 ? "⏳" : "○"} 4. Calculate Skill Match against JD
            </li>
            <li style={{ color: currentStep >= 5 ? (currentStep > 5 ? "#10b981" : "#4f46e5") : "#94a3b8" }}>
              {currentStep > 5 ? "✓" : currentStep === 5 ? "⏳" : "○"} 5. Evaluate Talent Check Readiness Bar
            </li>
          </ul>
        </div>
      )}

      {/* Error Message Box */}
      {error && (
        <div style={{ padding: "1rem 1.25rem", borderRadius: "8px", backgroundColor: "#fef2f2", color: "#991b1b", border: "1px solid #fecaca", marginBottom: "1.5rem" }}>
          <strong style={{ display: "block", marginBottom: "0.25rem" }}>Pipeline Error</strong>
          <span>{error}</span>
        </div>
      )}

      {/* Results Summary */}
      {pipelineResult && (
        <div style={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "1.5rem", boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #f1f5f9", paddingBottom: "1rem", marginBottom: "1rem" }}>
            <div>
              <h2 style={{ margin: "0 0 0.25rem 0", color: "#0f172a", fontSize: "1.4rem" }}>
                Evaluation Results: {pipelineResult.profile.name}
              </h2>
              <span style={{ fontSize: "0.85rem", color: "#64748b" }}>
                ID: {pipelineResult.profile.candidate_id} · JD: {pipelineResult.jd.source_file}
              </span>
            </div>
            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "0.8rem", color: "#64748b", display: "block" }}>Data Source</span>
              <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "#334155" }}>
                {pipelineResult.talentCheck.data_source || "Supabase"}
              </span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            {/* Readiness Card */}
            <div style={{ backgroundColor: "#f8fafc", padding: "1.25rem", borderRadius: "8px", textAlign: "center" }}>
              <span style={{ fontSize: "0.85rem", color: "#64748b", textTransform: "uppercase", fontWeight: "600" }}>
                Talent Check Readiness
              </span>
              <div style={{ fontSize: "2.5rem", fontWeight: "bold", color: pipelineResult.talentCheck.readiness_score >= 70 ? "#10b981" : pipelineResult.talentCheck.readiness_score >= 45 ? "#f59e0b" : "#ef4444", marginTop: "0.25rem" }}>
                {pipelineResult.talentCheck.readiness_score}%
              </div>
              <span style={{ fontSize: "0.85rem", color: "#475569" }}>
                Bar: {pipelineResult.talentCheck.company} ({selectedRole})
              </span>
            </div>

            {/* Match Card */}
            <div style={{ backgroundColor: "#f8fafc", padding: "1.25rem", borderRadius: "8px", textAlign: "center" }}>
              <span style={{ fontSize: "0.85rem", color: "#64748b", textTransform: "uppercase", fontWeight: "600" }}>
                JD Skill Match Score
              </span>
              <div style={{ fontSize: "2.5rem", fontWeight: "bold", color: pipelineResult.match.match_score >= 70 ? "#10b981" : pipelineResult.match.match_score >= 45 ? "#f59e0b" : "#ef4444", marginTop: "0.25rem" }}>
                {pipelineResult.match.match_score}%
              </div>
              <span style={{ fontSize: "0.85rem", color: "#475569" }}>
                {pipelineResult.match.matched_skills?.length || 0} matched · {pipelineResult.match.missing_skills?.length || 0} missing
              </span>
            </div>
          </div>

          {/* Top 3 Gaps */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h4 style={{ margin: "0 0 0.5rem 0", color: "#334155" }}>Top Skill Gaps</h4>
            {pipelineResult.talentCheck.skillset_gap && pipelineResult.talentCheck.skillset_gap.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {pipelineResult.talentCheck.skillset_gap
                  .filter((g) => g.gap_size > 0)
                  .sort((a, b) => b.gap_size - a.gap_size)
                  .slice(0, 3)
                  .map((gap) => (
                    <div key={gap.category_code} style={{ display: "flex", justifyContent: "space-between", background: "#fef2f2", padding: "0.5rem 0.75rem", borderRadius: "6px", fontSize: "0.85rem" }}>
                      <span style={{ fontWeight: "600", color: "#991b1b" }}>{gap.category_code}</span>
                      <span style={{ color: "#7f1d1d" }}>
                        Level: {gap.candidate_level} / Required: {gap.required_level} (Gap: -{gap.gap_size})
                      </span>
                    </div>
                  ))}
                {pipelineResult.talentCheck.skillset_gap.filter((g) => g.gap_size > 0).length === 0 && (
                  <p style={{ fontSize: "0.85rem", color: "#10b981", margin: 0 }}>✓ No gaps detected for this role bar!</p>
                )}
              </div>
            ) : (
              <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No gap data available.</p>
            )}
          </div>

          {/* Navigation Links */}
          <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
            <button
              onClick={() => navigate("/skill-matching")}
              style={{
                padding: "0.6rem 1.2rem",
                borderRadius: "6px",
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                color: "#334155",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Explore in Skill Matching →
            </button>
            <button
              onClick={() =>
                navigate("/talent-check", {
                  state: {
                    candidateId: pipelineResult.profile.candidate_id,
                    company: pipelineResult.talentCheck.company,
                    role: selectedRole,
                  },
                })
              }
              style={{
                padding: "0.6rem 1.2rem",
                borderRadius: "6px",
                border: "none",
                background: "#4f46e5",
                color: "#ffffff",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Explore in Talent Check →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
