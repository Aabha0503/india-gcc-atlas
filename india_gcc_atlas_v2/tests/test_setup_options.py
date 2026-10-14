import unittest
from datetime import date

from report_pdf import build_pdf_report
from setup_options import (
    DECISION_STATUSES,
    DECISION_TOPICS,
    DIMENSIONS,
    MODEL_NAMES,
    build_model_comparison,
    build_planning_brief,
    initial_decision_log,
    recorded_decision_count,
)


class SetupOptionsTests(unittest.TestCase):
    def test_initial_log_has_six_undecided_records_and_zero_recorded_decisions(self):
        decisions = initial_decision_log()

        self.assertEqual(len(decisions), 6)
        self.assertEqual(len(DECISION_TOPICS), 6)
        self.assertTrue(all(row["status"] == "Undecided" for row in decisions.values()))
        self.assertEqual(recorded_decision_count(decisions), 0)
        self.assertEqual(
            set(DECISION_STATUSES),
            {"Decided", "Proposed", "Undecided", "Waiting on verification"},
        )

    def test_recorded_count_includes_only_explicit_non_undecided_statuses(self):
        decisions = initial_decision_log()
        decisions["candidate_cities"]["status"] = "Proposed"
        decisions["operating_model"]["status"] = "Waiting on verification"
        decisions["policy_route"]["status"] = "Decided"

        self.assertEqual(recorded_decision_count(decisions), 3)

    def test_model_comparison_covers_all_models_and_dimensions_without_ranking(self):
        answers = {
            "headcount": "200-499",
            "ramp_timeline": "25-36 months",
            "decision_deadline": date(2027, 1, 1),
            "india_presence": "No",
            "regulatory_constraints": "Review data access and security requirements.",
        }
        rows = build_model_comparison(answers)

        self.assertEqual(len(rows), len(MODEL_NAMES) * len(DIMENSIONS))
        self.assertEqual({row["Operating model"] for row in rows}, set(MODEL_NAMES))
        self.assertTrue(all(row["Assessment"] == "Cannot be judged" for row in rows))
        self.assertTrue(
            all("Supporting source or assumption" in row for row in rows)
        )
        control_rows = [
            row for row in rows
            if row["Dimension"] == "Desired operational control"
        ]
        self.assertTrue(
            all(row["Company-stated context"] == "Not provided"
                for row in control_rows)
        )
        self.assertTrue(
            all(row["Evidence state"] == "Not available" for row in control_rows)
        )

    def test_planning_brief_preserves_status_evidence_assumptions_and_missing_values(self):
        decisions = initial_decision_log()
        decisions["operating_model"].update(
            {
                "status": "Proposed",
                "decision": "Evaluate EOR as an interim proposal",
                "rationale": "Compare against the stated ramp and control needs.",
                "evidence_references": "No verified reference recorded.",
                "assumptions": "Planning hypothesis only.",
            }
        )
        decisions["transition_path"]["transition_details"] = {
            "initial_model": "Employer of Record (EOR)",
            "destination_model": "Own entity",
            "transition_trigger": "When operating and legal conditions are reviewed",
            "transition_window": "",
            "switching_costs": "",
            "switching_time": "",
            "dependencies": "",
            "validation_evidence": "",
        }
        brief = build_planning_brief(
            {
                "company_name": "Example Co",
                "headcount": "",
                "priority_1": "Talent availability",
            },
            decisions,
        )

        self.assertIn("1 of 6 decisions recorded", brief)
        self.assertIn("Evidence state: Company-provided", brief)
        self.assertIn("Evidence state: Assumption", brief)
        self.assertIn("Switching costs: To confirm", brief)
        self.assertIn("Switching time: To confirm", brief)
        self.assertIn("Awaiting module integration", brief)
        self.assertIn("## Needs professional verification", brief)
        self.assertIn("Not provided", brief)
        self.assertIn("No overall winner or readiness assessment is calculated.", brief)

    def test_existing_pdf_builder_exports_the_planning_brief(self):
        brief = build_planning_brief({}, initial_decision_log())
        pdf = build_pdf_report(brief)

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
