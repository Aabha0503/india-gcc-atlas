"""CSV-backed policy review and shared service-provider directory."""

from __future__ import annotations

import csv
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


POLICY_DATA_DIRECTORY = (
    Path(__file__).parent / "data" / "policies_ecosystem_demo"
)

POLICY_COLUMNS = (
    "policy_id",
    "state",
    "policy_name",
    "policy_type",
    "issuing_department",
    "effective_date",
    "expiry_date",
    "policy_url",
    "document_url",
    "policy_exists_status",
    "eligibility_ladder_stage",
    "policy_relevance_to_intake",
    "benefits_summary",
    "eligibility_criteria",
    "application_process",
    "deadlines",
    "setup_model_required_or_assumed",
    "setup_model_verification_status",
    "company_eligibility_status",
    "city_or_location_scope",
    "source_status",
    "verification_status",
    "last_checked_date",
    "next_research_action",
    "notes",
    "reviewer_notes",
    "eligibility_confirmation_source_url",
)
CHECKLIST_COLUMNS = (
    "policy_id",
    "checklist_item",
    "question_to_verify",
    "status",
    "evidence_required",
    "setup_model_required_or_assumed",
    "reviewer_notes",
    "source_url",
    "last_checked_date",
)
SOURCE_COLUMNS = (
    "source_id",
    "state",
    "source_title",
    "source_type",
    "url",
    "publication_date",
    "accessed_date",
    "what_it_supports",
    "limitations",
    "verification_status",
    "policy_id",
)
PROVIDER_COLUMNS = (
    "provider_id",
    "provider_name",
    "provider_category",
    "services_offered",
    "cities_served",
    "relevant_experience",
    "pricing_or_quote",
    "pricing_basis",
    "due_diligence_status",
    "source_url",
    "last_checked_date",
    "verification_status",
    "notes",
)

ELIGIBILITY_STAGES = (
    "Policy exists",
    "Potentially relevant",
    "Eligibility assessed",
    "Eligibility confirmed",
)
CHECKLIST_STATUSES = (
    "Needs verification",
    "In progress",
    "Evidence located",
    "Reviewed",
    "Not applicable",
)
COMPANY_ELIGIBILITY_STATUSES = (
    "Not assessed",
    "In assessment",
    "Unresolved",
    "Not eligible",
    "Eligibility confirmed",
)
PROVIDER_CATEGORIES = (
    "Legal and tax advisers",
    "EOR and HR providers",
    "Recruitment partners",
    "Real-estate partners",
    "Cybersecurity and IT providers",
    "Government investment facilitation",
)

_POLICY_REVIEW_FIELDS = {
    "document_url",
    "eligibility_ladder_stage",
    "policy_relevance_to_intake",
    "company_eligibility_status",
    "setup_model_required_or_assumed",
    "setup_model_verification_status",
    "verification_status",
    "reviewer_notes",
    "eligibility_confirmation_source_url",
    "last_checked_date",
}
_CHECKLIST_REVIEW_FIELDS = {
    "status",
    "setup_model_required_or_assumed",
    "reviewer_notes",
    "source_url",
    "last_checked_date",
}


class PolicyDataError(ValueError):
    """Raised when policy review data is malformed or a save is unsafe."""


