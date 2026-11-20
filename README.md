# Oncology Knowledge Builder

Personal AI-powered oncology learning and intelligence platform.

The goal is to build a practical, continuously updated oncology knowledge system that combines **oncology fundamentals, disease-level learning, pharmaceutical intelligence, clinical development, regulatory updates, scientific literature, and commercial insights** in one place.

## What this project does

The Oncology Knowledge Builder is being developed as a free, continuously updated learning and intelligence platform.

### Daily Oncology Intelligence

Automatically collects and processes information from credible public sources including:

- FDA / regulatory sources
- ClinicalTrials.gov
- PubMed / NCBI
- Other authoritative oncology and regulatory sources

The collected information is processed into structured daily intelligence covering:

- Regulatory approvals and decisions
- Clinical trial developments
- Pipeline activity
- Scientific and research developments
- Important oncology concepts
- Analyst takeaways

## Disease Knowledge Builder

A structured learning system for mastering individual oncology indications.

Each disease module is designed to cover:

1. Definition
2. Disease classification
3. Epidemiology
4. Etiology
5. Risk factors
6. Causes
7. Pathophysiology
8. Disease severity
9. Signs and symptoms
10. Diagnosis
11. Biomarkers
12. Staging
13. Patient journey
14. Treatment landscape
15. Treatment algorithms
16. Clinical guidelines
17. Current standard of care
18. Emerging therapies
19. Clinical trials
20. Treatment resistance
21. Unmet needs
22. Key companies and products
23. Pipeline
24. Commercial / market implications
25. Regional differences
26. Key concepts to remember
27. Knowledge checks and quizzes

The content is intended to be based on **credible, authoritative sources** and presented in a simple, structured format designed for learning, retention, and practical application.

## Initial focus

The first detailed disease module is:

**Lung Cancer → NSCLC + SCLC**

The same framework will subsequently be expanded to other major oncology indications.

## Company Watchlist

A dedicated section for tracking important oncology companies and their:

- Pipeline
- Key assets
- Clinical trials
- Regulatory events
- Partnerships
- Acquisitions
- Major oncology announcements
- Strategic developments

## Oncology Conference Tracker

A dedicated tracker for major oncology conferences and congresses, including:

- ASCO
- ESMO
- AACR
- ASH
- SABCS
- WCLC
- SITC
- Other relevant oncology meetings

The objective is to identify important upcoming meetings and capture significant oncology data presented at those conferences.

## My Oncology Map

A personal learning-progress system to track:

- Diseases studied
- Disease modules completed
- Concepts mastered
- Topics requiring revision
- Companies studied
- Therapeutic areas covered

## Technology

The project is designed around a **zero-cost / free-tier architecture**.

Current stack:

- GitHub
- GitHub Actions
- GitHub Pages
- Python
- Public / free APIs and data sources
- Gemini API free tier
- HTML / CSS / JavaScript

## Repository structure

```text
oncology-knowledge-builder/
│
├── .github/
│   └── workflows/
│       ├── daily_digest.yml
│       ├── deploy.yml
│       ├── test_clinicaltrials.yml
│       ├── test_fda.yml
│       └── test_pubmed.yml
│
├── ai/
│   └── digest.py
│
├── collectors/
│   ├── fda.py
│   ├── clinicaltrials.py
│   └── pubmed.py
│
├── data/
│   ├── issues/
│   └── digests/
│
├── website/
│   ├── index.html
│   ├── prototype-reference.html
│   └── data/
│
├── requirements.txt
└── README.md
```

## Data flow

```text
Authoritative public sources
          ↓
     Python collectors
          ↓
     Structured JSON
          ↓
      Gemini AI layer
          ↓
    Daily intelligence
          ↓
      GitHub repository
          ↓
       GitHub Pages
          ↓
  Oncology Knowledge Builder
```

## Learning philosophy

The objective is not simply to collect oncology news.

The platform is intended to help build **deep therapeutic-area expertise** by connecting:

**Disease → Biology → Biomarkers → Diagnosis → Treatment → Clinical Development → Regulatory → Companies → Pipeline → Commercial implications**

Information should be presented in a way that is:

- Easy to understand
- Structured
- Concise
- Memorable
- Clinically meaningful
- Commercially relevant
- Suitable for progressive learning

## Status

Current development stage:

- [x] GitHub repository
- [x] FDA data collector
- [x] ClinicalTrials.gov collector
- [x] PubMed collector
- [x] Gemini daily digest generation
- [x] GitHub Actions automation
- [x] GitHub Pages deployment workflow
- [x] Website foundation
- [x] Claude-inspired website theme
- [ ] Live website → data integration
- [ ] Disease Knowledge Builder engine
- [ ] NSCLC master indication
- [ ] Company Watchlist
- [ ] Oncology Conference Tracker
- [ ] My Oncology Map
- [ ] Automated disease knowledge updates

## Vision

Build a personal oncology intelligence and learning system that progressively develops from a **news and knowledge dashboard** into a comprehensive **oncology therapeutic-area knowledge engine**.
