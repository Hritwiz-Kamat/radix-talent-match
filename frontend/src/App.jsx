import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import TalentCheck from "./pages/TalentCheck";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <nav className="app-nav">
        <span className="nav-brand">🎯 RADIX Talent Match</span>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            Home
          </NavLink>
          <NavLink to="/talent-check" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            Talent Check
          </NavLink>
        </div>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={
            <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
              <h1 style={{ fontSize: "2.5rem", color: "#6366f1" }}>RADIX Talent Match</h1>
              <p style={{ color: "#94a3b8", fontSize: "1.1rem", maxWidth: 480, margin: "1rem auto" }}>
                An end-to-end readiness tool. Pick a JD → Parse a resume → Build a profile → Run Talent Check → Match Skills.
              </p>
              <NavLink to="/talent-check" className="run-btn" style={{ display: "inline-block", textDecoration: "none", marginTop: "1.5rem" }}>
                Open Talent Check →
              </NavLink>
            </div>
          } />
          <Route path="/talent-check" element={<TalentCheck />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
