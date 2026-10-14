# India GCC Atlas — expanded MVP

A Streamlit prototype that brings the following into one research workspace:
- Interactive India map with clickable city markers
- GCC city distribution, sector analysis, and parent-country analysis based on the supplied AIM Research PDF
- Searchable starter company leads
- Contact directory with public LinkedIn URLs and evidence links
- Real-estate directory template with building, submarket, area, asking rent, availability and source fields
- Service-provider directory for legal, tax/audit, recruitment, payroll/EOR, real estate, site selection and incentives
- Source/methodology notes and CSV import/export

## Run on Windows
1. Extract the ZIP.
2. Open PowerShell in the extracted folder.
3. Run:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Streamlit will print a local URL (usually http://localhost:8501). Open it in your browser.

## Data and caveats
- AIM Research report figures are transcribed from the user-provided `The State of GCCs in India — 2026 Edition`, published 13 October 2026. The app labels these as source-reported figures.
- **Data-quality flag:** city values shown on page 3 sum to more than the 1,784+ headline on page 2. The PDF excerpt does not explain the discrepancy. Values are preserved as printed and explicitly flagged; verify with the publisher before relying on city counts.
- City-wide office leasing is from JLL's 2025 market report and is not GCC-only leasing, property availability or asking rent.
- Company rows remain discovery leads with broad links, not verified GCC records.
- The AIM PDF does not provide named contact details, personal LinkedIn URLs, property-level rents/availability, or a service-provider directory. These are blank/manual-add directories, not fabricated sample data.
- Records added through forms are session-based. Export CSVs to keep a copy; upload a CSV to reload records in the current session. No database/authentication is included.
- LinkedIn URLs are user-entered public links; this app does not scrape LinkedIn or connect to a LinkedIn account.

## Main source links
- AIM Research / GCC Explorer: https://gccexplorer.com/press
- Government of India Economic Survey 2025–26, Chapter 7: https://www.indiabudget.gov.in/economicsurvey/doc/eschapter/echap07.pdf
- JLL 2025 India office market: https://www.jll.com/en-in/newsroom/india-s-office-market-scales-unprecedented-highs-with-gross-leasing-activity-at-83-3-million-sq-ft-for-the-year-2025-jll
- JLL India GCC Guide 2026: https://www.jll.com/en-in/insights/how-india-s-gccs-transformed-from-cost-centres-to-enterprise-powerhouse
- CBRE GCC office landscape: https://www.cbre.co.in/insights/reports/gccs-transforming-india-s-office-landscape
