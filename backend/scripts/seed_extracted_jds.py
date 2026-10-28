"""
Seed extracted skill lists for all 6 sample Job Descriptions into backend/data/store/jd/.
This unblocks offline Skill Matching evaluations for all candidate-JD pairs.
"""
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.core import storage
from app.schemas import ExtractedSkillList, Skill

JDS_DATA = [
    {
        "filename": "Google LLC - Software Engineer.pdf",
        "company": "Google LLC",
        "role": "Software Engineer",
        "skills": [
            Skill(skill_name="Data Structures and Algorithms", category_code="DSA", evidence="Strong grasp of data structures and algorithms and ability to reason about time and space complexity under pressure", confidence="high", importance="required"),
            Skill(skill_name="General Coding Ability", category_code="COD", evidence="Hands-on programming ability to turn a problem statement into working, efficient code quickly", confidence="high", importance="required"),
            Skill(skill_name="C++", category_code="COD", evidence="Proficiency in modern systems programming", confidence="high", importance="required"),
            Skill(skill_name="Backend Services and APIs", category_code="SWE", evidence="Design and implement backend services and APIs that operate reliably at Google scale", confidence="high", importance="required"),
            Skill(skill_name="System Design and Distributed Systems", category_code="SYSD", evidence="Design large-scale distributed systems and reason about system design at scale", confidence="high", importance="required"),
            Skill(skill_name="Operating Systems", category_code="OS", evidence="Working knowledge of operating systems fundamentals such as processes, threads, and virtual memory", confidence="high", importance="required"),
            Skill(skill_name="Networking Concepts", category_code="NETW", evidence="Core networking concepts such as TCP/UDP, HTTP, and how a web request travels", confidence="high", importance="required"),
            Skill(skill_name="Object-Oriented Design", category_code="OOD", evidence="Common design patterns with an eye for extensible, maintainable architecture", confidence="high", importance="required"),
            Skill(skill_name="Testing Strategy", category_code="SWE", evidence="Solid software engineering fundamentals including testing strategy and code review", confidence="high", importance="required"),
            Skill(skill_name="Git", category_code="SWE", evidence="Version control and collaboration in team environments", confidence="high", importance="required"),
        ]
    },
    {
        "filename": "Google LLC - Data Scientist.pdf",
        "company": "Google LLC",
        "role": "Data Scientist",
        "skills": [
            Skill(skill_name="SQL", category_code="SQL", evidence="Write efficient, production-grade SQL against very large datasets, schema design and query optimization", confidence="high", importance="required"),
            Skill(skill_name="Quantitative and Analytical Reasoning", category_code="APTI", evidence="Solid quantitative and analytical reasoning, interpreting experiment results, probability", confidence="high", importance="required"),
            Skill(skill_name="A/B Testing and Experimentation", category_code="AI", evidence="Design and run experiments (A/B tests) and interpret their results rigorously", confidence="high", importance="required"),
            Skill(skill_name="Machine learning", category_code="AI", evidence="Foundational machine learning knowledge: bias-variance tradeoff, regression vs. classification, gradient descent", confidence="high", importance="required"),
            Skill(skill_name="Python", category_code="COD", evidence="Python for data analysis and predictive modeling", confidence="high", importance="required"),
            Skill(skill_name="Statistics", category_code="AI", evidence="Applying sound statistical judgment and metrics evaluation", confidence="high", importance="required"),
            Skill(skill_name="Communication", category_code="COMM", evidence="Able to explain a complex model or surprising result to a product manager in plain language", confidence="high", importance="required"),
            Skill(skill_name="Data Visualization", category_code="OTHER", evidence="Visualizing metrics and findings for cross-functional partners", confidence="medium", importance="preferred"),
        ]
    },
    {
        "filename": "Microsoft - Data Analyst.pdf",
        "company": "Microsoft Corporation",
        "role": "Data Analyst",
        "skills": [
            Skill(skill_name="SQL", category_code="SQL", evidence="Write and optimize SQL queries against large production datasets", confidence="high", importance="required"),
            Skill(skill_name="Database schema design", category_code="SQL", evidence="Design schemas for telemetry and usage data, normalize vs denormalize", confidence="high", importance="required"),
            Skill(skill_name="Quantitative Reasoning", category_code="APTI", evidence="Interpreting trends, sampling, probability, and reasoning with data tables", confidence="high", importance="required"),
            Skill(skill_name="Applied Statistics", category_code="AI", evidence="Basic applied statistics/ML literacy: regression vs classification, overfitting", confidence="high", importance="required"),
            Skill(skill_name="Power BI / dashboards", category_code="OTHER", evidence="Build dashboards and reporting that stakeholders actually use", confidence="high", importance="required"),
            Skill(skill_name="Anomaly detection", category_code="AI", evidence="Detect and explain anomalies in usage or business metrics", confidence="medium", importance="preferred"),
            Skill(skill_name="Presenting to non-technical audiences", category_code="COMM", evidence="Translating a dashboard or analysis into a decision a non-technical leader can act on", confidence="high", importance="required"),
            Skill(skill_name="Excel", category_code="OTHER", evidence="Hands-on reporting tools and data modeling", confidence="medium", importance="preferred"),
        ]
    },
    {
        "filename": "Microsoft - Software Engineer.pdf",
        "company": "Microsoft Corporation",
        "role": "Software Engineer",
        "skills": [
            Skill(skill_name="Data Structures & Algorithms", category_code="DSA", evidence="Strong data structures and algorithms fundamentals: hash maps, trees, complexity analysis", confidence="high", importance="required"),
            Skill(skill_name="Coding", category_code="COD", evidence="Practical coding skills: pattern matching, interval problems, writing code for large inputs", confidence="high", importance="required"),
            Skill(skill_name="C++", category_code="COD", evidence="C++ or modern programming language proficiency", confidence="high", importance="required"),
            Skill(skill_name="Operating Systems", category_code="OS", evidence="Process scheduling, virtual memory, concurrency primitives", confidence="high", importance="required"),
            Skill(skill_name="Computer Networks", category_code="NETW", evidence="REST APIs, timeouts, request lifecycle, HTTP", confidence="high", importance="required"),
            Skill(skill_name="System Design", category_code="SYSD", evidence="Sketch a cloud-based storage or notification service and reason about scalability and fault tolerance", confidence="high", importance="required"),
            Skill(skill_name="Object-Oriented Design", category_code="OOD", evidence="Common design patterns with extensible, maintainable architecture", confidence="high", importance="required"),
            Skill(skill_name="Git", category_code="SWE", evidence="Version control, pull requests, and software lifecycle", confidence="high", importance="required"),
            Skill(skill_name="Testing and CI", category_code="SWE", evidence="Write clean, well-tested code and participate in code reviews", confidence="high", importance="required"),
            Skill(skill_name="Docker", category_code="CLOUD", evidence="Experience building and containerizing services on Azure or cloud platforms", confidence="medium", importance="preferred"),
        ]
    },
    {
        "filename": "Oracle - Application Support Analyst.pdf",
        "company": "Oracle Financial Services Software",
        "role": "Application Support Analyst",
        "skills": [
            Skill(skill_name="SQL (basic)", category_code="SQL", evidence="Comfort with basic SQL: simple SELECT/WHERE queries and understanding primary keys", confidence="high", importance="required"),
            Skill(skill_name="Linux basics", category_code="OS", evidence="Basic command-line usage, log file inspection, batch vs real-time processing", confidence="high", importance="required"),
            Skill(skill_name="Networking fundamentals", category_code="NETW", evidence="What an IP address is, client-server architecture fundamentals, latency", confidence="high", importance="required"),
            Skill(skill_name="Analytical reasoning", category_code="APTI", evidence="Data interpretation from tables, arithmetic, and structured problem-solving", confidence="high", importance="required"),
            Skill(skill_name="Team coordination", category_code="COMM", evidence="Able to explain a technical issue to a non-technical client, stay calm during incidents", confidence="high", importance="required"),
            Skill(skill_name="Incident troubleshooting", category_code="OTHER", evidence="Triage, investigate, and resolve incidents raised by banking clients within SLA", confidence="high", importance="required"),
            Skill(skill_name="Ticketing tools", category_code="OTHER", evidence="Coordinate with development teams on escalations, monitoring tools", confidence="medium", importance="preferred"),
        ]
    },
    {
        "filename": "Oracle - Associate Software Engineer.pdf",
        "company": "Oracle Financial Services Software",
        "role": "Associate Software Engineer",
        "skills": [
            Skill(skill_name="Java", category_code="COD", evidence="Read and predict output of code, solve basic string/array manipulation problems", confidence="high", importance="required"),
            Skill(skill_name="SQL", category_code="SQL", evidence="Correct SELECT/WHERE syntax, DELETE vs TRUNCATE, simple relational queries", confidence="high", importance="required"),
            Skill(skill_name="Data Structures", category_code="DSA", evidence="Arrays vs linked lists, when to use a stack or queue, basic algorithmic problem-solving", confidence="high", importance="required"),
            Skill(skill_name="Object-Oriented Programming", category_code="OOD", evidence="Inheritance, polymorphism, abstract classes vs interfaces with real examples", confidence="high", importance="required"),
            Skill(skill_name="Operating Systems", category_code="OS", evidence="Basic understanding of processes, threads, and filesystems", confidence="medium", importance="preferred"),
            Skill(skill_name="Communication", category_code="COMM", evidence="Document work clearly for future maintainers, participate in Agile ceremonies", confidence="high", importance="required"),
            Skill(skill_name="Testing and CI", category_code="SWE", evidence="Unit testing, collaborating closely with QA, debugging code", confidence="high", importance="required"),
        ]
    },
]


def seed():
    for item in JDS_DATA:
        obj = ExtractedSkillList(
            source_type="jd",
            source_file=item["filename"],
            company=item["company"],
            role=item["role"],
            skills=item["skills"],
            extras={},
        )
        storage.save("jd", item["filename"], obj)
        print(f"Saved JD: {item['filename']} ({len(item['skills'])} skills)")


if __name__ == "__main__":
    seed()
