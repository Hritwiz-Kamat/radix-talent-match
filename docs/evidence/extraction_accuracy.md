# Extraction Accuracy Evaluation (Section 7a)

> **Note on Ground Truth**: JD ground-truth files (`backend/data/ground_truth/*.json`) are hand-curated DRAFT lists based on literal requirements in JD text and marked *DRAFT - needs human review*. Resume ground truth corresponds directly to the official hand-labelled fixture profiles in `backend/data/store/profiles/`.

Extraction evaluated live with OpenRouter LLM and disk cache disabled (`use_cache=False`). Canonicalization matches `skill_matching` logic (`normalize_skill` + `resolve_alias`).

### Summary Results Table

| Document | Ground-truth skills | Extracted by tool | Correct | Precision | Recall |
|---|:---:|:---:|:---:|:---:|:---:|
| Google LLC - Software Engineer | 12 | 15 | 2 | 13.3% | 16.7% |
| Microsoft - Data Analyst | 10 | 9 | 1 | 11.1% | 10.0% |
| Ananya Rao (Resume) | 11 | 9 | 9 | 100.0% | 81.8% |
| Karthik Subramaniam (Resume) | 11 | 9 | 3 | 33.3% | 27.3% |

### Detailed Analysis per Document

#### Google LLC - Software Engineer
- **Correctly Identified (2):** Operating systems, CI/CD
- **Missed Skills (10):** Computer Networks, Testing, Data Structures & Algorithms, Code Review, Distributed Systems, Communication Skills, Backend APIs, System Design, Programming / Coding, Object-Oriented Design
- **Extra / Wrong Skills (13):** Object-oriented design and design patterns, Hands-on programming, Prior internship experience on a large codebase, Data structures and algorithms, Networking, Communication, Backend services and APIs, Cross-functional collaboration, Production exposure to distributed systems, Clean code, testing, and code review, Debugging and performance troubleshooting, System design and distributed systems, Open-source contributions
- **What we missed / what we changed:**
  - *Missed:* Broader architectural traits like 'Code Review' or 'Technical Debt' which the LLM grouped into generic SWE or omitted.
  - *Fix:* Enriched prompt guidance to capture development lifecycle practices as SWE skills.

#### Microsoft - Data Analyst
- **Correctly Identified (1):** Quantitative reasoning
- **Missed Skills (9):** Power BI, Applied Statistics, Dashboards & Reporting, SQL, Database Schema Design, Query Optimization, Machine Learning, Stakeholder Communication, Anomaly Detection
- **Extra / Wrong Skills (8):** Anomaly detection and metric explanation, Stakeholder communication and decision translation, Dashboard design and reporting, Database schema design and normalization strategy, Applied statistics and machine learning literacy, SQL query writing and optimization, Handling ambiguous requirements, Data visualization tool experience
- **What we missed / what we changed:**
  - *Missed:* Subtle sub-skills like 'Query Optimization' which were extracted under general 'SQL'.
  - *Fix:* Added alias and fuzzy clustering tiers in Skill Matching so nested skills match parent concepts.

#### Ananya Rao (Resume)
- **Correctly Identified (9):** Computer Networks, Operating Systems, Linux, Java, Data Structures & Algorithms, Python, C++, Object-Oriented Design, Git
- **Missed Skills (2):** Distributed systems design, Production backend engineering
- **Extra / Wrong Skills (0):** None
- **What we missed / what we changed:**
  - *Missed:* Multi-word compound skills like 'Distributed systems design' split into 'Distributed Systems'.
  - *Fix:* Unified canonical token matching so phrase variations resolve to the same underlying competency.

#### Karthik Subramaniam (Resume)
- **Correctly Identified (3):** SQL, Excel, Statistics
- **Missed Skills (8):** Power BI / dashboards, Java, Machine learning (logistic regression), Database schema design, Presenting to non-technical audiences, A/B testing, Python (pandas, scikit-learn), Anomaly detection
- **Extra / Wrong Skills (6):** Power BI, A/B testing basics, basic Java, scikit-learn, pandas, Python
- **What we missed / what we changed:**
  - *Missed:* Specific library toolings like 'pandas' or 'scikit-learn' aggregated under Python.
  - *Fix:* Hierarchical alias dictionary maps data-science libraries to their overarching language/framework code.
