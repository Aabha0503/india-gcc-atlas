"""Phase-one Strategy Workspace shell and intake-driven Overview."""

from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from report_pdf import build_pdf_report
from policy_ecosystem import (
    CHECKLIST_STATUSES,
    COMPANY_ELIGIBILITY_STATUSES,
    ELIGIBILITY_STAGES,
    PROVIDER_CATEGORIES,
    PolicyDataError,
    load_policy_workspace,
    save_checklist_review,
    save_policy_review,
    summarize_policy_status,
)
from talent_costs import (
    SYNTHETIC_LABEL,
    budget_comparison,
    calculate_cost_scenarios,
    default_role_mix,
    load_demo_pack,
    parse_headcount,
)
from setup_options import render_setup_options


SECTIONS = [
    "Overview",
    "Compare cities",
    "Talent and costs",
    "Policies and ecosystem",
    "Setup options",
    "Compliance and risk",
    "Entry roadmap",
    "Sources and evidence",
]

INITIAL_CITY_SHORTLIST = ("Bengaluru", "Hyderabad", "Pune", "Chennai")

EVIDENCE_STATUSES = (
    "unreviewed",
    "source_located",
    "verified",
    "disputed",
    "rejected",
)

REQUIRED_RULES = (
    ("headquarters_country", "Headquarters country"),
    ("industry", "Industry"),
    ("headcount", "Target headcount response"),
    ("ramp_timeline", "Hiring / launch ramp"),
    ("priority_1", "First location priority"),
)

CITY_DATA_COLUMNS = (
    "city",
    "state",
    "gcc_count_as_printed",
    "source",
    "source_page",
)
OFFICE_DATA_COLUMNS = (
    "city",
    "region",
    
    "office_leasing_2025_mn_sqft",
    "source",
    "source_url",
    "evidence_note",
)
GCC_COMPANY_DATA_COLUMNS = (
    "company",
    "city",
    "sector",
    "presence_status",
    "source",
    "source_url",
    "confidence",
    "last_reviewed",
)
DEMO_DATA_DIRECTORY = (
    Path(__file__).parent / "data" / "india_gcc_atlas_demo_sample_data"
)
DEMO_METRIC_COLUMNS = (
    "record_id",
    "city",
    "priority",
    "metric_name",
    "value_low",
    "value_high",
    "unit",
    "evidence_status",
    "evidence_grade",
    "geographic_scope",
    "caveat",
    "source_id",
    "source_location",
    "last_checked_date",
    "is_synthetic",
)
DEMO_SOURCE_COLUMNS = (
    "source_id",
    "publisher",
    "source_title",
    "source_url",
    "publication_date",
    "source_type",
    "source_notes",
    "last_checked_date",
    "is_synthetic",
)
DEMO_CLAIM_COLUMNS = (
    "claim_id",
    "claim_name",
    "claim_text",
    "entity_type",
    "entity_id",
    "entity_name_as_reported",
    "geographic_scope",
    "reported_value",
    "unit",
    "period",
    "source_id",
    "source_location",
    "last_checked_date",
    "verification_status",
    "evidence_quality",
    "caveat",
    "conflicts_with",
    "is_synthetic",
)
DEMO_POLICY_COLUMNS = (
    "policy_id",
    "state",
    "policy_name",
    "benefit_summary",
    "eligibility_status",
    "evidence_status",
    "caveat",
    "is_synthetic",
)

EVIDENCE_DISPLAY_STATES = (
    "Sourced",
    "To confirm",
    "Indicative",
    "Context only",
    "Not available",
)
EVIDENCE_MARKS = {
    "Sourced": "● Sourced",
    "To confirm": "○ To confirm",
    "Indicative": "◒ Indicative",
    "Context only": "◇ Context only",
    "Not available": "▧ Not available",
}

CRITERION_TASKS = {
    "Talent availability": {
        "id": "talent-availability",
        "group": "Talent and hiring feasibility",
        "title": "Validate role-level talent supply and hiring capacity",
        "evidence": (
            "Comparable city-level talent-pool evidence by role and seniority, "
            "plus hiring capacity and ramp assumptions."
        ),
        "why": (
            "Talent availability is the first stated location priority, and "
            "the planned technical team depends on hiring feasibility."
        ),
        "decision": "Which candidate locations can support the planned hiring ramp?",
        "source_type": (
            "Dated labor-market studies, role-specific skills data, and "
            "documented recruiting-capacity evidence."
        ),
    },
    "Talent cost": {
        "id": "talent-cost",
        "group": "Compensation and operating costs",
        "title": "Obtain comparable role-specific salary benchmarks",
        "evidence": (
            "Salary ranges by role, seniority, city, currency, data period, "
            "and methodology."
        ),
        "why": (
            "Talent cost is the second stated priority and cost sensitivity is "
            "set to very cost-sensitive."
        ),
        "decision": "How do compensation assumptions affect the viable location and team plan?",
        "source_type": (
            "Dated compensation surveys or validated recruiter data with "
            "role and seniority definitions."
        ),
    },
    "Proximity to customers or leadership": {
        "id": "proximity",
        "group": "Talent and hiring feasibility",
        "title": "Define customer and leadership proximity requirements",
        "evidence": (
            "Customer and leadership locations, required travel frequency, "
            "and comparable route or time-zone information."
        ),
        "why": "This is a stated location priority, but no origin locations or travel needs are captured.",
        "decision": "Which city locations meet the company's actual collaboration and travel needs?",
        "source_type": (
            "Company-provided customer/leadership locations and dated "
            "air-route or travel-time data."
        ),
    },
    "Office availability and cost": {
        "id": "office-cost",
        "group": "Office space and infrastructure",
        "title": "Verify office inventory, rent, and infrastructure fit",
        "evidence": (
            "Available space, asking rent, unit and period, submarket, "
            "building specification, and connectivity requirements."
        ),
        "why": (
            "Office cost is a stated priority. Existing city data records "
            "gross leasing volume only, not rent or available inventory."
        ),
        "decision": "Can suitable office space be secured within the operating constraints and budget?",
        "source_type": (
            "Dated commercial-property inventory and comparable broker or "
            "market reports; connectivity service evidence."
        ),
    },
    "Relevant industry ecosystem": {
        "id": "industry-ecosystem",
        "group": "Setup model and service providers",
        "title": "Validate relevant company and service-provider ecosystem",
        "evidence": (
            "Record-level company and provider evidence with city, service "
            "scope, source, and verification status."
        ),
        "why": "This is a user-selected location criterion; current presence leads require record-level validation.",
        "decision": "Which locations have a relevant ecosystem supported by the company's needs?",
        "source_type": "Company disclosures, official ecosystem records, and due-diligenced provider information.",
    },
    "Connectivity and infrastructure": {
        "id": "connectivity",
        "group": "Office space and infrastructure",
        "title": "Assess site-level connectivity and infrastructure requirements",
        "evidence": (
            "Company service requirements and site/building-specific network, "
            "power, cloud-connectivity, and resilience information."
        ),
        "why": "Connectivity is a user-selected criterion and is mentioned in the intake constraints; city-level generalizations are insufficient.",
        "decision": "Can candidate sites meet the company's actual technical and continuity needs?",
        "source_type": "Company architecture requirements and provider/building documentation.",
    },
    "Quality of life and talent retention": {
        "id": "retention",
        "group": "Talent and hiring feasibility",
        "title": "Define and compare talent-retention factors",
        "evidence": (
            "Company-defined retention measures and comparable, dated "
            "role- and location-specific workforce evidence."
        ),
        "why": "Retention is a user-selected criterion; no comparable retention evidence is in the current register.",
        "decision": "Which locations meet the company's defined retention needs?",
        "source_type": "Dated labor-market surveys and company-specific retention requirements.",
    },
    "State incentives and support": {
        "id": "state-incentives",
        "group": "State policies and incentives",
        "title": "Verify state-policy and incentive relevance and eligibility",
        "evidence": (
            "Current official policy text, effective dates, eligibility "
            "conditions, application steps, and written confirmation where needed."
        ),
        "why": "This is a user-selected criterion; no incentive or eligibility claims are registered.",
        "decision": "Are current state programs relevant and is the company eligible?",
        "source_type": "Official state-government notifications and program documentation.",
    },
    "Business continuity and risk diversification": {
        "id": "continuity",
        "group": "Office space and infrastructure",
        "title": "Assess continuity and location-concentration risks",
        "evidence": (
            "Company continuity requirements and comparable site/location "
            "risk, redundancy, and recovery information."
        ),
        "why": "This is a user-selected criterion; no company-specific risk tolerance or comparable continuity evidence is recorded.",
        "decision": "Do candidate locations meet the company's continuity and diversification requirements?",
        "source_type": "Company continuity plan and documented site/location risk assessments.",
    },
}

BASE_RESEARCH_TASKS = (
    {
        "id": "corporate-compliance",
        "group": "Corporate setup and compliance",
        "title": "Scope legal, employment, data, tax, and transfer-pricing review",
        "evidence": (
            "Company structure, work types, data flows, employment model, "
            "and written advice from qualified advisers."
        ),
        "why": "These requirements may constrain setup and operations; no compliance claims are verified in the current register.",
        "decision": "Which obligations and approvals must be addressed before choosing a setup model?",
        "source_type": "Qualified Indian legal, employment, tax, and data-protection advisers; official dated materials.",
    },
    {
        "id": "policy-incentives",
        "group": "State policies and incentives",
        "title": "Check current state policy and incentive eligibility",
        "evidence": (
            "Current official policy text, effective dates, eligibility "
            "conditions, application steps, and written confirmation where needed."
        ),
        "why": "The evidence register contains no policy or incentive claims; eligibility cannot be assumed from location.",
        "decision": "Are any current policies relevant and is the company eligible?",
        "source_type": "Official state-government notifications and program documentation.",
    },
    {
        "id": "setup-options",
        "group": "Setup model and service providers",
        "title": "Compare EOR, BOT, and own-entity options with advisers",
        "evidence": (
            "Operating requirements, control needs, expected duration, "
            "professional advice, and validated provider due diligence."
        ),
        "why": "The intake identifies a new India presence, but no setup-model or service-provider claims are registered.",
        "decision": "Which operating model fits the company's control, timing, and risk needs?",
        "source_type": "Qualified legal/tax advice, provider contracts, and client-specific diligence.",
    },
)


def _value(answers: dict[str, Any], key: str) -> Any:
    return answers.get(key)


def _is_selected(value: Any, placeholders: tuple[str, ...]) -> bool:
    return (
        value is not None
        and bool(str(value).strip())
        and str(value).strip() not in placeholders
    )


def _industry(answers: dict[str, Any]) -> str:
    industry = str(_value(answers, "industry") or "").strip()
    if industry == "Other":
        return str(_value(answers, "industry_other") or "").strip()
    if industry == "Select an industry":
        return ""
    return industry


def _headcount(answers: dict[str, Any]) -> str:
    headcount = str(_value(answers, "headcount") or "").strip()
    if headcount == "Custom range":
        return str(_value(answers, "headcount_custom") or "").strip()
    if headcount == "Select a target range":
        return ""
    return headcount


def _priorities(answers: dict[str, Any]) -> list[str]:
    return [
        str(answers.get(f"priority_{rank}") or "").strip()
        for rank in range(1, 5)
        if _is_selected(
            answers.get(f"priority_{rank}"),
            ("Select a priority",),
        )
    ]


def _planned_functions(answers: dict[str, Any]) -> list[str]:
    functions = [
        str(function).strip()
        for function in (_value(answers, "gcc_functions") or [])
        if str(function).strip()
    ]
    other_function = str(_value(answers, "functions_other") or "").strip()
    if other_function:
        functions.append(other_function)
    return functions


def _required_checks(answers: dict[str, Any]) -> list[tuple[str, bool]]:
    industry_complete = bool(_industry(answers))
    headcount = str(_value(answers, "headcount") or "").strip()
    headcount_complete = headcount not in ("", "Select a target range")
    if headcount == "Custom range":
        headcount_complete = bool(_headcount(answers))

    return [
        (
            REQUIRED_RULES[0][1],
            _is_selected(_value(answers, "headquarters_country"), ("",)),
        ),
        (REQUIRED_RULES[1][1], industry_complete),
        (REQUIRED_RULES[2][1], headcount_complete),
        (
            REQUIRED_RULES[3][1],
            _is_selected(
                _value(answers, "ramp_timeline"),
                ("Select a timeline",),
            ),
        ),
        (
            REQUIRED_RULES[4][1],
            _is_selected(_value(answers, "priority_1"), ("Select a priority",)),
        ),
    ]


def _required_gaps(answers: dict[str, Any]) -> list[tuple[str, str]]:
    gaps: list[tuple[str, str]] = []
    if not str(_value(answers, "headquarters_country") or "").strip():
        gaps.append(
            (
                "Add the headquarters country",
                "It provides the company’s home-market context for the entry plan.",
            )
        )

    industry = str(_value(answers, "industry") or "").strip()
    if not _industry(answers):
        prompt = (
            "Add the industry."
            if industry != "Other"
            else "Specify the industry selected as Other."
        )
        gaps.append(
            (
                prompt,
                "Industry context affects which market, talent, and compliance "
                "evidence may be relevant.",
            )
        )

    headcount = str(_value(answers, "headcount") or "").strip()
    if headcount == "Select a target range":
        gaps.append(
            (
                "Add a target headcount or choose “Not sure yet”",
                "Team size informs hiring capacity and any future cost assumptions.",
            )
        )
    elif headcount == "Custom range" and not _headcount(answers):
        gaps.append(
            (
                "Describe the custom headcount range",
                "The selected custom-range option needs a value before it is complete.",
            )
        )

    if not _is_selected(
        _value(answers, "ramp_timeline"),
        ("Select a timeline",),
    ):
        gaps.append(
            (
                "Add a hiring / launch ramp or choose “Not sure yet”",
                "Timing is needed to assess capacity and later plan dependencies.",
            )
        )
    if not _is_selected(
        _value(answers, "priority_1"),
        ("Select a priority",),
    ):
        gaps.append(
            (
                "Choose at least one location priority",
                "The workspace should compare evidence against your priorities, "
                "not invent a ranking.",
            )
        )
    return gaps


def _optional_gaps(answers: dict[str, Any]) -> list[tuple[str, str]]:
    gaps: list[tuple[str, str]] = []
    if not str(_value(answers, "plan_description") or "").strip():
        gaps.append(
            (
                "Describe the India plan",
                "A short description gives reviewers the user-provided context "
                "behind the structured answers.",
            )
        )
    if not str(_value(answers, "decision_makers") or "").strip():
        gaps.append(
            (
                "Identify who must approve or influence the decision",
                "This helps clarify ownership and whose input is needed before "
                "the company commits.",
            )
        )
    if not _is_selected(
        _value(answers, "india_presence"),
        ("Select an option",),
    ):
        gaps.append(
            (
                "Clarify the company’s existing India presence",
                "An existing entity, team, or vendor can affect setup choices "
                "and the starting point for the plan.",
            )
        )
    if not _is_selected(
        _value(answers, "budget_sensitivity"),
        ("Select an option",),
    ):
        gaps.append(
            (
                "Set or explicitly defer budget / cost sensitivity",
                "This helps frame later comparisons; “Budget not set yet” is a "
                "valid answered response.",
            )
        )
    if not str(_value(answers, "roles_seniority") or "").strip():
        gaps.append(
            (
                "Add priority roles and seniority when known",
                "Role mix is needed before salary benchmarks or talent "
                "availability can be meaningfully compared.",
            )
        )
    if not _value(answers, "decision_deadline"):
        gaps.append(
            (
                "Add a decision deadline if one is known",
                "The roadmap can only work backwards from an actual target date.",
            )
        )
    if not str(_value(answers, "launch_deadline") or "").strip():
        gaps.append(
            (
                "Add a target launch timing if one is known",
                "This separates the decision date from the intended operating "
                "start date.",
            )
        )
    if not str(_value(answers, "regulatory_constraints") or "").strip():
        gaps.append(
            (
                "Record known constraints or note what remains under review",
                "Data, security, and regulatory constraints can change setup "
                "and location requirements.",
            )
        )
    return gaps


