# India GCC Atlas

**India GCC Atlas** is a Streamlit prototype for international companies researching the establishment or expansion of a Global Capability Centre (GCC) in India. It brings company requirements, location research, talent and cost planning, policy research, operating-model options, and follow-up decisions into one guided workflow.

**Repository:** https://github.com/Aabha0503/india-gcc-atlas

> **Status:** Prototype / MVP in progress. Some features and cross-module integrations still require validation. Treat sample or synthetic data as illustrative unless explicitly supported by a source.

## Contents
- [Purpose](#purpose)
- [Product journey](#product-journey)
- [Screen 1: Company intake](#screen-1-company-intake)
- [Screen 2: Strategy workspace](#screen-2-strategy-workspace)
- [Evidence principles](#evidence-principles)
- [Run locally](#run-locally)
- [Project structure](#project-structure)
- [Limitations and next steps](#limitations-and-next-steps)

## Purpose

A company planning a GCC may need to compare cities, define functions and hiring plans, estimate costs, investigate policies, choose an operating model, and coordinate approvals. These questions are often researched across separate reports, spreadsheets, websites, and advisors.

India GCC Atlas is intended to organise this work, make assumptions and evidence visible, and create a structured planning brief. It supports decision-making; it does not replace professional legal, tax, HR, employment, data, or IP advice.

## Product journey

1. **Screen 1 — Company intake:** Capture the company's goals, constraints, proposed scope, and priorities.
2. **Screen 2 — Strategy workspace:** Use that context to organise research, compare options, track decisions, and plan follow-up work.

Intake answers are context, not automatic recommendations. They should not independently determine a city, operating model, policy eligibility, or final decision.

# Screen 1: Company intake

Screen 1 is a guided, multi-step questionnaire. Its intention is to understand the company's needs before it enters the research workspace.

### Step 1 — Your India plan

**Captures:** A description of the India plan, optional company name, headquarters country, and industry.

**Intention:** Establishes who is planning the expansion and why. It gives later research a company and sector context without forcing the user to express everything through fixed options.

### Step 2 — GCC scope and growth

**Captures:** Functions, target headcount range, ramp timeline, and illustrative roles/seniority.

**Intention:** Defines the intended scale and capabilities. A small analytics team and a large engineering centre have different talent, location, and operating needs. These are company planning inputs, not guaranteed forecasts.

### Step 3 — Budget and constraints

**Captures:** Budget sensitivity, existing India presence, regulatory/data/infrastructure constraints, and decision-makers.

**Intention:** Makes practical limits visible early. Options should be considered against the company's own budget, control needs, and constraints. User-entered information is not a compliance certification.

### Step 4 — Locations and decisions

**Captures:** Ranked location priorities, deal-breakers, decision-makers, and deadlines where supplied.

**Intention:** Clarifies what matters most in a location assessment and what could rule out an option. Priorities guide discussion; they are not an automated city ranking.

### Step 5 — Review and brief

**Does:** Displays intake answers for review and generates a structured entry-planning brief, with PDF export where supported.

**Intention:** Lets users check their inputs and creates a consistent starting document for internal discussion and Screen 2 planning.

# Screen 2: Strategy workspace

Screen 2 is intended to turn intake answers into connected research and decision tools. Each module has a distinct responsibility to avoid duplicating the same editors in multiple places.

## 1. Overview and navigation

**Purpose:** Provides access to the workspace's research and planning sections.

**Intention:** Helps users move between city research, talent and costs, policy research, operating-model choices, risk review, and roadmap planning while keeping the original company requirements in view.

## 2. Compare Cities

**Purpose:** Researches and compares candidate Indian cities and maintains a shortlist where supported.

**Intended content:** Candidate cities, city-level indicators, comparison factors tied to company priorities, and a shortlist.

**Intention:** Helps users compare locations using several relevant considerations rather than one headline metric. Metrics may differ by reporting period, geography, and methodology, so sources and caveats matter.

**Module boundary:** Compare Cities owns the city comparison and shortlist. Setup Options should use a read-only summary rather than recreate the city-selection tool.

## 3. Talent and Costs

**Purpose:** Organises workforce requirements, hiring-ramp assumptions, and cost-planning inputs.

**Intended content:** Functions, roles, seniority, target headcount, hiring-ramp assumptions, and cost estimates where supported by available data and calculations.

**Intention:** Connects the proposed scope to people and budget implications. It helps users identify assumptions that need validation before they are used in a business case.

**Module boundary:** Talent and Costs owns the hiring-ramp editor and cost estimate. Setup Options should reference those inputs rather than create a second editor. Synthetic values must be labelled as illustrative, not market-verified quotes.

## 4. Policies and Incentives

**Purpose:** Organises research into potentially relevant state policies, incentives, and ecosystem information.

**Intended content:** Policy checklist items, state/geographic context, sources and verification status where available, plus related ecosystem/provider information when supported by the data.

**Intention:** Helps users identify policies to investigate and the evidence needed to understand possible applicability. A policy listed in the workspace does **not** mean the company qualifies for an incentive.

**Module boundary:** Policies and Incentives owns the policy checklist. Setup Options should summarise the policy route and open verification questions, not duplicate the checklist.

## 5. Setup Options

**Purpose:** Compares possible operating models and records the decisions needed to move forward.

### Operating-model paths
- **Own entity:** Explore establishing and operating a company-owned Indian entity.
- **EOR (Employer of Record):** Explore using an employment provider for a defined scope, subject to legal, commercial, and operational review.
- **BOT (Build-Operate-Transfer):** Explore a partner building and operating a capability before a potential transfer, subject to contract and feasibility review.
- **Phased path:** Explore a possible transition from an initial model to a later model. This is a hypothesis to verify, not a default recommendation.

### Comparison dimensions
The intended comparison considers timeline, headcount/ramp, desired control, IP and data-control needs, risk tolerance, and existing India presence. Each assessment should state the company constraint, whether an option **Meets**, **Conflicts**, or **Cannot be judged**, the evidence state, source or explanation, and the open question.

Missing evidence should result in **Cannot be judged**, not a guessed answer. The comparison is not a scorecard and should not automatically rank models.

### Decision log
The log tracks six topics:
1. Candidate cities
2. Operating model
3. Hiring ramp
4. Budget and cost assumptions
5. Policy route
6. Transition path

Each record is intended to capture status, decision/proposal, rationale, owner, date, evidence references, assumptions, open questions, and next action.

Statuses:
- **Decided**
- **Proposed**
- **Undecided**
- **Waiting on verification**

Progress counts should reflect meaningful records with valid statuses, not empty placeholders. For example, “3 of 6 decisions recorded” describes record completion; it is not a launch-readiness score.

### Phased-path planning
Where relevant, record the initial and destination models, transition trigger/window, switching costs and time (if evidenced), legal/tax/HR/contract/data/IP dependencies, and evidence still required. Unknown costs and timelines must remain **To confirm** or **Not available**, not be invented.

**Intention:** Setup Options is the decision-management layer. It brings company requirements and summaries from other modules together to show what is known, proposed, unresolved, and who should act next.

**Module boundary:** It owns operating-model comparison and the decision log—not the city shortlist, hiring-ramp editor, cost estimate, or policy checklist.

## 6. Compliance and risk review

**Purpose:** Records compliance-related questions, risk considerations, and review status where supported.

**Intention:** Makes risks visible and identifies questions that require qualified internal or external review. It is not a legal/tax opinion, eligibility determination, or compliance certification.

## 7. Entry roadmap

**Purpose:** Organises actions and milestones after key planning decisions have been considered.

**Intention:** Turns decisions and open questions into follow-up work. The roadmap should reflect actual choices and dependencies, not present a generic schedule as a guaranteed implementation timeline.

## 8. Sources and evidence

**Purpose:** Provides source references and research context for claims and datasets used by the workspace.

**Intention:** Helps users inspect provenance, caveats, and freshness, and distinguish sourced information from assumptions. A source link alone does not prove that every claim is correct, current, or applicable.

## Evidence principles

| Evidence state | Meaning |
|---|---|
| **Verified source** | The relevant claim has been checked against the identified source for the stated purpose. |
| **Company-provided** | Supplied by the company; not independently verified. |
| **Assumption** | An illustrative planning input used to explore a scenario. |
| **To confirm** | Further research or review is required. |
| **Not available** | The information is not currently available in the workspace. |

Keep these states distinct. A company-provided headcount is not a market fact, an assumption is not a quote, and an unverified policy lead is not proof of eligibility.

### Responsible-use notes
- Do not claim an operating model is legally eligible, compliant, or ready to launch based only on this prototype.
- Do not invent setup costs, policy benefits, legal obligations, or implementation timelines.
- Preserve source, date, scope, and caveats for material claims where available.
- Keep uncertainty and conflicting evidence visible.
- Seek qualified professional review for legal, tax, employment, HR, data-protection, IP, and policy matters before acting.
- Treat demo or synthetic data as illustrative unless its provenance and status explicitly say otherwise.

## Run locally

The following commands reflect the Windows development workspace. Adjust paths to match the clone.

### Prerequisites
- Python installed.
- Git installed if cloning.
- Dependencies installed in a virtual environment.

### Clone
```powershell
git clone https://github.com/Aabha0503/india-gcc-atlas.git
cd india-gcc-atlas
```

### Create and activate a virtual environment
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies
If `requirements.txt` is in the repository root:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If it is inside `india_gcc_atlas_v2`:
```powershell
pip install -r .\india_gcc_atlas_v2\requirements.txt
```

### Launch the intake app
From the workspace root, using the development path:
```powershell
.\.venv\Scripts\python.exe -m streamlit run .\india_gcc_atlas_v2\intake_app.py
```

Streamlit prints a local URL in the terminal; open it in your browser. If launch fails, confirm the location of `intake_app.py`, the location of `requirements.txt`, and that the active environment has the required packages.

## Project structure

High-level structure discussed during development:

```text
india-gcc-atlas/
├── .gitignore
└── india_gcc_atlas_v2/
    ├── intake_app.py       # Screen 1 intake flow and app entry point
    ├── workspace.py        # Screen 2 workspace sections and navigation
    ├── setup_options.py    # Operating-model comparison and decision log
    ├── talent_costs.py     # Talent and cost planning
    ├── policy_ecosystem.py # Policy and ecosystem functionality
    ├── report_pdf.py       # PDF generation helpers
    ├── data/               # Research datasets and templates
    ├── tests/              # Automated tests, where present
    ├── requirements.txt    # App dependencies
    └── .streamlit/
        └── config.toml     # Streamlit theme/configuration
```

This is a high-level guide, not a guarantee that every file is present in the latest commit. Confirm the current repository tree before relying on a path or filename.

## Limitations and next steps

The prototype still needs verification in several areas:

- **Cross-module integration:** Confirm summaries reflect actual city, talent/cost, and policy inputs rather than placeholders.
- **Session-state continuity:** Confirm inputs survive navigation between sections.
- **Navigation reliability:** Test all navigation buttons for duplicate Streamlit widget keys and runtime errors.
- **Decision-log validation:** Ensure decisions marked Decided have adequate rationale and ownership information.
- **Brief/PDF wording:** Identify the output as a planning brief and include evidence states, assumptions, unresolved decisions, and professional-verification notes.
- **Data provenance:** Label sample/synthetic data and preserve sources and caveats.
- **Testing:** Run syntax checks, existing tests, a browser walkthrough, and PDF export checks in the target environment.

India GCC Atlas should be presented as a **planning and research prototype**, not a complete GCC establishment service. Its intended value is to organise questions, evidence, assumptions, and decisions so teams can conduct more structured research and professional review.

## Feedback and contributions

For a bug or feature request, open an issue in the [GitHub repository](https://github.com/Aabha0503/india-gcc-atlas) and include:
- The screen and feature involved.
- Steps to reproduce.
- Expected and actual behaviour.
- Relevant screenshots or error messages, with confidential information removed.

Test affected flows and update this README when the user journey or feature behaviour changes.

## License

No license terms are specified in this README. Check the repository for a `LICENSE` file before reusing, modifying, or redistributing the project.
