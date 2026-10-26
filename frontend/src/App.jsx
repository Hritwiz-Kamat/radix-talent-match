
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import JDAnalytics from "./pages/JDAnalytics";
import ResumeParsing from "./pages/ResumeParsing";
import ProfileBuilder from "./pages/ProfileBuilder";
import TalentCheck from "./pages/TalentCheck";
import SkillMatching from "./pages/SkillMatching";
import "./App.css";

const pages = [
  { path: "/jd-analytics", label: "JD Analytics", icon: "📊" },
  { path: "/resume-parsing", label: "Resume Parsing", icon: "📄" },
  { path: "/profile-builder", label: "Profile Builder", icon: "👤" },
  { path: "/talent-check", label: "Talent Check", icon: "🎯" },
  { path: "/skill-matching", label: "Skill Matching", icon: "🔗" },
];

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="brand">
              <span className="brand-mark">R</span>
              <div>
                <h2>RADIX</h2>
                <p>Talent Match</p>
              </div>
            </div>

            <p className="nav-heading">WORKSPACE</p>
            <nav>
              {pages.map((page) => (
                <NavLink
                  key={page.path}
                  to={page.path}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? "active" : ""}`
                  }
                >
                  <span>{page.icon}</span>
                  {page.label}
                </NavLink>
              ))}
            </nav>

            <div className="sidebar-footer">RADIX · Local Workspace</div>
          </aside>

          <main className="main-content">
            <header className="topbar">
              <span>Talent Intelligence Platform</span>
              <span className="status-dot">● API workspace</span>
            </header>

            <Routes>
              <Route path="/" element={<Navigate to="/profile-builder" replace />} />
              <Route path="/jd-analytics" element={<JDAnalytics />} />
              <Route path="/resume-parsing" element={<ResumeParsing />} />
              <Route path="/profile-builder" element={<ProfileBuilder />} />
              <Route path="/talent-check" element={<TalentCheck />} />
              <Route path="/skill-matching" element={<SkillMatching />} />
              <Route path="*" element={<Navigate to="/profile-builder" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AppProvider>
  );
}
