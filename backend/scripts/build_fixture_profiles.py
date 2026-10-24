"""Builds the 4 HAND-LABELLED sample candidate profiles (ground truth) from the resumes.
Run:  python scripts/build_fixture_profiles.py     (from backend/)
These unblock Roles 4 and 5 and double as the 'golden' answer key for Resume Parsing tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas import CandidateProfile, ProfileItem as I, Skill
from app.core import storage


def S(name, cat, ev, conf):
    return Skill(skill_name=name, category_code=cat, evidence=ev, confidence=conf)


P = []
P.append(CandidateProfile(
    candidate_id="ananya-rao", name="Ananya Rao", education="B.Tech CSE, Class of 2026, CGPA 8.6",
    skills=[
        S("C++", "COD", "multithreaded job scheduler in C++", "high"),
        S("Python", "COD", "listed in technical skills", "medium"),
        S("Java", "COD", "parking-lot system in Java", "high"),
        S("Data Structures & Algorithms", "DSA", "350+ competitive programming problems; mentors juniors on DSA", "high"),
        S("Operating Systems", "OS", "simulated Round Robin/Priority/SJF scheduling", "high"),
        S("Linux", "OS", "listed in technical skills", "medium"),
        S("Computer Networks", "NETW", "listed in technical skills", "medium"),
        S("Object-Oriented Design", "OOD", "Factory and Strategy patterns in parking-lot design", "high"),
        S("Distributed systems design", "SYSD", "distributed URL shortener with Redis cache, horizontally scalable API", "high"),
        S("Git", "SWE", "listed in technical skills", "medium"),
        S("Production backend engineering", "SWE", "shipped a rate-limiter used in production during internship", "high"),
    ],
    hackathons=[I(title="Finalist, national 24-hour hackathon", description="real-time chat backend")],
    internships=[I(title="Backend intern", organization="mid-size product startup", description="shipped a production rate-limiter")],
    preferred_roles=["Software Engineer", "Backend Engineer"]))
P.append(CandidateProfile(
    candidate_id="karthik-subramaniam", name="Karthik Subramaniam", education="B.Tech CSE, Class of 2026, CGPA 8.2",
    skills=[
        S("SQL", "SQL", "listed first; SQL extraction in churn pipeline", "high"),
        S("Database schema design", "SQL", "normalized schema for event-management system", "high"),
        S("Python (pandas, scikit-learn)", "COD", "churn-prediction pipeline", "high"),
        S("Machine learning (logistic regression)", "AI", "end-to-end churn-prediction model", "high"),
        S("Statistics", "AI", "listed; A/B test analysis", "high"),
        S("A/B testing", "AI", "ran and analysed an A/B test simulation", "medium"),
        S("Anomaly detection", "AI", "registration-spike anomaly detection", "medium"),
        S("Power BI / dashboards", "OTHER", "built recurring dashboards at fintech internship", "high"),
        S("Excel", "OTHER", "listed in technical skills", "low"),
        S("Java", "COD", "basic Java listed", "low"),
        S("Presenting to non-technical audiences", "COMM", "presented A/B results to a non-technical audience", "high"),
    ],
    hackathons=[I(title="Runner-up, inter-college data visualization competition")],
    internships=[I(title="Data Analytics intern", organization="fintech startup", description="built two recurring dashboards")],
    certifications=[I(title="Google Data Analytics Certificate")],
    preferred_roles=["Data Analyst", "Data Scientist"]))
P.append(CandidateProfile(
    candidate_id="priya-menon", name="Priya Menon", education="B.Tech IT, Class of 2026, CGPA 7.4",
    skills=[
        S("SQL (basic)", "SQL", "MySQL backend in attendance tracker; 'SQL (basic)'", "low"),
        S("Java", "COD", "attendance tracker built in Java", "medium"),
        S("Linux basics", "OS", "listed as basics", "low"),
        S("Networking fundamentals", "NETW", "listed; Cisco Networking Basics course", "medium"),
        S("Incident troubleshooting", "OTHER", "first-level troubleshooting and escalations at IT support desk", "medium"),
        S("Ticketing tools", "OTHER", "exposure to ticketing tools; helpdesk simulation", "low"),
        S("MS Excel", "OTHER", "listed in technical skills", "low"),
        S("Team coordination", "COMM", "volunteer coordinator for college technical fest", "medium"),
    ],
    hackathons=[I(title="Participant, 12-hour campus hackathon (non-finalist)")],
    internships=[I(title="Summer intern, IT support desk", organization="local business")],
    certifications=[I(title="Cisco Networking Basics (online course)")],
    preferred_roles=["Application Support Analyst", "Associate Software Engineer"]))
P.append(CandidateProfile(
    candidate_id="rohan-verma", name="Rohan Verma", education="B.Tech CSE, Class of 2026, CGPA 9.1",
    skills=[
        S("C++", "COD", "listed in technical skills", "high"),
        S("Python", "COD", "open-source PRs to a Python library", "high"),
        S("SQL", "SQL", "listed in technical skills", "medium"),
        S("Data Structures & Algorithms", "DSA", "500+ competitive programming problems", "high"),
        S("System Design", "SYSD", "scalable pub-sub notification service with architecture diagrams", "high"),
        S("Object-Oriented Design", "OOD", "technical blog series on OO design patterns", "high"),
        S("Operating Systems", "OS", "listed in technical skills", "medium"),
        S("Machine learning (collaborative filtering)", "AI", "recommendation engine evaluated with precision/recall", "medium"),
        S("Git", "SWE", "open-source contributor, 2 merged PRs", "high"),
        S("Testing and CI", "SWE", "shipped a feature end-to-end with tests and CI at internship", "high"),
        S("Docker", "CLOUD", "listed in technical skills", "medium"),
        S("Technical writing", "COMM", "technical blog series", "medium"),
    ],
    hackathons=[I(title="Winner, national inter-college hackathon", description="real-time collaborative document editor")],
    internships=[I(title="Software Engineering intern", organization="Series-B startup", description="shipped a feature end-to-end with tests and CI")],
    preferred_roles=["Software Engineer", "Data Scientist", "Backend Engineer"]))

for p in P:
    storage.save("profiles", p.candidate_id, p)
    print("saved", p.candidate_id, len(p.skills), "skills")