def _read_csv(
    directory: Path,
    filename: str,
    required_columns: tuple[str, ...],
    errors: list[str],
) -> list[dict[str, str]]:
    path = directory / filename
    if not path.is_file():
        errors.append(f"Missing policy ecosystem data file: {filename}")
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fields = reader.fieldnames
            if not fields:
                errors.append(f"{filename} has no header row.")
                return []
            if len(fields) != len(set(fields)):
                errors.append(f"{filename} has duplicate column names.")
                return []
            missing = [column for column in required_columns if column not in fields]
            if missing:
                errors.append(
                    f"{filename} is missing required columns: " + ", ".join(missing)
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


def load_policy_workspace(
    data_directory: Path | str | None = None,
) -> dict[str, Any]:
    """Load the policy, checklist, source, and shared provider CSV tables."""
    directory = Path(data_directory) if data_directory else POLICY_DATA_DIRECTORY
    errors: list[str] = []
    policies = _read_csv(directory, "state_policies.csv", POLICY_COLUMNS, errors)
    checklist = _read_csv(
        directory, "policy_eligibility_checklist.csv", CHECKLIST_COLUMNS, errors
    )
    sources = _read_csv(directory, "policy_sources.csv", SOURCE_COLUMNS, errors)
    providers = _read_csv(
        directory, "service_providers.csv", PROVIDER_COLUMNS, errors
    )

    policy_ids: set[str] = set()
    valid_policies: list[dict[str, str]] = []
    for line_number, policy in enumerate(policies, start=2):
        policy_id = policy.get("policy_id", "")
        if not policy_id or not policy.get("state"):
            errors.append(
                f"state_policies.csv, row {line_number}: policy_id and state are required."
            )
            continue
        if policy_id in policy_ids:
            errors.append(
                f"state_policies.csv, row {line_number}: duplicate policy_id {policy_id}."
            )
            continue
        stage = policy.get("eligibility_ladder_stage", "")
        if stage and stage not in ELIGIBILITY_STAGES:
            errors.append(
                f"state_policies.csv, row {line_number}: unknown eligibility ladder stage."
            )
            continue
        policy_ids.add(policy_id)
        valid_policies.append(policy)

    valid_checklist: list[dict[str, str]] = []
    for line_number, item in enumerate(checklist, start=2):
        if not item.get("policy_id") or not item.get("checklist_item"):
            errors.append(
                f"policy_eligibility_checklist.csv, row {line_number}: "
                "policy_id and checklist_item are required."
            )
            continue
        if item["policy_id"] not in policy_ids:
            errors.append(
                f"policy_eligibility_checklist.csv, row {line_number}: "
                f"unknown policy_id {item['policy_id']}."
            )
            continue
        if item.get("status") and item["status"] not in CHECKLIST_STATUSES:
            errors.append(
                f"policy_eligibility_checklist.csv, row {line_number}: "
                "unknown checklist status."
            )
            continue
        valid_checklist.append(item)

    source_ids: set[str] = set()
    valid_sources: list[dict[str, str]] = []
    for line_number, source in enumerate(sources, start=2):
        required = ("source_id", "state", "source_title", "source_type", "url")
        if any(not source.get(key) for key in required):
            errors.append(
                f"policy_sources.csv, row {line_number}: source identity, type, and URL are required."
            )
            continue
        if source["source_id"] in source_ids:
            errors.append(
                f"policy_sources.csv, row {line_number}: duplicate source_id {source['source_id']}."
            )
            continue
        source_ids.add(source["source_id"])
        valid_sources.append(source)

    valid_providers: list[dict[str, str]] = []
    for line_number, provider in enumerate(providers, start=2):
        if not provider.get("provider_id") and not provider.get("provider_name"):
            if not any(provider.values()):
                continue
        if not provider.get("provider_id") or not provider.get("provider_name"):
            errors.append(
                f"service_providers.csv, row {line_number}: provider_id and provider_name are required."
            )
            continue
        category = provider.get("provider_category", "")
        if category not in PROVIDER_CATEGORIES:
            errors.append(
                f"service_providers.csv, row {line_number}: unknown provider category."
            )
            continue
        valid_providers.append(provider)

    return {
        "policies": valid_policies,
        "checklist": valid_checklist,
        "sources": valid_sources,
        "providers": valid_providers,
        "errors": errors,
    }


def _read_for_update(
    directory: Path,
    filename: str,
    required_columns: tuple[str, ...],
) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    rows = _read_csv(directory, filename, required_columns, errors)
    if errors:
        raise PolicyDataError("; ".join(errors))
    return rows, list(required_columns)


def _atomic_write(
    directory: Path,
    filename: str,
    fields: list[str],
    rows: list[dict[str, str]],
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=directory,
            prefix=f".{filename}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            writer = csv.DictWriter(
                temp_file,
                fieldnames=fields,
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, directory / filename)
    except OSError as error:
        raise PolicyDataError(f"Could not save {filename}: {error}") from error
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def summarize_policy_status(
    policies: list[dict[str, str]],
    shortlisted_states: list[str],
    today: date | None = None,
) -> dict[str, Any]:
    """Derive executive counts and verified future deadlines from recorded rows."""
    stages = {row.get("policy_id", ""): row.get("eligibility_ladder_stage", "") for row in policies}
    located = [
        row for row in policies
        if "located" in row.get("policy_exists_status", "").casefold()
    ]
    assessed = sum(
        stages.get(row.get("policy_id", "")) in {
            "Eligibility assessed",
            "Eligibility confirmed",
        }
        for row in policies
    )
    confirmed = sum(
        row.get("eligibility_ladder_stage") == "Eligibility confirmed"
        for row in policies
    )
    potentially_relevant = sum(
        row.get("eligibility_ladder_stage") == "Potentially relevant"
        for row in policies
    )
    today = today or date.today()
    verified_deadlines: list[date] = []
    for row in policies:
        if row.get("verification_status", "").casefold() != "verified":
            continue
        match = re.fullmatch(r"\s*(\d{4}-\d{2}-\d{2})\s*", row.get("deadlines", ""))
        if not match:
            continue
        try:
            deadline = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if deadline >= today:
            verified_deadlines.append(deadline)

    return {
        "shortlisted_state_count": len(set(shortlisted_states)),
        "official_policy_reference_count": len(located),
        "potentially_relevant_count": potentially_relevant,
        "assessed_count": assessed,
        "confirmed_count": confirmed,
        "nearest_verified_deadline": (
            min(verified_deadlines) if verified_deadlines else None
        ),
    }


def save_policy_review(
    policy_id: str,
    updates: dict[str, str],
    data_directory: Path | str | None = None,
) -> None:
    """Persist only reviewable fields, retaining all latest non-edited values."""
    unknown = set(updates) - _POLICY_REVIEW_FIELDS
    if unknown:
        raise PolicyDataError(
            "Unsupported policy review fields: " + ", ".join(sorted(unknown))
        )
    directory = Path(data_directory) if data_directory else POLICY_DATA_DIRECTORY
    rows, fields = _read_for_update(directory, "state_policies.csv", POLICY_COLUMNS)
    matches = [row for row in rows if row.get("policy_id") == policy_id]
    if len(matches) != 1:
        raise PolicyDataError(f"Expected one policy row for {policy_id}; found {len(matches)}.")

    candidate = {**matches[0], **{key: str(value).strip() for key, value in updates.items()}}
    stage = candidate.get("eligibility_ladder_stage", "")
    if stage not in ELIGIBILITY_STAGES:
        raise PolicyDataError("Choose one of the four defined eligibility ladder stages.")
    company_status = candidate.get("company_eligibility_status", "")
    confirmation_url = candidate.get("eligibility_confirmation_source_url", "")
    verification_status = candidate.get("verification_status", "").casefold()
    if verification_status == "verified":
        if not _is_http_url(candidate.get("document_url", "")):
            raise PolicyDataError(
                "Policy verification requires the URL of the reviewed official policy document."
            )
        if not candidate.get("reviewer_notes", ""):
            raise PolicyDataError(
                "Add reviewer notes describing which policy text was reviewed."
            )
    if company_status == "Eligibility confirmed" or stage == "Eligibility confirmed":
        if company_status != "Eligibility confirmed" or stage != "Eligibility confirmed":
            raise PolicyDataError(
                "Confirmed eligibility requires both the confirmed status and ladder stage."
            )
        if not _is_http_url(confirmation_url):
            raise PolicyDataError(
                "Eligibility confirmation requires a recorded written-evidence URL."
            )
        if verification_status != "verified" or not candidate.get("reviewer_notes", ""):
            raise PolicyDataError(
                "Eligibility confirmation also requires verified policy text and reviewer notes."
            )
        checklist_rows, _ = _read_for_update(
            directory, "policy_eligibility_checklist.csv", CHECKLIST_COLUMNS
        )
        evidence_found = any(
            row.get("policy_id") == policy_id
            and row.get("status") in {"Evidence located", "Reviewed"}
            and _is_http_url(row.get("source_url", ""))
            for row in checklist_rows
        )
        if not evidence_found:
            raise PolicyDataError(
                "Eligibility confirmation requires a supporting checklist source URL."
            )
    if stage == "Potentially relevant" and not candidate.get(
        "policy_relevance_to_intake", ""
    ):
        raise PolicyDataError(
            "Record the policy-to-intake relevance basis before advancing this stage."
        )
    if stage == "Eligibility assessed":
        if verification_status != "verified":
            raise PolicyDataError(
                "Eligibility cannot be assessed until the official policy text is verified."
            )
        if not candidate.get("reviewer_notes", ""):
            raise PolicyDataError(
                "Add reviewer notes describing the criteria-to-intake assessment."
            )
        checklist_rows, _ = _read_for_update(
            directory, "policy_eligibility_checklist.csv", CHECKLIST_COLUMNS
        )
        evidence_found = any(
            row.get("policy_id") == policy_id
            and row.get("status") in {"Evidence located", "Reviewed"}
            and _is_http_url(row.get("source_url", ""))
            for row in checklist_rows
        )
        if not evidence_found:
            raise PolicyDataError(
                "Eligibility assessment requires a checklist item with a supporting source URL."
            )
    if company_status == "Not eligible":
        checklist_rows, _ = _read_for_update(
            directory, "policy_eligibility_checklist.csv", CHECKLIST_COLUMNS
        )
        evidence_found = any(
            row.get("policy_id") == policy_id
            and row.get("status") in {"Evidence located", "Reviewed"}
            and _is_http_url(row.get("source_url", ""))
            for row in checklist_rows
        )
        if not candidate.get("reviewer_notes", "") or not evidence_found:
            raise PolicyDataError(
                "A not-eligible conclusion requires reviewer notes and a supporting checklist source."
            )

    for row in rows:
        if row.get("policy_id") == policy_id:
            row.update(candidate)
    _atomic_write(directory, "state_policies.csv", fields, rows)


def save_checklist_review(
    policy_id: str,
    checklist_item: str,
    updates: dict[str, str],
    data_directory: Path | str | None = None,
) -> None:
    """Persist one checklist item without rewriting unrelated review rows."""
    unknown = set(updates) - _CHECKLIST_REVIEW_FIELDS
    if unknown:
        raise PolicyDataError(
            "Unsupported checklist fields: " + ", ".join(sorted(unknown))
        )
    directory = Path(data_directory) if data_directory else POLICY_DATA_DIRECTORY
    rows, fields = _read_for_update(
        directory, "policy_eligibility_checklist.csv", CHECKLIST_COLUMNS
    )
    matches = [
        row for row in rows
        if row.get("policy_id") == policy_id
        and row.get("checklist_item") == checklist_item
    ]
    if len(matches) != 1:
        raise PolicyDataError(
            f"Expected one checklist row for {policy_id} / {checklist_item}; "
            f"found {len(matches)}."
        )
    candidate = {
        **matches[0],
        **{key: str(value).strip() for key, value in updates.items()},
    }
    status = candidate.get("status", "")
    if status not in CHECKLIST_STATUSES:
        raise PolicyDataError("Choose a valid checklist status.")
    if status in {"Evidence located", "Reviewed"} and not _is_http_url(
        candidate.get("source_url", "")
    ):
        raise PolicyDataError(
            "Evidence located or reviewed checklist items require a source URL."
        )
    if status == "Not applicable" and not candidate.get("reviewer_notes", ""):
        raise PolicyDataError(
            "Explain why the checklist item is not applicable before saving."
        )

    for row in rows:
        if (
            row.get("policy_id") == policy_id
            and row.get("checklist_item") == checklist_item
        ):
            row.update(candidate)
    _atomic_write(directory, "policy_eligibility_checklist.csv", fields, rows)
