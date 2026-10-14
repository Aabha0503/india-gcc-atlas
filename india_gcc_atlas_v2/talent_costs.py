"""Synthetic talent and cost demo data loading and calculation helpers."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


DEMO_DIRECTORY = (
    Path(__file__).parent / "data" / "india_gcc_talent_cost_demo_pack"
)

TABLES: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], str | None]] = {
    "role_mix": (
        "demo_role_mix.csv",
        (
            "role_id", "role", "planned_headcount", "junior_share",
            "mid_share", "senior_share", "is_synthetic", "note",
        ),
        ("planned_headcount", "junior_share", "mid_share", "senior_share"),
        "is_synthetic",
    ),
    "salary_ranges": (
        "demo_city_role_salary_ranges.csv",
        (
            "city", "state", "role", "seniority", "salary_low_lpa",
            "salary_central_lpa", "salary_high_lpa", "currency",
            "salary_unit", "evidence_status", "source_id",
            "geographic_scope", "as_of_date", "is_synthetic", "caveat",
        ),
        ("salary_low_lpa", "salary_central_lpa", "salary_high_lpa"),
        "is_synthetic",
    ),
    "state_city_mapping": (
        "demo_state_city_mapping.csv",
        ("state", "candidate_city", "mapping_status", "caveat", "is_synthetic"),
        (),
        "is_synthetic",
    ),
    "headcount_ramp": (
        "demo_headcount_ramp.csv",
        (
            "period", "share_of_steady_state",
            "illustrative_end_of_period_headcount", "note", "is_synthetic",
        ),
        ("share_of_steady_state", "illustrative_end_of_period_headcount"),
        "is_synthetic",
    ),
    "cost_assumptions": (
        "demo_cost_assumptions.csv",
        (
            "assumption_id", "value", "unit", "caveat",
            "evidence_status", "is_synthetic",
        ),
        ("value",),
        "is_synthetic",
    ),
    "hiring_routes": (
        "demo_hiring_route_costs.csv",
        (
            "hiring_route", "pricing_basis", "cost_low", "cost_central",
            "cost_high_or_fee_rate", "caveat", "evidence_status",
            "is_synthetic",
        ),
        ("cost_low", "cost_central", "cost_high_or_fee_rate"),
        "is_synthetic",
    ),
    "setup_costs": (
        "demo_one_time_and_tools_costs.csv",
        (
            "cost_item", "low", "central", "high", "unit", "caveat",
            "evidence_status", "is_synthetic",
        ),
        ("low", "central", "high"),
        "is_synthetic",
    ),
    "budget_template": (
        "budget_input_template.csv",
        ("budget_field", "default_value", "unit", "note", "is_synthetic"),
        (),
        None,
    ),
    "evidence_register": (
        "demo_evidence_register.csv",
        ("data_domain", "status", "interpretation"),
        (),
        None,
    ),
}

ROW_REQUIRED_FIELDS = {
    "role_mix": ("role", "note"),
    "salary_ranges": (
        "city", "state", "role", "seniority", "currency", "salary_unit",
        "evidence_status", "source_id", "geographic_scope", "as_of_date",
    ),
    "state_city_mapping": ("state", "candidate_city", "mapping_status", "caveat"),
    "headcount_ramp": ("period", "note"),
    "cost_assumptions": ("assumption_id", "unit", "caveat", "evidence_status"),
    "hiring_routes": (
        "hiring_route", "pricing_basis", "caveat", "evidence_status",
    ),
    "setup_costs": ("cost_item", "unit", "caveat", "evidence_status"),
    "budget_template": ("budget_field", "unit", "note"),
    "evidence_register": ("data_domain", "status", "interpretation"),
}

SYNTHETIC_EVIDENCE_TABLES = {
    "salary_ranges",
    "cost_assumptions",
    "hiring_routes",
    "setup_costs",
}

SCENARIOS = ("low", "central", "high")
SENIORITIES = ("Junior", "Mid", "Senior")
SYNTHETIC_LABEL = "Illustrative demo assumption — not verified market data"


def _number(value: Any, field: str, *, allow_blank: bool = False) -> float | None:
    if value is None or str(value).strip() == "":
        if allow_blank:
            return None
        raise ValueError(f"{field} is blank")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be numeric") from error
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def load_demo_pack(directory: Path = DEMO_DIRECTORY) -> dict[str, Any]:
    """Read and validate the standalone demo pack without touching production data."""
    result: dict[str, Any] = {"errors": []}
    errors: list[str] = result["errors"]
    for table_name, (filename, required, numeric, synthetic_field) in TABLES.items():
        path = directory / filename
        if not path.is_file():
            result[table_name] = []
            errors.append(f"Missing demo file: {filename}")
            continue
        try:
            with path.open(encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                if not reader.fieldnames:
                    result[table_name] = []
                    errors.append(f"{filename} has no header row.")
                    continue
                missing = [column for column in required if column not in reader.fieldnames]
                if missing:
                    result[table_name] = []
                    errors.append(
                        f"{filename} is missing required columns: {', '.join(missing)}"
                    )
                    continue
                rows: list[dict[str, Any]] = []
                for line, raw_row in enumerate(reader, start=2):
                    if None in raw_row:
                        errors.append(
                            f"{filename}, row {line}: unexpected extra CSV values; row omitted."
                        )
                        continue
                    row: dict[str, Any] = {
                        key: (value or "").strip()
                        for key, value in raw_row.items()
                        if key is not None
                    }
                    row_valid = True
                    missing_values = [
                        field for field in ROW_REQUIRED_FIELDS[table_name]
                        if not row.get(field)
                    ]
                    if missing_values:
                        errors.append(
                            f"{filename}, row {line}: missing "
                            f"{', '.join(missing_values)}; row omitted."
                        )
                        row_valid = False
                    if synthetic_field and row.get(synthetic_field, "").casefold() not in (
                        "true", "1", "yes"
                    ):
                        errors.append(
                            f"{filename}, row {line}: {synthetic_field} must be true; row omitted."
                        )
                        row_valid = False
                    if (
                        table_name in SYNTHETIC_EVIDENCE_TABLES
                        and row.get("evidence_status", "").casefold()
                        != "demo_only_synthetic"
                    ):
                        errors.append(
                            f"{filename}, row {line}: evidence_status must be "
                            "DEMO_ONLY_SYNTHETIC; row omitted."
                        )
                        row_valid = False
                    for field in numeric:
                        try:
                            parsed = _number(
                                row.get(field),
                                f"{filename}, row {line}, {field}",
                                allow_blank=(
                                    table_name in ("salary_ranges", "cost_assumptions")
                                ),
                            )
                        except ValueError as error:
                            errors.append(f"{error}; row omitted.")
                            row_valid = False
                            break
                        row[field] = parsed
                    if row_valid:
                        rows.append(row)
                result[table_name] = rows
        except (OSError, UnicodeError, csv.Error) as error:
            result[table_name] = []
            errors.append(f"Could not read {filename}: {error}")
    return result


def parse_headcount(answer: Any) -> tuple[int | None, str]:
    """Turn a numeric value or a simple intake range into an explicit planning count."""
    text = str(answer or "").strip().replace(",", "")
    if not text or text.casefold() in ("not sure yet", "select a target range"):
        return None, "The intake does not contain a usable headcount."
    if text.isdigit():
        return int(text), "Exact headcount from intake."
    parts = text.replace("–", "-").split("-")
    if len(parts) == 2:
        try:
            low, high = (int(part.strip()) for part in parts)
        except ValueError:
            return None, f"Could not interpret intake headcount {text!r}."
        if low < 0 or high < low:
            return None, f"Could not interpret intake headcount {text!r}."
        midpoint = int(round((low + high) / 2))
        return midpoint, (
            f"Planning count initialized from the midpoint of intake range "
            f"{low:,}-{high:,}; edit it to your planning value."
        )
    return None, f"Could not interpret intake headcount {text!r}."


def default_role_mix(role_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(float(row["planned_headcount"]) for row in role_rows)
    if total <= 0:
        return []
    return [
        {
            "Role": row["role"],
            "Role share (%)": float(row["planned_headcount"]) / total * 100,
            "Junior share (%)": float(row["junior_share"]) * 100,
            "Mid share (%)": float(row["mid_share"]) * 100,
            "Senior share (%)": float(row["senior_share"]) * 100,
        }
        for row in role_rows
    ]


def _assumption_values(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        row["assumption_id"]: float(row["value"])
        for row in rows
        if row.get("value") is not None
    }


def _salary_index(
    salary_rows: list[dict[str, Any]],
    city: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (row["role"].casefold(), row["seniority"].casefold()): row
        for row in salary_rows
        if row["city"].casefold() == city.casefold()
    }


def _validate_role_mix(
    role_mix: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, row in enumerate(role_mix, start=1):
        role = str(row.get("Role", "")).strip()
        if not role:
            errors.append(f"Role mix row {index} needs a role name.")
            continue
        try:
            role_share = _number(row.get("Role share (%)"), "Role share")
            seniority_shares = {
                level: _number(row.get(f"{level} share (%)"), f"{level} share")
                for level in SENIORITIES
            }
        except ValueError as error:
            errors.append(str(error))
            continue
        if role_share is None or role_share < 0:
            errors.append(f"{role} role share must be zero or greater.")
            continue
        if any(value is None or value < 0 for value in seniority_shares.values()):
            errors.append(f"{role} seniority shares must be zero or greater.")
            continue
        if abs(sum(seniority_shares.values()) - 100) > 0.05:
            errors.append(f"{role} seniority shares must total 100%.")
            continue
        normalized.append(
            {
                "role": role,
                "role_share": role_share / 100,
                "seniority_shares": {
                    level: value / 100
                    for level, value in seniority_shares.items()
                },
            }
        )
    if not normalized:
        errors.append("Add at least one valid role to the role mix.")
    elif abs(sum(row["role_share"] for row in normalized) - 1) > 0.0005:
        errors.append("Role shares must total 100%.")
    return normalized, errors


def _salary_totals(
    role_mix: list[dict[str, Any]],
    salary_index: dict[tuple[str, str], dict[str, Any]],
    headcount: float,
) -> tuple[dict[str, float] | None, list[str]]:
    totals = {scenario: 0.0 for scenario in SCENARIOS}
    missing: list[str] = []
    for role in role_mix:
        for seniority, share in role["seniority_shares"].items():
            employees = headcount * role["role_share"] * share
            if employees <= 0:
                continue
            salary = salary_index.get(
                (role["role"].casefold(), seniority.casefold())
            )
            if salary is None:
                missing.append(f"{role['role']} · {seniority}")
                continue
            values = {
                "low": salary.get("salary_low_lpa"),
                "central": salary.get("salary_central_lpa"),
                "high": salary.get("salary_high_lpa"),
            }
            if any(value is None for value in values.values()):
                missing.append(f"{role['role']} · {seniority} (salary range incomplete)")
                continue
            if not (
                values["low"] <= values["central"] <= values["high"]
            ):
                missing.append(f"{role['role']} · {seniority} (salary range invalid)")
                continue
            for scenario in SCENARIOS:
                totals[scenario] += employees * float(values[scenario]) * 100_000
    return (None if missing else totals), sorted(set(missing))


def _route_per_hire(
    route: dict[str, Any],
    average_salary_inr: dict[str, float],
) -> dict[str, float]:
    low = float(route["cost_low"])
    central = float(route["cost_central"])
    third = float(route["cost_high_or_fee_rate"])
    basis = route["pricing_basis"].casefold()
    if "percent" in basis:
        return {
            scenario: average_salary_inr[scenario] * rate
            for scenario, rate in zip(SCENARIOS, (low, central, third))
        }
    if "fixed inr per hire plus salary fee share" in basis:
        fee_share = third
        return {
            "low": low + average_salary_inr["low"] * fee_share,
            "central": central + average_salary_inr["central"] * fee_share,
            "high": central + average_salary_inr["high"] * fee_share,
        }
    return {"low": low, "central": central, "high": third}


def _cost_item(
    rows: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    return next(
        (row for row in rows if row["cost_item"].casefold() == name.casefold()),
        None,
    )


def calculate_cost_scenarios(
    *,
    city: str,
    headcount: int,
    role_mix: list[dict[str, Any]],
    salary_rows: list[dict[str, Any]],
    ramp_rows: list[dict[str, Any]],
    assumption_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
    setup_rows: list[dict[str, Any]],
    preferred_route: str,
    existing_headcount: int = 0,
) -> dict[str, Any]:
    """Calculate demo-only cost scenarios; all returned amounts are INR."""
    output: dict[str, Any] = {
        "valid": False,
        "errors": [],
        "missing_salary": [],
        "city": city,
        "headcount": headcount,
        "label": SYNTHETIC_LABEL,
    }
    errors: list[str] = output["errors"]
    normalized_mix, mix_errors = _validate_role_mix(role_mix)
    errors.extend(mix_errors)
    if headcount <= 0:
        errors.append("Target headcount must be greater than zero.")
    if existing_headcount < 0 or existing_headcount > headcount:
        errors.append("Existing India headcount must be at least zero and not exceed target headcount.")
    if not ramp_rows:
        errors.append("No phased headcount ramp is available.")
    elif not any(row["period"].casefold() == "year 1" for row in ramp_rows):
        errors.append("The demo ramp does not contain a Year 1 phase.")
    else:
        parsed_ramp: list[tuple[int, float]] = []
        for row in ramp_rows:
            try:
                year = int(row["period"].casefold().replace("year ", ""))
                share = float(row["share_of_steady_state"])
            except (TypeError, ValueError):
                errors.append(
                    f"Invalid ramp row {row.get('period', 'unknown')!r}; "
                    "year and share must be numeric."
                )
                continue
            if year < 1 or not 0 <= share <= 1:
                errors.append("Ramp years must be positive and shares between 0 and 1.")
                continue
            parsed_ramp.append((year, share))
        parsed_ramp.sort()
        if len({year for year, _ in parsed_ramp}) != len(parsed_ramp):
            errors.append("Ramp periods must not be duplicated.")
        if any(
            parsed_ramp[index][1] > parsed_ramp[index + 1][1]
            for index in range(len(parsed_ramp) - 1)
        ):
            errors.append("Ramp shares must not decrease between years.")
        if parsed_ramp and parsed_ramp[-1][1] != 1:
            errors.append("The final ramp year must reach 100% of target headcount.")

    assumptions = _assumption_values(assumption_rows)
    required_assumptions = (
        "employer_on_cost_rate",
        "annual_salary_inflation_rate",
        "annual_attrition_rate",
    )
    for assumption_id in required_assumptions:
        if assumption_id not in assumptions:
            errors.append(f"Missing assumption: {assumption_id}.")
    route = next(
        (row for row in route_rows if row["hiring_route"] == preferred_route),
        None,
    )
    if route is None:
        errors.append(f"No demo pricing is available for route {preferred_route!r}.")

    if errors:
        return output

    year1_ramp = next(
        row for row in ramp_rows if row["period"].casefold() == "year 1"
    )
    year1_share = float(year1_ramp["share_of_steady_state"])
    if not 0 <= year1_share <= 1:
        errors.append("Year 1 ramp share must be between 0 and 1.")
        return output
    existing = float(existing_headcount)
    net_additions = headcount - existing
    year1_end_headcount = existing + net_additions * year1_share
    year1_average_headcount = (existing + year1_end_headcount) / 2
    attrition_rate = assumptions["annual_attrition_rate"]
    year1_backfills = year1_average_headcount * attrition_rate
    year1_gross_hires = (year1_end_headcount - existing) + year1_backfills
    steady_backfills = headcount * attrition_rate

    salary_index = _salary_index(salary_rows, city)
    steady_base, missing_salary = _salary_totals(
        normalized_mix, salary_index, float(headcount)
    )
    output["missing_salary"] = missing_salary
    if steady_base is None:
        errors.append(
            "Salary totals are unavailable because one or more selected "
            "city/role/seniority salary ranges are missing or incomplete."
        )
        return output

    average_salary = {
        scenario: steady_base[scenario] / headcount
        for scenario in SCENARIOS
    }
    route_per_hire = _route_per_hire(route, average_salary)
    on_cost_rate = assumptions["employer_on_cost_rate"]
    inflation_rate = assumptions["annual_salary_inflation_rate"]
    if on_cost_rate < 0 or inflation_rate < 0 or attrition_rate < 0:
        errors.append("Cost rates must not be negative.")
        return output
    inflation_years = max(
        int(row["period"].split()[-1]) - 1 for row in ramp_rows
    )
    steady_inflation_factor = (1 + inflation_rate) ** inflation_years

    fixed_setup: dict[str, float] = {scenario: 0.0 for scenario in SCENARIOS}
    for name in ("Office fit-out", "Legal entity and professional setup"):
        row = _cost_item(setup_rows, name)
        if row is None:
            errors.append(f"Missing one-time setup assumption: {name}.")
            continue
        for scenario in SCENARIOS:
            fixed_setup[scenario] += float(row[scenario])
    onboarding = _cost_item(setup_rows, "Onboarding and equipment per employee")
    if onboarding is None:
        errors.append("Missing onboarding and equipment per-employee assumption.")
        return output
    if errors:
        return output

    base_payroll = steady_base
    loaded_payroll = {
        scenario: steady_base[scenario] * (1 + on_cost_rate)
        for scenario in SCENARIOS
    }
    year1_base_payroll = {
        scenario: steady_base[scenario] * year1_average_headcount / headcount
        for scenario in SCENARIOS
    }
    year1_loaded_payroll = {
        scenario: year1_base_payroll[scenario] * (1 + on_cost_rate)
        for scenario in SCENARIOS
    }
    steady_state_loaded_payroll = {
        scenario: loaded_payroll[scenario] * steady_inflation_factor
        for scenario in SCENARIOS
    }
    year1_recruitment = {
        scenario: route_per_hire[scenario] * year1_gross_hires
        for scenario in SCENARIOS
    }
    steady_recruitment = {
        scenario: route_per_hire[scenario] * steady_backfills
        for scenario in SCENARIOS
    }
    year1_onboarding = {
        scenario: float(onboarding[scenario]) * year1_gross_hires
        for scenario in SCENARIOS
    }
    steady_onboarding = {
        scenario: float(onboarding[scenario]) * steady_backfills
        for scenario in SCENARIOS
    }
    one_time_setup = {
        scenario: fixed_setup[scenario] + year1_onboarding[scenario]
        for scenario in SCENARIOS
    }
    year1_total = {
        scenario: (
            year1_loaded_payroll[scenario]
            + year1_recruitment[scenario]
            + one_time_setup[scenario]
        )
        for scenario in SCENARIOS
    }
    steady_state_total = {
        scenario: (
            steady_state_loaded_payroll[scenario]
            + steady_recruitment[scenario]
            + steady_onboarding[scenario]
        )
        for scenario in SCENARIOS
    }
    output.update(
        {
            "valid": True,
            "on_cost_rate": on_cost_rate,
            "inflation_rate": inflation_rate,
            "attrition_rate": attrition_rate,
            "time_to_fill_days": assumptions.get("average_time_to_fill_days"),
            "year1_end_headcount": year1_end_headcount,
            "year1_average_headcount": year1_average_headcount,
            "year1_net_hires": year1_end_headcount - existing,
            "year1_backfills": year1_backfills,
            "year1_gross_hires": year1_gross_hires,
            "steady_backfills": steady_backfills,
            "steady_inflation_years": inflation_years,
            "route": preferred_route,
            "route_pricing_basis": route["pricing_basis"],
            "route_caveat": route["caveat"],
            "route_cost_per_hire": route_per_hire,
            "base_payroll": base_payroll,
            "loaded_payroll": loaded_payroll,
            "year1_base_payroll": year1_base_payroll,
            "year1_loaded_payroll": year1_loaded_payroll,
            "year1_recruitment": year1_recruitment,
            "year1_onboarding": year1_onboarding,
            "fixed_setup": fixed_setup,
            "one_time_setup": one_time_setup,
            "year1_total": year1_total,
            "steady_state_loaded_payroll": steady_state_loaded_payroll,
            "steady_recruitment": steady_recruitment,
            "steady_onboarding": steady_onboarding,
            "steady_state_total": steady_state_total,
            "average_salary_per_hire": average_salary,
            "linked_in_license_reference": (
                _cost_item(setup_rows, "LinkedIn sourcing licence")
            ),
        }
    )
    return output


def budget_comparison(
    budget: float | None, cost: float | None
) -> dict[str, float | str | None]:
    if budget is None or cost is None:
        return {
            "status": "Insufficient budget data",
            "budget": budget,
            "cost": cost,
            "headroom": None,
        }
    headroom = budget - cost
    return {
        "status": "Within budget" if headroom >= 0 else "Over budget",
        "budget": budget,
        "cost": cost,
        "headroom": headroom,
    }
