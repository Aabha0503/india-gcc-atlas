import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from policy_ecosystem import (
    CHECKLIST_STATUSES,
    ELIGIBILITY_STAGES,
    POLICY_DATA_DIRECTORY,
    PolicyDataError,
    load_policy_workspace,
    save_checklist_review,
    save_policy_review,
    summarize_policy_status,
)


class PolicyWorkspaceDataTests(unittest.TestCase):
    def test_policy_pack_loads_with_unreviewed_terms_left_blank(self):
        data = load_policy_workspace()

        self.assertEqual(data["errors"], [])
        self.assertEqual(len(data["policies"]), 2)
        self.assertEqual(data["providers"], [])
        self.assertTrue(
            all(policy["benefits_summary"] == "" for policy in data["policies"])
        )
        self.assertTrue(
            all(policy["company_eligibility_status"] == "Not assessed"
                for policy in data["policies"])
        )
        setup_checks = [
            item for item in data["checklist"]
            if item["checklist_item"] == "Required or assumed setup model"
        ]
        self.assertEqual(len(setup_checks), 2)
        self.assertTrue(
            all(item["status"] == "Needs verification" for item in setup_checks)
        )

    def test_ladder_has_the_four_requested_stages_and_starts_at_policy_exists(self):
        data = load_policy_workspace()
        self.assertEqual(
            ELIGIBILITY_STAGES,
            (
                "Policy exists",
                "Potentially relevant",
                "Eligibility assessed",
                "Eligibility confirmed",
            ),
        )
        self.assertTrue(
            all(row["eligibility_ladder_stage"] == "Policy exists"
                for row in data["policies"])
        )

    def test_summary_counts_are_derived_and_deadlines_require_verified_iso_date(self):
        data = load_policy_workspace()
        summary = summarize_policy_status(
            data["policies"], ["Karnataka", "Maharashtra"], today=date(2026, 10, 14)
        )
        self.assertEqual(summary["shortlisted_state_count"], 2)
        self.assertEqual(summary["official_policy_reference_count"], 2)
        self.assertEqual(summary["potentially_relevant_count"], 0)
        self.assertEqual(summary["assessed_count"], 0)
        self.assertEqual(summary["confirmed_count"], 0)
        self.assertIsNone(summary["nearest_verified_deadline"])

        policies = [
            {
                **data["policies"][0],
                "eligibility_ladder_stage": "Eligibility assessed",
                "verification_status": "Verified",
                "deadlines": "2026-12-01",
            },
            {
                **data["policies"][1],
                "eligibility_ladder_stage": "Eligibility confirmed",
                "verification_status": "Unverified",
                "deadlines": "2026-11-01",
            },
        ]
        summary = summarize_policy_status(policies, [], today=date(2026, 10, 14))
        self.assertEqual(summary["assessed_count"], 2)
        self.assertEqual(summary["confirmed_count"], 1)
        self.assertEqual(
            summary["nearest_verified_deadline"], date(2026, 12, 1)
        )

    def test_checklist_and_policy_review_saves_persist_without_replacing_other_rows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_directory = Path(temporary_directory)
            for filename in (
                "state_policies.csv",
                "policy_eligibility_checklist.csv",
                "policy_sources.csv",
                "service_providers.csv",
            ):
                shutil.copy(POLICY_DATA_DIRECTORY / filename, data_directory / filename)

            save_checklist_review(
                "KAR-GCC-2024-2029",
                "Required or assumed setup model",
                {
                    "status": "Evidence located",
                    "source_url": "https://example.gov.in/policy",
                    "reviewer_notes": "Setup clause located; interpretation pending.",
                    "setup_model_required_or_assumed": "Needs legal interpretation",
                    "last_checked_date": "2026-10-14",
                },
                data_directory,
            )
            updated_checklist = load_policy_workspace(data_directory)["checklist"]
            updated = next(
                row for row in updated_checklist
                if row["policy_id"] == "KAR-GCC-2024-2029"
                and row["checklist_item"] == "Required or assumed setup model"
            )
            untouched = next(
                row for row in updated_checklist
                if row["policy_id"] == "MAH-GCC-2025"
                and row["checklist_item"] == "Required or assumed setup model"
            )
            self.assertEqual(updated["status"], "Evidence located")
            self.assertEqual(untouched["status"], "Needs verification")

            save_policy_review(
                "KAR-GCC-2024-2029",
                {
                    "document_url": "https://example.gov.in/policy.pdf",
                    "eligibility_ladder_stage": "Eligibility assessed",
                    "policy_relevance_to_intake": "Review remains tied to company activities.",
                    "company_eligibility_status": "In assessment",
                    "setup_model_required_or_assumed": "Needs legal interpretation",
                    "setup_model_verification_status": "In progress",
                    "verification_status": "Verified",
                    "reviewer_notes": "Policy text reviewed; unresolved criteria remain.",
                    "eligibility_confirmation_source_url": "",
                    "last_checked_date": "2026-10-14",
                },
                data_directory,
            )
            updated_policies = load_policy_workspace(data_directory)["policies"]
            updated_policy = next(
                row for row in updated_policies
                if row["policy_id"] == "KAR-GCC-2024-2029"
            )
            untouched_policy = next(
                row for row in updated_policies if row["policy_id"] == "MAH-GCC-2025"
            )
            self.assertEqual(
                updated_policy["eligibility_ladder_stage"], "Eligibility assessed"
            )
            self.assertEqual(untouched_policy["eligibility_ladder_stage"], "Policy exists")

    def test_confirmed_eligibility_requires_written_evidence_url(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_directory = Path(temporary_directory)
            for filename in (
                "state_policies.csv",
                "policy_eligibility_checklist.csv",
                "policy_sources.csv",
                "service_providers.csv",
            ):
                shutil.copy(POLICY_DATA_DIRECTORY / filename, data_directory / filename)
            with self.assertRaisesRegex(PolicyDataError, "written-evidence URL"):
                save_policy_review(
                    "KAR-GCC-2024-2029",
                    {
                        "eligibility_ladder_stage": "Eligibility confirmed",
                        "company_eligibility_status": "Eligibility confirmed",
                        "eligibility_confirmation_source_url": "",
                    },
                    data_directory,
                )

    def test_malformed_or_missing_files_are_reported_and_empty_provider_directory_is_valid(self):
        data = load_policy_workspace()
        self.assertEqual(data["providers"], [])
        self.assertTrue(all(status in CHECKLIST_STATUSES for status in {
            row["status"] for row in data["checklist"]
        }))

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_directory = Path(temporary_directory)
            missing = load_policy_workspace(data_directory)
            self.assertEqual(len(missing["errors"]), 4)
            self.assertEqual(missing["providers"], [])

            for filename in (
                "state_policies.csv",
                "policy_eligibility_checklist.csv",
                "policy_sources.csv",
                "service_providers.csv",
            ):
                shutil.copy(POLICY_DATA_DIRECTORY / filename, data_directory / filename)
            (data_directory / "service_providers.csv").write_text(
                "provider_name,wrong_column\n",
                encoding="utf-8",
            )
            malformed = load_policy_workspace(data_directory)
            self.assertTrue(
                any("service_providers.csv is missing required columns" in error
                    for error in malformed["errors"])
            )


if __name__ == "__main__":
    unittest.main()
