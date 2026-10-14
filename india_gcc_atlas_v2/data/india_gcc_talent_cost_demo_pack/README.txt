INDIA GCC ATLAS — TALENT & COSTS SYNTHETIC DEMO PACK
Created: 2026-10-14

Purpose: prototype a payroll/budget calculator and hiring-route comparison for the NovaTech Solutions demo.

IMPORTANT: ALL SALARIES, HIRING FEES, SETUP COSTS, ON-COST RATES, INFLATION, ATTRITION AND TIME-TO-FILL VALUES ARE SYNTHETIC.
They are not researched market facts, salary quotes, or official requirements. Do not use for real budgets or client advice.

Files:
- demo_role_mix.csv: illustrative role mix totaling 200 employees.
- demo_city_role_salary_ranges.csv: city x role x seniority low/central/high annual base salary ranges, INR lakh.
- demo_state_city_mapping.csv: candidate city for each state; all comparisons remain city-specific.
- demo_headcount_ramp.csv: illustrative three-year ramp to 200 employees.
- demo_cost_assumptions.csv: employer on-cost, salary inflation, attrition and time-to-fill placeholders.
- demo_hiring_route_costs.csv: illustrative in-house, consultancy and hybrid costs; not quotes.
- demo_one_time_and_tools_costs.csv: fit-out, legal setup, onboarding/equipment and sourcing-tool costs.
- budget_input_template.csv: budget values deliberately blank; ask the user rather than infer.
- demo_evidence_register.csv: separates synthetic from missing information.

Required UI:
1. Persistent banner: “DEMO MODE — All sample values are synthetic and are not market facts.”
2. Never label synthetic rows Sourced or Verified.
3. Blank budgets must never become zero or be inferred. If missing, outcome is “Insufficient budget data.”
4. Show low/central/high scenarios. Missing salary values remain visibly missing, not zero.
5. Separate phased annual payroll, steady-state annual payroll, hiring-route costs and one-time setup.
6. Disclose salary inflation, attrition and employer-cost assumptions.
7. Compare in-house sourcing, recruitment consultancy and hybrid routes.
8. Do not use a city’s metrics as a whole-state result.
9. Keep demo files separate from production claims/sources.
10. Do not declare a factual city winner from synthetic inputs.

Narration:
“The calculator starts with the hiring plan. It separates recurring payroll, hiring-route costs and one-time setup. As verified city-role salary and talent data is added, the same calculations become evidence-backed. Today's values demonstrate the method, not real market affordability.”