def _read_csv(path: Path, required_columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        st.error(f"Required evidence file is missing: {path.name}")
        st.stop()

    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            st.error(f"Evidence file has no header row: {path.name}")
            st.stop()
        missing_columns = [name for name in required_columns if name not in reader.fieldnames]
        if missing_columns:
            st.error(
                f"{path.name} is missing required columns: "
                + ", ".join(missing_columns)
            )
            st.stop()
        return list(reader)


def _load_evidence() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    data_dir = Path(__file__).parent / "data"
    sources = _read_csv(
        data_dir / "sources.csv",
        ("source_id", "publisher", "source_title", "source_url", "publication_date"),
    )
    claims = _read_csv(
        data_dir / "claims.csv",
        (
            "claim_id",
            "claim_name",
            "claim_text",
            "entity_name_as_reported",
            "reported_value",
            "unit",
            "period",
            "source_id",
            "source_location",
            "last_checked_date",
            "verification_status",
            "evidence_quality",
            "caveat",
            "conflicts_with",
        ),
    )
    return sources, claims


def _load_city_data() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    data_dir = Path(__file__).parent / "data"
    city_counts = _read_csv(data_dir / "aim_city_counts.csv", CITY_DATA_COLUMNS)
    office_market = _read_csv(data_dir / "cities.csv", OFFICE_DATA_COLUMNS)
    return city_counts, office_market


def _city_comparison_rows(
    city_counts: list[dict[str, str]],
    office_market: list[dict[str, str]],
    claims: list[dict[str, str]],
    priorities: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    count_by_city = {
        row.get("city", "").strip().casefold(): row for row in city_counts
    }
    office_by_city = {
        row.get("city", "").strip().casefold(): row for row in office_market
    }
    claim_by_city = {
        claim.get("entity_name_as_reported", "").strip().casefold(): claim
        for claim in claims
        if claim.get("entity_type", "").strip() == "city"
    }
    city_names = list(dict.fromkeys(
        [
            row.get("city", "").strip()
            for row in city_counts + office_market
            if row.get("city", "").strip()
        ]
    ))
    rows: list[dict[str, str]] = []
    for city in city_names:
        key = city.casefold()
        count_record = count_by_city.get(key)
        office_record = office_by_city.get(key)
        claim = claim_by_city.get(key)
        if count_record:
            count_value = count_record.get("gcc_count_as_printed", "").strip()
            count_location = count_record.get("source_page", "").strip()
            count_source = count_record.get("source", "").strip()
            if claim:
                count_status = (
                    f"{claim.get('verification_status', '').strip() or 'status not recorded'}"
                    f" · {claim.get('claim_id', '').strip()}"
                )
            else:
                count_status = "Unreviewed CSV row; no claim-level status"
            count_citation = " · ".join(
                value for value in (count_source, f"page {count_location}" if count_location else "") if value
            )
            count_note = (
                claim.get("caveat", "").strip()
                if claim
                else "Transcribed dataset row; no claim-level verification status is recorded."
            )
        else:
            count_value = "Not available in current evidence"
            count_status = "No city-count row"
            count_citation = ""
            count_note = ""

        if office_record:
            office_value = office_record.get("office_leasing_2025_mn_sqft", "").strip()
            office_status = "Source-reported city-wide gross leasing; not independently verified"
            office_citation = office_record.get("source", "").strip()
            office_url = office_record.get("source_url", "").strip()
            office_note = office_record.get("evidence_note", "").strip()
        else:
            office_value = "Not available in current evidence"
            office_status = "No city-specific office-leasing row"
            office_citation = ""
            office_url = ""
            office_note = ""

        rows.append(
            {
                "City / region (kept as recorded)": city,
                "State / region": (
                    count_record.get("state", "").strip()
                    if count_record
                    else office_record.get("region", "").strip()
                    if office_record
                    else "Not recorded"
                ),
                "Reported GCC count": count_value,
                "Count verification status": count_status,
                "Count source / location": count_citation or "Not recorded",
                "2025 gross office leasing (mn sq ft)": office_value,
                "Office evidence status": office_status,
                "Talent availability": "Not available in current evidence",
                "Role-specific talent cost": "Not available in current evidence",
                "Office rent / available space": "Not available in current evidence",
                "Policy / incentive evidence": "Not available in current evidence",
                "City fit assessment": (
                    "Not scored — requires comparable evidence against the user's priorities"
                    if priorities
                    else "Not assessed — no location priorities provided"
                ),
                "Key caveats": "; ".join(
                    value
                    for value in (
                        count_note,
                        office_note,
                        "No city ranking is calculated.",
                    )
                    if value
                ),
                "_office_source": office_citation,
                "_office_url": office_url,
            }
        )
    return city_names, rows


def _load_gcc_company_data() -> list[dict[str, str]]:
    data_dir = Path(__file__).parent / "data"
    return _read_csv(data_dir / "gcc_companies.csv", GCC_COMPANY_DATA_COLUMNS)


def _read_demo_csv(
    filename: str,
    required_columns: tuple[str, ...],
    errors: list[str],
) -> list[dict[str, str]]:
    path = DEMO_DATA_DIRECTORY / filename
    if not path.is_file():
        errors.append(f"Missing demo data file: {filename}")
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                errors.append(f"{filename} has no header row.")
                return []
            missing_columns = [
                column for column in required_columns
                if column not in reader.fieldnames
            ]
            if missing_columns:
                errors.append(
                    f"{filename} is missing required columns: "
                    + ", ".join(missing_columns)
                )
                return []
            rows: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    errors.append(
                        f"{filename}, row {line_number}: unexpected extra CSV values."
                    )
                    continue
                rows.append(
                    {
                        key: (value or "").strip()
                        for key, value in row.items()
                        if key is not None
                    }
                )
            return rows
    except (OSError, UnicodeError, csv.Error) as error:
        errors.append(f"Could not read {filename}: {error}")
        return []


def _demo_flag_is_true(value: str) -> bool:
    return value.strip().casefold() in ("true", "1", "yes")


def _load_demo_dataset() -> dict[str, Any]:
    errors: list[str] = []
    raw_metrics = _read_demo_csv(
        "demo_city_metrics.csv", DEMO_METRIC_COLUMNS, errors
    )
    sources = _read_demo_csv(
        "demo_sources.csv", DEMO_SOURCE_COLUMNS, errors
    )
    claims = _read_demo_csv(
        "demo_claims.csv", DEMO_CLAIM_COLUMNS, errors
    )
    policies = _read_demo_csv(
        "demo_state_policy_placeholders.csv", DEMO_POLICY_COLUMNS, errors
    )

    valid_sources: list[dict[str, Any]] = []
    for line_number, source in enumerate(sources, start=2):
        if not source.get("source_id") or not source.get("source_title"):
            errors.append(
                f"demo_sources.csv, row {line_number}: source_id and source_title are required."
            )
            continue
        if not _demo_flag_is_true(source.get("is_synthetic", "")):
            errors.append(
                f"demo_sources.csv, row {line_number}: is_synthetic must be true."
            )
            continue
        valid_sources.append({**source, "is_synthetic": True})
    source_ids = {source["source_id"] for source in valid_sources}

    valid_claims: list[dict[str, Any]] = []
    for line_number, claim in enumerate(claims, start=2):
        if not claim.get("claim_id") or not claim.get("source_id"):
            errors.append(
                f"demo_claims.csv, row {line_number}: claim_id and source_id are required."
            )
            continue
        if claim.get("verification_status", "").casefold() != "demo_only":
            errors.append(
                f"demo_claims.csv, row {line_number}: verification_status must remain demo_only."
            )
            continue
        if not _demo_flag_is_true(claim.get("is_synthetic", "")):
            errors.append(
                f"demo_claims.csv, row {line_number}: is_synthetic must be true."
            )
            continue
        if claim["source_id"] not in source_ids:
            errors.append(
                f"demo_claims.csv, row {line_number}: source_id "
                f"{claim['source_id']} does not match a demo source."
            )
            continue
        valid_claims.append({**claim, "is_synthetic": True})

    valid_metrics: list[dict[str, Any]] = []
    for line_number, metric in enumerate(raw_metrics, start=2):
        required_values = (
            "record_id",
            "city",
            "priority",
            "metric_name",
            "unit",
            "evidence_status",
            "geographic_scope",
            "source_id",
            "source_location",
        )
        missing = [key for key in required_values if not metric.get(key)]
        if missing:
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: missing "
                + ", ".join(missing)
                + "."
            )
            continue
        if metric.get("evidence_status", "").upper() != "DEMO_ONLY":
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: evidence_status must be DEMO_ONLY."
            )
            continue
        if not _demo_flag_is_true(metric.get("is_synthetic", "")):
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: is_synthetic must be true."
            )
            continue
        if metric["source_id"] not in source_ids:
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: source_id "
                f"{metric['source_id']} does not match a demo source."
            )
            continue
        try:
            low = float(metric.get("value_low", ""))
            high = float(metric.get("value_high", ""))
        except ValueError:
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: value_low and "
                "value_high must be numeric; the row was omitted, not set to zero."
            )
            continue
        if not (math.isfinite(low) and math.isfinite(high)):
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: range values must be finite."
            )
            continue
        if low > high:
            errors.append(
                f"demo_city_metrics.csv, row {line_number}: value_low exceeds value_high."
            )
            continue
        valid_metrics.append(
            {
                **metric,
                "value_low": low,
                "value_high": high,
                "is_synthetic": True,
                "demo_label": "Illustrative demo data",
            }
        )

    valid_policies: list[dict[str, Any]] = []
    for line_number, policy in enumerate(policies, start=2):
        if not policy.get("policy_id") or not policy.get("state"):
            errors.append(
                f"demo_state_policy_placeholders.csv, row {line_number}: policy_id and state are required."
            )
            continue
        if not _demo_flag_is_true(policy.get("is_synthetic", "")):
            errors.append(
                f"demo_state_policy_placeholders.csv, row {line_number}: is_synthetic must be true."
            )
            continue
        valid_policies.append({**policy, "is_synthetic": True})

    claim_ids = {claim.get("claim_id") for claim in valid_claims}
    for metric in valid_metrics:
        if metric["record_id"] not in claim_ids:
            errors.append(
                f"{metric['record_id']}: no matching synthetic claim row is available."
            )

    return {
        "metrics": valid_metrics,
        "sources": valid_sources,
        "claims": valid_claims,
        "policies": valid_policies,
        "errors": errors,
    }


def _claim_display_state(
    claim: dict[str, str],
    sources_by_id: dict[str, dict[str, str]],
) -> str:
    status = claim.get("verification_status", "").strip().casefold()
    if status in ("rejected",):
        return "Not available"
    if status in ("indicative",):
        return "Indicative"
    if status in ("context only", "context_only"):
        return "Context only"
    if status != "verified":
        return "To confirm"

    source_id = claim.get("source_id", "").strip()
    city_name = claim.get("entity_name_as_reported", "").strip()
    geographic_scope = claim.get("geographic_scope", "").strip()
    required_fields = (
        "claim_name",
        "entity_name_as_reported",
        "geographic_scope",
        "reported_value",
        "unit",
        "period",
        "source_location",
        "evidence_quality",
    )
    if (
        source_id in sources_by_id
        and all(claim.get(field, "").strip() for field in required_fields)
        and city_name.casefold() in geographic_scope.casefold()
    ):
        return "Sourced"
    return "To confirm"


def _priority_evidence_cell(
    city: str,
    priority: str,
    claims: list[dict[str, str]],
    city_counts: list[dict[str, str]],
    sources: list[dict[str, str]],
    office_market: list[dict[str, str]],
    company_presence: list[dict[str, str]],
) -> dict[str, Any]:
    sources_by_id = {
        source.get("source_id", "").strip(): source
        for source in sources
        if source.get("source_id", "").strip()
    }
    terms = LOCATION_EVIDENCE_TERMS.get(priority, ())
    matching_claims = [
        claim
        for claim in claims
        if claim.get("entity_type", "").strip() == "city"
        and claim.get("entity_name_as_reported", "").strip().casefold()
        == city.casefold()
        and terms
        and _claim_has_terms(claim, terms)
    ]
    supporting_claims = [
        claim for claim in matching_claims
        if claim.get("verification_status", "").strip().casefold() != "rejected"
    ]
    states = [
        _claim_display_state(claim, sources_by_id)
        for claim in supporting_claims
    ]
    has_conflict = any(
        claim.get("conflicts_with", "").strip()
        or claim.get("verification_status", "").strip().casefold() == "disputed"
        for claim in matching_claims
    )
    if has_conflict or "To confirm" in states:
        state = "To confirm"
    elif "Sourced" in states:
        state = "Sourced"
    elif "Indicative" in states:
        state = "Indicative"
    elif "Context only" in states:
        state = "Context only"
    elif matching_claims:
        state = "Not available"
    elif priority == "Office availability and cost" and any(
        record.get("city", "").strip().casefold() == city.casefold()
        for record in office_market
    ):
        state = "Context only"
    elif priority == "Relevant industry ecosystem" and any(
        record.get("city", "").strip().casefold() == city.casefold()
        for record in company_presence
    ):
        state = "To confirm"
    else:
        state = "Not available"

    office_records = [
        record for record in office_market
        if record.get("city", "").strip().casefold() == city.casefold()
    ]
    presence_records = [
        record for record in company_presence
        if record.get("city", "").strip().casefold() == city.casefold()
    ]
    count_records = [
        record
        for record in city_counts
        if record.get("city", "").strip().casefold() == city.casefold()
    ]
    count_claims = [
        claim
        for claim in claims
        if claim.get("entity_type", "").strip() == "city"
        and claim.get("entity_name_as_reported", "").strip().casefold()
        == city.casefold()
    ]

    explanations = {
        "Sourced": "A matching claim is verified, linked to a registered source, and has a value, unit, period, geographic scope, and source location.",
        "To confirm": "A relevant record exists, but it is unreviewed, disputed, incomplete, or still needs record-level source validation.",
        "Indicative": "The underlying record is explicitly labelled indicative; it is not treated as verified evidence.",
        "Context only": "A related record exists, but it does not directly measure this priority and cannot support a city comparison.",
        "Not available": "No relevant, usable city-level record is available for this priority.",
    }
    return {
        "city": city,
        "priority": priority,
        "state": state,
        "label": EVIDENCE_MARKS[state],
        "explanation": explanations[state],
        "claims": matching_claims,
        "sources_by_id": sources_by_id,
        "office_records": office_records,
        "company_presence": presence_records,
        "city_count_records": count_records,
        "city_count_claims": count_claims,
    }


def _coverage_weighted_rows(
    selected_cities: list[str],
    priorities: list[str],
    evidence_cells: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    weights = {
        priority: max(0, 5 - rank)
        for rank, priority in enumerate(priorities[:4], start=1)
    }
    total_weight = sum(weights.values())
    rows: list[dict[str, Any]] = []
    for city in selected_cities:
        sourced_priorities = [
            priority
            for priority in priorities[:4]
            if evidence_cells[(city, priority)]["state"] == "Sourced"
        ]
        covered_weight = sum(weights[priority] for priority in sourced_priorities)
        rows.append(
            {
                "City": city,
                "Evidence coverage": (
                    round(covered_weight / total_weight * 100)
                    if total_weight
                    else 0
                ),
                "Sourced priorities": len(sourced_priorities),
                "Covered weight": covered_weight,
                "Available weight": total_weight,
            }
        )
    return rows


def _demo_priority_weights(priorities: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "Priority order": rank,
            "Intake priority": priority,
            "Discussion weight": max(0, 5 - rank) if rank <= 4 else "Not assigned",
        }
        for rank, priority in enumerate(priorities, start=1)
    ]


def _demo_range_label(metric: dict[str, Any]) -> str:
    low = metric.get("value_low")
    high = metric.get("value_high")
    if low is None or high is None:
        return "Not available"
    return f"{low:g}–{high:g} {metric.get('unit', '').strip()}"


def _demo_metrics_for(
    metrics: list[dict[str, Any]],
    cities: list[str],
    priorities: list[str],
) -> list[dict[str, Any]]:
    selected_city_keys = {city.casefold() for city in cities}
    selected_priorities = set(priorities)
    return [
        metric
        for metric in metrics
        if metric["city"].casefold() in selected_city_keys
        and metric["priority"] in selected_priorities
    ]


