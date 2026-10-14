"""Decision-record and planning-brief workspace for setup options."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

import streamlit as st

from report_pdf import build_pdf_report


DECISION_STATUSES = (
    "Decided",
    "Proposed",
    "Undecided",
    "Waiting on verification",
)
MODEL_NAMES = (
    "Own entity",
    "Employer of Record (EOR)",
    "Build-Operate-Transfer (BOT)",
    "Phased path: interim model to own entity",
)
NO_MODEL_PREFERENCE = "No preference recorded"

DECISION_TOPICS = (
    ("candidate_cities", "Candidate cities"),
    ("operating_model", "Operating model"),
    ("hiring_ramp", "Hiring ramp"),
    ("budget_costs", "Budget and cost assumptions"),
    ("policy_route", "Policy route"),
    ("transition_path", "Transition path, if applicable"),
)

MODEL_DESCRIPTIONS = {
    "Own entity": (
        "A company-operated India entity. Review entity structure, governance, "
        "operating control, and ongoing responsibilities with qualified advisers."
    ),
    "Employer of Record (EOR)": (
        "An interim employment arrangement to assess with a provider and "
        "qualified advisers; this description does not establish legal treatment."
    ),
    "Build-Operate-Transfer (BOT)": (
        "A project-specific arrangement to assess for build, operating, "
        "governance, and possible transfer terms."
    ),
    "Phased path: interim model to own entity": (
        "Planning hypothesis only: begin with a selected interim model and "
        "consider a later transition to an own entity. No transition is assumed."
    ),
}

DIMENSIONS = (
    (
        "Target timeline",
        "decision_deadline",
        "What launch or decision milestones apply, and what model-specific timing is evidenced?",
    ),
    (
        "Target headcount and ramp",
        "headcount_ramp",
        "What hiring capacity, responsibilities, and ramp milestones need confirmation?",
    ),
    (
        "Desired operational control",
        "operational_control",
        "What level of day-to-day and strategic control is required?",
    ),
    (
        "Intellectual-property and data requirements",
        "data_ip",
        "What data access, security, privacy, and IP ownership requirements apply?",
    ),
    (
        "Risk tolerance",
        "risk_tolerance",
        "What risks and dependencies can the company accept?",
    ),
    (
        "India presence and constraints",
        "india_presence",
        "What existing entity, workforce, contractual, regulatory, or other constraints affect the option?",
    ),
)

_EMPTY_DECISION = {
    "status": "Undecided",
    "decision": "",
    "rationale": "",
    "decision_owner": "",
    "decision_date": "",
    "evidence_references": "",
    "assumptions": "",
    "open_questions": "",
}


def initial_decision_log() -> dict[str, dict[str, Any]]:
    """Return six empty records; none is treated as a decision."""
    return {
        decision_id: dict(_EMPTY_DECISION)
        for decision_id, _ in DECISION_TOPICS
    }


def recorded_decision_count(
    decisions: dict[str, dict[str, Any]],
) -> int:
    """Count explicitly Proposed, Decided, or Waiting on verification records."""
    return sum(
        decisions.get(decision_id, {}).get("status") in {
            "Proposed",
            "Decided",
            "Waiting on verification",
        }
        for decision_id, _ in DECISION_TOPICS
    )


def _text(value: Any, missing: str = "Not provided") -> str:
    if value is None:
        return missing
    if isinstance(value, date):
        return value.isoformat()
    rendered = str(value).strip()
    return rendered or missing


def _context_value(answers: dict[str, Any], field: str) -> tuple[str, str]:
    if field == "headcount_ramp":
        headcount = _text(
            answers.get("headcount_custom")
            if answers.get("headcount") == "Custom range"
            else answers.get("headcount")
        )
        ramp = _text(answers.get("ramp_timeline"))
        parts = []
        if headcount != "Not provided":
            parts.append(f"Headcount: {headcount}")
        if ramp != "Not provided":
            parts.append(f"Ramp: {ramp}")
        if parts:
            return (
                "; ".join(parts),
                "Company-provided",
            )
        return "Not provided", "Not available"

    if field == "decision_deadline":
        deadline = _text(answers.get("decision_deadline"))
        launch = _text(answers.get("launch_deadline"))
        details = []
        if deadline != "Not provided":
            details.append(f"Decision deadline: {deadline}")
        if launch != "Not provided":
            details.append(f"Launch timing response: {launch}")
        if details:
            return "; ".join(details), "Company-provided"
        return "Not provided", "Not available"

    if field == "india_presence":
        presence = _text(answers.get("india_presence"))
        if presence != "Not provided":
            return f"Existing India presence: {presence}", "Company-provided"
        return "Not provided", "Not available"

    if field == "data_ip":
        constraints = _text(answers.get("regulatory_constraints"))
        if constraints != "Not provided":
            return (
                f"Intake text (reconfirm as a company requirement): {constraints}",
                "Company-provided",
            )
        return "Not provided", "Not available"

    return "Not provided", "Not available"


def build_model_comparison(
    answers: dict[str, Any],
) -> list[dict[str, str]]:
    """Build a non-ranking comparison without inferring model suitability."""
    rows: list[dict[str, str]] = []
    for model in MODEL_NAMES:
        for dimension, field, question in DIMENSIONS:
            company_constraint, evidence_state = _context_value(answers, field)
            rows.append(
                {
                    "Operating model": model,
                    "Dimension": dimension,
                    "Company-stated context": company_constraint,
                    "Assessment": "Cannot be judged",
                    "Evidence state": evidence_state,
                    "Supporting source or assumption": (
                        "Intake context only; no model-specific official source "
                        "or professional-adviser reference is integrated."
                    ),
                    "Open question": question,
                }
            )
    return rows


def build_planning_brief(
    answers: dict[str, Any],
    decisions: dict[str, dict[str, Any]],
) -> str:
    """Build an evidence-labelled Markdown brief from saved decisions."""
    lines = [
        "# Setup options planning brief",
        "",
        "Structural planning prototype. This brief is not legal, tax, HR, "
        "employment, data/IP, policy, or investment advice.",
        "",
        "## Company and planning context",
    ]
    context_fields = (
        ("Company", "company_name"),
        ("Headquarters country", "headquarters_country"),
        ("Industry", "industry"),
        ("Planning description", "plan_description"),
        ("Target headcount", "headcount"),
        ("Hiring ramp", "ramp_timeline"),
        ("Decision deadline", "decision_deadline"),
        ("India presence", "india_presence"),
        ("Intake constraints", "regulatory_constraints"),
    )
    for label, field in context_fields:
        value = answers.get(field)
        if field == "headcount" and answers.get(field) == "Custom range":
            value = answers.get("headcount_custom")
        if field == "industry" and value == "Other":
            value = answers.get("industry_other")
        if field == "industry" and not value:
            value = answers.get("industry_other")
        lines.append(
            f"- {label}: {_text(value)} "
            "[Evidence state: Company-provided intake; reconfirm, as profile "
            "values may be illustrative.]"
        )
    functions = answers.get("gcc_functions")
    if isinstance(functions, (list, tuple)):
        functions = ", ".join(str(item) for item in functions)
    lines.append(
        f"- Planned functions: {_text(functions)} "
        "[Evidence state: Company-provided intake; reconfirm.]"
    )
    priorities = [
        _text(answers.get(f"priority_{rank}"), "")
        for rank in range(1, 5)
    ]
    priorities = [priority for priority in priorities if priority]
    lines.append(
        f"- Location priorities: {_text(' > '.join(priorities))} "
        "[Evidence state: Company-provided intake; no city recommendation inferred.]"
    )

    count = recorded_decision_count(decisions)
    lines.extend(
        [
            "",
            "## Executive decision summary",
            f"- {count} of {len(DECISION_TOPICS)} decisions recorded. "
            "A record counts when its saved status is Proposed, Decided, or "
            "Waiting on verification; Undecided records are not counted.",
            "- No overall winner or readiness assessment is calculated.",
            "",
            "## Decision records",
        ]
    )
    for decision_id, topic in DECISION_TOPICS:
        record = decisions.get(decision_id, {})
        lines.append(f"### {topic}")
        lines.append(f"- Status: {_text(record.get('status'), 'Undecided')}")
        for field, label in (
            ("decision", "Decision or current proposal"),
            ("rationale", "Rationale"),
            ("decision_owner", "Decision owner"),
            ("decision_date", "Decision date"),
            ("evidence_references", "Evidence references"),
            ("assumptions", "Assumptions"),
            ("open_questions", "Open questions and next action"),
        ):
            lines.append(f"- {label}: {_text(record.get(field), 'Not recorded')}")
        lines.append(
            "- Record evidence state: Company-provided planning record; "
            "not independently verified unless an evidence reference is reviewed."
        )

    lines.extend(["", "## Operating-model comparison"])
    lines.append(
        "Conceptual descriptions only. Assessments below are not conclusions; "
        "each is Cannot be judged until company-specific requirements and "
        "supporting evidence are reviewed."
    )
    for model, description in MODEL_DESCRIPTIONS.items():
        lines.extend([f"### {model}", f"- Description [Evidence state: Assumption]: {description}"])
        for row in build_model_comparison(answers):
            if row["Operating model"] != model:
                continue
            lines.append(
                f"- {row['Dimension']}: constraint = {row['Company-stated context']}; "
                f"assessment = {row['Assessment']}; evidence state = "
                f"{row['Evidence state']}; supporting source/assumption = "
                f"{row['Supporting source or assumption']}; open question = "
                f"{row['Open question']}."
            )

    transition = decisions.get("transition_path", {})
    transition_details = transition.get("transition_details", {})
    lines.extend(
        [
            "",
            "## Proposed phased transition",
            "Planning hypothesis only; it is not a sourced recommendation.",
        ]
    )
    for key, label in (
        ("initial_model", "Initial operating model"),
        ("destination_model", "Potential destination model"),
        ("transition_trigger", "Proposed transition trigger"),
        ("transition_window", "Target transition window"),
        ("switching_costs", "Switching costs"),
        ("switching_time", "Switching time"),
        ("dependencies", "Legal, tax, employment, and contractual dependencies"),
        ("validation_evidence", "Evidence needed to validate the transition"),
    ):
        missing = "To confirm" if key in {"switching_costs", "switching_time"} else "Not recorded"
        lines.append(
            f"- {label}: {_text(transition_details.get(key), missing)} "
            "[Evidence state: Assumption / To confirm.]"
        )

    lines.extend(["", "## Read-only module summaries"])
    for module, action in (
        ("Compare Cities", "Change in Compare Cities"),
        ("Talent & Costs", "Change in Talent & Costs"),
        ("Policies & Incentives", "Review in Policies & Incentives"),
    ):
        lines.append(
            f"- {module}: Awaiting module integration; no independent data copy "
            f"is used here. [Evidence state: Not available; navigation: {action}.]"
        )

    lines.extend(["", "## Assumptions and unavailable data"])
    lines.append(
        "- No model-specific cost, setup time, transition cost/time, compliance "
        "determination, or policy route is verified in this workspace. "
        "[Evidence state: Not available.]"
    )
    lines.append(
        "- Missing company requirements are shown as Not provided or Cannot be "
        "judged; no favourable conclusion is inferred."
    )

    lines.extend(["", "## Open decisions and next actions"])
    open_actions: list[str] = []
    for decision_id, topic in DECISION_TOPICS:
        record = decisions.get(decision_id, {})
        status = record.get("status", "Undecided")
        next_action = _text(record.get("open_questions"), "Record an owner and next action.")
        if status != "Decided" or next_action != "Record an owner and next action.":
            open_actions.append(f"- {topic} ({status}): {next_action}")
    lines.extend(open_actions or ["- None recorded; review all six decision records."])

    lines.extend(
        [
            "",
            "## Needs professional verification",
            "- Legal: entity structure, governance, contracts, and any transition documents.",
            "- Tax: company-specific tax, permanent-establishment, and transfer-pricing implications.",
            "- HR and employment: worker classification, employment responsibilities, and workforce transition.",
            "- Data and IP: access, security, privacy, ownership, licensing, and transfer terms.",
            "- Policy: current policy text, applicant and setup-model requirements, and written company-specific eligibility evidence.",
            "- Validate any proposed timing, provider terms, fees, switching costs, and dependencies with appropriate sources and qualified advisers.",
        ]
    )
    return "\n".join(lines)


def _decision_widget_key(decision_id: str, field: str) -> str:
    return f"setup_decision_{decision_id}_{field}"


def _ensure_widget_values(
    decision_id: str,
    record: dict[str, Any],
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        st.session_state.setdefault(
            _decision_widget_key(decision_id, field),
            record.get(field, ""),
        )


def _render_decision_editor(
    decision_id: str,
    topic: str,
    record: dict[str, Any],
    decisions: dict[str, dict[str, Any]],
) -> None:
    with st.expander(topic):
        common_fields = (
            "decision",
            "rationale",
            "decision_owner",
            "decision_date",
            "evidence_references",
            "assumptions",
            "open_questions",
        )
        _ensure_widget_values(decision_id, record, ("status", *common_fields))
        status_key = _decision_widget_key(decision_id, "status")
        if st.session_state.get(status_key) not in DECISION_STATUSES:
            st.session_state[status_key] = "Undecided"
        with st.form(f"setup_decision_form_{decision_id}"):
            st.selectbox(
                "Status",
                DECISION_STATUSES,
                key=status_key,
                help="Undecided is the default. No intake value automatically records a decision.",
            )
            if decision_id == "operating_model":
                preference_key = _decision_widget_key(decision_id, "preferred_model")
                st.session_state.setdefault(
                    preference_key,
                    record.get("preferred_model", NO_MODEL_PREFERENCE),
                )
                if st.session_state.get(preference_key) not in (
                    NO_MODEL_PREFERENCE,
                    *MODEL_NAMES,
                ):
                    st.session_state[preference_key] = NO_MODEL_PREFERENCE
                st.selectbox(
                    "Preferred model (record a proposal only if appropriate)",
                    (NO_MODEL_PREFERENCE, *MODEL_NAMES),
                    key=preference_key,
                )
            st.text_area(
                "Decision or current proposal",
                key=_decision_widget_key(decision_id, "decision"),
            )
            st.text_area(
                "Rationale",
                key=_decision_widget_key(decision_id, "rationale"),
            )
            st.text_input(
                "Decision owner",
                key=_decision_widget_key(decision_id, "decision_owner"),
            )
            st.text_input(
                "Decision date (YYYY-MM-DD; leave blank if not recorded)",
                key=_decision_widget_key(decision_id, "decision_date"),
                placeholder="YYYY-MM-DD",
            )
            st.text_area(
                "Evidence references (URLs or internal reference IDs)",
                key=_decision_widget_key(decision_id, "evidence_references"),
            )
            st.text_area(
                "Assumptions",
                key=_decision_widget_key(decision_id, "assumptions"),
            )
            st.text_area(
                "Open questions and next action",
                key=_decision_widget_key(decision_id, "open_questions"),
            )
            if decision_id == "transition_path":
                st.markdown("**Phased-path hypothesis fields**")
                details = record.get("transition_details", {})
                transition_fields = (
                    "transition_trigger",
                    "transition_window",
                    "switching_costs",
                    "switching_time",
                    "dependencies",
                    "validation_evidence",
                )
                _ensure_widget_values(decision_id, details, transition_fields)
                initial_key = _decision_widget_key(decision_id, "initial_model")
                destination_key = _decision_widget_key(decision_id, "destination_model")
                st.session_state.setdefault(
                    initial_key, details.get("initial_model", "Not recorded")
                )
                st.session_state.setdefault(
                    destination_key,
                    details.get("destination_model", "Not recorded"),
                )
                model_choices = ("Not recorded", *MODEL_NAMES[:-1])
                if st.session_state.get(initial_key) not in model_choices:
                    st.session_state[initial_key] = "Not recorded"
                if st.session_state.get(destination_key) not in (
                    "Not recorded",
                    "Own entity",
                ):
                    st.session_state[destination_key] = "Not recorded"
                st.selectbox("Initial operating model", model_choices, key=initial_key)
                st.selectbox(
                    "Potential destination model",
                    ("Not recorded", "Own entity"),
                    key=destination_key,
                )
                for field, label, placeholder in (
                    ("transition_trigger", "Proposed transition trigger", ""),
                    ("transition_window", "Target transition window", "To confirm"),
                    ("switching_costs", "Switching costs", "To confirm"),
                    ("switching_time", "Switching time", "To confirm"),
                    (
                        "dependencies",
                        "Legal, tax, employment, and contractual dependencies",
                        "To confirm",
                    ),
                    (
                        "validation_evidence",
                        "Evidence needed to validate the transition",
                        "To confirm",
                    ),
                ):
                    st.text_input(
                        label,
                        key=_decision_widget_key(decision_id, field),
                        placeholder=placeholder,
                    )
            submitted = st.form_submit_button("Save decision record")
        if submitted:
            saved_date = str(
                st.session_state[_decision_widget_key(decision_id, "decision_date")]
            ).strip()
            if saved_date:
                try:
                    if date.fromisoformat(saved_date).isoformat() != saved_date:
                        raise ValueError
                except ValueError:
                    st.error("Decision date must use YYYY-MM-DD, or be left blank.")
                    return
            updated = {
                field: st.session_state[_decision_widget_key(decision_id, field)]
                for field in ("status", *common_fields)
            }
            if decision_id == "operating_model":
                updated["preferred_model"] = st.session_state[
                    _decision_widget_key(decision_id, "preferred_model")
                ]
            if decision_id == "transition_path":
                transition_fields = (
                    "initial_model",
                    "destination_model",
                    "transition_trigger",
                    "transition_window",
                    "switching_costs",
                    "switching_time",
                    "dependencies",
                    "validation_evidence",
                )
                updated["transition_details"] = {
                    field: st.session_state[
                        _decision_widget_key(decision_id, field)
                    ]
                    for field in transition_fields
                }
            decisions[decision_id] = updated
            st.rerun()


def render_setup_options(
    answers: dict[str, Any],
    navigate: Callable[[str], None],
) -> None:
    """Render the decision shell without duplicating module-owned data."""
    st.title("Setup options")
    st.caption(
        "Decision-record workspace only. Changes persist for this Streamlit "
        "session; they are not saved to a durable database."
    )

    decisions = st.session_state.setdefault("setup_decision_log", initial_decision_log())
    for decision_id, _ in DECISION_TOPICS:
        decisions.setdefault(decision_id, dict(_EMPTY_DECISION))
    recorded = recorded_decision_count(decisions)
    st.markdown("### Setup decision log")
    st.write(f"**{recorded} of {len(DECISION_TOPICS)} decisions recorded.**")
    st.caption(
        "Recorded means a saved status of Proposed, Decided, or Waiting on "
        "verification. Undecided is the unrecorded default; it is not a decision."
    )
    summary_rows = [
        {
            "Decision topic": topic,
            "Status": decisions[decision_id].get("status", "Undecided"),
            "Decision or current proposal": _text(
                decisions[decision_id].get("decision"), "Not recorded"
            ),
        }
        for decision_id, topic in DECISION_TOPICS
    ]
    st.dataframe(summary_rows, hide_index=True, width="stretch")
    for decision_id, topic in DECISION_TOPICS:
        _render_decision_editor(
            decision_id,
            topic,
            decisions[decision_id],
            decisions,
        )

    st.markdown("### Operating-model comparison")
    st.caption(
        "Conceptual descriptions are for planning only. They do not establish "
        "legal obligations, tax position, employment compliance, policy eligibility, "
        "costs, or suitability. No model is ranked or recommended automatically."
    )
    with st.expander("Conceptual model descriptions", expanded=False):
        for model, description in MODEL_DESCRIPTIONS.items():
            st.markdown(f"**{model}.** {description}")

    comparison = build_model_comparison(answers)
    model_tabs = st.tabs(MODEL_NAMES)
    for tab, model in zip(model_tabs, MODEL_NAMES):
        with tab:
            rows = [
                {
                    "Dimension": row["Dimension"],
                    "Company-stated context": row["Company-stated context"],
                    "Assessment": row["Assessment"],
                    "Evidence state": row["Evidence state"],
                    "Supporting source or assumption": row[
                        "Supporting source or assumption"
                    ],
                    "Open question": row["Open question"],
                }
                for row in comparison
                if row["Operating model"] == model
            ]
            st.dataframe(rows, hide_index=True, width="stretch")
            st.caption(
                "No model-specific source or qualified-adviser assessment is "
                "connected. Missing requirements remain Cannot be judged."
            )
            if model == "Phased path: interim model to own entity":
                st.info(
                    "Phased path is a planning hypothesis only. Record transition "
                    "triggers, window, costs, time, dependencies, and validation "
                    "evidence in the Transition path decision record above."
                )

    st.markdown("### Read-only module summaries")
    st.caption(
        "Awaiting module integration. These panels do not create editable copies "
        "of data owned by other sections."
    )
    module_summaries = (
        (
            "Candidate cities",
            "Awaiting module integration from Compare Cities.",
            "Compare cities",
            "Change in Compare Cities",
        ),
        (
            "Hiring ramp",
            "Awaiting module integration from Talent & Costs.",
            "Talent and costs",
            "Change in Talent & Costs",
        ),
        (
            "Budget and costs",
            "Awaiting module integration from Talent & Costs.",
            "Talent and costs",
            "Change in Talent & Costs",
        ),
        (
            "Policy route",
            "Awaiting module integration from Policies & Incentives.",
            "Policies and ecosystem",
            "Review in Policies & Incentives",
        ),
    )
    for title, summary, target, action in module_summaries:
        with st.expander(title):
            st.write(summary)
            st.caption("Evidence state: Not available in this decision shell.")
            st.button(
                action,
                key=f"setup_navigate_{target}",
                on_click=navigate,
                args=(target,),
            )

    st.markdown("### Planning recommendation")
    st.info(
        "No planning recommendation is generated automatically. Record a "
        "company-proposed model and rationale in the decision log, then review "
        "the outstanding professional checks in the planning brief."
    )
    if st.button("Generate planning brief", type="primary", key="setup_generate_brief"):
        brief = build_planning_brief(answers, decisions)
        st.session_state["setup_planning_brief"] = brief
        st.session_state["setup_planning_pdf"] = build_pdf_report(brief)
    if st.session_state.get("setup_planning_brief"):
        st.download_button(
            "Download planning brief PDF",
            data=st.session_state["setup_planning_pdf"],
            file_name="india_gcc_setup_planning_brief.pdf",
            mime="application/pdf",
            key="setup_download_brief",
        )
        with st.expander("Preview planning brief"):
            st.markdown(st.session_state["setup_planning_brief"])
