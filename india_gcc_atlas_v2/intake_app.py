from copy import deepcopy
from datetime import date
from textwrap import dedent

import streamlit as st

from report_pdf import build_pdf_report
from workspace import render_workspace


st.set_page_config(
    page_title="India GCC Atlas | Intake",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

STEPS = [
    "Your plan",
    "GCC scope",
    "Budget & constraints",
    "Location priorities",
    "Review",
]

INDUSTRIES = [
    "Not sure yet",
    "Banking, financial services & insurance (BFSI)",
    "Technology",
    "Healthcare & life sciences",
    "Manufacturing & engineering",
    "Retail & consumer",
    "Telecommunications",
    "Energy & utilities",
    "Professional services",
    "Other",
]

FUNCTIONS = [
    "Technology / software engineering",
    "Data, analytics & AI",
    "Finance & accounting",
    "Customer operations",
    "Research & development",
    "Cybersecurity",
    "Human resources",
    "Supply chain & procurement",
    "Legal & compliance",
    "Sales & marketing",
    "Other",
]

LOCATION_PRIORITIES = [
    "Talent availability",
    "Talent cost",
    "Relevant industry ecosystem",
    "Office availability and cost",
    "Connectivity and infrastructure",
    "Proximity to customers or leadership",
    "Quality of life and talent retention",
    "State incentives and support",
    "Business continuity and risk diversification",
]

FIELD_DEFAULTS = {
    "plan_description": (
        "Illustrative scenario for a fictional company: establish an India GCC "
        "to support global software engineering, data analytics, cloud "
        "operations, and enterprise technology delivery. The objectives are to "
        "expand access to skilled talent, build a scalable engineering team, "
        "and support global customers across time zones."
    ),
    "company_name": "NovaTech Solutions Inc.",
    "headquarters_country": "United States",
    "industry": "Other",
    "industry_other": "Enterprise Technology / IT Services",
    "gcc_functions": [
        "Technology / software engineering",
        "Data, analytics & AI",
    ],
    "functions_other": (
        "Cloud and DevOps engineering; quality assurance and testing"
    ),
    "headcount": "200-499",
    "headcount_custom": "",
    "ramp_timeline": "25-36 months",
    "roles_seniority": (
        "Illustrative roles: software engineers, data analysts and BI "
        "developers, cloud and DevOps engineers, and QA / test engineers. "
        "Seniority mix remains to be validated."
    ),
    "budget_sensitivity": "Very cost-sensitive",
    "budget_detail": (
        "No approved budget amount provided. Compare costs only when supported "
        "by verified sources and explicit assumptions."
    ),
    "india_presence": "No",
    "india_presence_detail": "",
    "regulatory_constraints": (
        "Illustrative considerations to investigate: reliable internet and "
        "cloud infrastructure; data security and access controls; employment "
        "and corporate compliance requirements; and ability to recruit and "
        "retain technical talent at scale."
    ),
    "decision_makers": "CEO, CFO, CTO, and Head of Global Operations",
    "decision_deadline": date(2027, 1, 1),
    "launch_deadline": (
        "Establish a scalable operating presence in India after evaluating "
        "locations, hiring feasibility, operating models, and compliance "
        "requirements; launch timing to be determined."
    ),
    "bfsi_regulations": [],
    "bfsi_regulations_other": "",
    "bfsi_data_residency": "Not sure yet",
    "bfsi_data_detail": "",
    "large_hiring_ramp": "Several hiring waves",
    "large_hiring_capacity": (
        "Illustrative planning assumption: internal talent-acquisition team "
        "supported by external recruiting partners; validate capacity."
    ),
    "large_city_strategy": "Not decided",
    "priority_1": "Talent availability",
    "priority_2": "Talent cost",
    "priority_3": "Proximity to customers or leadership",
    "priority_4": "Office availability and cost",
    "location_deal_breaker": (
        "Inability to recruit enough qualified talent within the planned "
        "hiring timeline."
    ),
}


def answer(key):
    return st.session_state.intake_answers[key]


def widget_key(key):
    return f"intake_field_{key}"


def field(key):
    key_name = widget_key(key)
    if key_name not in st.session_state:
        st.session_state[key_name] = answer(key)
    return key_name


def mark_profile_field_edited(key):
    st.session_state[f"intake_edited_{key}"] = True


def sync_widget_values():
    answers = st.session_state.intake_answers
    for key in FIELD_DEFAULTS:
        key_name = widget_key(key)
        if key_name in st.session_state:
            answers[key] = st.session_state[key_name]


def initialize_state():
    if "intake_answers" not in st.session_state:
        st.session_state.intake_answers = deepcopy(FIELD_DEFAULTS)
    else:
        for key, default in FIELD_DEFAULTS.items():
            st.session_state.intake_answers.setdefault(key, default)
    sync_widget_values()
    st.session_state.setdefault("screen", "intake")
    st.session_state.setdefault("workspace_section", "Overview")
    st.session_state.setdefault("step", 0)
    st.session_state.setdefault("generated_brief", "")
    st.session_state.setdefault("generated_pdf", b"")
    st.session_state.setdefault("validation_error", "")


def suggest_profile_from_description():
    """Pre-fill only blank profile fields when the description has clear clues."""
    description = st.session_state.get(
        widget_key("plan_description"), answer("plan_description")
    )
    st.session_state.intake_answers["plan_description"] = description
    lowered = description.lower()

    country_markers = (
        "headquartered in ",
        "headquarters in ",
        "hq in ",
        "based in ",
    )
    if (
        not st.session_state.get("intake_edited_headquarters_country", False)
        and answer("headquarters_country").strip().lower() in ("", "not sure yet")
    ):
        for marker in country_markers:
            if marker in lowered:
                suggestion = description[lowered.index(marker) + len(marker) :]
                for separator in (".", ",", ";", " and ", " while "):
                    suggestion = suggestion.split(separator, 1)[0]
                suggestion = suggestion.strip()
                if suggestion:
                    suggestion = suggestion.title()
                    st.session_state.intake_answers["headquarters_country"] = suggestion
                    st.session_state[widget_key("headquarters_country")] = suggestion
                break

    if (
        not st.session_state.get("intake_edited_industry", False)
        and answer("industry") in ("Select an industry", "Not sure yet")
    ):
        industry_terms = {
            "Banking, financial services & insurance (BFSI)": (
                "bank",
                "banking",
                "financial services",
                "insurance",
                "fintech",
                "bfsi",
            ),
            "Technology": ("technology", "software", "saas", "tech company"),
            "Healthcare & life sciences": (
                "healthcare",
                "health care",
                "life sciences",
                "pharma",
                "biotech",
            ),
            "Manufacturing & engineering": (
                "manufacturing",
                "industrial",
                "engineering",
            ),
            "Retail & consumer": ("retail", "consumer goods", "e-commerce"),
            "Telecommunications": ("telecom", "telecommunications"),
            "Energy & utilities": ("energy", "utilities", "renewables"),
            "Professional services": ("professional services", "consulting firm"),
        }
        for industry, terms in industry_terms.items():
            if any(term in lowered for term in terms):
                st.session_state.intake_answers["industry"] = industry
                st.session_state[widget_key("industry")] = industry
                break


def is_bfsi():
    industry = answer("industry")
    return industry.startswith("Banking, financial services")


def is_large_headcount():
    return answer("headcount") in {
        "500-999",
        "1,000-2,499",
        "2,500+",
    }


def validate_step(step):
    if step == 0:
        if not answer("headquarters_country").strip():
            return "Enter the company's headquarters country to continue."
        industry = answer("industry")
        if industry in ("Select an industry", "Other") and not (
            industry == "Other"
            and answer("industry_other").strip()
        ):
            return "Choose an industry, or enter one if you selected Other."
    elif step == 1:
        if answer("headcount") == "Select a target range":
            return "Choose a target headcount range, or select Not sure yet."
        if answer("headcount") == "Custom range" and not (
            answer("headcount_custom").strip()
        ):
            return "Describe the custom target headcount, or choose Not sure yet."
        if answer("ramp_timeline") == "Select a timeline":
            return "Choose a ramp timeline, or select Not sure yet."
    elif step == 3:
        if answer("priority_1") == "Select a priority":
            return "Select at least one location priority to continue."
    return ""


def go_back():
    sync_widget_values()
    st.session_state.step = max(0, st.session_state.step - 1)
    st.session_state.generated_brief = ""
    st.session_state.generated_pdf = b""
    st.session_state.validation_error = ""


def go_next():
    sync_widget_values()
    error = validate_step(st.session_state.step)
    if error:
        st.session_state.validation_error = error
        return
    st.session_state.step = min(len(STEPS) - 1, st.session_state.step + 1)
    st.session_state.generated_brief = ""
    st.session_state.generated_pdf = b""
    st.session_state.validation_error = ""


def display_value(value):
    if value is None or value == "":
        return "Not provided"
    if isinstance(value, list):
        return ", ".join(value) if value else "Not provided"
    return str(value)


def resolved_industry():
    if answer("industry") == "Other":
        return answer("industry_other").strip() or "Other (not specified)"
    if answer("industry") == "Select an industry":
        return "Not provided"
    return answer("industry")


def resolved_functions():
    functions = list(answer("gcc_functions"))
    other = answer("functions_other").strip()
    if other:
        functions.append(f"Other: {other}")
    return functions


def ranked_priorities():
    return [
        answer(key)
        for key in ("priority_1", "priority_2", "priority_3", "priority_4")
        if answer(key) != "Select a priority"
    ]


def normalize_rankings():
    """Clear later ranks when the same location priority is selected twice."""
    sync_widget_values()
    seen = set()
    for key in ("priority_1", "priority_2", "priority_3", "priority_4"):
        choice = answer(key)
        if choice == "Select a priority":
            continue
        if choice in seen:
            st.session_state.intake_answers[key] = "Select a priority"
            st.session_state[widget_key(key)] = "Select a priority"
        else:
            seen.add(choice)


def build_entry_brief():
    functions = resolved_functions()
    priorities = ranked_priorities()
    bfsi_lines = ""
    if is_bfsi():
        bfsi_lines = dedent(
            f"""

            ### BFSI regulatory and data follow-up
            - Regulatory areas to assess: {display_value(answer("bfsi_regulations"))}
            - Other regulatory areas: {display_value(answer("bfsi_regulations_other").strip())}
            - Data residency / in-country storage: {display_value(answer("bfsi_data_residency"))}
            - Additional details: {display_value(answer("bfsi_data_detail"))}
            """
        )

    hiring_lines = ""
    if is_large_headcount():
        hiring_lines = dedent(
            f"""

            ### Large-team hiring follow-up
            - Hiring ramp pattern: {display_value(answer("large_hiring_ramp"))}
            - Expected hiring capacity: {display_value(answer("large_hiring_capacity"))}
            - City strategy: {display_value(answer("large_city_strategy"))}
            """
        )

    decision_deadline = answer("decision_deadline")
    return dedent(
        f"""
        # India GCC entry brief

        > This intake starts from a fictional, illustrative demo scenario. Answers are editable and are not independently verified company facts. Evidence claims require cited support. This prototype-generated summary is not legal, tax, regulatory, or location advice.

        ## Company profile
        - Company: {display_value(answer("company_name").strip())}
        - Headquarters country: {display_value(answer("headquarters_country").strip())}
        - Industry: {resolved_industry()}
        - Original plan: {display_value(answer("plan_description").strip())}

        ## GCC scope and hiring
        - Planned functions: {display_value(functions)}
        - Target headcount: {display_value(answer("headcount_custom").strip() if answer("headcount") == "Custom range" else answer("headcount"))}
        - Ramp timeline: {display_value(answer("ramp_timeline"))}
        - Roles and seniority: {display_value(answer("roles_seniority").strip())}
        {hiring_lines}
        ## Budget and India presence
        - Budget / cost sensitivity: {display_value(answer("budget_sensitivity"))}
        - Budget detail: {display_value(answer("budget_detail").strip())}
        - Existing India presence: {display_value(answer("india_presence"))}
        - India presence detail: {display_value(answer("india_presence_detail").strip())}

        ## Regulatory, data, and decision constraints
        - Constraints: {display_value(answer("regulatory_constraints").strip())}
        - Decision-makers: {display_value(answer("decision_makers").strip())}
        - Decision deadline: {display_value(decision_deadline)}
        - Target launch timing: {display_value(answer("launch_deadline").strip())}
        {bfsi_lines}
        ## Location priorities
        {chr(10).join(f"{index}. {priority}" for index, priority in enumerate(priorities, start=1)) if priorities else "No location priorities selected."}
        - Deal-breaker: {display_value(answer("location_deal_breaker").strip())}

        ## Items to confirm
        Review any fields marked “Not provided” with your team. Validate regulatory and data requirements with qualified advisors before making decisions.
        """
    ).strip()


def show_plan_step():
    st.subheader("Tell us about your India plan")
    st.write(
        "The fields start with a fictional demo profile. When profile fields "
        "are blank, clear description clues can suggest values."
    )
    st.text_area(
        "Describe your India plan in your own words",
        key=field("plan_description"),
        height=130,
        placeholder=(
            "Example only — replace with your plan: We are exploring an India "
            "centre to support software engineering and analytics."
        ),
        help="Prefilled illustrative demo text; edit or replace it with your plan.",
        on_change=suggest_profile_from_description,
    )

    st.markdown("#### Company profile")
    company, country = st.columns(2)
    company.text_input(
        "Company name (optional)",
        key=field("company_name"),
        placeholder="Example only — enter your company name",
        help="The prefilled fictional demo company name is editable; replace it as needed.",
    )
    country.text_input(
        "Headquarters country *",
        key=field("headquarters_country"),
        help="Prefilled for the fictional demo; replace it with the company's actual country.",
        on_change=mark_profile_field_edited,
        args=("headquarters_country",),
    )

    industry, other = st.columns(2)
    industry.selectbox(
        "Industry *",
        ["Select an industry", *INDUSTRIES],
        key=field("industry"),
        help="The demo's industry selection is editable.",
        on_change=mark_profile_field_edited,
        args=("industry",),
    )
    if answer("industry") == "Other":
        other.text_input(
            "Tell us the industry",
            key=field("industry_other"),
            placeholder="Example only — describe the actual industry",
        )
    elif answer("industry") == "Select an industry":
        other.caption("Industry suggestions from your description can be changed here.")
    else:
        other.caption("The demo industry selection is editable.")


def show_scope_step():
    st.subheader("What will your GCC do?")
    st.multiselect(
        "Functions you expect the centre to support",
        FUNCTIONS,
        key=field("gcc_functions"),
        help=(
            "The selected functions illustrate the demo scenario. Edit them "
            "to match the company plan; add other functions below."
        ),
    )
    st.text_input(
        "Other function (optional)",
        key=field("functions_other"),
        placeholder="Example only — enter a function not listed above",
    )

    left, right = st.columns(2)
    left.selectbox(
        "Target team size",
        [
            "Select a target range",
            "1-49",
            "50-199",
            "200-499",
            "500-999",
            "1,000-2,499",
            "2,500+",
            "Custom range",
            "Not sure yet",
        ],
        key=field("headcount"),
        help="The demo starts at 200-499; edit this to match the planned team size.",
    )
    right.selectbox(
        "Expected hiring / launch ramp",
        [
            "Select a timeline",
            "Under 12 months",
            "12-24 months",
            "25-36 months",
            "More than 36 months",
            "Not sure yet",
        ],
        key=field("ramp_timeline"),
        help="The demo starts at 25-36 months; edit this to match the intended ramp.",
    )
    if answer("headcount") == "Custom range":
        st.text_input(
            "Describe the target team size",
            key=field("headcount_custom"),
            placeholder="Example only — e.g. approximately 350 roles",
        )

    st.text_area(
        "Important roles and seniority (optional)",
        key=field("roles_seniority"),
        placeholder=(
            "Example only — e.g. senior data engineers and mid-level analysts; "
            "replace with your roles when known."
        ),
        height=95,
    )

    if is_large_headcount():
        st.markdown("#### Large-team hiring follow-up")
        st.caption(
            "For teams of 500 or more, a clearer hiring sequence and delivery plan can help test feasibility."
        )
        left, right = st.columns(2)
        left.selectbox(
            "How do you expect hiring to ramp?",
            [
                "Select an option",
                "Steady hiring each quarter",
                "Small pilot, then accelerate",
                "Large initial hiring wave",
                "Several hiring waves",
                "Not sure yet",
            ],
            key=field("large_hiring_ramp"),
            help="Illustrative demo assumption; change the hiring pattern if it does not fit.",
        )
        right.text_input(
            "Expected hiring capacity or partners (optional)",
            key=field("large_hiring_capacity"),
            placeholder=(
                "Example only — internal hiring team or recruitment partners; "
                "replace with confirmed plans."
            ),
            help="Illustrative demo assumption; replace with confirmed hiring capacity.",
        )
        st.selectbox(
            "How are you thinking about city coverage?",
            [
                "Select an option",
                "One city preferred",
                "Open to multiple cities",
                "Not decided",
            ],
            key=field("large_city_strategy"),
            help="Starts at “Not decided”; no single-city or multi-city strategy is assumed.",
        )


def show_constraints_step():
    st.subheader("What boundaries should the plan account for?")
    left, right = st.columns(2)
    left.selectbox(
        "Budget or cost sensitivity",
        [
            "Select an option",
            "Very cost-sensitive",
            "Balance cost with talent and quality",
            "Prioritize capability and speed",
            "Budget not set yet",
        ],
        key=field("budget_sensitivity"),
        help="Starts at “Budget not set yet”; no approved budget or cost preference is assumed.",
    )
    right.text_input(
        "Budget range or cost notes (optional)",
        key=field("budget_detail"),
        placeholder=(
            "Example format only — e.g. USD 2 million annually; replace with "
            "a confirmed range or leave blank."
        ),
        help="Do not enter an illustrative amount as an approved company budget.",
    )

    st.selectbox(
        "Does your company already have a presence in India?",
        [
            "Select an option",
            "No",
            "Yes",
            "In progress",
            "Not sure",
        ],
        key=field("india_presence"),
        help="The demo assumes no existing India presence; edit this if the scenario differs.",
    )
    if answer("india_presence") in ("Yes", "In progress"):
        st.text_input(
            "Tell us about the existing or planned presence (optional)",
            key=field("india_presence_detail"),
            placeholder=(
                "Example only — describe an existing entity, team, or vendor "
                "if confirmed."
            ),
        )

    st.text_area(
        "Regulatory, data, security, or other constraints (optional)",
        key=field("regulatory_constraints"),
        height=105,
        placeholder=(
            "Example topics only — data residency, security, or connectivity. "
            "Enter your actual requirements or leave blank if unknown."
        ),
        help="Keep infrastructure and regulatory constraints here, not under decision-makers.",
    )

    if is_bfsi():
        st.markdown("#### BFSI regulatory and data follow-up")
        st.caption(
            "These prompts help capture topics to investigate; they are not regulatory advice."
        )
        st.multiselect(
            "Which regulatory areas may need review?",
            [
                "Banking regulation",
                "Insurance regulation",
                "Securities / capital markets",
                "Payments",
                "Customer due diligence / AML",
                "Not sure yet",
            ],
            key=field("bfsi_regulations"),
            help="No topics are preselected; select only areas relevant to your plan.",
        )
        st.text_input(
            "Other regulatory area (optional)",
            key=field("bfsi_regulations_other"),
            placeholder="Example only — describe another area to review",
        )
        st.selectbox(
            "Does the plan involve data that may need to remain in India?",
            [
                "Select an option",
                "Yes",
                "No",
                "Under review",
                "Not sure yet",
            ],
            key=field("bfsi_data_residency"),
            help="Starts at “Not sure yet”; this is not a conclusion about your data.",
        )
        st.text_input(
            "Sensitive data or handling notes (optional)",
            key=field("bfsi_data_detail"),
            placeholder=(
                "Example topics only — customer or payment records; enter "
                "details only if relevant."
            ),
        )

    st.markdown("#### People and timing")
    st.text_area(
        "Who will make or influence the decision? (optional)",
        key=field("decision_makers"),
        height=80,
        placeholder=(
            "Example only — CEO, CFO, Head of India Expansion. Replace with "
            "your actual decision-makers or leave blank if unknown."
        ),
        help="This field is for decision owners and influencers, not infrastructure requirements.",
    )
    date_col, launch_col = st.columns(2)
    date_col.date_input(
        "Decision deadline (optional)",
        key=field("decision_deadline"),
        min_value=date.today(),
        help="The prefilled date is illustrative demo data and can be changed or cleared.",
    )
    launch_col.text_input(
        "Target launch date or timing (optional)",
        key=field("launch_deadline"),
        placeholder="Example only — e.g. Q2 2027; replace with your target timing.",
        help="The prefilled launch objective is illustrative and editable; no launch date is assumed.",
    )


def show_location_step():
    st.subheader("What matters most in a location?")
    st.write(
        "Rank up to four priorities. If you choose the same priority twice, the later rank will be cleared."
    )
    ranks = ("priority_1", "priority_2", "priority_3", "priority_4")
    for index, key in enumerate(ranks, start=1):
        options = ["Select a priority", *LOCATION_PRIORITIES]
        st.selectbox(
            f"Priority {index}",
            options,
            key=field(key),
            on_change=normalize_rankings,
        )

    st.text_area(
        "Location deal-breaker (optional)",
        key=field("location_deal_breaker"),
        height=85,
        placeholder=(
            "Example only — a confirmed travel, continuity, or operating "
            "requirement; leave blank if none is known."
        ),
    )


def show_review_step():
    st.subheader("Review your India plan")
    st.write("Check the details below. Use Back to change any answer.")

    profile_col, scope_col = st.columns(2)
    with profile_col:
        st.markdown("#### Company profile")
        st.write(f"**Company:** {display_value(answer('company_name').strip())}")
        st.write(
            f"**Headquarters:** {display_value(answer('headquarters_country').strip())}"
        )
        st.write(f"**Industry:** {resolved_industry()}")
        st.write(
            f"**Description:** {display_value(answer('plan_description').strip())}"
        )
    with scope_col:
        st.markdown("#### Scope and hiring")
        st.write(f"**Functions:** {display_value(resolved_functions())}")
        headcount = (
            answer("headcount_custom").strip()
            if answer("headcount") == "Custom range"
            else answer("headcount")
        )
        st.write(f"**Target team:** {display_value(headcount)}")
        st.write(f"**Ramp:** {display_value(answer('ramp_timeline'))}")
        st.write(
            f"**Roles and seniority:** {display_value(answer('roles_seniority').strip())}"
        )

    st.markdown("#### Budget, constraints, and decisions")
    st.write(
        f"**Cost sensitivity:** {display_value(answer('budget_sensitivity'))} · "
        f"**India presence:** {display_value(answer('india_presence'))}"
    )
    st.write(
        f"**Constraints:** {display_value(answer('regulatory_constraints').strip())}"
    )
    st.write(
        f"**Decision-makers:** {display_value(answer('decision_makers').strip())}"
    )
    st.write(
        f"**Decision deadline:** {display_value(answer('decision_deadline'))} · "
        f"**Launch timing:** {display_value(answer('launch_deadline').strip())}"
    )
    if is_bfsi():
        st.info("BFSI-specific regulatory and data follow-up questions are included.")
    if is_large_headcount():
        st.info("Large-team hiring and city-capacity follow-up questions are included.")

    st.markdown("#### Location priorities")
    priorities = ranked_priorities()
    if priorities:
        for index, priority in enumerate(priorities, start=1):
            st.write(f"{index}. {priority}")
    else:
        st.write("No priorities selected.")
    st.write(
        f"**Deal-breaker:** {display_value(answer('location_deal_breaker').strip())}"
    )

    st.divider()
    st.button(
        "Generate my India entry brief",
        type="primary",
        use_container_width=True,
        on_click=generate_entry_brief,
    )
    if st.session_state.generated_brief:
        st.success("Your brief is ready.")
        st.markdown(st.session_state.generated_brief)
        st.download_button(
            "Download PDF Report",
            data=st.session_state.generated_pdf,
            file_name="india_gcc_entry_brief.pdf",
            mime="application/pdf",
        )
        st.button(
            "Open Strategy Workspace",
            type="primary",
            on_click=open_strategy_workspace,
        )


def render_navigation():
    st.divider()
    previous, _, next_col = st.columns([1, 3, 1])
    if st.session_state.step > 0:
        previous.button(
            "← Back",
            use_container_width=True,
            on_click=go_back,
        )
    if st.session_state.step < len(STEPS) - 1:
        next_col.button(
            "Next →",
            type="primary",
            use_container_width=True,
            on_click=go_next,
        )
    if st.session_state.validation_error:
        st.error(st.session_state.validation_error)


def generate_entry_brief():
    sync_widget_values()
    st.session_state.generated_brief = build_entry_brief()
    st.session_state.generated_pdf = build_pdf_report(st.session_state.generated_brief)


def open_strategy_workspace():
    sync_widget_values()
    st.session_state.screen = "workspace"


def reset_intake():
    for key in FIELD_DEFAULTS:
        st.session_state.pop(widget_key(key), None)
    st.session_state.pop("intake_edited_headquarters_country", None)
    st.session_state.pop("intake_edited_industry", None)
    st.session_state.intake_answers = deepcopy(FIELD_DEFAULTS)
    st.session_state.step = 0
    st.session_state.generated_brief = ""
    st.session_state.generated_pdf = b""
    st.session_state.validation_error = ""
    st.session_state.screen = "intake"
    st.session_state.workspace_section = "Overview"


def main():
    initialize_state()
    if st.session_state.screen == "workspace":
        render_workspace(st.session_state.intake_answers)
        return

    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background-color: #f1f3f6;
            color: #253247;
        }
        [data-testid="stHeader"] {
            background-color: #f1f3f6;
        }
        .block-container { max-width: 1050px; padding-top: 2rem; padding-bottom: 3rem; }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
            color: #14243a;
        }
        .stApp p,
        .stApp li,
        .stApp label,
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stMarkdownContainer"] {
            color: #253247;
        }
        .stApp [data-testid="stCaptionContainer"] {
            color: #4b5563;
        }
        .stApp a {
            color: #005a9c;
            text-decoration: underline;
        }
        .eyebrow {
            color: #a5f3e5;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .hero {
            padding: 1.5rem 1.7rem;
            border-radius: 18px;
            background: linear-gradient(120deg,#10243e,#14535b);
            color: #ffffff;
            margin: .6rem 0 1.2rem;
        }
        .stApp .hero h1 { color: #ffffff; margin: 0 0 .35rem 0; }
        .stApp .hero p { color: #e5eef2; margin: 0; }
        .prototype-notice {
            padding: .9rem 1rem;
            border: 1px solid #52759a;
            border-left: 5px solid #005a9c;
            border-radius: .5rem;
            background: #e7f1fc;
            color: #173b68;
            margin: .75rem 0;
        }
        .prototype-notice strong, .prototype-notice p { color: #173b68; }
        .stApp input,
        .stApp textarea,
        .stApp [data-baseweb="input"],
        .stApp [data-baseweb="textarea"],
        .stApp [data-baseweb="select"] > div,
        .stApp [data-baseweb="datepicker"] {
            background-color: #ffffff;
            color: #253247;
            border-color: #64748b;
        }
        .stApp input,
        .stApp textarea {
            -webkit-text-fill-color: #253247;
        }
        .stApp input::placeholder,
        .stApp textarea::placeholder {
            color: #526173;
            opacity: 1;
            -webkit-text-fill-color: #526173;
        }
        .stApp [data-baseweb="select"] div,
        .stApp [data-baseweb="select"] span {
            color: #253247;
        }
        .stApp [data-baseweb="select"] > div {
            border: 1px solid #64748b;
        }
        .stApp [data-testid="stTextInput"] input,
        .stApp [data-testid="stTextArea"] textarea,
        .stApp [data-testid="stDateInput"] input {
            background-color: #ffffff;
            color: #253247;
            border: 1px solid #64748b;
        }
        .stApp [data-baseweb="input"]:focus-within,
        .stApp [data-baseweb="textarea"]:focus-within,
        .stApp [data-baseweb="select"]:focus-within,
        .stApp input:focus,
        .stApp textarea:focus {
            border-color: #005a9c;
            outline: 2px solid #005a9c;
            outline-offset: 1px;
        }
        .stApp [data-baseweb="tag"] {
            background-color: #dceafb;
            color: #173b68;
        }
        [role="listbox"], [role="option"] {
            background-color: #ffffff;
            color: #253247;
        }
        [role="option"]:hover, [role="option"][aria-selected="true"] {
            background-color: #dceafb;
            color: #173b68;
        }
        .stApp button[kind="primary"],
        .stApp [data-testid="stBaseButton-primary"] {
            background-color: #005a9c;
            color: #ffffff;
            border: 1px solid #004574;
        }
        .stApp button[kind="primary"]:hover,
        .stApp [data-testid="stBaseButton-primary"]:hover {
            background-color: #004574;
            color: #ffffff;
            border-color: #00385c;
        }
        .stApp button[kind="secondary"],
        .stApp [data-testid="stBaseButton-secondary"] {
            background-color: #ffffff;
            color: #173b68;
            border: 1px solid #526173;
        }
        .stApp button[kind="secondary"]:hover,
        .stApp [data-testid="stBaseButton-secondary"]:hover {
            background-color: #e7f1fc;
            color: #14243a;
            border-color: #005a9c;
        }
        .stApp button:focus-visible {
            outline: 3px solid #005a9c;
            outline-offset: 2px;
        }
        [data-testid="stProgressBarTrack"] {
            background-color: #c6ced8;
            border: 1px solid #64748b;
            border-radius: 999px;
        }
        [data-testid="stProgressBarTrack"] > div {
            background-color: #005a9c;
        }
        .stApp [data-testid="stAlert"] {
            color: #173b68;
            border: 1px solid #52759a;
            background-color: #e7f1fc;
        }
        .stApp [data-testid="stAlert"] p,
        .stApp [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
            color: #173b68;
        }
        .stApp [data-testid="stAlert"] svg {
            fill: #173b68;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {
            color: #7f1d1d;
            border-color: #9b1c1c;
            background-color: #fdecec;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) p,
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) [data-testid="stMarkdownContainer"] {
            color: #7f1d1d;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) {
            color: #14532d;
            border-color: #287044;
            background-color: #eaf7ee;
        }
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) p,
        .stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) [data-testid="stMarkdownContainer"] {
            color: #14532d;
        }
        .stApp hr { border-color: #9aa5b1; }
        </style>
        <div class="hero">
          <div class="eyebrow">India GCC Atlas · Intake</div>
          <h1>Plan your India GCC</h1>
          <p>A guided intake to organize your goals, constraints, and location priorities.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="prototype-notice" role="note">
          <strong>Rule-based prototype — not connected to an AI service.</strong>
          <p>Profile suggestions use simple keyword matching. Your answers are not sent to an AI provider.</p>
          <p><strong>Illustrative demo:</strong> the prefilled NovaTech scenario is fictional; replace or edit any answer. It is not market research or independently verified company information.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Answers are held in this active Streamlit session. A new session or server restart may clear them."
    )
    with st.expander("Reset demo"):
        st.caption(
            "Reset clears current answers and the generated report, restoring "
            "the fictional NovaTech demo profile. All answers remain editable."
        )
        st.button(
            "Reset to demo profile",
            key="reset_intake",
            on_click=reset_intake,
        )

    step = st.session_state.step
    st.caption(f"STEP {step + 1} OF {len(STEPS)} · {STEPS[step]}")
    st.progress((step + 1) / len(STEPS))

    renderers = [
        show_plan_step,
        show_scope_step,
        show_constraints_step,
        show_location_step,
        show_review_step,
    ]
    renderers[step]()
    render_navigation()


if __name__ == "__main__":
    main()
