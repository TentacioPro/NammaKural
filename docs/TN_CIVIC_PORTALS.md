# Tamil Nadu Civic & Public Grievance Portals — Department Breakdown

Compiled `2026-11-26` from public official Tamil Nadu government portal references for `NammaKural` routing & Round 2 schema design.

## 1. Department-Wise Portal Matrix

| # | Department / Jurisdiction | Official Portal / App | Helpline | Issues Covered | Primary Citizen Confusion / Friction |
|---|---|---|---|---|---|
| 1 | **State Umbrella (All Depts & Schemes)** | **Mudhalvarin Mugavari (CM Helpline / IIPGCMS)** · `cmhelpline.tnega.org` / `gdp.tn.gov.in` | `1100` | Welfare schemes (*Magalir Urimai*), revenue delays, multi-dept & unresolved escalations | Nested District → Body Type → Department → Sub-Dept dropdowns + OTP + English/Tamil formal summary |
| 2 | **Chennai Municipal Civic** | **Greater Chennai Corporation (GCC) — Namma Chennai / PGRS** · `chennaicorporation.gov.in` | `1913` | Solid Waste Management (garbage), Electrical (streetlights), SWD/Engineering (roads, potholes, stormwater drains), Public Health (mosquitoes, stray dogs), Town Planning | Cascading **Zone (`I–XV`) → Ward → Department → Sub-Category**; residents don't know Zone/Ward numbers and confuse Electrical vs. TANGEDCO or SWD vs. CMWSSB |
| 3 | **Chennai Water & Sewage** | **CMWSSB GMS** (Chennai Metrowater) | `044-4567 4567` / `14416` | Drinking water supply, sewage overflow, open manholes, road-cut repairs, tanker booking | Separate site from GCC despite overlapping street flooding symptoms |
| 4 | **Rest-of-TN Drinking Water** | **TWAD Board — PUNAL** · `punal.tn.gov.in` | `1916` / WhatsApp `9499991916` | Rural & non-Chennai municipal/town-panchayat drinking water grievances | Separate District/Block/Panchayat routing outside Chennai |
| 5 | **Electricity** | **TANGEDCO / TNPDCL (CCMS)** · `tnebltd.gov.in` | `1912` / `94987 94987` | Power outages, voltage drops, transformer faults, live wire/pole hazards, billing | Requires consumer/service number & fault classification; frequently confused with GCC streetlight maintenance |
| 6 | **Ration & Civil Supplies** | **TNPDS** · `tnpds.gov.in` | `1967` / `1800-425-5901` | Smart ration card updates, member add/delete, fair-price shop complaints | Strict card-number/OTP flows & shop-code lookups |
| 7 | **Revenue & Certificates** | **TN e-Sevai** · `tnesevai.tn.gov.in` | — | Patta/Chitta transfers, income/community/nativity certificates | District/Taluk/Village mapping + formal grievance drafting |
| 8 | **Law & Order / Cyber** | **TN Police Citizen Portal** · `police.tn.gov.in/citizenportal` | `100` / `112` / `1091` | Missing documents, general petitions, CSR/FIR tracking | Station jurisdiction lookup + formal petition text |
| 9 | **Transport / RTO** | **TNSTA / Parivahan** · `tnsta.gov.in` | — | Driving licence, RC delays, permit & RTO office grievances | Split between central Parivahan & state transport offices |

## 2. Common Form Structure Observed Across GCC PGRS & Mudhalvarin Mugavari
1. **Identity:** Applicant Name, Mobile Number (OTP), Email (optional), Residential Address + Pincode.
2. **Spatial Hierarchy (The #1 Headache):** `District` → `Urban/Rural Body Type` → `Zone (e.g., I–XV)` → `Ward Number` → `Street / Landmark`.
3. **Routing Taxonomy:** `Primary Department` → `Dynamic Sub-Category` (e.g., *Electrical → Non-burning of streetlights / Glowing in daytime / Damaged pole*; *SWM → Garbage non-removal / Irregular sweeping*).
4. **Narrative & Evidence:** `Subject` + `Detailed Description` + `Geo-tagged Photo / PDF`.

## 3. High-Value Round 2 Scope (For 48h Build)
For Round 2 (`Nov 27–29`), verify exact public form field schemas for the **top 6 civic portals** (`Mudhalvarin Mugavari`, `GCC PGRS`, `CMWSSB`, `TWAD PUNAL`, `TANGEDCO CCMS`, `TNPDS`) + load **Chennai/TN Zone & Ward lookup data + landmark disambiguation**, ensuring zero login/CAPTCHA automation and 100% live interactive routing in the browser.
