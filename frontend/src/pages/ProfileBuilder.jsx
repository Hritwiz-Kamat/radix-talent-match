
import { useEffect, useState } from "react";
import { BASE, get, put } from "../api";

const CATEGORIES = [
  "DSA", "COD", "OOD", "APTI", "COMM", "AI", "CLOUD",
  "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER",
];

const inputStyle = {
  display: "block",
  width: "100%",
  padding: "10px 12px",
  marginTop: 6,
  border: "1px solid #cbd5e1",
  borderRadius: 7,
  background: "#fff",
  color: "#172033",
  boxSizing: "border-box",
  font: "inherit",
};

const labelStyle = {
  display: "block",
  fontSize: 14,
  fontWeight: 600,
  color: "#334155",
};

const cardStyle = {
  background: "#fff",
  padding: 24,
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  marginBottom: 20,
  maxWidth: 1000,
};

const primaryButton = {
  padding: "11px 20px",
  border: 0,
  borderRadius: 8,
  background: "#4f46e5",
  color: "#fff",
  fontWeight: 600,
  cursor: "pointer",
};

const secondaryButton = {
  padding: "9px 14px",
  border: "1px solid #cbd5e1",
  borderRadius: 7,
  background: "#fff",
  color: "#172033",
  cursor: "pointer",
};

const emptyItem = () => ({
  title: "",
  organization: "",
  description: "",
  year: "",
});

function ProfileItemEditor({ title, items = [], onChange }) {
  function updateItem(index, field, value) {
    onChange(
      items.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      )
    );
  }

  function addItem() {
    onChange([...items, emptyItem()]);
  }

  function removeItem(index) {
    onChange(items.filter((_, i) => i !== index));
  }

  return (
    <div style={cardStyle}>
      <h2>{title} ({items.length})</h2>

      {items.map((item, index) => (
        <div
          key={index}
          style={{
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: 16,
            marginBottom: 14,
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 14,
            }}
          >
            <label style={labelStyle}>
              Title *
              <input
                required
                value={item.title || ""}
                onChange={(e) =>
                  updateItem(index, "title", e.target.value)
                }
                style={inputStyle}
              />
            </label>

            <label style={labelStyle}>
              Organization
              <input
                value={item.organization || ""}
                onChange={(e) =>
                  updateItem(index, "organization", e.target.value)
                }
                style={inputStyle}
              />
            </label>

            <label style={labelStyle}>
              Year
              <input
                value={item.year ?? ""}
                onChange={(e) =>
                  updateItem(index, "year", e.target.value)
                }
                placeholder="e.g. 2026"
                style={inputStyle}
              />
            </label>
          </div>

          <label style={{ ...labelStyle, marginTop: 14 }}>
            Description
            <textarea
              value={item.description || ""}
              onChange={(e) =>
                updateItem(index, "description", e.target.value)
              }
              style={{ ...inputStyle, minHeight: 75 }}
            />
          </label>

          <button
            type="button"
            onClick={() => removeItem(index)}
            style={{ ...secondaryButton, color: "#b91c1c", marginTop: 12 }}
          >
            Remove
          </button>
        </div>
      ))}

      <button type="button" onClick={addItem} style={secondaryButton}>
        + Add {title.replace(/s$/, "")}
      </button>
    </div>
  );
}

