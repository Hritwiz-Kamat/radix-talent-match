import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function AutoDashboard() {
  const [jdFile, setJdFile] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const navigate = useNavigate();

  const runPipeline = async () => {
    if (!jdFile || !resumeFile) {
      alert("Please upload both the JD and the Resume PDF.");
      return;
    }

    setLoading(true);
    try {
      // 1. Parse Job Description
      setStatus("Parsing Job Description...");
      const jdData = new FormData();
      jdData.append("file", jdFile);
      const jdRes = await fetch("http://127.0.0.1:8000/api/jd-analytics/parse", { method: "POST", body: jdData });
      const jdJson = await jdRes.json();

      // 2. Parse Resume
      setStatus("Parsing Candidate Resume...");
      const resumeData = new FormData();
      resumeData.append("file", resumeFile);
      const resumeRes = await fetch("http://127.0.0.1:8000/api/resume-parsing/parse", { method: "POST", body: resumeData });
      const resumeJson = await resumeRes.json();

      // 3. Generate Skill Matrix via Supabase & OpenRouter
      setStatus("Generating Talent Score Matrix...");
      const scoreRes = await fetch("http://127.0.0.1:8000/api/talent-check/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jd: jdJson, resume: resumeJson })
      });
      const scoreJson = await scoreRes.json();

      // 4. Redirect to Dashboard with automated data
      setStatus("Complete! Redirecting...");
      navigate("/talent-check", { state: { jdJson, resumeJson, scoreJson } });
      
    } catch (error) {
      console.error("Pipeline Error:", error);
      alert("Pipeline failed. Check backend terminal for errors.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
      <h2>Automated Talent Pipeline</h2>
      <p>Upload documents to instantly generate the capability skill matrix.</p>
      
      <div style={{ marginTop: "1.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label style={{ fontWeight: "bold", display: "block", marginBottom: "0.5rem" }}>1. Upload Job Description (PDF)</label>
          <input type="file" accept="application/pdf" onChange={(e) => setJdFile(e.target.files[0])} />
        </div>
        
        <div>
          <label style={{ fontWeight: "bold", display: "block", marginBottom: "0.5rem" }}>2. Upload Candidate Resume (PDF)</label>
          <input type="file" accept="application/pdf" onChange={(e) => setResumeFile(e.target.files[0])} />
        </div>

        <button 
          onClick={runPipeline} 
          disabled={loading}
          style={{ padding: "0.75rem", backgroundColor: "#007bff", color: "white", border: "none", borderRadius: "4px", cursor: "pointer", marginTop: "1rem" }}
        >
          {loading ? status : "Generate Skill Matrix"}
        </button>
      </div>
    </div>
  );
}