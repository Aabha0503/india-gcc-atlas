INDIA GCC ATLAS — SYNTHETIC DEMO DATA PACK
Created: 2026-10-14

PURPOSE
Demonstrate the intended Compare Cities workflow for the NovaTech Solutions demo profile:
US-headquartered enterprise technology / IT services company; planned 200–499 person GCC;
software engineering, data/AI, cloud/DevOps, QA/testing; priorities are talent availability,
talent cost, proximity to customers/leadership, and office availability/cost; decision deadline 2027-01-01.

IMPORTANT: ALL CITY METRICS IN THIS PACK ARE INVENTED.
They are NOT researched facts, verified salary benchmarks, actual office rents, real flight itineraries,
or official policy claims. Do not use in production or present as factual market research.

FILES
1. demo_city_metrics.csv — 16 illustrative records (four cities x four priorities), including ranges,
   units, scope, caveats, source ID, and an explicit is_synthetic flag.
2. demo_sources.csv — clearly labelled synthetic source record; not an external source.
3. demo_claims.csv — claim-register-shaped examples; verification_status=demo_only and evidence_quality=synthetic.
4. demo_state_policy_placeholders.csv — placeholders only, not actual incentive information.

HOW TO USE
- Keep these files separate from production data, e.g. in a demo_data/ folder.
- Add a visible “Demo mode — illustrative data, not market facts” banner.
- If the app's evidence classifier only accepts verified claims, do NOT change the production classifier
  to treat these rows as verified. Add a separate demo-only path that renders sample charts while keeping
  synthetic labels visible.
- If you want a demo comparison to unlock, make the gate explicitly depend on demo mode and display
  “Illustrative demo comparison — not a factual recommendation.”
- Do not mix these rows into the real claims.csv or sources.csv.
- Replace every synthetic metric with independently checked sources before using production evidence.

Suggested narration:
“Here is how the product works once evidence is available. It compares the priorities you entered,
shows ranges rather than false precision, exposes evidence status and caveats, and explains what is
still missing. These numbers are synthetic so we can demonstrate the experience without pretending
we have verified market data.”
