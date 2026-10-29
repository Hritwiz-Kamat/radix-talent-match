import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function AutoDashboard() {
  const [jdFile, setJdFile] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusStep, setStatusStep] = useState(0); 
  const navigate = useNavigate();

  const handleFileChange = (e, setFile) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const runPipeline = async () => {
    if (!jdFile || !resumeFile) {
      alert("Please upload both the Job Description and the Candidate Resume.");
      return;
    }

    setLoading(true);
    try {
      // Step 1: Parse JD
      setStatusStep(1);
      const jdData = new FormData();
      jdData.append("file", jdFile);
      const jdRes = await fetch("http://127.0.0.1:8000/api/jd-analytics/parse", { method: "POST", body: jdData });
      const jdJson = await jdRes.json();

      // Step 2: Parse Resume
      setStatusStep(2);
      const resumeData = new FormData();
      resumeData.append("file", resumeFile);
      const resumeRes = await fetch("http://127.0.0.1:8000/api/resume-parsing/parse", { method: "POST", body: resumeData });
      const resumeJson = await resumeRes.json();

      // 🌟 FILENAME EXTRACTION HACK (Bypasses backend mock data) 🌟
      // Strips the file extension (.pdf, .docx)
      const cleanJdName = jdFile.name.replace(/\.[^/.]+$/, ""); 
      const jdParts = cleanJdName.split("-").map(part => part.trim()); // Splits "Company - Role"
      
      const fallbackCompany = jdParts[0] || "Extracted Company";
      const fallbackRole = jdParts.length > 1 ? jdParts[1] : "Extracted Role";
      const fallbackCandidate = resumeFile.name.replace(/\.[^/.]+$/, "").trim();

      // Prioritize actual JSON if it exists, otherwise use the filename
      const autoCompany = jdJson.company || jdJson.company_name || jdJson.metadata?.company || fallbackCompany;
      const autoRole = jdJson.role || jdJson.job_title || jdJson.title || jdJson.metadata?.role || fallbackRole;
      const autoCandidate = resumeJson.name || resumeJson.candidate_name || resumeJson.personal_info?.name || fallbackCandidate;

      // Step 3: Generate Skill Matrix
      setStatusStep(3);
      const scoreRes = await fetch("http://127.0.0.1:8000/api/talent-check/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          jd: jdJson, 
          resume: resumeJson,
          company: autoCompany,
          role: autoRole,
          candidate_name: autoCandidate 
        })
      });
      const scoreJson = await scoreRes.json();

      // Step 4: Complete & Redirect
      setStatusStep(4);
      setTimeout(() => {
        navigate("/talent-check", { 
          state: { 
            jdJson, 
            resumeJson, 
            scoreJson, 
            company: autoCompany, 
            role: autoRole, 
            candidate: autoCandidate 
          } 
        });
      }, 800);
      
    } catch (error) {
      console.error("Pipeline Error:", error);
      alert("Pipeline failed. Check backend terminal for errors.");
      setLoading(false);
      setStatusStep(0);
    }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <h1 style={{ fontSize: "2.5rem", color: "#1e293b", marginBottom: "0.5rem" }}>Talent Match Pipeline</h1>
        <p style={{ color: "#64748b", fontSize: "1.1rem" }}>Upload documents (.pdf, .doc, .docx) to instantly evaluate candidate readiness.</p>
      </div>
      
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginBottom: "2rem" }}>
        {/* JD Upload Card */}
        <div style={{ backgroundColor: "#f8fafc", border: "2px dashed #cbd5e1", borderRadius: "12px", padding: "2rem", textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>🏢</div>
          <h3 style={{ margin: "0 0 1rem 0", color: "#334155" }}>1. Job Description</h3>
          <input 
            type="file" 
            accept=".pdf,.doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
            onChange={(e) => handleFileChange(e, setJdFile)} 
            style={{ width: "100%", cursor: "pointer" }}
          />
          {jdFile && <p style={{ color: "#10b981", marginTop: "1rem", fontSize: "0.9rem", fontWeight: "bold" }}>✓ {jdFile.name}</p>}
        </div>
        
        {/* Resume Upload Card */}
        <div style={{ backgroundColor: "#f8fafc", border: "2px dashed #cbd5e1", borderRadius: "12px", padding: "2rem", textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>📄</div>
          <h3 style={{ margin: "0 0 1rem 0", color: "#334155" }}>2. Candidate Resume</h3>
          <input 
            type="file" 
            accept=".pdf,.doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
            onChange={(e) => handleFileChange(e, setResumeFile)} 
            style={{ width: "100%", cursor: "pointer" }}
          />
          {resumeFile && <p style={{ color: "#10b981", marginTop: "1rem", fontSize: "0.9rem", fontWeight: "bold" }}>✓ {resumeFile.name}</p>}
        </div>
      </div>

      <div style={{ textAlign: "center" }}>
        <button 
          onClick={runPipeline} 
          disabled={loading || !jdFile || !resumeFile}
          style={{ 
            padding: "1rem 3rem", fontSize: "1.2rem", fontWeight: "bold",
            backgroundColor: (loading || !jdFile || !resumeFile) ? "#94a3b8" : "#4f46e5", 
            color: "white", border: "none", borderRadius: "8px", cursor: (loading || !jdFile || !resumeFile) ? "not-allowed" : "pointer",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
          }}
        >
          {loading ? "Processing Documents..." : "Generate Skill Matrix"}
        </button>
      </div>
    </div>
  );
}