def _ranking_gate(
    answers: dict[str, Any],
    selected_cities: list[str],
    priorities: list[str],
    evidence_cells: dict[tuple[str, str], dict[str, Any]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not priorities:
        reasons.append("Add location priorities in the intake before comparing candidates.")
        return False, reasons
    if len(selected_cities) < 2:
        reasons.append("Select at least two cities to meet the minimum comparison threshold.")

    top_priorities = priorities[:2]
    for priority in top_priorities:
        sourced_count = sum(
            evidence_cells[(city, priority)]["state"] == "Sourced"
            for city in selected_cities
        )
        if sourced_count < 2:
            reasons.append(
                f"{priority}: only {sourced_count} selected city/cities have Sourced evidence; at least two are required."
            )

    incomplete = [
        f"{city} · {priority}"
        for city in selected_cities
        for priority in priorities
        if evidence_cells[(city, priority)]["state"] != "Sourced"
    ]
    if incomplete:
        reasons.append(
            "Selected-city coverage is incomplete for the stated priorities: "
            + ", ".join(incomplete[:4])
            + (" and other gaps." if len(incomplete) > 4 else ".")
        )

    for priority in priorities:
        signatures: set[tuple[str, str, str]] = set()
        comparable_records = True
        for city in selected_cities:
            cell = evidence_cells[(city, priority)]
            records = [
                claim
                for claim in cell["claims"]
                if _claim_display_state(claim, cell["sources_by_id"]) == "Sourced"
            ]
            if not records:
                comparable_records = False
                continue
            for claim in records:
                signature = (
                    claim.get("claim_name", "").strip().casefold(),
                    claim.get("unit", "").strip().casefold(),
                    claim.get("period", "").strip().casefold(),
                )
                if not all(signature):
                    comparable_records = False
                signatures.add(signature)
        if comparable_records and len(signatures) > 1:
            reasons.append(
                f"{priority}: metric names, units, or reporting periods differ across cities."
            )

    deal_breaker = str(_value(answers, "location_deal_breaker") or "").strip()
    if deal_breaker:
        reasons.append(
            "The intake deal-breaker is free text and there is no verified city-level eligibility record to apply it consistently."
        )

    evidence_quality_values = [
        claim.get("evidence_quality", "").strip()
        for cell in evidence_cells.values()
        for claim in cell["claims"]
        if _claim_display_state(claim, cell["sources_by_id"]) == "Sourced"
    ]
    if evidence_quality_values:
        reasons.append(
            "The evidence register stores quality as unstandardized free text, "
            "so a consistent evidence-grade threshold for ranking cannot be checked."
        )
    return not reasons, reasons


def _research_tasks(answers: dict[str, Any]) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    seen: set[str] = set()
    priorities = _priorities(answers)
    for priority_rank, priority in enumerate(priorities, start=1):
        template = CRITERION_TASKS.get(priority)
        if template and template["id"] not in seen:
            task = {**template, "priority": str(priority_rank)}
            if task["id"] == "talent-availability":
                roles = str(_value(answers, "roles_seniority") or "").strip()
                functions = list(_value(answers, "gcc_functions") or [])
                other_functions = str(_value(answers, "functions_other") or "").strip()
                if other_functions:
                    functions.append(other_functions)
                task["evidence"] += (
                    f" Intake roles/seniority: {roles or 'not specified'}; "
                    f"functions: {', '.join(functions) or 'not specified'}; "
                    f"target team: {_headcount(answers) or 'not specified'}; "
                    f"ramp: {_value(answers, 'ramp_timeline') or 'not specified'}."
                )
                task["why"] = (
                    "Talent availability is the first stated location priority, "
                    "and this plan includes the user's current team size, functions, "
                    "and hiring ramp."
                )
            elif task["id"] == "talent-cost":
                roles = str(_value(answers, "roles_seniority") or "").strip()
                task["evidence"] += (
                    f" Apply to the intake role mix: {roles or 'not specified'}."
                )
                if _value(answers, "budget_sensitivity") == "Very cost-sensitive":
                    task["why"] = (
                        "Talent cost is a stated location priority, and the intake "
                        "marks the company as very cost-sensitive."
                    )
                else:
                    task["why"] = (
                        "Talent cost is a stated location priority; use the current "
                        "budget sensitivity and company assumptions when analyzing evidence."
                    )
            tasks.append(task)
            seen.add(template["id"])
    priority_task_count = len(tasks)
    for template in BASE_RESEARCH_TASKS:
        if template["id"] == "policy-incentives" and "state-incentives" in seen:
            continue
        if template["id"] not in seen:
            tasks.append({**template, "priority": "Additional"})
            seen.add(template["id"])
    if "Talent availability" not in priorities and any(
        marker in str(_value(answers, "plan_description") or "").lower()
        for marker in ("software", "engineering", "data", "technical")
    ):
        tasks.insert(
            priority_task_count,
            {
                **CRITERION_TASKS["Talent availability"],
                "priority": "Plan-driven",
            },
        )
    return tasks


def _store_research_task(task_id: str) -> None:
    completed = st.session_state.setdefault("research_tasks_completed", {})
    completed[task_id] = bool(
        st.session_state.get(f"research_task_{task_id}", False)
    )


def _store_city_selection() -> None:
    st.session_state["selected_city_entities"] = list(
        st.session_state.get("city_comparison_selection", [])
    )


def _display_value(value: Any, missing: str = "Not provided") -> str:
    if value is None or not str(value).strip():
        return missing
    return str(value).strip()


def _answer_display(
    answers: dict[str, Any],
    key: str,
    placeholders: tuple[str, ...],
) -> str:
    value = _value(answers, key)
    if _is_selected(value, placeholders):
        return str(value).strip()
    return "Not provided"


def _show_profile_sidebar(answers: dict[str, Any]) -> None:
    st.sidebar.markdown("### Company profile")
    industry = _industry(answers)
    headcount = _headcount(answers)
    india_presence = str(_value(answers, "india_presence") or "").strip()
    budget_sensitivity = str(
        _value(answers, "budget_sensitivity") or ""
    ).strip()
    ramp_timeline = str(_value(answers, "ramp_timeline") or "").strip()
    decision_deadline = _value(answers, "decision_deadline")

    profile_fields = [
        (
            "Company",
            _display_value(
                _value(answers, "company_name"),
                "Optional: add a company name for a client-ready profile.",
            ),
        ),
        (
            "Headquarters country",
            _display_value(
                _value(answers, "headquarters_country"),
                "Add the home country to give the plan company context.",
            ),
        ),
        (
            "Industry",
            industry
            or "Add an industry to focus relevant market and compliance evidence.",
        ),
        (
            "India presence",
            india_presence
            if india_presence and india_presence != "Select an option"
            else "Clarify existing presence; it may change the setup starting point.",
        ),
        (
            "Target headcount",
            headcount
            or "Add a team size, or choose “Not sure yet” to mark it uncertain.",
        ),
        (
            "Hiring / launch ramp",
            ramp_timeline
            if ramp_timeline and ramp_timeline != "Select a timeline"
            else "Add a hiring timeline, or choose “Not sure yet”.",
        ),
        (
            "Budget sensitivity",
            budget_sensitivity
            if budget_sensitivity and budget_sensitivity != "Select an option"
            else "Add cost sensitivity, or choose “Budget not set yet”.",
        ),
        (
            "Decision deadline",
            _display_value(
                decision_deadline,
                "Add a target date if known; it anchors the roadmap.",
            ),
        ),
    ]
    for label, value in profile_fields:
        st.sidebar.caption(label)
        st.sidebar.write(value)

    priorities = _priorities(answers)
    st.sidebar.caption("Location priorities")
    if priorities:
        for rank, priority in enumerate(priorities, start=1):
            st.sidebar.write(f"{rank}. {priority}")
    else:
        st.sidebar.info(
            "Choose a first location priority to guide future evidence comparisons."
        )

    if not str(_value(answers, "decision_makers") or "").strip():
        st.sidebar.info(
            "Add who must approve or influence the decision; it clarifies "
            "ownership and required input."
        )


def _show_evidence(claims: list[dict[str, str]], sources: list[dict[str, str]]) -> None:
    statuses = Counter(
        (claim.get("verification_status") or "").strip() or "status not recorded"
        for claim in claims
    )
    verified = statuses.get("verified", 0)

    st.markdown("#### Evidence register status")
    source_label = "source record" if len(sources) == 1 else "source records"
    st.write(
        f"{len(claims)} claims recorded across {len(sources)} {source_label}; "
        f"{verified} claim(s) marked verified."
    )
    st.caption(
        "Claims are not treated as verified because a source name or page "
        "appears in a CSV. Statuses below are read directly from the evidence register."
    )
    if not claims:
        st.info(
            "No claims are recorded yet. Add a claim with a stable source reference, "
            "source location, verification status, and caveats before showing "
            "research-backed metrics."
        )
        return

    source_by_id = {
        source.get("source_id", "").strip(): source
        for source in sources
        if source.get("source_id", "").strip()
    }
    for status in EVIDENCE_STATUSES:
        st.write(f"**{status}:** {statuses.get(status, 0)}")
    other_statuses = [
        (status, count)
        for status, count in statuses.items()
        if status not in EVIDENCE_STATUSES
    ]
    for status, count in other_statuses:
        st.write(f"**{status}:** {count}")

    if verified == 0:
        st.info(
            "There are currently no verified claims in the register. Treat the "
            "listed values as unreviewed source-reported entries, not established facts."
        )
    st.info(
        "The current pilot claims cover city-count entries and their reported "
        "discrepancy only. It contains no salary benchmarks, office-rent claims, "
        "policy or incentive claims, or service-provider evidence for comparisons."
    )

    for claim in claims:
        claim_id = claim.get("claim_id", "").strip() or "Claim ID not recorded"
        claim_name = claim.get("claim_name", "").strip() or "Claim name not recorded"
        status = claim.get("verification_status", "").strip() or "status not recorded"
        with st.expander(f"{claim_id} · {claim_name} · {status}"):
            st.markdown("**Claim text**")
            st.text(claim.get("claim_text", "") or "Not recorded")
            st.markdown("**Reported value and scope**")
            st.text(
                " | ".join(
                    value
                    for value in (
                        claim.get("entity_name_as_reported", "").strip(),
                        claim.get("reported_value", "").strip(),
                        claim.get("unit", "").strip(),
                        claim.get("period", "").strip(),
                    )
                    if value
                )
                or "Not recorded"
            )
            source_id = claim.get("source_id", "").strip()
            source = source_by_id.get(source_id)
            if source is None:
                st.warning(
                    f"Source reference {source_id or '(blank)'} is not resolved "
                    "to a record in sources.csv."
                )
            else:
                st.markdown("**Source**")
                st.text(
                    " · ".join(
                        value
                        for value in (
                            source.get("publisher", "").strip(),
                            source.get("source_title", "").strip(),
                            f"ID {source_id}",
                        )
                        if value
                    )
                )
                source_url = source.get("source_url", "").strip()
                if source_url:
                    st.link_button("Open source", source_url)
                else:
                    st.caption("Source URL is not recorded.")
                publication_date = source.get("publication_date", "").strip()
                st.caption(
                    f"Publication date: {publication_date or 'not recorded'}"
                )
                st.caption(
                    "Source type: "
                    + (source.get("source_type", "").strip() or "not recorded")
                )
                st.caption(
                    "Source last checked: "
                    + (source.get("last_checked_date", "").strip() or "not recorded")
                )
                source_notes = source.get("source_notes", "").strip()
                if source_notes:
                    st.markdown("**Source notes**")
                    st.text(source_notes)

            source_location = claim.get("source_location", "").strip()
            st.markdown("**Source location**")
            st.text(source_location or "Not recorded")
            st.markdown("**Evidence quality**")
            st.text(claim.get("evidence_quality", "").strip() or "Not recorded")
            st.markdown("**Last checked**")
            st.text(claim.get("last_checked_date", "").strip() or "Not recorded")
            caveat = claim.get("caveat", "").strip()
            if caveat:
                st.markdown("**Caveat**")
                st.text(caveat)
            conflicts = claim.get("conflicts_with", "").strip()
            if conflicts:
                st.markdown("**Conflicts with**")
                st.text(conflicts)


def _decision_deadline(answers: dict[str, Any]) -> tuple[date | None, str]:
    value = _value(answers, "decision_deadline")
    if isinstance(value, datetime):
        deadline = value.date()
    elif isinstance(value, date):
        deadline = value
    elif isinstance(value, str) and value.strip():
        try:
            deadline = date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None, "Invalid date — update the decision deadline in the intake."
    else:
        return None, "No decision deadline recorded."

    days_remaining = (deadline - date.today()).days
    if days_remaining < 0:
        countdown = f"Passed by {abs(days_remaining)} days"
    elif days_remaining == 0:
        countdown = "Decision deadline is today"
    else:
        countdown = f"{days_remaining} days remaining"
    return deadline, countdown


def _claim_has_terms(claim: dict[str, str], terms: tuple[str, ...]) -> bool:
    text = " ".join(
        (
            claim.get("claim_name", ""),
            claim.get("claim_text", ""),
        )
    ).casefold()
    return any(term.casefold() in text for term in terms)


def _verified_city_evidence(
    claims: list[dict[str, str]],
    sources: list[dict[str, str]],
    city: str,
    terms: tuple[str, ...],
) -> list[dict[str, str]]:
    source_ids = {
        source.get("source_id", "").strip()
        for source in sources
        if source.get("source_id", "").strip()
    }
    return [
        claim
        for claim in claims
        if claim.get("verification_status", "").strip() == "verified"
        and claim.get("entity_type", "").strip() == "city"
        and claim.get("entity_name_as_reported", "").strip().casefold() == city.casefold()
        and _claim_has_terms(claim, terms)
        and claim.get("claim_name", "").strip()
        and claim.get("reported_value", "").strip()
        and claim.get("geographic_scope", "").strip()
        and claim.get("unit", "").strip()
        and claim.get("period", "").strip()
        and claim.get("source_location", "").strip()
        and claim.get("evidence_quality", "").strip()
        and claim.get("source_id", "").strip() in source_ids
        and not claim.get("conflicts_with", "").strip()
    ]


LOCATION_EVIDENCE_TERMS = {
    "Talent availability": ("talent availability", "talent supply", "hiring capacity", "skills supply"),
    "Talent cost": ("salary", "compensation", "talent cost"),
    "Proximity to customers or leadership": ("customer proximity", "leadership proximity", "travel time"),
    "Office availability and cost": ("office rent", "available office space", "office availability"),
    "Relevant industry ecosystem": ("industry ecosystem", "company ecosystem"),
    "Connectivity and infrastructure": ("connectivity", "infrastructure quality"),
    "Quality of life and talent retention": ("quality of life", "talent retention"),
    "State incentives and support": ("state incentive", "state policy"),
    "Business continuity and risk diversification": ("business continuity", "risk diversification"),
}


def _has_comparable_city_evidence(
    claims: list[dict[str, str]],
    sources: list[dict[str, str]],
    priorities: list[str],
) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for priority in priorities:
        terms = LOCATION_EVIDENCE_TERMS.get(priority, ())
        metric_signatures: set[tuple[str, str, str]] = set()
        for city in INITIAL_CITY_SHORTLIST:
            conflicting = any(
                claim.get("entity_type", "").strip() == "city"
                and claim.get("entity_name_as_reported", "").strip().casefold()
                == city.casefold()
                and _claim_has_terms(claim, terms)
                and (
                    claim.get("verification_status", "").strip().casefold()
                    == "disputed"
                    or claim.get("conflicts_with", "").strip()
                )
                for claim in claims
            )
            evidence = _verified_city_evidence(claims, sources, city, terms)
            if conflicting or not evidence:
                missing.append(f"{priority} ({city})")
                continue
            metric_signatures.update(
                (
                    claim.get("claim_name", "").strip().casefold(),
                    claim.get("period", "").strip().casefold(),
                    claim.get("unit", "").strip().casefold(),
                )
                for claim in evidence
            )
        if len(metric_signatures) > 1:
            missing.append(f"comparable metric, period, and units for {priority}")
    return not missing, missing


def _decision_readiness(
    answers: dict[str, Any],
    sources: list[dict[str, str]],
    claims: list[dict[str, str]],
) -> list[dict[str, str]]:
    required_gaps = _required_gaps(answers)
    priorities = _priorities(answers)
    location_supported, location_gaps = _has_comparable_city_evidence(
        claims, sources, priorities
    )
    if str(_value(answers, "location_deal_breaker") or "").strip():
        location_supported = False
        location_gaps.append("city-level application of the location deal-breaker")
    if required_gaps:
        location_status = "Blocked"
        location_reason = "Required intake inputs are missing: " + "; ".join(
            prompt for prompt, _ in required_gaps
        ) + "."
    elif location_supported:
        location_status = "Ready"
        location_reason = (
            "Verified, comparable city-level evidence covers every stated priority "
            "across the four-city research shortlist."
        )
    else:
        location_status = "Needs evidence"
        location_reason = (
            "Verified, comparable evidence is missing for " + "; ".join(location_gaps[:3])
            + (" and other criteria." if len(location_gaps) > 3 else ".")
        )

    setup_inputs_missing = []
    if not _is_selected(_value(answers, "india_presence"), ("Select an option",)):
        setup_inputs_missing.append("existing India presence")
    if not (_value(answers, "gcc_functions") or _value(answers, "functions_other")):
        setup_inputs_missing.append("planned functions")
    if not str(_value(answers, "decision_makers") or "").strip():
        setup_inputs_missing.append("decision-makers")
    if not str(_value(answers, "regulatory_constraints") or "").strip():
        setup_inputs_missing.append("known constraints")
    setup_model_terms = (
        ("EOR", "employer of record"),
        ("BOT", "build operate transfer"),
        ("own entity", "owned entity"),
    )
    setup_models_supported = all(
        any(
            claim.get("verification_status", "").strip() == "verified"
            and _claim_has_terms(claim, terms)
            and claim.get("source_location", "").strip()
            and claim.get("source_id", "").strip()
            for claim in claims
        )
        for terms in setup_model_terms
    )
    if setup_inputs_missing:
        setup_status = "Blocked"
        setup_reason = "Setup inputs still needed: " + ", ".join(setup_inputs_missing) + "."
    elif setup_models_supported:
        setup_status = "Ready"
        setup_reason = (
            "Verified evidence is recorded for EOR, BOT, and own-entity options; "
            "company-specific professional review is still required."
        )
    else:
        setup_status = "Needs evidence"
        setup_reason = (
            "The intake describes the plan, but verified evidence comparing EOR, "
            "BOT, and own-entity requirements is not recorded."
        )

    cost_terms = {
        "Salary benchmarks": ("salary", "compensation"),
        "Office rent and space": ("office rent", "available office space"),
        "Other operating costs": ("operating cost", "cost per employee", "operating expense"),
    }
    cost_records = {
        label: [
            claim for claim in claims
            if _claim_has_terms(claim, terms)
        ]
        for label, terms in cost_terms.items()
    }
    verified_cost_records = {
        label: [
            claim for claim in rows
            if claim.get("verification_status", "").strip() == "verified"
            and claim.get("unit", "").strip()
            and claim.get("period", "").strip()
            and claim.get("geographic_scope", "").strip()
            and claim.get("source_location", "").strip()
        ]
        for label, rows in cost_records.items()
    }
    if not any(cost_records.values()):
        cost_status = "Blocked"
        cost_reason = (
            "No salary, office-rent/space, or other operating-cost claims are "
            "recorded in the evidence register."
        )
    elif all(verified_cost_records.values()) and str(
        _value(answers, "role_headcount_allocation") or ""
    ).strip():
        cost_status = "Ready"
        cost_reason = (
            "The required cost categories and role-level headcount allocation "
            "have verified units, periods, and geographic scope."
        )
    else:
        cost_status = "Needs evidence"
        missing_costs = [
            label for label, rows in verified_cost_records.items() if not rows
        ]
        if not str(_value(answers, "role_headcount_allocation") or "").strip():
            missing_costs.append("role-level headcount allocation")
        cost_reason = "Still needed: " + ", ".join(missing_costs) + "."

    deadline, _ = _decision_deadline(answers)
    ramp = str(_value(answers, "ramp_timeline") or "").strip()
    launch_text = str(_value(answers, "launch_deadline") or "").strip()
    launch_has_date = False
    if launch_text:
        try:
            date.fromisoformat(launch_text[:10])
            launch_has_date = True
        except ValueError:
            launch_has_date = False
    has_launch_dependencies = all(
        any(
            claim.get("verification_status", "").strip() == "verified"
            and _claim_has_terms(claim, terms)
            and claim.get("source_location", "").strip()
            for claim in claims
        )
        for terms in (
            ("hiring capacity", "talent availability"),
            ("setup lead time", "entity formation timeline"),
        )
    )
    if not ramp or ramp == "Select a timeline" or deadline is None:
        launch_status = "Blocked"
        launch_reason = (
            "A decision deadline and a usable hiring ramp are both needed to plan "
            "the launch dependency sequence."
        )
    elif launch_has_date and has_launch_dependencies:
        launch_status = "Ready"
        launch_reason = (
            "A dated launch target and verified hiring/setup lead-time evidence "
            "are recorded for planning."
        )
    else:
        launch_status = "Needs evidence"
        missing = []
        if not launch_has_date:
            missing.append("a confirmed launch date")
        if not has_launch_dependencies:
            missing.append("verified hiring-capacity and setup lead-time evidence")
        launch_reason = "Still needed: " + " and ".join(missing) + "."

    return [
        {
            "decision": "Where to locate",
            "status": location_status,
            "reason": location_reason,
            "next_step": "Review city claims and collect comparable evidence for the stated priorities.",
            "section": "Compare cities",
        },
        {
            "decision": "How to set up",
            "status": setup_status,
            "reason": setup_reason,
            "next_step": "Compare operating models and confirm requirements with qualified advisers.",
            "section": "Setup options",
        },
        {
            "decision": "What it will cost",
            "status": cost_status,
            "reason": cost_reason,
            "next_step": "Build role-level salary and office-cost inputs before estimating annual cost.",
            "section": "Talent and costs",
        },
        {
            "decision": "When to launch",
            "status": launch_status,
            "reason": launch_reason,
            "next_step": "Confirm launch timing and validate hiring and setup dependencies.",
            "section": "Entry roadmap",
        },
    ]


def _assessment_text(
    readiness: list[dict[str, str]],
    required_gaps: list[tuple[str, str]],
    actions: list[dict[str, str]],
) -> str:
    blocked = [item["decision"] for item in readiness if item["status"] == "Blocked"]
    pending = [
        item["decision"] for item in readiness if item["status"] == "Needs evidence"
    ]
    if required_gaps:
        assessment = (
            f"The company profile is incomplete for {', '.join(blocked) or 'the planning decisions'}. "
            f"Add {required_gaps[0][0].lower()} first."
        )
    elif pending:
        assessment = (
            "The company profile is defined for initial planning, but market evidence "
            f"does not yet support {', '.join(pending).lower()}."
        )
    else:
        assessment = (
            "The recorded inputs and verified evidence meet the current decision checks; "
            "review assumptions and remaining professional-advice requirements before acting."
        )
    if actions:
        assessment += f" Immediate next step: {actions[0]['title']}."
    return assessment


def _action_section(task: dict[str, str]) -> str:
    task_id = task.get("id", "")
    if task_id in ("talent-availability", "talent-cost", "office-cost", "proximity"):
        return "Talent and costs" if task_id in ("talent-availability", "talent-cost") else "Compare cities"
    if task_id in ("policy-incentives", "state-incentives"):
        return "Policies and ecosystem"
    if task_id == "corporate-compliance":
        return "Compliance and risk"
    if task_id == "setup-model":
        return "Setup options"
    return "Sources and evidence"


def _priority_actions(
    answers: dict[str, Any],
    claims: list[dict[str, str]],
    deadline: date | None,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for index, (prompt, reason) in enumerate(_required_gaps(answers)):
        actions.append(
            {
                "id": f"intake-gap-{index}",
                "title": prompt,
                "why": reason,
                "decision": "All four planning decisions",
                "owner": "To be assigned",
                "effort": "Estimate not available",
                "due": _planning_gate(deadline),
                "section": "Edit intake",
            }
        )

    status_counts = Counter(
        (claim.get("verification_status") or "").strip() or "status not recorded"
        for claim in claims
    )
    claims_to_review = sum(
        status_counts.get(status, 0)
        for status in ("unreviewed", "source_located", "disputed", "rejected")
    )
    if claims_to_review:
        actions.append(
            {
                "id": "review-evidence-register",
                "title": f"Review {claims_to_review} claims and resolve source gaps",
                "why": (
                    f"{status_counts.get('unreviewed', 0)} claim(s) are unreviewed; "
                    "the source register also lacks publication-date or URL details "
                    "where those have not been recorded."
                ),
                "decision": "Where to locate",
                "owner": "To be assigned",
                "effort": "Estimate not available",
                "due": _planning_gate(deadline),
                "section": "Sources and evidence",
            }
        )

    for task in _research_tasks(answers):
        if task["priority"] == "Additional" and len(actions) >= 3:
            continue
        actions.append(
            {
                "id": task["id"],
                "title": task["title"],
                "why": task["why"],
                "decision": task["decision"],
                "owner": "To be assigned",
                "effort": "Estimate not available",
                "due": _planning_gate(deadline),
                "section": _action_section(task),
                "evidence": task["evidence"],
                "source_type": task["source_type"],
            }
        )
    return actions


def _planning_gate(deadline: date | None) -> str:
    if deadline is None:
        return "No date assigned; effort and owner are not yet estimated."
    if deadline < date.today():
        return (
            f"Decision deadline {deadline.isoformat()} has passed; confirm a new "
            "planning date before assigning task deadlines."
        )
    return (
        f"Complete before the {deadline.isoformat()} decision gate; no separate "
        "task date is assigned because effort is not estimated."
    )


def _open_questions(readiness: list[dict[str, str]]) -> list[dict[str, str]]:
    by_decision = {item["decision"]: item for item in readiness}
    questions = [
        {
            "decision": "Location",
            "question": "Can the four candidate cities meet the stated priorities using comparable, verified evidence?",
            "why": by_decision["Where to locate"]["reason"],
            "how": "Compare evidence for each priority in the Compare cities section.",
            "source": "Dated, city-specific talent, salary, office, and other priority evidence.",
        },
        {
            "decision": "Cost",
            "question": "What is the fully loaded annual cost for the planned team?",
            "why": by_decision["What it will cost"]["reason"],
            "how": "Define role-level headcount and assemble salary, office, and other operating inputs.",
            "source": "Comparable salary surveys, office market data, and documented cost assumptions.",
        },
        {
            "decision": "Setup model",
            "question": "Which setup model meets the company's control, timing, and compliance needs?",
            "why": by_decision["How to set up"]["reason"],
            "how": "Compare EOR, BOT, and own-entity options with qualified legal and tax advisers.",
            "source": "Verified model terms and company-specific professional review.",
        },
        {
            "decision": "Launch",
            "question": "What launch date is realistic given hiring and establishment dependencies?",
            "why": by_decision["When to launch"]["reason"],
            "how": "Confirm a launch target and validate hiring-capacity and setup lead times.",
            "source": "Company-approved hiring plan and documented setup milestones.",
        },
    ]
    return [question for question in questions if by_decision[
        {
            "Location": "Where to locate",
            "Cost": "What it will cost",
            "Setup model": "How to set up",
            "Launch": "When to launch",
        }[question["decision"]]
    ]["status"] != "Ready"]


def _navigate_to_intake() -> None:
    st.session_state.screen = "intake"


def _navigate_to_section(section: str) -> None:
    st.session_state.workspace_section = section


def _add_city_to_comparison(city: str) -> None:
    selected = list(
        st.session_state.get(
            "selected_city_entities",
            st.session_state.get("city_comparison_selection", []),
        )
    )
    if city not in selected:
        selected.append(city)
    st.session_state.selected_city_entities = selected
    st.session_state.city_comparison_selection = selected
    st.session_state.workspace_section = "Compare cities"


def _city_shortlist_records(
    claims: list[dict[str, str]],
    priorities: list[str],
) -> list[dict[str, str]]:
    city_counts, office_market = _load_city_data()
    _, rows = _city_comparison_rows(city_counts, office_market, claims, priorities)
    row_by_city = {row["City / region (kept as recorded)"]: row for row in rows}
    return [
        {
            "city": city,
            "record": row_by_city.get(city, {}),
        }
        for city in INITIAL_CITY_SHORTLIST
    ]


def _executive_brief_markdown(
    answers: dict[str, Any],
    sources: list[dict[str, str]],
    claims: list[dict[str, str]],
    readiness: list[dict[str, str]],
    actions: list[dict[str, str]],
    questions: list[dict[str, str]],
    cities: list[dict[str, Any]],
    assessment: str,
) -> str:
    deadline, countdown = _decision_deadline(answers)
    status_counts = Counter(
        (claim.get("verification_status") or "").strip() or "status not recorded"
        for claim in claims
    )
    sections = [
        "# India GCC Atlas — Executive Brief",
        f"Report generated: {date.today().isoformat()}",
        "",
        "A Global Capability Centre (GCC) is an India-based team that performs business or technology functions for its parent company.",
        "",
        "## Company profile · Company-provided",
        f"- Company: {_display_value(_value(answers, 'company_name'))}",
        f"- Headquarters: {_display_value(_value(answers, 'headquarters_country'))}",
        f"- Industry: {_industry(answers) or 'Not provided'}",
        f"- Objective: {_display_value(_value(answers, 'plan_description'))}",
        f"- Planned functions: {_display_value(', '.join(_planned_functions(answers)))}",
        f"- Target headcount: {_headcount(answers) or 'Not provided'}",
        f"- Hiring ramp: {_answer_display(answers, 'ramp_timeline', ('Select a timeline',))}",
        f"- Decision deadline: {deadline.isoformat() if deadline else countdown} ({countdown})",
        f"- Launch timing: {_display_value(_value(answers, 'launch_deadline'))}",
        f"- Decision-makers: {_display_value(_value(answers, 'decision_makers'))}",
        f"- Regulatory / infrastructure considerations: {_display_value(_value(answers, 'regulatory_constraints'))}",
        f"- Location priorities: {_display_value(', '.join(_priorities(answers)))}",
        f"- Location deal-breaker: {_display_value(_value(answers, 'location_deal_breaker'))}",
        "",
        "## Current assessment",
        assessment,
        "",
        "## Decision readiness",
    ]
    sections.extend(
        f"- {item['decision']}: {item['status']} — {item['reason']} Next: {item['next_step']}"
        for item in readiness
    )
    sections.extend(
        [
            "",
            "## Annual operating cost",
            "**Not available yet.** No defensible annual estimate can be calculated from the current evidence. Salary benchmarks by role and seniority, role-level headcount allocation, comparable office rent/space assumptions, other material operating costs, currency, and cost period are missing or insufficiently verified. City-wide gross leasing volume is not rent or an operating-cost estimate.",
            "",
            "## City evaluation shortlist · Initial research scope, not a recommendation or ranking",
        ]
    )
    for item in cities:
        row = item["record"]
        count = row.get("Reported GCC count", "No count row in current data")
        count_status = row.get("Count verification status", "No count row")
        office = row.get("2025 gross office leasing (mn sq ft)", "No office record")
        office_status = row.get("Office evidence status", "No office record")
        sections.append(
            f"- {item['city']}: source-reported city-count row {count} "
            f"({count_status}); gross office leasing {office} ({office_status}). "
            "Missing: comparable talent supply, salary, rent/available space, and location-priority evidence."
        )
    sections.extend(["", "## Priority actions"])
    sections.extend(
        f"- {index}. {action['title']} — Why: {action['why']} "
        f"Decision: {action['decision']}. Owner: {action['owner']}. "
        f"Effort: {action['effort']}. Planning date: {action['due']}"
        for index, action in enumerate(actions, start=1)
    )
    sections.extend(["", "## Open questions · Not confirmed risks"])
    sections.extend(
        f"- {question['decision']}: {question['question']} "
        f"Why: {question['why']} How to answer: {question['how']} "
        f"Review/source needed: {question['source']}"
        for question in questions
    )
    sections.extend(
        [
            "",
            "## Evidence summary",
            f"- Verified: {status_counts.get('verified', 0)}",
            f"- Unreviewed: {status_counts.get('unreviewed', 0)}",
            f"- Disputed: {status_counts.get('disputed', 0)}",
            f"- Rejected: {status_counts.get('rejected', 0)}",
            "- Company answers are Company-provided and are not verified market evidence.",
            "- City-count rows are Source-reported and remain unreviewed unless a claim explicitly has Verified status.",
            "- No salary benchmarks, office rents, incentives, or total operating costs are verified in the current register.",
            "",
            "## Source register · Source-reported; source record does not verify a claim",
        ]
    )
    for source in sources:
        sections.append(
            f"- {source.get('source_id', 'Source ID not recorded')}: "
            f"{source.get('publisher', 'Publisher not recorded')} — "
            f"{source.get('source_title', 'Title not recorded')}; "
            f"URL: {source.get('source_url', '').strip() or 'not recorded'}; "
            f"publication date: {source.get('publication_date', '').strip() or 'not recorded'}; "
            f"notes: {source.get('source_notes', '').strip() or 'none recorded'}."
        )
    for claim in claims:
        sections.append(
            f"- Claim {claim.get('claim_id', 'ID not recorded')} "
            f"({claim.get('verification_status', 'status not recorded')}): "
            f"{claim.get('claim_text', 'Claim text not recorded')} "
            f"Source location: {claim.get('source_location', '').strip() or 'not recorded'}. "
            f"Caveat: {claim.get('caveat', '').strip() or 'none recorded'}"
        )
    sections.extend(
        [
            "",
            "## Caveat",
            "The NovaTech profile is an Illustrative fictional scenario. This brief is a planning aid, not legal, tax, investment, or location advice. No city ranking or financial estimate is supported by the current register.",
        ]
    )
    return "\n".join(sections)


def _generate_executive_brief(answers: dict[str, Any]) -> None:
    sources, claims = _load_evidence()
    readiness = _decision_readiness(answers, sources, claims)
    deadline, _ = _decision_deadline(answers)
    actions = _priority_actions(answers, claims, deadline)
    questions = _open_questions(readiness)
    cities = _city_shortlist_records(claims, _priorities(answers))
    assessment = _assessment_text(readiness, _required_gaps(answers), actions)
    brief = _executive_brief_markdown(
        answers, sources, claims, readiness, actions, questions, cities, assessment
    )
    st.session_state.generated_brief = brief
    st.session_state.generated_pdf = build_pdf_report(brief)
    st.session_state.workspace_executive_brief_generated = True


def _show_decision_overview(answers: dict[str, Any]) -> None:
    sources, claims = _load_evidence()
    deadline, countdown = _decision_deadline(answers)
    readiness = _decision_readiness(answers, sources, claims)
    required_gaps = _required_gaps(answers)
    priorities = _priorities(answers)
    by_decision = {item["decision"]: item for item in readiness}

    st.title("Overview")
    header_cols = st.columns([2, 1])
    header_cols[0].markdown(
        f"**{_display_value(_value(answers, 'company_name'), 'Company name not provided')}**"
    )
    header_cols[1].markdown(
        f"**Decision deadline**  \n"
        f"{deadline.isoformat() if deadline else 'Not provided'} · "
        f"{countdown if deadline else 'Add a valid date in the intake.'}"
    )

    pending = [
        item["decision"]
        for item in readiness
        if item["status"] != "Ready"
    ]
    if required_gaps:
        assessment = (
            "The plan needs one more input before the decision checks can proceed: "
            f"{required_gaps[0][0].lower()}."
        )
    elif pending:
        assessment = (
            "Your expansion plan is defined, but evidence is not yet sufficient "
            f"for {', '.join(pending).lower()}."
        )
    else:
        assessment = (
            "Current inputs and verified evidence meet the workspace checks; "
            "review assumptions before making a commitment."
        )
    st.info(assessment)

    card_definitions = (
        (
            "Location",
            by_decision["Where to locate"],
            "Verified, comparable evidence for the stated priorities is missing.",
        ),
        (
            "Setup model",
            by_decision["How to set up"],
            "Verified comparison of EOR, BOT, and own-entity requirements is missing.",
        ),
        (
            "Operating cost",
            by_decision["What it will cost"],
            "Role-level salary, rent/space, and other cost inputs are not verified.",
        ),
        (
            "Launch timeline",
            by_decision["When to launch"],
            "Confirm a launch target and verified hiring/setup lead times.",
        ),
    )
    decision_cols = st.columns(4)
    for column, (title, item, pending_reason) in zip(decision_cols, card_definitions):
        with column.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(f"**{item['status']}**")
            st.caption(
                "Required inputs and evidence checks are satisfied."
                if item["status"] == "Ready"
                else (
                    item["reason"]
                    if item["status"] == "Blocked"
                    else pending_reason
                )
            )

    if required_gaps:
        next_title = required_gaps[0][0]
        next_reason = required_gaps[0][1]
        next_section = "Edit intake"
    else:
        next_item = next(
            (item for item in readiness if item["status"] != "Ready"),
            None,
        )
        if next_item is None:
            next_title = (
                "Review source records and remaining assumptions"
            )
            next_reason = (
                "Keep the evidence register current before treating a decision "
                "as final."
            )
            next_section = "Sources and evidence"
        elif next_item["decision"] == "Where to locate":
            top_priority = priorities[0] if priorities else "location evidence"
            task = CRITERION_TASKS.get(top_priority)
            next_title = (
                task["title"]
                if task
                else f"Validate evidence for {top_priority.lower()}"
            )
            next_reason = (
                f"Start with your top priority, {top_priority}; compare candidate "
                "cities using sourced evidence, not inferred advantages."
            )
            next_section = "Compare cities"
        else:
            next_title = next_item["next_step"]
            next_reason = next_item["reason"]
            next_section = next_item["section"]

    st.markdown("#### Next priority")
    priority_cols = st.columns([4, 1])
    with priority_cols[0]:
        st.markdown(f"**{next_title}**")
        st.caption(next_reason)
    with priority_cols[1]:
        st.button(
            f"Open {next_section}",
            key="overview_next_priority",
            type="secondary",
            width="stretch",
            on_click=(
                _navigate_to_intake
                if next_section == "Edit intake"
                else _navigate_to_section
            ),
            args=() if next_section == "Edit intake" else (next_section,),
        )

    st.button(
        "Generate executive brief",
        key="generate_executive_brief",
        type="primary",
        on_click=_generate_executive_brief,
        args=(answers,),
    )
    if st.session_state.get("workspace_executive_brief_generated"):
        st.success("Executive brief generated from the current intake and evidence register.")
        with st.expander("Preview executive brief"):
            st.markdown(st.session_state.generated_brief)
        st.download_button(
            "Download executive brief PDF",
            data=st.session_state.generated_pdf,
            file_name="india_gcc_executive_brief.pdf",
            mime="application/pdf",
            type="secondary",
        )


def _render_demo_city_comparison(
    answers: dict[str, Any],
    selected_cities: list[str],
    priorities: list[str],
    dataset: dict[str, Any],
) -> None:
    metrics = _demo_metrics_for(dataset["metrics"], selected_cities, priorities)
    metrics_by_city_priority = {
        (metric["city"].casefold(), metric["priority"]): metric
        for metric in metrics
    }
    sources_by_id = {
        source["source_id"]: source for source in dataset["sources"]
    }
    claims_by_id = {
        claim["claim_id"]: claim for claim in dataset["claims"]
    }

    st.subheader("Illustrative executive takeaway")
    if not selected_cities:
        st.info("Select one or more cities to view the synthetic comparison.")
    elif not priorities:
        st.info(
            "No location priorities are available from the current intake. Add "
            "priorities in Screen 1 to order the illustrative comparison."
        )
    elif metrics:
        top_priority = priorities[0]
        top_records = [
            metric for metric in metrics if metric["priority"] == top_priority
        ]
        second_records = [
            metric for metric in metrics
            if len(priorities) > 1 and metric["priority"] == priorities[1]
        ]
        takeaway = (
            f"Synthetic ranges are available for {len(top_records)} of "
            f"{len(selected_cities)} selected cities on the top priority "
            f"({top_priority})"
        )
        if len(priorities) > 1:
            takeaway += (
                f" and {len(second_records)} on priority 2 "
                f"({priorities[1]})"
            )
        takeaway += (
            ". This illustrates how the intake order frames trade-offs; it is "
            "not a factual recommendation and does not identify a winning city."
        )
        st.info(takeaway)
    else:
        st.info(
            "No synthetic values match the selected cities and priorities. "
            "Those cells remain Not available; no zero values are substituted."
        )

    st.markdown("### City-by-priority comparison · synthetic values")
    st.caption(
        "The grid uses the current intake priorities in order. "
        "`Illustrative demo data` is a synthetic-only label, never Sourced or "
        "Verified; unsupported cells are Not available."
    )
    grid_rows: list[dict[str, str]] = []
    for city in selected_cities:
        row: dict[str, str] = {"City / region": city}
        for rank, priority in enumerate(priorities, start=1):
            metric = metrics_by_city_priority.get((city.casefold(), priority))
            row[f"Priority {rank} · {priority}"] = (
                f"◒ Illustrative demo data · {_demo_range_label(metric)}"
                if metric
                else "▧ Not available"
            )
        grid_rows.append(row)
    if grid_rows:
        st.dataframe(grid_rows, hide_index=True, width="stretch")

    st.markdown("### Priority order and discussion weights")
    st.caption(
        "The intake priority order guides the conversation. Weights 4, 3, 2, 1 "
        "are displayed as relative discussion emphasis only; no values are "
        "normalized or combined into a city score."
    )
    weights = _demo_priority_weights(priorities)
    if weights:
        st.dataframe(weights, hide_index=True, width="stretch")
    else:
        st.info("No intake priorities are available to weight.")

    st.markdown("### Synthetic metric ranges")
    st.caption(
        "Each priority has its own axis and supplied unit. Higher talent-index "
        "values are directionally higher only within this invented example; "
        "lower cost and travel-time values are directionally lower. These "
        "directions are not aggregated or treated as validated methods."
    )
    if not priorities:
        st.info("Add priorities in the intake before displaying metric ranges.")
    for rank, priority in enumerate(priorities, start=1):
        priority_metrics = [
            metric for metric in metrics if metric["priority"] == priority
        ]
        st.markdown(f"#### Priority {rank} · {priority}")
        if not priority_metrics:
            st.info(
                f"Not available: the synthetic dataset has no numeric range "
                f"for {priority} in the selected cities."
            )
            continue

        unit_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for metric in priority_metrics:
            unit_groups.setdefault(
                (metric["metric_name"], metric["unit"]), []
            ).append(metric)
        if len(unit_groups) > 1:
            st.warning(
                "This priority has multiple metric definitions or units in the "
                "synthetic file. They are shown in separate charts and must not "
                "be compared on one numerical axis."
            )

        for group_index, ((metric_name, unit), group_metrics) in enumerate(
            unit_groups.items()
        ):
            group_metrics.sort(
                key=lambda metric: selected_cities.index(metric["city"])
            )
            city_to_metric = {
                metric["city"].casefold(): metric for metric in group_metrics
            }
            missing_cities = [
                city for city in selected_cities
                if city.casefold() not in city_to_metric
            ]
            figure = go.Figure(
                go.Scatter(
                    x=[
                        (metric["value_low"] + metric["value_high"]) / 2
                        for metric in group_metrics
                    ],
                    y=[metric["city"] for metric in group_metrics],
                    mode="markers",
                    marker=dict(color="#005A9C", size=9, symbol="circle"),
                    error_x=dict(
                        type="data",
                        symmetric=False,
                        array=[
                            metric["value_high"]
                            - (metric["value_low"] + metric["value_high"]) / 2
                            for metric in group_metrics
                        ],
                        arrayminus=[
                            (metric["value_low"] + metric["value_high"]) / 2
                            - metric["value_low"]
                            for metric in group_metrics
                        ],
                        color="#005A9C",
                        thickness=2,
                        width=5,
                    ),
                    customdata=[
                        [
                            metric["value_low"],
                            metric["value_high"],
                            unit,
                            "Illustrative demo data · synthetic",
                            metric.get("caveat", "").strip() or "No caveat recorded.",
                            metric["record_id"],
                        ]
                        for metric in group_metrics
                    ],
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        + metric_name
                        + "<br>Illustrative range: %{customdata[0]:g}–%{customdata[1]:g} "
                        + "%{customdata[2]}"
                        + "<br>%{customdata[3]}"
                        + "<br>Record: %{customdata[5]}"
                        + "<br>Caveat: %{customdata[4]}"
                        + "<extra></extra>"
                    ),
                    name="Illustrative demo data",
                )
            )
            figure.update_layout(
                template="plotly_white",
                title=dict(
                    text=f"Illustrative demo range — {priority}",
                    font=dict(color="#14243A"),
                ),
                height=max(250, 58 * len(group_metrics) + 90),
                margin=dict(l=16, r=22, t=55, b=45),
                xaxis=dict(
                    title=f"{metric_name} · {unit}",
                    gridcolor="#D7DEE8",
                    tickfont=dict(color="#253247"),
                    title_font=dict(color="#253247"),
                    zeroline=False,
                ),
                yaxis=dict(
                    title=None,
                    categoryorder="array",
                    categoryarray=[metric["city"] for metric in group_metrics],
                    autorange="reversed",
                    tickfont=dict(color="#253247"),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#253247"),
                showlegend=False,
            )
            st.plotly_chart(
                figure,
                width="stretch",
                theme=None,
                key=f"demo_range_{rank}_{group_index}_{metric_name}",
                config={"displayModeBar": False, "responsive": True},
            )
            if missing_cities:
                st.caption(
                    "Not available for: "
                    + ", ".join(missing_cities)
                    + ". Missing values are omitted, not plotted as zero."
                )
            else:
                st.caption(
                    "Synthetic range comparison only. No city score or winner "
                    "is inferred from these values."
                )

    st.markdown("### Decision explanation")
    if priorities:
        priority_sequence = " → ".join(priorities)
        st.write(
            "This view follows the company's current intake priority order: "
            f"{priority_sequence}. Differences describe only this demo dataset; "
            "overlapping ranges, invented assumptions, and missing "
            "company-specific evidence prevent a real-world conclusion."
        )
    else:
        st.write(
            "The current intake has no recorded location priorities, so no "
            "priority-based comparison or conclusion can be made."
        )
    deal_breaker = str(
        _value(answers, "location_deal_breaker") or ""
    ).strip()
    if deal_breaker:
        st.caption(
            f"Intake deal-breaker to evaluate separately: "
            f"{_display_value(deal_breaker)}. No synthetic data establishes "
            "whether any city meets it."
        )
    st.info(
        "No shortlist or winning city is generated. The synthetic ranges are "
        "illustrations of the comparison workflow, not decision evidence."
    )
    st.caption(
        "No combined score is calculated. The comparison does not account for "
        "role-level talent needs, actual hiring capacity, verified travel routes, "
        "real rent/availability, deal-breaker feasibility, or evidence from "
        "independent sources."
    )

    st.markdown("### Inspect a synthetic metric")
    if metrics:
        if st.session_state.get("demo_metric_inspector") not in {
            metric["record_id"] for metric in metrics
        }:
            st.session_state.pop("demo_metric_inspector", None)
        record_id = st.selectbox(
            "City / metric record",
            [metric["record_id"] for metric in metrics],
            format_func=lambda record: next(
                f"{metric['city']} · {metric['priority']} · "
                f"{_demo_range_label(metric)}"
                for metric in metrics
                if metric["record_id"] == record
            ),
            key="demo_metric_inspector",
        )
        metric = next(
            record for record in metrics if record["record_id"] == record_id
        )
        claim = claims_by_id.get(record_id)
        source = sources_by_id.get(metric["source_id"])
        with st.container(border=True):
            st.markdown(
                f"**{metric['city']} · {metric['metric_name']}**"
            )
            st.write(f"**Value range:** {_demo_range_label(metric)}")
            st.write(f"**Priority:** {metric['priority']}")
            st.write(
                f"**Geographic scope:** "
                f"{metric.get('geographic_scope', '').strip() or 'Not recorded'}"
            )
            st.write(
                "**Demo status:** Illustrative demo data · "
                f"{metric.get('evidence_status', 'DEMO_ONLY')}"
            )
            st.write(
                f"**Source record ID:** {metric['source_id']} "
                "(synthetic internal demo record; not an external source)"
            )
            st.write(
                f"**Synthetic-data flag:** {metric['is_synthetic']}"
            )
            st.write(
                f"**Evidence grade field:** "
                f"{metric.get('evidence_grade', '').strip() or 'Not provided'} "
                "(demo metadata only; not a factual evidence grade)"
            )
            st.write(
                f"**Source location:** "
                f"{metric.get('source_location', '').strip() or 'Not provided'}"
            )
            st.write(
                f"**Last checked field:** "
                f"{metric.get('last_checked_date', '').strip() or 'Not provided'} "
                "(demo-file metadata, not a source verification date)"
            )
            st.write(
                f"**Caveat:** {metric.get('caveat', '').strip() or 'Not provided'}"
            )
            if claim:
                st.markdown("**Matching synthetic claim row**")
                st.write(
                    f"{claim.get('claim_id', record_id)} · "
                    f"{claim.get('claim_text', '').strip() or 'Claim text not provided'}"
                )
                st.write(
                    "Claim verification status: "
                    f"{claim.get('verification_status', '').strip() or 'Not provided'} "
                    "(synthetic; not verified)"
                )
            if source:
                st.markdown("**Synthetic source-register row**")
                st.write(
                    " · ".join(
                        value
                        for value in (
                            source.get("publisher", "").strip(),
                            source.get("source_title", "").strip(),
                            source.get("source_id", "").strip(),
                        )
                        if value
                    )
                )
                st.caption(
                    "This is a synthetic demonstration record, not an external "
                    "citation. No source URL or publication date is provided."
                )
    else:
        st.info("No synthetic metric records are available to inspect.")

    st.markdown("### Synthetic state-policy placeholders")
    st.caption(
        f"{len(dataset['policies'])} placeholder row(s) were loaded. They are "
        "not real policies, incentive evidence, or eligibility guidance and are "
        "excluded from the city comparison."
    )
    with st.expander("Show data · synthetic policy placeholders"):
        if dataset["policies"]:
            st.dataframe(
                dataset["policies"],
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No policy placeholder rows are available.")

    with st.expander("Show data · synthetic city metrics"):
        if metrics:
            st.dataframe(metrics, hide_index=True, width="stretch")
        else:
            st.info("No synthetic metric rows match this selection.")
    with st.expander("Show data · synthetic claims and sources"):
        data_tabs = st.tabs(["Demo claims", "Demo sources"])
        with data_tabs[0]:
            if dataset["claims"]:
                st.dataframe(
                    dataset["claims"], hide_index=True, width="stretch"
                )
            else:
                st.info("No synthetic claim rows are available.")
        with data_tabs[1]:
            if dataset["sources"]:
                st.dataframe(
                    dataset["sources"], hide_index=True, width="stretch"
                )
            else:
                st.info("No synthetic source rows are available.")


def _show_city_comparison(answers: dict[str, Any]) -> None:
    sources, claims = _load_evidence()
    city_counts, office_market = _load_city_data()
    company_presence = _load_gcc_company_data()
    priorities = _priorities(answers)
    city_names, _ = _city_comparison_rows(
        city_counts, office_market, claims, priorities
    )
    city_names = list(dict.fromkeys(city_names + [
        record.get("city", "").strip()
        for record in company_presence
        if record.get("city", "").strip()
    ]))

    st.title("Compare cities")
    st.caption(
        f"{_display_value(_value(answers, 'company_name'), 'Company not provided')} · "
        f"{_headcount(answers) or 'Headcount not provided'} · "
        f"Decision deadline: {_decision_deadline(answers)[0].isoformat() if _decision_deadline(answers)[0] else 'not provided'}"
    )
    demo_mode = st.toggle(
        "Use synthetic demo data",
        key="compare_cities_demo_mode",
        help=(
            "Loads the separate synthetic sample CSVs for this page only. It "
            "does not add or promote records in the production evidence register."
        ),
    )
    demo_dataset: dict[str, Any] = {
        "metrics": [],
        "sources": [],
        "claims": [],
        "policies": [],
        "errors": [],
    }
    if demo_mode:
        demo_dataset = _load_demo_dataset()
        st.warning(
            "DEMO MODE — Illustrative data only. Values are synthetic and must not be used for real business decisions."
        )
        if demo_dataset["errors"]:
            st.warning(
                "Some synthetic demo data is missing or invalid. Invalid rows "
                "were omitted, not replaced with zero."
            )
            with st.expander("Show demo-data loading issues"):
                for error in demo_dataset["errors"]:
                    st.write(f"- {error}")
        city_names = list(dict.fromkeys(
            city_names
            + [
                metric["city"]
                for metric in demo_dataset["metrics"]
                if metric["city"].strip()
            ]
        ))
        st.write(
            "Inspect a fictional, synthetic demonstration of the workflow using "
            "the company answers currently saved in Screen 1. Demo metrics are "
            "separate from production evidence and cannot unlock the production "
            "ranking gate."
        )
    else:
        st.write(
            "Investigate evidence coverage against the current intake priorities. "
            "Candidates are not recommendations, and missing evidence never counts "
            "as poor city performance."
        )
        st.caption(
            "Production mode: city ranking depends on source-backed, verified, "
            "comparable evidence. Synthetic demo records are not used."
        )

    prior_selection = st.session_state.get("selected_city_entities")
    if prior_selection is not None:
        default_cities = [city for city in prior_selection if city in city_names]
    else:
        default_cities = [city for city in INITIAL_CITY_SHORTLIST if city in city_names]
    selected_cities = st.multiselect(
        "Cities / regions to include",
        city_names,
        default=default_cities,
        key="city_comparison_selection",
        on_change=_store_city_selection,
        help=(
            "The four initial suggestions are an unranked starting shortlist. "
            "Add or remove any city or region present in the current records. "
            "Delhi, Gurugram, and Delhi NCR remain distinct."
        ),
    )
    selected_cities = list(selected_cities)
    st.caption(
        "Suggested starting shortlist: Bengaluru, Hyderabad, Pune, and Chennai. "
        "Available names come from the actual city-count, office-leasing, and "
        "company-presence files; no missing city is treated as a zero."
    )

    if demo_mode:
        _render_demo_city_comparison(
            answers, selected_cities, priorities, demo_dataset
        )
        return

    deal_breaker = str(_value(answers, "location_deal_breaker") or "").strip()
    if deal_breaker:
        st.info(
            f"Intake deal-breaker · {_display_value(deal_breaker)} "
            "No city is automatically excluded because city-level eligibility "
            "evidence is not recorded."
        )

    evidence_cells = {
        (city, priority): _priority_evidence_cell(
            city,
            priority,
            claims,
            city_counts,
            sources,
            office_market,
            company_presence,
        )
        for city in selected_cities
        for priority in priorities
    }
    ranking_eligible, ranking_reasons = _ranking_gate(
        answers, selected_cities, priorities, evidence_cells
    )

    st.subheader("Ranking eligibility")
    st.caption(
        "Minimum gate: at least two selected cities need Sourced evidence for "
        "each of the top two intake priorities. Before any ranking, this workspace "
        "also requires coverage for every selected city and recorded priority, "
        "comparable metric names, units and periods, resolved source/verification "
        "states, and a consistently applied deal-breaker."
    )
    if not ranking_eligible:
        st.warning("No defensible ranking yet")
        if ranking_reasons:
            st.write(ranking_reasons[0])
        with st.expander("Why the ranking gate is locked"):
            for reason in ranking_reasons:
                st.write(f"- {reason}")
            st.caption(
                "The current evidence model records evidence_quality as free text, "
                "not as a standardized grade. Review that field manually before "
                "using evidence to support a ranking."
            )
    else:
        st.success(
            "The evidence coverage checks passed. This workspace does not generate "
            "a city score; review evidence quality and apply the business criteria "
            "before making a recommendation."
        )

    st.markdown("### Evidence status key")
    st.caption(
        "Claim mapping: verified + a registered source + value, unit, period, "
        "geographic scope and source location → Sourced; unreviewed, source_located, "
        "disputed, incomplete, or unresolved claims → To confirm; explicitly "
        "indicative/context_only records keep those labels; rejected claims → Not "
        "available. A source name alone never verifies a claim. Office-leasing "
        "records are Context only for rent/space priorities; company-presence rows "
        "remain To confirm until record-level source validation."
    )
    st.write(" · ".join(EVIDENCE_MARKS[state] for state in EVIDENCE_DISPLAY_STATES))

    st.subheader("City-by-priority evidence grid")
    st.caption(
        "Columns retain the user's priority order. Each cell has a text state and "
        "a distinct mark; use the inspector below to see the underlying record, "
        "source, dates, status, and caveats."
    )
    grid_rows = []
    for city in selected_cities:
        row: dict[str, str] = {"City / region": city}
        for rank, priority in enumerate(priorities, start=1):
            row[f"Priority {rank} · {priority}"] = evidence_cells[
                (city, priority)
            ]["label"]
        grid_rows.append(row)
    if grid_rows:
        st.dataframe(grid_rows, hide_index=True, width="stretch")
        cell_labels = {
            f"{city} · Priority {rank}: {priority}": evidence_cells[
                (city, priority)
            ]
            for city in selected_cities
            for rank, priority in enumerate(priorities, start=1)
        }
        if cell_labels:
            if st.session_state.get("city_evidence_inspector") not in cell_labels:
                st.session_state.pop("city_evidence_inspector", None)
            selected_cell_label = st.selectbox(
                "Inspect an evidence cell",
                list(cell_labels),
                key="city_evidence_inspector",
            )
            cell = cell_labels[selected_cell_label]
            with st.container(border=True):
                st.markdown(f"**{cell['city']} · {cell['priority']}**")
                st.markdown(f"**Evidence state: {cell['label']}**")
                st.write(cell["explanation"])
                for claim in cell["claims"]:
                    st.markdown(
                        f"**{claim.get('claim_id', 'Claim ID not recorded')} · "
                        f"{claim.get('claim_name', 'Claim name not recorded')}**"
                    )
                    st.write(claim.get("claim_text", "") or "Claim text not recorded.")
                    st.write(
                        "Value / unit / period: "
                        + " · ".join(
                            value
                            for value in (
                                claim.get("reported_value", "").strip(),
                                claim.get("unit", "").strip(),
                                claim.get("period", "").strip(),
                            )
                            if value
                        )
                    )
                    st.write(
                        "Geographic scope: "
                        + (claim.get("geographic_scope", "").strip() or "Not recorded")
                    )
                    source_id = claim.get("source_id", "").strip()
                    source = cell["sources_by_id"].get(source_id)
                    st.write(
                        f"Source ID / location: {source_id or 'Not recorded'} · "
                        f"{claim.get('source_location', '').strip() or 'Not recorded'}"
                    )
                    st.write(
                        "Verification / evidence quality: "
                        f"{claim.get('verification_status', '').strip() or 'Not recorded'} · "
                        f"{claim.get('evidence_quality', '').strip() or 'Not recorded'}"
                    )
                    st.caption(
                        "Last checked: "
                        + (claim.get("last_checked_date", "").strip() or "Not recorded")
                    )
                    if claim.get("caveat", "").strip():
                        st.write("Caveat: " + claim["caveat"].strip())
                    if claim.get("conflicts_with", "").strip():
                        st.warning("Unresolved conflict: " + claim["conflicts_with"].strip())
                    if source:
                        st.write(
                            "Source record: "
                            + " · ".join(
                                value
                                for value in (
                                    source.get("publisher", "").strip(),
                                    source.get("source_title", "").strip(),
                                    source_id,
                                )
                                if value
                            )
                        )
                        st.caption(
                            "Publication date: "
                            + (source.get("publication_date", "").strip() or "Not recorded")
                        )
                        if source.get("source_url", "").strip():
                            st.link_button(
                                "Open registered source",
                                source["source_url"].strip(),
                                key=(
                                    f"source_{source_id}_{cell['city']}_"
                                    f"{claim.get('claim_id', 'claim')}"
                                ),
                            )
                if not cell["claims"]:
                    st.caption("No priority-specific claim is recorded.")
                for record in cell["company_presence"]:
                    st.markdown(
                        f"**Company-presence record · {record.get('company', 'Name not recorded')}**"
                    )
                    st.write(
                        f"Sector: {record.get('sector', '').strip() or 'Not recorded'} · "
                        f"Status: {record.get('presence_status', '').strip() or 'Not recorded'}"
                    )
                    st.write(
                        "Source / confidence: "
                        f"{record.get('source', '').strip() or 'Not recorded'} · "
                        f"{record.get('confidence', '').strip() or 'Not recorded'}"
                    )
                    st.caption(
                        "Last reviewed: "
                        + (record.get("last_reviewed", "").strip() or "Not recorded")
                    )
                    if record.get("source_url", "").strip():
                        st.link_button(
                            "Open listed presence source",
                            record["source_url"].strip(),
                            key=f"presence_{record.get('company', 'record')}_{cell['city']}",
                        )
                for record in cell["office_records"]:
                    st.markdown("**Office-market context · not a rent or availability metric**")
                    st.write(
                        f"{record.get('office_leasing_2025_mn_sqft', '').strip() or 'Not recorded'} "
                        "million sq ft · city-wide gross leasing · 2025"
                    )
                    st.write(
                        "Geography / source: "
                        f"{record.get('region', '').strip() or 'Not recorded'} · "
                        f"{record.get('source', '').strip() or 'Not recorded'}"
                    )
                    if record.get("source_url", "").strip():
                        st.link_button(
                            "Open office-market source",
                            record["source_url"].strip(),
                            key=f"office_{cell['city']}",
                        )
                    st.caption(record.get("evidence_note", "").strip())
                for record in cell["city_count_records"]:
                    st.markdown("**Additional context · transcribed city-count record**")
                    st.write(
                        f"{record.get('gcc_count_as_printed', '').strip() or 'Not recorded'} "
                        f"GCCs · {record.get('state', '').strip() or 'Geography not recorded'} · "
                        f"{record.get('source', '').strip() or 'Source not recorded'}"
                    )
                    count_claims = cell["city_count_claims"]
                    if count_claims:
                        for count_claim in count_claims:
                            count_source_id = count_claim.get("source_id", "").strip()
                            count_source = cell["sources_by_id"].get(count_source_id)
                            st.write(
                                f"Claim {count_claim.get('claim_id', 'ID not recorded')} · "
                                f"verification: {count_claim.get('verification_status', '').strip() or 'not recorded'} · "
                                f"evidence quality: {count_claim.get('evidence_quality', '').strip() or 'not recorded'}"
                            )
                            st.write(
                                "Claim source / location: "
                                f"{count_source_id or 'Not recorded'} · "
                                f"{count_claim.get('source_location', '').strip() or 'Not recorded'}"
                            )
                            if count_claim.get("caveat", "").strip():
                                st.caption("Caveat: " + count_claim["caveat"].strip())
                            if count_source:
                                st.caption(
                                    f"Registered source: {count_source.get('publisher', '').strip() or 'Publisher not recorded'} · "
                                    f"URL: {count_source.get('source_url', '').strip() or 'not recorded'} · "
                                    f"Publication date: {count_source.get('publication_date', '').strip() or 'not recorded'}"
                                )
                    else:
                        st.caption(
                            "No claim-level verification status is recorded for "
                            "this transcribed city-count row."
                        )
                    st.caption(
                        "This city count is not used as evidence for the selected "
                        "priority; original source review remains required."
                    )
    else:
        st.info("Select at least one city and add location priorities in the intake.")

    st.subheader("Evidence coverage · not city performance")
    st.caption(
        "Coverage counts only Sourced cells. Priority weights follow the intake "
        "order (4, 3, 2, 1); when fewer priorities are present, only those weights "
        "are included in the denominator. To confirm, Indicative, Context only, "
        "and Not available do not count as usable coverage. A larger bar is not a "
        "better city."
    )
    coverage_rows = _coverage_weighted_rows(
        selected_cities, priorities, evidence_cells
    )
    if coverage_rows:
        coverage_fig = go.Figure(
            go.Bar(
                x=[row["Evidence coverage"] for row in coverage_rows],
                y=[row["City"] for row in coverage_rows],
                orientation="h",
                marker_color="#005A9C",
                text=[f"{row['Evidence coverage']}%" for row in coverage_rows],
                textposition="outside",
                customdata=[
                    [
                        row["Sourced priorities"],
                        row["Covered weight"],
                        row["Available weight"],
                    ]
                    for row in coverage_rows
                ],
                hovertemplate=(
                    "<b>%{y}</b><br>Evidence coverage: %{x}%"
                    "<br>Sourced priorities: %{customdata[0]}"
                    "<br>Covered weight: %{customdata[1]}/%{customdata[2]}"
                    "<extra>Coverage only · not performance</extra>"
                ),
            )
        )
        coverage_fig.update_layout(
            height=max(240, 48 * len(coverage_rows) + 70),
            margin=dict(l=12, r=38, t=12, b=42),
            xaxis=dict(
                title="Weighted evidence coverage (%)",
                range=[0, 100],
                ticksuffix="%",
                gridcolor="#D7DEE8",
            ),
            yaxis=dict(title=None, autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#253247"),
            showlegend=False,
        )
        st.plotly_chart(
            coverage_fig,
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
        with st.expander("Show data · evidence coverage"):
            st.dataframe(coverage_rows, hide_index=True, width="stretch")
    else:
        st.info("Select at least one city to calculate evidence coverage.")

    st.subheader("Comparable numeric ranges")
    st.caption(
        "Range plots need comparable city-level values with explicit units, "
        "geography, period, source, and evidence state."
    )
    st.info(
        "No comparable salary bands or office-rent / available-space ranges are "
        "recorded. The current office dataset contains city-wide gross leasing "
        "volume (a point context value), which is not rent or a comparable range; "
        "it is intentionally not plotted as a cost."
    )
    with st.expander("Show data · numeric ranges"):
        st.write(
            "Salary range data: not available in the current files. "
            "Office rent/available-space range data: the real_estate_template.csv "
            "contains headers only. No values are plotted."
        )
        st.write(
            "The cities.csv rows are shown only as Context only in applicable "
            "evidence-cell details; they are gross leasing volumes, not price "
            "ranges, rent, or available inventory."
        )


def _render_research_checklist(
    answers: dict[str, Any], tasks: list[dict[str, str]] | None = None
) -> None:
    tasks = tasks or _research_tasks(answers)
    completed = st.session_state.setdefault("research_tasks_completed", {})
    grouped: dict[str, list[dict[str, str]]] = {}
    for task in tasks:
        grouped.setdefault(task["group"], []).append(task)
    for group, group_tasks in grouped.items():
        st.markdown(f"#### {group}")
        for task in group_tasks:
            task_id = task["id"]
            widget_key = f"research_task_{task_id}"
            if widget_key not in st.session_state:
                st.session_state[widget_key] = bool(completed.get(task_id, False))
            st.checkbox(
                f"{task.get('priority', 'Additional')} · {task['title']}",
                key=widget_key,
                on_change=_store_research_task,
                args=(task_id,),
            )
            st.write(f"**Missing evidence / input:** {task['evidence']}")
            st.write(f"**Why it matters:** {task['why']}")
            st.write(f"**Decision affected:** {task['decision']}")
            selected_cities = st.session_state.get("selected_city_entities", [])
            affected = (
                ", ".join(selected_cities)
                if selected_cities
                else "Candidate locations; shortlist not yet selected"
            )
            st.write(f"**Locations / scope affected:** {affected}")
            st.write(f"**Suggested source type:** {task['source_type']}")
            if task["id"] == "office-cost":
                st.caption(
                    "Related source-reported context exists for 2025 gross office "
                    "leasing in some city/region records. Rent and available-space "
                    "evidence still needs to be located."
                )
            else:
                st.caption("Source status: a relevant source still needs to be located.")
            st.caption(
                "Verification status: no sufficient verified evidence for this task. "
                "The checklist records research-task progress, not evidence verification."
            )


def _show_talent_costs(answers: dict[str, Any]) -> None:
    pack = load_demo_pack()
    st.title("Talent and costs")
    st.warning(
        "DEMO MODE — All sample values are synthetic and are not market facts."
    )
    st.caption(
        "The sample pack demonstrates a calculator and decision workflow, not "
        "investment-grade estimates. Synthetic demo assumptions are separate "
        "from the production evidence register and cannot become sourced or verified."
    )
    if pack["errors"]:
        with st.expander("Demo-pack loading issues", expanded=True):
            for error in pack["errors"]:
                st.write(f"- {error}")

    functions = _planned_functions(answers)
    roles_note = str(_value(answers, "roles_seniority") or "").strip()
    st.caption(
        f"Intake context · Functions: {', '.join(functions) if functions else 'Not provided'}"
        f" · Role/seniority notes: {roles_note or 'Not provided'}"
        f" · Budget sensitivity: {_answer_display(answers, 'budget_sensitivity', ('Select an option',))}"
    )

    st.markdown("### 1. Executive cost calculator")
    intake_headcount, headcount_note = parse_headcount(_headcount(answers))
    headcount = st.number_input(
        "Planning headcount (employees)",
        min_value=1,
        max_value=100000,
        value=intake_headcount,
        step=1,
        key="talent_cost_target_headcount",
        help=(
            "Initialized from the current intake; edit this planning count "
            "without changing the intake answers."
        ),
    )
    st.caption(headcount_note)

    presence = str(_value(answers, "india_presence") or "").strip().casefold()
    if presence == "no":
        existing_headcount = 0
        st.caption("Starting India headcount: 0, based on the intake answer “No existing presence.”")
    else:
        existing_text = st.text_input(
            "Current India headcount (required when a presence exists or is unknown)",
            key="talent_cost_existing_headcount",
            placeholder="Enter a whole-number headcount",
        ).strip()
        try:
            existing_headcount = int(existing_text) if existing_text else None
            if existing_headcount is not None and (
                str(existing_headcount) != existing_text or existing_headcount < 0
            ):
                existing_headcount = None
        except ValueError:
            existing_headcount = None
        if existing_headcount is None:
            st.info(
                "Enter the current India headcount to calculate net ramp hires "
                "and backfills. Payroll totals remain a target-state illustration."
            )

    city_salary_rows = pack["salary_ranges"]
    cities = list(dict.fromkeys(
        row["city"] for row in city_salary_rows if row.get("city")
    ))
    selected_cities = st.multiselect(
        "Shortlisted cities for salary comparison",
        options=cities,
        default=cities,
        key="talent_cost_city_shortlist",
        help="The intake does not collect a city shortlist; these are editable demo candidates.",
    )
    calculator_cities = [city for city in selected_cities if city in cities]
    calculator_city = st.selectbox(
        "City used by the calculator",
        options=calculator_cities,
        index=0 if calculator_cities else None,
        key="talent_cost_calculator_city",
        placeholder="Select a shortlisted city",
    )
    if calculator_city:
        mapped_state = next(
            (
                row["state"]
                for row in pack["state_city_mapping"]
                if row["candidate_city"].casefold() == calculator_city.casefold()
            ),
            "",
        )
        if mapped_state:
            st.caption(
                f"{calculator_city} · {mapped_state}. The state mapping is a "
                "demo candidate mapping only; all salary rows remain city-level."
            )

    st.markdown("#### Editable illustrative role / seniority mix")
    st.caption(
        "The intake provides functions and free-text role notes, not role or "
        "seniority headcounts. This editable demo mix is not attributed to the user."
    )
    initial_role_mix = default_role_mix(pack["role_mix"])
    if initial_role_mix:
        role_mix_editor = st.data_editor(
            initial_role_mix,
            hide_index=True,
            num_rows="dynamic",
            width="stretch",
            key="talent_cost_role_mix",
            column_config={
                "Role": st.column_config.TextColumn(
                    "Role", help="Must match a city-role salary row."
                ),
                "Role share (%)": st.column_config.NumberColumn(
                    "Role share (%)", min_value=0.0, max_value=100.0, step=1.0
                ),
                "Junior share (%)": st.column_config.NumberColumn(
                    "Junior share (%)", min_value=0.0, max_value=100.0, step=1.0
                ),
                "Mid share (%)": st.column_config.NumberColumn(
                    "Mid share (%)", min_value=0.0, max_value=100.0, step=1.0
                ),
                "Senior share (%)": st.column_config.NumberColumn(
                    "Senior share (%)", min_value=0.0, max_value=100.0, step=1.0
                ),
            },
        )
        if hasattr(role_mix_editor, "to_dict"):
            role_mix = role_mix_editor.to_dict(orient="records")
        else:
            role_mix = list(role_mix_editor)
    else:
        role_mix = []
        st.info("No role-mix demo rows are available.")

    st.markdown("#### Phased hiring ramp")
    st.caption(
        "Edit end-of-year shares if needed. Payroll assumes hires arrive evenly "
        "through each year, so Year 1 average headcount is the midpoint between "
        "starting and year-end headcount. Year 1 has no salary inflation applied."
    )
    ramp_rows = pack["headcount_ramp"]
    if ramp_rows:
        ramp_editor = st.data_editor(
            [
                {
                    "Period": row["period"],
                    "Share of target at year-end (%)": (
                        float(row["share_of_steady_state"]) * 100
                    ),
                }
                for row in ramp_rows
            ],
            hide_index=True,
            num_rows="fixed",
            width="stretch",
            key="talent_cost_ramp",
            column_config={
                "Period": st.column_config.TextColumn("Period", disabled=True),
                "Share of target at year-end (%)": st.column_config.NumberColumn(
                    "Share of target at year-end (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=5.0,
                ),
            },
        )
        if hasattr(ramp_editor, "to_dict"):
            ramp_edits = ramp_editor.to_dict(orient="records")
        else:
            ramp_edits = list(ramp_editor)
        edited_ramp = {
            row["Period"]: float(row["Share of target at year-end (%)"]) / 100
            for row in ramp_edits
        }
        calculation_ramp = [
            {
                **row,
                "share_of_steady_state": edited_ramp.get(
                    row["period"], float(row["share_of_steady_state"])
                ),
            }
            for row in ramp_rows
        ]
    else:
        calculation_ramp = []

    route_names = [row["hiring_route"] for row in pack["hiring_routes"]]
    preferred_route = st.selectbox(
        "Preferred hiring route",
        route_names,
        key="talent_cost_preferred_route",
        index=0 if route_names else None,
        placeholder="No route assumptions available",
    )

    st.markdown("#### Your budget inputs · optional, deliberately blank")
    budget_columns = st.columns(3)
    budget_texts = {}
    budget_specs = (
        ("annual_budget", "Annual steady-state operating budget · INR/year"),
        ("setup_budget", "One-time setup budget · INR"),
        ("hire_budget", "Maximum recruitment cost per hire · INR"),
    )
    for column, (field, label) in zip(budget_columns, budget_specs):
        with column:
            budget_texts[field] = st.text_input(
                label,
                key=f"talent_cost_{field}",
                placeholder="Enter budget or leave blank",
            ).strip()

    def read_budget(field: str) -> float | None:
        text = budget_texts[field].replace(",", "").strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            st.error(f"{dict(budget_specs)[field]} must be a number.")
            return None
        if not math.isfinite(value) or value < 0:
            st.error(f"{dict(budget_specs)[field]} must be a finite, non-negative amount.")
            return None
        return value

    annual_budget = read_budget("annual_budget")
    setup_budget = read_budget("setup_budget")
    hire_budget = read_budget("hire_budget")

    result: dict[str, Any] = {"valid": False, "errors": []}
    if calculator_city and preferred_route and existing_headcount is not None:
        result = calculate_cost_scenarios(
            city=calculator_city,
            headcount=int(headcount),
            role_mix=role_mix,
            salary_rows=pack["salary_ranges"],
            ramp_rows=calculation_ramp,
            assumption_rows=pack["cost_assumptions"],
            route_rows=pack["hiring_routes"],
            setup_rows=pack["setup_costs"],
            preferred_route=preferred_route,
            existing_headcount=existing_headcount,
        )
    elif not calculator_city:
        result["errors"].append("Select at least one city to calculate the scenarios.")
    elif existing_headcount is None:
        result["errors"].append(
            "Current India headcount is needed because existing presence is not “No.”"
        )

    def money(value: float | None) -> str:
        return "Not available" if value is None else f"INR {value:,.0f}"

    if result["valid"]:
        central_year1 = result["year1_total"]["central"]
        central_steady = result["steady_state_total"]["central"]
        central_route_hire = result["route_cost_per_hire"]["central"]
        annual_status = budget_comparison(annual_budget, central_steady)
        setup_status = budget_comparison(
            setup_budget, result["one_time_setup"]["central"]
        )
        hire_status = budget_comparison(hire_budget, central_route_hire)
        headline_cols = st.columns(4)
        headline_cols[0].metric("Estimated year-one cost · central", money(central_year1))
        headline_cols[1].metric("Steady-state annual cost · central", money(central_steady))
        headline_cols[2].metric("Route cost per hire · central", money(central_route_hire))
        headline_cols[3].metric("Annual operating budget status", annual_status["status"])

        def status_message(title: str, comparison: dict[str, Any]) -> None:
            amount = money(comparison["budget"])
            estimate = money(comparison["cost"])
            headroom = comparison["headroom"]
            detail = (
                f"Budget: {amount} · Estimate: {estimate} · "
                + (
                    f"Headroom: {money(headroom)}"
                    if headroom is not None and headroom >= 0
                    else (
                        f"Overspend: {money(-headroom)}"
                        if headroom is not None
                        else "Enter a budget to calculate headroom."
                    )
                )
            )
            message = f"{title}: **{comparison['status']}** · {detail}"
            if comparison["status"] == "Within budget":
                st.success(message)
            elif comparison["status"] == "Over budget":
                st.error(message)
            else:
                st.info(message)

        status_message("Steady-state operating budget", annual_status)
        status_message("One-time setup budget", setup_status)
        status_message("Maximum recruitment cost per hire", hire_status)

        scenario_rows = [
            ("Annual base payroll at target headcount", result["base_payroll"]),
            ("Annual employer-loaded payroll at base salary level", result["loaded_payroll"]),
            ("Year-one base payroll after phased ramp", result["year1_base_payroll"]),
            ("Year-one employer-loaded payroll", result["year1_loaded_payroll"]),
            ("Year-one recruitment fees · net hires and backfills", result["year1_recruitment"]),
            ("Year-one onboarding / equipment for hires", result["year1_onboarding"]),
            ("Fixed one-time fit-out and entity setup", result["fixed_setup"]),
            ("One-time setup total · fixed setup plus Year 1 onboarding", result["one_time_setup"]),
            ("Total estimated Year 1 cost · payroll + recruitment + setup", result["year1_total"]),
            (
                f"Steady-state annual operating cost · Year 3 salary level "
                f"({result['steady_inflation_years']} inflation year(s))",
                result["steady_state_total"],
            ),
        ]
        st.markdown("#### Low / central / high cost scenarios")
        st.dataframe(
            [
                {
                    "Cost category": title,
                    **{
                        f"{scenario.title()} · INR": money(values[scenario])
                        for scenario in ("low", "central", "high")
                    },
                }
                for title, values in scenario_rows
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Year 1 ramp: average {result['year1_average_headcount']:,.1f} FTE, "
            f"{result['year1_net_hires']:,.1f} net hires plus "
            f"{result['year1_backfills']:,.1f} attrition backfills "
            f"({result['year1_gross_hires']:,.1f} total modeled hires)."
        )
        st.caption(
            f"Rates applied: employer on-cost {result['on_cost_rate']:.0%}; "
            f"annual salary inflation {result['inflation_rate']:.0%}; "
            f"annual attrition {result['attrition_rate']:.0%}. "
            f"Year 1 salary inflation is 0%; steady state compounds inflation "
            f"through the last ramp year."
        )
        st.caption(
            f"Year-one total combines recurring payroll and recruitment with "
            f"one-time fixed setup and onboarding. Steady-state operating cost "
            f"excludes fit-out and entity setup, but includes attrition hiring "
            f"and backfill onboarding. All costs are {SYNTHETIC_LABEL.lower()}."
        )
        central_drivers = [
            ("Year-one loaded payroll", result["year1_loaded_payroll"]["central"]),
            ("Year-one recruitment", result["year1_recruitment"]["central"]),
            ("One-time fixed setup", result["fixed_setup"]["central"]),
            ("Year-one onboarding", result["year1_onboarding"]["central"]),
        ]
        st.markdown("#### Main central-case cost drivers")
        st.write(
            " · ".join(f"{name}: {money(value)}" for name, value in central_drivers)
        )
    else:
        st.info(
            "Insufficient data to calculate complete city-level cost scenarios. "
            "No missing salary or cost is replaced with zero."
        )
        for error in result["errors"]:
            st.write(f"- {error}")

    st.markdown("### 2. Role-by-city salary ranges")
    salary_rows = pack["salary_ranges"]
    salary_cities = list(dict.fromkeys(row["city"] for row in salary_rows))
    salary_roles = list(dict.fromkeys(row["role"] for row in salary_rows))
    seniorities = list(dict.fromkeys(row["seniority"] for row in salary_rows))
    filter_columns = st.columns(3)
    with filter_columns[0]:
        filtered_cities = st.multiselect(
            "Filter cities",
            salary_cities,
            default=calculator_cities or salary_cities,
            key="talent_cost_salary_filter_cities",
        )
    with filter_columns[1]:
        filtered_roles = st.multiselect(
            "Filter roles",
            salary_roles,
            default=salary_roles,
            key="talent_cost_salary_filter_roles",
        )
    with filter_columns[2]:
        filtered_seniorities = st.multiselect(
            "Filter seniority",
            seniorities,
            default=seniorities,
            key="talent_cost_salary_filter_seniority",
        )
    salary_lookup = {
        (
            row["city"].casefold(),
            row["role"].casefold(),
            row["seniority"].casefold(),
        ): row
        for row in salary_rows
    }
    filtered_salary_rows = []
    for city in filtered_cities:
        for role in filtered_roles:
            for seniority in filtered_seniorities:
                row = salary_lookup.get(
                    (city.casefold(), role.casefold(), seniority.casefold())
                )
                if row is None:
                    filtered_salary_rows.append(
                        {
                            "City": city,
                            "Role": role,
                            "Seniority": seniority,
                            "Low · INR lakh/year": "Not available",
                            "Central · INR lakh/year": "Not available",
                            "High · INR lakh/year": "Not available",
                            "Evidence status": "Needs evidence",
                            "Source / caveat": (
                                "No matching city-role-seniority row in the demo file."
                            ),
                            "Geographic scope": "Not available",
                            "As of": "Not available",
                        }
                    )
                    continue
                filtered_salary_rows.append(
                    {
                        "City": row["city"],
                        "Role": row["role"],
                        "Seniority": row["seniority"],
                        "Low · INR lakh/year": (
                            f"{row['salary_low_lpa']:g}"
                            if row["salary_low_lpa"] is not None else "Not available"
                        ),
                        "Central · INR lakh/year": (
                            f"{row['salary_central_lpa']:g}"
                            if row["salary_central_lpa"] is not None else "Not available"
                        ),
                        "High · INR lakh/year": (
                            f"{row['salary_high_lpa']:g}"
                            if row["salary_high_lpa"] is not None else "Not available"
                        ),
                        "Evidence status": "Illustrative demo assumption · not verified",
                        "Source / caveat": f"{row['source_id']} · {row['caveat']}",
                        "Geographic scope": row["geographic_scope"],
                        "As of": row["as_of_date"],
                    }
                )
    if filtered_salary_rows:
        st.dataframe(filtered_salary_rows, hide_index=True, width="stretch")
        with st.expander("Inspect underlying city-role-seniority salary rows"):
            st.dataframe(
                [
                    row for row in salary_rows
                    if row["city"] in filtered_cities
                    and row["role"] in filtered_roles
                    and row["seniority"] in filtered_seniorities
                ],
                hide_index=True,
                width="stretch",
            )
    else:
        st.info(
            "No salary rows match these filters. Missing city-role-seniority "
            "ranges remain unavailable and are not inferred."
        )

    st.markdown("### 3. Talent pool and hiring difficulty")
    evidence_by_domain = {
        row["data_domain"]: row for row in pack["evidence_register"]
    }
    for domain in ("talent_pool", "hiring_difficulty"):
        record = evidence_by_domain.get(domain, {})
        st.info(
            f"{domain.replace('_', ' ').title()}: "
            f"{record.get('status', 'Missing')} — "
            f"{record.get('interpretation', 'No verified evidence is available.')}"
        )
    if result.get("valid"):
        time_to_fill = result["time_to_fill_days"]
        st.write(
            "General average time-to-fill assumption: "
            + (
                f"{time_to_fill:g} days"
                if time_to_fill is not None else "Not available"
            )
            + f" · {SYNTHETIC_LABEL}. This is not a city- or role-specific "
            "hiring-time estimate."
        )
        st.write(
            f"Illustrative annual attrition implies about "
            f"{result['steady_backfills']:,.1f} replacement hires at steady state, "
            "separate from net headcount growth."
        )
    st.caption(
        "No talent-pool size, city-specific scarcity, or verified hiring "
        "difficulty is provided in this sample pack."
    )

    st.markdown("### 4. Hiring-route comparison")
    if calculator_city and role_mix and preferred_route and existing_headcount is not None:
        route_comparisons = []
        for route_row in pack["hiring_routes"]:
            route_result = calculate_cost_scenarios(
                city=calculator_city,
                headcount=int(headcount),
                role_mix=role_mix,
                salary_rows=pack["salary_ranges"],
                ramp_rows=calculation_ramp,
                assumption_rows=pack["cost_assumptions"],
                route_rows=pack["hiring_routes"],
                setup_rows=pack["setup_costs"],
                preferred_route=route_row["hiring_route"],
                existing_headcount=existing_headcount,
            )
            route_comparisons.append(
                {
                    "Hiring route": route_row["hiring_route"],
                    "Pricing basis": route_row["pricing_basis"],
                    "Cost per hire · low / central / high · INR": (
                        "Not available"
                        if not route_result["valid"]
                        else " / ".join(
                            money(route_result["route_cost_per_hire"][scenario])
                            for scenario in ("low", "central", "high")
                        )
                    ),
                    "Year-one route total · central · INR": (
                        "Not available"
                        if not route_result["valid"]
                        else money(route_result["year1_recruitment"]["central"])
                    ),
                    "Expected time-to-fill": (
                        (
                            f"{route_result['time_to_fill_days']:g} days · general demo assumption"
                            if route_result["time_to_fill_days"] is not None
                            else "Not available"
                        )
                        if route_result["valid"] else "Not available"
                    ),
                    "Budget fit": (
                        budget_comparison(
                            hire_budget,
                            route_result["route_cost_per_hire"]["central"],
                        )["status"]
                        if route_result["valid"]
                        else "Insufficient data"
                    ),
                    "Evidence / caveat": (
                        "Illustrative demo assumption · not a quote · "
                        + route_row["caveat"]
                    ),
                }
            )
        st.dataframe(route_comparisons, hide_index=True, width="stretch")
        selected_route_row = next(
            (
                route for route in pack["hiring_routes"]
                if route["hiring_route"] == preferred_route
            ),
            None,
        )
        if selected_route_row:
            st.caption(
                f"Selected route model: {selected_route_row['pricing_basis']}. "
                "Consultancy fees use the route's low/central/high percentage of "
                "the matching salary scenario. Hybrid uses fixed low/central cost "
                "plus its fee share; because the file has no high fixed fee, its "
                "high scenario holds the central fixed fee and applies the fee "
                "share to high salary."
            )
        st.info(
            "Provider shortlisting requires separate research; the sample contains "
            "no verified agency, recruiter, or platform quotations."
        )
    else:
        st.info(
            "Complete the calculator inputs to compare route costs. Route pricing "
            "assumptions alone are not provider quotes."
        )

    st.markdown("### 5. Assumptions and evidence")
    st.caption(
        "Every sample-pack number is synthetic. User budget entries are user "
        "inputs; blank entries remain blank. No synthetic row is added to the "
        "production claims or sources register."
    )
    research_gaps = [
        "City-by-role salary benchmarks",
        "Actual recruitment quotations",
        "City-specific hiring difficulty and time-to-fill",
        "Employer contribution and benefits benchmarks",
        "City-specific annual salary inflation",
        "Attrition and backfill assumptions",
        "Office fit-out, equipment and onboarding quotations",
        "Current LinkedIn or other recruitment-tool pricing",
    ]
    st.markdown(
        "**Still needs evidence:** " + " · ".join(research_gaps)
    )
    with st.expander("Assumptions and evidence", expanded=False):
        st.markdown("#### Cost assumptions")
        st.dataframe(
            [
                {
                    **row,
                    "Provenance": SYNTHETIC_LABEL,
                    "Validation needed": row["caveat"],
                }
                for row in pack["cost_assumptions"]
            ],
            hide_index=True,
            width="stretch",
        )
        st.markdown("#### Hiring-route pricing assumptions")
        st.dataframe(
            [
                {
                    **row,
                    "Provenance": SYNTHETIC_LABEL,
                    "Validation needed": row["caveat"],
                }
                for row in pack["hiring_routes"]
            ],
            hide_index=True,
            width="stretch",
        )
        st.markdown("#### One-time, onboarding and tools costs")
        st.dataframe(
            [
                {
                    **row,
                    "Provenance": SYNTHETIC_LABEL,
                    "Validation needed": row["caveat"],
                }
                for row in pack["setup_costs"]
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "The annual LinkedIn sourcing licence is shown as a reference "
            "assumption, not added to totals: the in-house per-hire route already "
            "states that it includes recruiter time and tools, so including both "
            "could double-count tool expense."
        )
        st.markdown("#### Evidence coverage and status")
        st.dataframe(pack["evidence_register"], hide_index=True, width="stretch")
        st.markdown("#### State-to-city demo mapping")
        st.dataframe(pack["state_city_mapping"], hide_index=True, width="stretch")
        st.markdown("#### User budget inputs")
        st.dataframe(
            [
                {
                    "Budget": label,
                    "User input": budget_texts[field] or "Not provided",
                    "Provenance": "User-supplied input" if budget_texts[field] else "Missing — not inferred",
                }
                for field, label in budget_specs
            ],
            hide_index=True,
            width="stretch",
        )
        st.markdown(
            "**Evidence maturity:** demo calculations need only illustrative "
            "inputs; an indicative business case needs city-role salary, benefits, "
            "hiring and setup quotations; an executive location/investment decision "
            "requires verified, dated, comparable city-specific evidence and "
            "company-approved budgets."
        )

    with st.expander(
        "Recruitment partner directory · shared with Policies and ecosystem",
        expanded=False,
    ):
        directory = load_policy_workspace()
        if directory["errors"]:
            st.error(
                "The shared provider directory could not be fully loaded: "
                + " ".join(directory["errors"])
            )
        recruitment_providers = [
            provider for provider in directory["providers"]
            if provider.get("provider_category") == "Recruitment partners"
        ]
        verified_providers = [
            provider for provider in recruitment_providers
            if provider.get("verification_status", "").casefold() == "verified"
        ]
        if verified_providers:
            st.dataframe(
                verified_providers, hide_index=True, width="stretch"
            )
        else:
            st.info("No verified provider yet.")
        unverified_providers = [
            provider for provider in recruitment_providers
            if provider not in verified_providers
        ]
        if unverified_providers:
            st.caption(
                "Unverified provider records are shown separately and are not "
                "presented as recommendations."
            )
            st.dataframe(
                unverified_providers, hide_index=True, width="stretch"
            )


def _policy_display(value: str, missing: str = "Not available") -> str:
    return value.strip() if value and value.strip() else missing


def _show_policies(answers: dict[str, Any]) -> None:
    data = load_policy_workspace()
    policies = data["policies"]
    checklist = data["checklist"]
    sources = data["sources"]
    providers = data["providers"]

    st.title("Policies and ecosystem")
    st.caption(
        "Policy references and company eligibility are tracked separately. "
        "A policy page does not establish that a benefit applies to this company."
    )
    if data["errors"]:
        with st.expander("Policy and provider data loading issues", expanded=True):
            for error in data["errors"]:
                st.error(error)

    industry = _industry(answers)
    functions = _planned_functions(answers)
    priorities = _priorities(answers)
    presence = _answer_display(
        answers, "india_presence", ("Select an option",)
    )
    st.markdown("### Intake context used for review")
    st.write(
        f"**Industry:** {_display_value(industry)} · "
        f"**Headquarters:** {_display_value(str(_value(answers, 'headquarters_country') or '').strip())} · "
        f"**India presence:** {presence}"
    )
    st.write(
        f"**Planned functions:** {', '.join(functions) if functions else 'Not provided'} · "
        f"**Target headcount:** {_headcount(answers) or 'Not provided'} · "
        f"**Ramp:** {_display_value(str(_value(answers, 'ramp_timeline') or '').strip())} · "
        f"**Budget sensitivity:** {_answer_display(answers, 'budget_sensitivity', ('Select an option',))}"
    )
    st.write(
        f"**Location-priority order:** {' → '.join(priorities) if priorities else 'Not provided'}"
    )
    constraints = str(_value(answers, "regulatory_constraints") or "").strip()
    if constraints:
        st.caption(f"Intake constraints to consider: {constraints}")

    state_city_map = {
        "Bengaluru": "Karnataka",
        "Hyderabad": "Telangana",
        "Pune": "Maharashtra",
        "Mumbai": "Maharashtra",
        "Chennai": "Tamil Nadu",
    }
    city_shortlist = list(
        st.session_state.get(
            "selected_city_entities",
            st.session_state.get("talent_cost_city_shortlist", []),
        )
    )
    state_options = list(
        dict.fromkeys(
            [
                "Karnataka",
                "Telangana",
                "Maharashtra",
                "Tamil Nadu",
                *[row["state"] for row in policies if row.get("state")],
                *[state_city_map[city] for city in city_shortlist if city in state_city_map],
            ]
        )
    )
    if "policy_selected_states" not in st.session_state:
        st.session_state["policy_selected_states"] = list(
            dict.fromkeys(
                state_city_map[city]
                for city in city_shortlist
                if city in state_city_map
            )
        )
    st.multiselect(
        "Candidate states for this review · user-selected",
        options=state_options,
        key="policy_selected_states",
        help=(
            "If a city shortlist is already selected in the workspace, its "
            "mapped states are prefilled. Change the selection to match the "
            "company's actual candidate locations."
        ),
    )
    selected_states = list(st.session_state["policy_selected_states"])

    summary = summarize_policy_status(policies, selected_states)
    state_count = summary["shortlisted_state_count"]
    ref_count = summary["official_policy_reference_count"]
    relevant_count = summary["potentially_relevant_count"]
    assessed_count = summary["assessed_count"]
    confirmed_count = summary["confirmed_count"]
    state_word = "state" if state_count == 1 else "states"
    ref_word = "reference" if ref_count == 1 else "references"
    st.markdown(
        f"**Summary:** {state_count} candidate {state_word} selected; "
        f"{ref_count} official policy {ref_word} located; "
        f"{relevant_count} marked potentially relevant; "
        f"{assessed_count} eligibility assessment(s) completed; "
        f"{confirmed_count} eligibility confirmation(s) recorded."
    )
    summary_columns = st.columns(5)
    summary_columns[0].metric("Shortlisted states", state_count)
    summary_columns[1].metric("Official references located", ref_count)
    summary_columns[2].metric("Potentially relevant", relevant_count)
    summary_columns[3].metric("Eligibility assessed", assessed_count)
    summary_columns[4].metric("Eligibility confirmed", confirmed_count)
    nearest_deadline = summary["nearest_verified_deadline"]
    st.caption(
        "Nearest verified application deadline: "
        + (
            nearest_deadline.isoformat()
            if nearest_deadline
            else "No verified deadline recorded"
        )
    )

    selected_policy_rows = [
        row for row in policies if row.get("state") in selected_states
    ]
    next_policy = next(
        (
            row for row in selected_policy_rows
            if row.get("eligibility_ladder_stage") != "Eligibility confirmed"
        ),
        None,
    )
    if not selected_states:
        next_action = (
            "Select the states being considered by the company; no location "
            "shortlist is currently recorded in the intake."
        )
    elif next_policy and next_policy.get("next_research_action"):
        next_action = next_policy["next_research_action"]
    elif any(state not in {row.get("state") for row in policies} for state in selected_states):
        next_action = (
            "Locate and review the current official policy or government order "
            "for each selected state; do not infer that no policy exists from "
            "a missing record."
        )
    else:
        next_action = (
            "Review the selected policies' source records and confirm whether "
            "any application deadline is current and applicable."
        )
    st.info(f"**Next research action:** {next_action}")

    st.markdown("### Four-step eligibility ladder")
    st.caption(
        "Stages are advanced only by an explicit saved reviewer action. "
        "Official-source status, intake relevance, policy verification, and "
        "company eligibility remain separate fields."
    )
    ladder_columns = st.columns(4)
    ladder_definitions = (
        "An official policy or government notification has been located.",
        "The stated scope appears relevant, but full eligibility is not assessed.",
        "Policy criteria have been compared with documented company and project facts.",
        "Written official confirmation or qualified professional validation supports this project.",
    )
    for column, stage, definition in zip(
        ladder_columns, ELIGIBILITY_STAGES, ladder_definitions
    ):
        column.markdown(f"**{stage}**")
        column.caption(definition)

    st.markdown("### Policy eligibility matrix")
    st.caption(
        "Blank policy terms remain blank in the research record and display as "
        "Not available. The current source records are research leads; no benefit "
        "or eligibility conclusion has been inferred."
    )
    policy_states = sorted({row.get("state", "") for row in policies if row.get("state")})
    policy_types = sorted(
        {row.get("policy_type", "") for row in policies if row.get("policy_type")}
    )
    ladder_filter = ["All", *ELIGIBILITY_STAGES]
    verification_values = sorted(
        {row.get("verification_status", "") for row in policies if row.get("verification_status")}
    )
    filter_columns = st.columns(4)
    with filter_columns[0]:
        state_filter = st.selectbox(
            "Filter by state",
            ["All", *policy_states],
            key="policy_matrix_state_filter",
        )
    with filter_columns[1]:
        type_filter = st.selectbox(
            "Filter by policy type",
            ["All", *policy_types],
            key="policy_matrix_type_filter",
        )
    with filter_columns[2]:
        stage_filter = st.selectbox(
            "Filter by ladder stage",
            ladder_filter,
            key="policy_matrix_stage_filter",
        )
    with filter_columns[3]:
        verification_filter = st.selectbox(
            "Filter by verification status",
            ["All", *verification_values],
            key="policy_matrix_verification_filter",
        )
    filtered_policies = [
        row for row in policies
        if (state_filter == "All" or row.get("state") == state_filter)
        and (type_filter == "All" or row.get("policy_type") == type_filter)
        and (stage_filter == "All" or row.get("eligibility_ladder_stage") == stage_filter)
        and (
            verification_filter == "All"
            or row.get("verification_status") == verification_filter
        )
    ]
    matrix_rows = [
        {
            "State": row.get("state", ""),
            "Policy name": row.get("policy_name", ""),
            "Policy type": row.get("policy_type", ""),
            "Effective / expiry": " / ".join(
                (
                    _policy_display(row.get("effective_date", ""), ""),
                    _policy_display(row.get("expiry_date", ""), ""),
                )
            ).strip(" /"),
            "Official policy link": row.get("policy_url", ""),
            "Eligibility ladder stage": row.get("eligibility_ladder_stage", ""),
            "Relevance to intake": _policy_display(
                row.get("policy_relevance_to_intake", "")
            ),
            "Setup model requirement / status": (
                _policy_display(row.get("setup_model_required_or_assumed", ""))
                + " · "
                + _policy_display(row.get("setup_model_verification_status", ""))
            ),
            "Key benefit categories": _policy_display(row.get("benefits_summary", "")),
            "Company eligibility": _policy_display(
                row.get("company_eligibility_status", "")
            ),
            "Next research action": _policy_display(
                row.get("next_research_action", "")
            ),
            "Last checked": row.get("last_checked_date", ""),
        }
        for row in filtered_policies
    ]
    if matrix_rows:
        st.dataframe(
            matrix_rows,
            hide_index=True,
            width="stretch",
            column_config={
                "Official policy link": st.column_config.LinkColumn(
                    "Official policy link", display_text="Open official page"
                )
            },
        )
    else:
        st.info("No policy rows match the current filters.")

    st.markdown("### Policy detail and eligibility checklist")
    if not filtered_policies:
        st.info("Select matrix filters that include at least one policy to inspect details.")
    else:
        policy_by_label = {
            f"{row.get('state', '')} · {row.get('policy_name', '')} "
            f"({row.get('policy_id', '')})": row
            for row in filtered_policies
        }
        policy_labels = list(policy_by_label)
        current_detail = st.session_state.get("policy_detail_label")
        if current_detail not in policy_labels:
            st.session_state.pop("policy_detail_label", None)
        selected_label = st.selectbox(
            "Select a policy reference",
            policy_labels,
            key="policy_detail_label",
        )
        policy = policy_by_label[selected_label]
        policy_id = policy["policy_id"]
        st.markdown(f"#### {policy.get('policy_name', policy_id)} · {policy.get('state', '')}")
        st.write(
            f"**Policy type:** {_policy_display(policy.get('policy_type', ''))} · "
            f"**Issuing department:** {_policy_display(policy.get('issuing_department', ''))}"
        )
        policy_url = policy.get("policy_url", "").strip()
        if policy_url.startswith(("https://", "http://")):
            st.link_button("Open official policy page", policy_url)
        document_url = policy.get("document_url", "").strip()
        if document_url.startswith(("https://", "http://")):
            st.link_button("Open recorded policy document", document_url)

        st.markdown("#### 1–6. Policy overview, validity, benefits, criteria, setup model and application")
        detail_rows = [
            ("Policy existence", policy.get("policy_exists_status", "")),
            ("Effective date", policy.get("effective_date", "")),
            ("Expiry date", policy.get("expiry_date", "")),
            ("Amendments / validity", ""),
            ("Benefits explicitly documented", policy.get("benefits_summary", "")),
            ("Eligibility criteria", policy.get("eligibility_criteria", "")),
            ("Setup model required or assumed", policy.get("setup_model_required_or_assumed", "")),
            ("Setup model verification", policy.get("setup_model_verification_status", "")),
            ("Application process", policy.get("application_process", "")),
            ("Application deadlines", policy.get("deadlines", "")),
            ("City / location scope", policy.get("city_or_location_scope", "")),
        ]
        for label, value in detail_rows:
            st.write(f"**{label}:** {_policy_display(value)}")
        st.caption(
            "The opened government pages identify policy references only. "
            "Their policy clauses have not been reviewed; dates, benefits, "
            "thresholds, setup-model rules, and application terms remain unverified."
        )

        policy_checklist = [
            row for row in checklist if row.get("policy_id") == policy_id
        ]
        st.markdown("#### 7. Eligibility checklist")
        if policy_checklist:
            st.dataframe(
                [
                    {
                        "Checklist item": item.get("checklist_item", ""),
                        "Question to verify": item.get("question_to_verify", ""),
                        "Status": item.get("status", ""),
                        "Setup model": _policy_display(
                            item.get("setup_model_required_or_assumed", "")
                        ),
                        "Evidence required": item.get("evidence_required", ""),
                    }
                    for item in policy_checklist
                ],
                hide_index=True,
                width="stretch",
            )
            checklist_items = [item["checklist_item"] for item in policy_checklist]
            checklist_label = st.selectbox(
                "Checklist item to update",
                checklist_items,
                key=f"policy_checklist_item_{policy_id}",
            )
            checklist_item = next(
                item for item in policy_checklist
                if item["checklist_item"] == checklist_label
            )
            checklist_prefix = f"policy_checklist_{policy_id}_{checklist_label}"
            with st.form(f"policy_checklist_form_{policy_id}"):
                current_status = checklist_item.get("status", "Needs verification")
                if current_status not in CHECKLIST_STATUSES:
                    current_status = "Needs verification"
                checklist_status = st.selectbox(
                    "Review status",
                    CHECKLIST_STATUSES,
                    index=CHECKLIST_STATUSES.index(current_status),
                    key=f"{checklist_prefix}_status",
                )
                setup_requirement = st.text_input(
                    "Required or assumed setup model",
                    value=checklist_item.get("setup_model_required_or_assumed", ""),
                    key=f"{checklist_prefix}_setup",
                )
                checklist_source = st.text_input(
                    "Evidence source URL",
                    value=checklist_item.get("source_url", ""),
                    key=f"{checklist_prefix}_source",
                )
                checklist_notes = st.text_area(
                    "Reviewer notes",
                    value=checklist_item.get("reviewer_notes", ""),
                    key=f"{checklist_prefix}_notes",
                )
                checklist_saved = st.form_submit_button("Save checklist review")
            if checklist_saved:
                try:
                    save_checklist_review(
                        policy_id,
                        checklist_label,
                        {
                            "status": checklist_status,
                            "setup_model_required_or_assumed": setup_requirement,
                            "source_url": checklist_source,
                            "reviewer_notes": checklist_notes,
                            "last_checked_date": date.today().isoformat(),
                        },
                    )
                    st.success("Checklist review saved to the policy CSV.")
                    st.rerun()
                except PolicyDataError as error:
                    st.error(f"Checklist review was not saved: {error}")
        else:
            st.warning("No checklist rows are recorded for this policy.")

        st.markdown("#### 8–9. Outstanding questions, evidence and source limitations")
        st.write(f"**Next action:** {_policy_display(policy.get('next_research_action', ''))}")
        st.write(f"**Source status:** {_policy_display(policy.get('source_status', ''))}")
        st.write(f"**Verification status:** {_policy_display(policy.get('verification_status', ''))}")
        st.write(f"**Last checked:** {_policy_display(policy.get('last_checked_date', ''))}")
        st.write(f"**Research notes:** {_policy_display(policy.get('notes', ''))}")
        linked_sources = [
            source for source in sources
            if source.get("policy_id") == policy_id
            or (not source.get("policy_id") and source.get("state") == policy.get("state"))
        ]
        with st.expander("Recorded sources for this state"):
            if linked_sources:
                st.dataframe(
                    linked_sources,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "url": st.column_config.LinkColumn(
                            "URL", display_text="Open source"
                        )
                    },
                )
            else:
                st.info("No source record is linked to this state.")

        st.markdown("#### Reviewer policy-status update")
        st.caption(
            "Explicit Save only. These controls assume this deployment is "
            "restricted to authorized reviewers; the app itself has no identity "
            "or access-control system."
        )
        with st.form(f"policy_review_form_{policy_id}"):
            document_url_input = st.text_input(
                "Official policy document URL",
                value=policy.get("document_url", ""),
                key=f"policy_document_url_{policy_id}",
            )
            current_stage = policy.get("eligibility_ladder_stage", "")
            if current_stage not in ELIGIBILITY_STAGES:
                current_stage = ELIGIBILITY_STAGES[0]
            stage_input = st.selectbox(
                "Eligibility ladder stage",
                ELIGIBILITY_STAGES,
                index=ELIGIBILITY_STAGES.index(current_stage),
                key=f"policy_ladder_stage_{policy_id}",
            )
            relevance_input = st.text_area(
                "Policy relevance to this intake · record the basis",
                value=policy.get("policy_relevance_to_intake", ""),
                key=f"policy_relevance_{policy_id}",
            )
            company_status = policy.get("company_eligibility_status", "Not assessed")
            if company_status not in COMPANY_ELIGIBILITY_STATUSES:
                company_status = COMPANY_ELIGIBILITY_STATUSES[0]
            company_status_input = st.selectbox(
                "Company eligibility status",
                COMPANY_ELIGIBILITY_STATUSES,
                index=COMPANY_ELIGIBILITY_STATUSES.index(company_status),
                key=f"policy_company_eligibility_{policy_id}",
            )
            setup_model_input = st.text_input(
                "Policy-required or assumed setup model",
                value=policy.get("setup_model_required_or_assumed", ""),
                key=f"policy_setup_model_{policy_id}",
            )
            setup_status_input = st.text_input(
                "Setup-model verification status",
                value=policy.get("setup_model_verification_status", "Needs verification"),
                key=f"policy_setup_status_{policy_id}",
            )
            verification_options = ("Unverified", "Under review", "Verified", "Disputed", "Rejected")
            recorded_verification = policy.get("verification_status", "Unverified")
            if recorded_verification not in verification_options:
                recorded_verification = "Unverified"
            verification_input = st.selectbox(
                "Policy-text verification status",
                verification_options,
                index=verification_options.index(recorded_verification),
                key=f"policy_verification_{policy_id}",
                help=(
                    "Verified requires a recorded official policy document URL "
                    "and reviewer notes. This is not company eligibility."
                ),
            )
            reviewer_notes = st.text_area(
                "Reviewer notes",
                value=policy.get("reviewer_notes", ""),
                key=f"policy_reviewer_notes_{policy_id}",
            )
            confirmation_url = st.text_input(
                "Company-specific written eligibility confirmation URL",
                value=policy.get("eligibility_confirmation_source_url", ""),
                key=f"policy_confirmation_url_{policy_id}",
            )
            policy_saved = st.form_submit_button("Save policy review")
        if policy_saved:
            try:
                save_policy_review(
                    policy_id,
                    {
                        "document_url": document_url_input,
                        "eligibility_ladder_stage": stage_input,
                        "policy_relevance_to_intake": relevance_input,
                        "company_eligibility_status": company_status_input,
                        "setup_model_required_or_assumed": setup_model_input,
                        "setup_model_verification_status": setup_status_input,
                        "verification_status": verification_input,
                        "reviewer_notes": reviewer_notes,
                        "eligibility_confirmation_source_url": confirmation_url,
                        "last_checked_date": date.today().isoformat(),
                    },
                )
                st.success("Policy review saved to the policy CSV.")
                st.rerun()
            except PolicyDataError as error:
                st.error(f"Policy review was not saved: {error}")

    st.markdown("### Setup model and policy eligibility")
    st.caption(
        "The detailed own-entity, EOR, and BOT comparison is in Setup options. "
        "Eligibility remains policy-specific; this workspace makes no assumption "
        "that any of these arrangements qualifies."
    )
    st.button(
        "Open Setup options",
        key="policy_open_setup_options",
        on_click=_navigate_to_section,
        args=("Setup options",),
    )

    st.markdown("### Shared service-provider directory")
    st.caption(
        "This directory is shared with Talent and costs. Sample hiring-route "
        "assumptions are not provider quotes."
    )
    with st.expander("Provider categories and verified records", expanded=True):
        for category in PROVIDER_CATEGORIES:
            category_rows = [
                provider for provider in providers
                if provider.get("provider_category") == category
            ]
            verified = [
                provider for provider in category_rows
                if provider.get("verification_status", "").casefold() == "verified"
            ]
            st.markdown(f"**{category}**")
            if verified:
                st.dataframe(verified, hide_index=True, width="stretch")
            else:
                st.write("No verified provider yet.")
            unverified = [provider for provider in category_rows if provider not in verified]
            if unverified:
                st.caption("Unverified leads — not validated recommendations.")
                st.dataframe(unverified, hide_index=True, width="stretch")

    st.markdown("### State policy sources and search limitations")
    if sources:
        st.dataframe(
            [
                {
                    "State": source.get("state", ""),
                    "Source title": source.get("source_title", ""),
                    "Source type": source.get("source_type", ""),
                    "URL": source.get("url", ""),
                    "Accessed": source.get("accessed_date", ""),
                    "What it supports": source.get("what_it_supports", ""),
                    "Limitations": source.get("limitations", ""),
                    "Verification status": source.get("verification_status", ""),
                }
                for source in sources
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "URL": st.column_config.LinkColumn(
                    "URL", display_text="Open official source"
                )
            },
        )
    else:
        st.info("No official policy-source records have been loaded.")


def _show_setup_options(answers: dict[str, Any]) -> None:
    render_setup_options(answers, _navigate_to_section)


def _show_compliance(answers: dict[str, Any]) -> None:
    st.title("Compliance and risk")
    st.warning(
        "Planning checklist only — not legal, tax, employment, or data-protection advice. "
        "Confirm company-specific obligations with qualified professionals."
    )
    user_constraints = str(_value(answers, "regulatory_constraints") or "").strip()
    st.markdown("### User-provided considerations")
    st.write(user_constraints or "No constraints have been entered.")
    checklist = [
        ("entity", "Entity formation, registrations, and corporate governance"),
        ("employment", "Employment terms, payroll, benefits, and worker classification"),
        ("data", "Data flows, security controls, privacy, and any localization requirements"),
        ("tax", "Corporate tax, indirect tax, and permanent-establishment questions"),
        ("transfer-pricing", "Related-party services, documentation, and transfer pricing"),
        ("ip", "Intellectual property ownership, access, and cross-border transfers"),
        ("continuity", "Business continuity, access controls, and operational resilience"),
    ]
    progress = st.session_state.setdefault("compliance_review_status", {})
    st.markdown("### Review questions")
    for key, label in checklist:
        options = ("Needs qualified review", "Under review", "Reviewed with adviser")
        widget_key = f"compliance_{key}_status"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = progress.get(key, options[0])
        choice = st.selectbox(label, options, key=widget_key)
        progress[key] = choice
    st.caption(
        "Checklist statuses record session progress only. They do not establish "
        "compliance or replace written professional advice."
    )
def _show_roadmap(answers: dict[str, Any]) -> None:
    st.title("Entry roadmap")
    deadline = _value(answers, "decision_deadline")
    if isinstance(deadline, date):
        days_remaining = (deadline - date.today()).days
        st.metric("User-provided decision deadline", deadline.isoformat())
        if days_remaining >= 0:
            st.caption(f"{days_remaining} days remain as of today; this is not a delivery forecast.")
        else:
            st.warning("The provided decision deadline is in the past; confirm or update it.")
    else:
        st.info("No decision deadline is recorded; the roadmap cannot be anchored to a target date.")

    milestones = [
        (
            "1. Confirm decision scope",
            "Confirm decision owners, launch objective, role mix, and candidate-city scope.",
            "Needed before evidence collection can be scoped precisely.",
        ),
        (
            "2. Complete priority evidence",
            "Research talent supply and cost, proximity needs, and suitable office conditions in the user's priority order.",
            "Blocks a defensible city comparison until evidence is comparable and reviewed.",
        ),
        (
            "3. Review operating and compliance options",
            "Assess setup models, hiring feasibility, legal/tax/data questions, and provider due diligence.",
            "Requires company-specific professional review; no compliance conclusion is assumed.",
        ),
        (
            "4. Build and review the decision case",
            "Compare candidate cities only when required evidence is available; record assumptions and unresolved risks.",
            "No city selection or final investment decision is currently supportable from this evidence register.",
        ),
    ]
    for title, action, dependency in milestones:
        st.markdown(f"### {title}")
        st.write(action)
        st.caption("Dependency / gate: " + dependency)
    st.caption(
        "No intermediate milestone dates or durations are invented. Add dated "
        "estimates only after owners, dependencies, and work effort are confirmed."
    )
def _show_sources_and_gaps(answers: dict[str, Any]) -> None:
    st.title("Sources and evidence")
    sources, claims = _load_evidence()
    _show_evidence(claims, sources)
    st.markdown("### Actionable research tasks")
    _render_research_checklist(answers)


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background-color: #F3F6FA;
            color: #253247;
        }
        .stApp [data-testid="stHeader"] {
            background-color: #F3F6FA;
            color: #253247;
            border-bottom: 1px solid #D7DEE8;
        }
        .stApp [data-testid="stHeader"] button {
            background-color: transparent;
            color: #253247;
            border: 1px solid transparent;
            border-radius: 6px;
        }
        .stApp [data-testid="stHeader"] button:hover {
            background-color: #EAF1F8;
            color: #14243A;
            border-color: #D7DEE8;
        }
        .stApp [data-testid="stHeader"] button:active {
            background-color: #DCE8F4;
            color: #14243A;
            border-color: #AAB7C7;
        }
        .stApp [data-testid="stHeader"] button:focus-visible {
            outline: 3px solid #005A9C;
            outline-offset: 2px;
        }
        .stApp [data-testid="stHeader"] button:disabled,
        .stApp [data-testid="stHeader"] button[aria-disabled="true"] {
            background-color: transparent;
            color: #526176;
            border-color: transparent;
            opacity: 1;
            cursor: not-allowed;
        }
        .stApp [data-testid="stHeader"] button [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stHeader"] button [data-testid="stMarkdownContainer"] p,
        .stApp [data-testid="stHeader"] button svg {
            color: inherit;
            fill: currentColor;
        }
        .stApp [data-testid="stMainBlockContainer"] {
            padding-top: 4rem;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            color: #253247;
            border-right: 1px solid #D7DEE8;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #14243A;
        }
        .stApp p, .stApp li, .stApp label,
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: #253247;
        }
        .stApp [data-testid="stText"] span,
        [data-testid="stSidebar"] [data-testid="stText"] span {
            color: #253247;
        }
        .stApp [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #526176;
        }

        .stApp button[data-testid="stBaseButton-primary"] {
            background-color: #005A9C;
            color: #FFFFFF;
            border: 1px solid #005A9C;
        }
        .stApp button[data-testid="stBaseButton-primary"]:hover {
            background-color: #004477;
            color: #FFFFFF;
            border-color: #004477;
        }
        .stApp button[data-testid="stBaseButton-primary"]:active {
            background-color: #004477;
            color: #FFFFFF;
            border-color: #004477;
        }
        .stApp button[data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"],
        .stApp button[data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"] p {
            color: #FFFFFF;
        }
        .stApp button[data-testid="stBaseButton-secondary"] {
            background-color: #FFFFFF;
            color: #14243A;
            border: 1px solid #AAB7C7;
        }
        .stApp button[data-testid="stBaseButton-secondary"]:hover {
            background-color: #EAF1F8;
            color: #14243A;
            border-color: #71839A;
        }
        .stApp button[data-testid="stBaseButton-secondary"]:active {
            background-color: #DCE8F4;
            color: #14243A;
            border-color: #71839A;
        }
        .stApp button[data-testid="stBaseButton-secondary"] [data-testid="stMarkdownContainer"],
        .stApp button[data-testid="stBaseButton-secondary"] [data-testid="stMarkdownContainer"] p {
            color: #14243A;
        }
        .stApp button[data-testid="stBaseButton-primary"]:focus-visible,
        .stApp button[data-testid="stBaseButton-secondary"]:focus-visible,
        [data-testid="stSidebar"] button:focus-visible {
            outline: 3px solid #005A9C;
            outline-offset: 2px;
        }
        [data-testid="stSidebar"] .st-key-return_to_intake
        button[data-testid="stBaseButton-secondary"] {
            background-color: #FFFFFF;
            color: #14243A;
            border: 1px solid #AAB7C7;
        }
        [data-testid="stSidebar"] .st-key-return_to_intake
        button[data-testid="stBaseButton-secondary"]:hover {
            background-color: #EAF1F8;
            color: #14243A;
            border-color: #71839A;
        }
        [data-testid="stSidebar"] .st-key-return_to_intake
        button[data-testid="stBaseButton-secondary"]:active {
            background-color: #DCE8F4;
            color: #14243A;
            border-color: #71839A;
        }
        [data-testid="stSidebar"] .st-key-return_to_intake
        button[data-testid="stBaseButton-secondary"]:focus-visible {
            outline: 3px solid #005A9C;
            outline-offset: 2px;
        }
        [data-testid="stSidebar"] .st-key-return_to_intake
        button[data-testid="stBaseButton-secondary"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] .st-key-return_to_intake
        button[data-testid="stBaseButton-secondary"] [data-testid="stMarkdownContainer"] p {
            color: #14243A;
        }

        .stApp [data-testid="stExpander"] {
            background-color: #FFFFFF;
            border: 1px solid #D7DEE8;
            border-radius: 8px;
            overflow: hidden;
        }
        .stApp [data-testid="stExpander"] details {
            background-color: #FFFFFF;
            border: 0;
        }
        .stApp [data-testid="stExpander"] summary {
            background-color: #FFFFFF;
            color: #253247;
        }
        .stApp [data-testid="stExpander"] summary:hover {
            background-color: #F0F4F8;
            color: #14243A;
        }
        .stApp [data-testid="stExpander"] summary:focus-visible {
            outline: 3px solid #005A9C;
            outline-offset: -3px;
        }
        .stApp [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {
            color: inherit;
        }
        .stApp [data-testid="stExpander"] [data-testid="stIconMaterial"] {
            color: #253247;
        }
        .stApp [data-testid="stExpander"] summary:hover [data-testid="stIconMaterial"] {
            color: #14243A;
        }
        .stApp [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            background-color: #FFFFFF;
            color: #253247;
            border-top: 1px solid #D7DEE8;
        }
        .stApp [data-testid="stExpander"] [data-testid="stExpanderDetails"] p,
        .stApp [data-testid="stExpander"] [data-testid="stExpanderDetails"] li,
        .stApp [data-testid="stExpander"] [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] {
            color: #253247;
        }

        .stApp [data-testid="stAlert"] [data-testid="stAlertContainer"] {
            background-color: #EEF4FA;
            color: #253247;
            border: 1px solid #C7D5E5;
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"])
        [data-testid="stAlertContainer"] {
            background-color: #EEF4FA;
            color: #253247;
            border-color: #C7D5E5;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"])
        [data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"])
        [data-testid="stAlertContainer"] p {
            color: #253247;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"])
        [data-testid="stAlertContainer"] {
            background-color: #EAF5EE;
            color: #214D32;
            border-color: #B7D8C1;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"])
        [data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"])
        [data-testid="stAlertContainer"] p {
            color: #214D32;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"])
        [data-testid="stAlertContainer"] {
            background-color: #FFF5E5;
            color: #704B00;
            border-color: #E7CC94;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"])
        [data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"])
        [data-testid="stAlertContainer"] p {
            color: #704B00;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"])
        [data-testid="stAlertContainer"] {
            background-color: #FCECEC;
            color: #8B2525;
            border-color: #E8B8B8;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"])
        [data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"])
        [data-testid="stAlertContainer"] p {
            color: #8B2525;
        }
        .stApp [data-testid="stAlert"] [data-testid="stAlertContainer"] svg {
            color: inherit;
            fill: currentColor;
        }

        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputContainer"],
        .stApp [class*="st-key-talent_cost"] [data-testid="stTextInputRootElement"],
        .stApp [class*="st-key-talent_cost"] [role="group"] {
            background-color: #FFFFFF;
            color: #253247;
            border: 1px solid #AAB7C7;
            border-radius: 6px;
        }
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputContainer"]:focus-within,
        .stApp [class*="st-key-talent_cost"] [data-testid="stTextInputRootElement"]:focus-within,
        .stApp [class*="st-key-talent_cost"] [role="group"]:focus-within {
            border-color: #005A9C;
            box-shadow: 0 0 0 2px rgba(0, 90, 156, 0.2);
        }
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputContainer"]:hover,
        .stApp [class*="st-key-talent_cost"] [data-testid="stTextInputRootElement"]:hover,
        .stApp [class*="st-key-talent_cost"] [role="group"]:hover {
            background-color: #F0F4F8;
        }
        .stApp [class*="st-key-talent_cost"] input,
        .stApp [class*="st-key-talent_cost"] textarea {
            background-color: transparent;
            color: #253247;
            -webkit-text-fill-color: #253247;
            caret-color: #14243A;
        }
        .stApp [class*="st-key-talent_cost"] input::placeholder,
        .stApp [class*="st-key-talent_cost"] textarea::placeholder {
            color: #526176;
            -webkit-text-fill-color: #526176;
            opacity: 1;
        }
        .stApp [class*="st-key-talent_cost"] [data-tag] {
            background-color: #E8EDF3;
            color: #253247;
        }
        .stApp [class*="st-key-talent_cost"] [data-tag] button {
            background-color: transparent;
            color: #253247;
            border: 0;
        }
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepUp"],
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepDown"] {
            background-color: #FFFFFF;
            color: #253247;
            border: 0;
        }
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepUp"]:hover,
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepDown"]:hover {
            background-color: #EAF1F8;
            color: #14243A;
        }
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepUp"]:active,
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepDown"]:active {
            background-color: #DCE8F4;
            color: #14243A;
        }
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepUp"]:focus-visible,
        .stApp [class*="st-key-talent_cost"] [data-testid="stNumberInputStepDown"]:focus-visible {
            outline: 2px solid #005A9C;
            outline-offset: -2px;
        }
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stSelectboxVirtualDropdown"],
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stMultiSelectVirtualDropdown"] {
            background-color: #FFFFFF;
            color: #253247;
            border: 1px solid #AAB7C7;
        }
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stSelectboxVirtualDropdown"] [role="option"],
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stMultiSelectVirtualDropdown"] [role="option"] {
            background-color: #FFFFFF;
            color: #253247;
        }
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stMultiSelectVirtualDropdown"] [role="option"]:hover,
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"],
        body:has(.stApp [class*="st-key-talent_cost"] [aria-expanded="true"])
        [data-testid="stMultiSelectVirtualDropdown"] [role="option"][aria-selected="true"] {
            background-color: #EAF1F8;
            color: #14243A;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_workspace(answers: dict[str, Any]) -> None:
    """Render the intake-driven decision workspace."""
    _apply_styles()
    st.sidebar.title("Strategy workspace")
    st.sidebar.button(
        "← Return to intake",
        key="return_to_intake",
        width="stretch",
        on_click=lambda: st.session_state.__setitem__("screen", "intake"),
    )
    st.sidebar.radio(
        "Workspace sections",
        SECTIONS,
        key="workspace_section",
    )
    st.sidebar.divider()
    _show_profile_sidebar(answers)

    selected_section = st.session_state.get("workspace_section", SECTIONS[0])
    if selected_section == "Overview":
        _show_decision_overview(answers)
    elif selected_section == "Compare cities":
        _show_city_comparison(answers)
    elif selected_section == "Talent and costs":
        _show_talent_costs(answers)
    elif selected_section == "Policies and ecosystem":
        _show_policies(answers)
    elif selected_section == "Setup options":
        _show_setup_options(answers)
    elif selected_section == "Compliance and risk":
        _show_compliance(answers)
    elif selected_section == "Entry roadmap":
        _show_roadmap(answers)
    elif selected_section == "Sources and evidence":
        _show_sources_and_gaps(answers)
