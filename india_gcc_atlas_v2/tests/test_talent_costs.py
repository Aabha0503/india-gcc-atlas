import shutil
import tempfile
import unittest
from pathlib import Path

import talent_costs


class TalentCostCalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = talent_costs.load_demo_pack()
        cls.role_mix = talent_costs.default_role_mix(cls.pack["role_mix"])

    def calculate(self, **overrides):
        arguments = {
            "city": "Bengaluru",
            "headcount": 350,
            "role_mix": self.role_mix,
            "salary_rows": self.pack["salary_ranges"],
            "ramp_rows": self.pack["headcount_ramp"],
            "assumption_rows": self.pack["cost_assumptions"],
            "route_rows": self.pack["hiring_routes"],
            "setup_rows": self.pack["setup_costs"],
            "preferred_route": "In-house sourcing",
            "existing_headcount": 0,
        }
        arguments.update(overrides)
        return talent_costs.calculate_cost_scenarios(**arguments)

    def test_demo_pack_loads_without_errors_and_stays_separate(self):
        self.assertEqual(self.pack["errors"], [])
        self.assertEqual(len(self.pack["salary_ranges"]), 48)
        self.assertEqual(len(self.pack["role_mix"]), 4)
        self.assertTrue(
            all(row["is_synthetic"].casefold() == "true"
                for row in self.pack["salary_ranges"])
        )

    def test_blank_budgets_are_insufficient(self):
        result = talent_costs.budget_comparison(None, 100)
        self.assertEqual(result["status"], "Insufficient budget data")
        self.assertIsNone(result["headroom"])

    def test_year_one_uses_ramp_average_and_scenarios_are_ordered(self):
        result = self.calculate()
        self.assertTrue(result["valid"], result["errors"])
        self.assertAlmostEqual(result["year1_average_headcount"], 52.5)
        self.assertAlmostEqual(result["year1_net_hires"], 105)
        for category in (
            "base_payroll",
            "loaded_payroll",
            "year1_loaded_payroll",
            "year1_total",
            "one_time_setup",
            "steady_state_total",
        ):
            self.assertLessEqual(result[category]["low"], result[category]["central"])
            self.assertLessEqual(result[category]["central"], result[category]["high"])
        self.assertEqual(result["steady_inflation_years"], 2)

    def test_fixed_setup_is_excluded_from_recurring_steady_state(self):
        result = self.calculate()
        self.assertTrue(result["valid"], result["errors"])
        for scenario in talent_costs.SCENARIOS:
            self.assertAlmostEqual(
                result["year1_total"][scenario],
                result["year1_loaded_payroll"][scenario]
                + result["year1_recruitment"][scenario]
                + result["one_time_setup"][scenario],
            )
            self.assertAlmostEqual(
                result["steady_state_total"][scenario],
                result["steady_state_loaded_payroll"][scenario]
                + result["steady_recruitment"][scenario]
                + result["steady_onboarding"][scenario],
            )
            self.assertGreater(result["one_time_setup"][scenario],
                               result["fixed_setup"][scenario])

    def test_higher_headcount_and_route_change_calculated_outputs(self):
        base = self.calculate()
        larger = self.calculate(headcount=700)
        consultancy = self.calculate(preferred_route="Recruitment consultancy")
        self.assertAlmostEqual(
            larger["base_payroll"]["central"],
            base["base_payroll"]["central"] * 2,
        )
        self.assertNotEqual(
            base["year1_recruitment"]["central"],
            consultancy["year1_recruitment"]["central"],
        )

    def test_missing_salary_is_not_zeroed(self):
        salary_rows = [
            row for row in self.pack["salary_ranges"]
            if not (
                row["city"] == "Bengaluru"
                and row["role"] == "Software Engineer"
                and row["seniority"] == "Junior"
            )
        ]
        result = self.calculate(salary_rows=salary_rows)
        self.assertFalse(result["valid"])
        self.assertTrue(result["missing_salary"])
        self.assertIsNone(result.get("base_payroll"))

    def test_malformed_schema_is_reported_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            for filename, *_ in talent_costs.TABLES.values():
                shutil.copyfile(
                    talent_costs.DEMO_DIRECTORY / filename,
                    target / filename,
                )
            salary_path = target / "demo_city_role_salary_ranges.csv"
            salary_path.write_text("city,role\nBengaluru,Engineer\n", encoding="utf-8")
            malformed = talent_costs.load_demo_pack(target)
        self.assertEqual(malformed["salary_ranges"], [])
        self.assertTrue(
            any("missing required columns" in error for error in malformed["errors"])
        )


if __name__ == "__main__":
    unittest.main()