export default function ProfileBuilder() {
  const [profiles, setProfiles] = useState([]);
  const [candidateId, setCandidateId] = useState("");
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [rolesInput, setRolesInput] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProfiles() {
      try {
        setLoading(true);
        setError("");

        const data = (await get("/api/profile")).filter(
          (item) => item.candidate_id !== "_test_no_name_profile"
        );

        if (!active) return;

        setProfiles(data);

        if (data.length > 0) {
          setCandidateId(data[0].candidate_id);
        }
      } catch (err) {
        if (active) setError(err.message || "Could not load candidates.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadProfiles();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!candidateId) {
      setProfile(null);
      setRolesInput("");
      return;
    }

    let active = true;

    async function loadProfile() {
      try {
        setProfile(null);
        setError("");
        setMessage("");
        setSelectedFile(null);

        const data = await get(`/api/profile/${candidateId}`);

        if (active) {
          setProfile(data);
          setRolesInput((data.preferred_roles || []).join(", "));
        }
      } catch (err) {
        if (active) {
          setProfile(null);
          setError(err.message || "Could not load this profile.");
        }
      }
    }

    loadProfile();

    return () => {
      active = false;
    };
  }, [candidateId]);

  function updateField(field, value) {
    setProfile((current) => ({ ...current, [field]: value }));
    setMessage("");
  }

  function updateSkill(index, field, value) {
    setProfile((current) => ({
      ...current,
      skills: current.skills.map((skill, i) =>
        i === index ? { ...skill, [field]: value } : skill
      ),
    }));
    setMessage("");
  }

  function addSkill() {
    updateField("skills", [
      ...profile.skills,
      {
        skill_name: "",
        category_code: "OTHER",
        evidence: "",
        confidence: "medium",
        importance: null,
      },
    ]);
  }

  function removeSkill(index) {
    updateField(
      "skills",
      profile.skills.filter((_, i) => i !== index)
    );
  }

  async function saveProfile(event) {
    event.preventDefault();

    if (!profile.name?.trim()) {
      setError("Candidate name is required.");
      return;
    }

    if (!profile.candidate_id || profile.candidate_id !== candidateId) {
      setError("Candidate ID does not match the selected profile.");
      return;
    }

    if (
      profile.skills.some(
        (skill) => !skill.skill_name?.trim() || !skill.evidence?.trim()
      )
    ) {
      setError("Each skill needs a name and evidence.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setMessage("");

      const payload = {
        ...profile,
        hackathons: profile.hackathons || [],
        internships: profile.internships || [],
        certifications: profile.certifications || [],
        preferred_roles: rolesInput
          .split(",")
          .map((role) => role.trim())
          .filter(Boolean),
      };

      const saved = await put(`/api/profile/${candidateId}`, payload);

      setProfile(saved);
      setRolesInput((saved.preferred_roles || []).join(", "));
      setMessage("Profile saved successfully.");
    } catch (err) {
      setError(err.message || "Could not save the profile.");
    } finally {
      setSaving(false);
    }
  }

  async function uploadCV() {
    if (!selectedFile) {
      setError("Please choose a CV file first.");
      return;
    }

    const extension = selectedFile.name.split(".").pop()?.toLowerCase();

    if (!["pdf", "docx", "txt"].includes(extension)) {
      setError("Upload a PDF, DOCX, or TXT file.");
      return;
    }

    try {
      setUploading(true);
      setError("");
      setMessage("");

      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(
        `${BASE}/api/profile/${candidateId}/cv`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        let detail = `CV upload failed (${response.status}).`;

        try {
          const data = await response.json();
          detail = data.detail || detail;
        } catch {
          // Use the default error message.
        }

        throw new Error(detail);
      }

      const updatedProfile = await response.json();
      setProfile(updatedProfile);
      setRolesInput((updatedProfile.preferred_roles || []).join(", "));
      setSelectedFile(null);
      setMessage("CV uploaded successfully.");
    } catch (err) {
      setError(err.message || "Could not upload the CV.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <section className="page">
        <h1>Profile Builder</h1>
        <p>Loading candidate profiles...</p>
      </section>
    );
  }

  return (
    <section className="page">
      <h1>Profile Builder</h1>
      <p className="page-description">
        Manage candidate information, skills, experience, and CV.
      </p>

      {error && (
        <p role="alert" style={{ color: "#b91c1c", marginBottom: 16 }}>
          {error}
        </p>
      )}

      
{message && (
  <div
    role="status"
    style={{
      position: "fixed",
      top: 24,
      right: 24,
      zIndex: 1000,
      background: "#166534",
      color: "#ffffff",
      padding: "14px 20px",
      borderRadius: 10,
      boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
      display: "flex",
      alignItems: "center",
      gap: 10,
      fontSize: 14,
      fontWeight: 600,
    }}
  >
    <span>✓</span>
    {message}
  </div>
)}


      <div style={cardStyle}>
        <label htmlFor="candidate-picker" style={labelStyle}>
          Select candidate
        </label>

        <select
          id="candidate-picker"
          value={candidateId}
          onChange={(event) => setCandidateId(event.target.value)}
          style={{ ...inputStyle, maxWidth: 450 }}
        >
          {profiles.map((item) => (
            <option key={item.candidate_id} value={item.candidate_id}>
              {item.name} ({item.candidate_id})
            </option>
          ))}
        </select>

        {profiles.length === 0 && !error && (
          <p>No candidate profiles found.</p>
        )}
      </div>

      {!profile && candidateId && !error && (
        <p>Loading selected profile...</p>
      )}

      {profile && (
        <form onSubmit={saveProfile}>
          <div style={cardStyle}>
            <h2>Basic Information</h2>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 18,
              }}
            >
              <label style={labelStyle}>
                Full name *
                <input
                  required
                  value={profile.name || ""}
                  onChange={(e) => updateField("name", e.target.value)}
                  style={inputStyle}
                />
              </label>

              <label style={labelStyle}>
                Email
                <input
                  type="email"
                  value={profile.email || ""}
                  onChange={(e) => updateField("email", e.target.value)}
                  style={inputStyle}
                />
              </label>

              <label style={labelStyle}>
                Education
                <input
                  value={profile.education || ""}
                  onChange={(e) => updateField("education", e.target.value)}
                  style={inputStyle}
                />
              </label>
            </div>
          </div>

          <div style={cardStyle}>
            <h2>Skills ({profile.skills.length})</h2>

            {profile.skills.map((skill, index) => (
              <div
                key={index}
                style={{
                  border: "1px solid #e2e8f0",
                  padding: 16,
                  borderRadius: 8,
                  marginBottom: 14,
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: 14,
                  }}
                >
                  <label style={labelStyle}>
                    Skill name *
                    <input
                      required
                      value={skill.skill_name || ""}
                      onChange={(e) =>
                        updateSkill(index, "skill_name", e.target.value)
                      }
                      style={inputStyle}
                    />
                  </label>

                  <label style={labelStyle}>
                    Category
                    <select
                      value={skill.category_code}
                      onChange={(e) =>
                        updateSkill(index, "category_code", e.target.value)
                      }
                      style={inputStyle}
                    >
                      {CATEGORIES.map((category) => (
                        <option key={category} value={category}>
                          {category}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label style={labelStyle}>
                    Confidence
                    <select
                      value={skill.confidence}
                      onChange={(e) =>
                        updateSkill(index, "confidence", e.target.value)
                      }
                      style={inputStyle}
                    >
                      {["high", "medium", "low"].map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label style={labelStyle}>
                    Importance
                    <select
                      value={skill.importance || ""}
                      onChange={(e) =>
                        updateSkill(index, "importance", e.target.value || null)
                      }
                      style={inputStyle}
                    >
                      <option value="">Not specified</option>
                      <option value="required">Required</option>
                      <option value="preferred">Preferred</option>
                    </select>
                  </label>
                </div>

                <label style={{ ...labelStyle, marginTop: 14 }}>
                  Evidence *
                  <textarea
                    required
                    value={skill.evidence || ""}
                    onChange={(e) =>
                      updateSkill(index, "evidence", e.target.value)
                    }
                    style={{ ...inputStyle, minHeight: 75 }}
                  />
                </label>

                <button
                  type="button"
                  onClick={() => removeSkill(index)}
                  style={{
                    ...secondaryButton,
                    marginTop: 12,
                    color: "#b91c1c",
                  }}
                >
                  Remove skill
                </button>
              </div>
            ))}

            <button type="button" onClick={addSkill} style={secondaryButton}>
              + Add skill
            </button>
          </div>

          <ProfileItemEditor
            title="Hackathons"
            items={profile.hackathons || []}
            onChange={(items) => updateField("hackathons", items)}
          />

          <ProfileItemEditor
            title="Internships"
            items={profile.internships || []}
            onChange={(items) => updateField("internships", items)}
          />

          <ProfileItemEditor
            title="Certifications"
            items={profile.certifications || []}
            onChange={(items) => updateField("certifications", items)}
          />

          <div style={cardStyle}>
            <h2>Preferred Roles</h2>

            <label style={labelStyle}>
              Roles (separate with commas)
              <input
                value={rolesInput}
                onChange={(e) => {
                  setRolesInput(e.target.value);
                  setMessage("");
                }}
                placeholder="Data Analyst, ML Engineer"
                style={inputStyle}
              />
            </label>
          </div>

          <div style={cardStyle}>
            <h2>CV / Resume</h2>

            <p style={{ color: "#475569" }}>
              {profile.cv_file
                ? `Uploaded CV: ${profile.cv_file}`
                : "No CV uploaded yet."}
            </p>

            <label style={labelStyle}>
              Choose a CV (PDF, DOCX, or TXT)
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => {
                  setSelectedFile(e.target.files?.[0] || null);
                  setError("");
                  setMessage("");
                }}
                style={inputStyle}
              />
            </label>

            <button
              type="button"
              onClick={uploadCV}
              disabled={uploading || !selectedFile}
              style={{
                ...primaryButton,
                marginTop: 14,
                opacity: uploading || !selectedFile ? 0.65 : 1,
              }}
            >
              {uploading ? "Uploading..." : "Upload CV"}
            </button>
          </div>

          <button
            type="submit"
            disabled={saving || uploading}
            style={{
              ...primaryButton,
              opacity: saving || uploading ? 0.65 : 1,
            }}
          >
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </form>
      )}
    </section>
  );
}
