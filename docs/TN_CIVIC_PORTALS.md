# Tamil Nadu Civic & Public Grievance Portals — Department Breakdown

Compiled `2026-11-26` from public official Tamil Nadu government portal references for `NammaKural` routing & Round 2 schema design.

## 1. Department-Wise Portal Matrix

| # | Department / Jurisdiction | Official Live Complaint URL | Web Gate Status | Official WhatsApp / Email / Helpline | Exact Form Schema Extracted (2026-11-26) |
|---|---|---|---|---|---|
| 1 | **Chennai Municipal Civic (GCC PGRS)** | `https://gccservices.in/pgr/registercomplaints` | **OPEN without mandatory OTP** (`Share Mobile? Yes/No`) | **WhatsApp:** `+91 94450 61913` / `+91 94455 51913`<br>**Helpline:** `1913` | **4-Step Wizard:** Step 1: `shareMobile`, `shareEmail`, `#name`, `gender`; Step 2: `#pac-input` (Google Places), `#streetName`, `#landmark`, `#latitude_field`, `#longitude_field`; Step 3: `#specificComplaintType` (17 exact categories: `Street Light`, `Garbage`, `Road and Footpath`, `Storm Water Drains`, `Water Stagnation`, `Public Health`, `Flood`, `Park and Playground`, `Public Toilet`, etc.), `#specificComplaintSubType`, `#specificComplaintDetails`, `#specificComplaintImage` (`<1MB`) |
| 2 | **State Umbrella (Mudhalvarin Mugavari)** | `https://cmhelpline.tnega.org/portal/en/signin` | **Mobile OTP / Password Gate** (Zoho Desk) | **Email:** `cmcell@tn.gov.in`, `mudhalvarinmugavari@gmail.com`<br>**Helpline:** `1100` | `District` → `Civic Body` → `Zone/Taluk` → `Department` → `Sub-Category` → `Subject` → `Bilingual Petition Description` + `Attachment` (or 1-tap `mailto:cmcell@tn.gov.in`) |
| 3 | **Chennai Water & Sewage (CMWSSB GMS)** | `https://cms-cmwssb.tn.gov.in/#/portalcomplregistration` | **Mobile / CMC No + Captcha + OTP Gate** | **WhatsApp:** `+91 81449 30308`<br>**Helpline:** `1916` / `044-4567 4567` | Extracted from Angular `regFrom`: `complaintType` (`Public Complaint` vs `Consumer Complaint`), `complMobNo`, `complName`, `complDoorNo`, `complAreaName` (Area), `depoStationCode` (Depot/Ward), `localityDtlsCode` (Locality), `streetDtlsCode` (Street), `ccId` (Category), `cscId` (Sub-Category), `probDurationDays` (Duration in days), `complRemarks` (**max 200 chars**), `complFile` (`<5MB`) |
| 4 | **Rest-of-TN Drinking Water (TWAD PUNAL)** | `https://punal.tn.gov.in/grievance/#/` | **Mobile OTP Gate** | **WhatsApp:** `+91 94999 91916`<br>**Helpline:** `1916` | `District` → `Local Body Type` (24 Corps / 144 Municipalities / 480 Town Panchayats / 12,525 Village Panchayats) → `Block/Ward` → `Street/Habitat` → `Category` → `Description` + `Photo` |
| 5 | **Electricity (TANGEDCO / TNPDCL CCMS)** | `https://ccms.tangedco.org/tangedco-public/` | **Mobile + Captcha + OTP Gate** | **Minnagam Helpline / WhatsApp:** `94987 94987`<br>**Toll-Free:** `1912` | `Mobile Number` + `Captcha` → `Service Oriented / General Complaint` → `Consumer No / Pole Landmark` → `Fault Category` → `Description` |
| 6 | **Ration & Civil Supplies (TNPDS)** | `https://www.tnpds.gov.in/auth/login` & `/pages/feedback` | **Complaint:** Mobile + OTP<br>**Feedback:** **OPEN without OTP** | **Helpline:** `1967` / `1800-425-5901`<br>**Email:** `support@tnpds.com` | **Post-OTP (`registerComplaintForm`):** `name`, `mobileNumber`, `email`, `classification`, `problemDescription` (1000 chars)<br>**Open (`/pages/feedback`):** `name`, `mobileNumber`, `email`, `feedbackSuggestions` (1000 chars) |

## 2. Common Form Structure Observed Across GCC PGRS & Mudhalvarin Mugavari
1. **Identity:** Applicant Name, Mobile Number (OTP), Email (optional), Residential Address + Pincode.
2. **Spatial Hierarchy (The #1 Headache):** `District` → `Urban/Rural Body Type` → `Zone (e.g., I–XV)` → `Ward Number` → `Street / Landmark`.
3. **Routing Taxonomy:** `Primary Department` → `Dynamic Sub-Category` (e.g., *Electrical → Non-burning of streetlights / Glowing in daytime / Damaged pole*; *SWM → Garbage non-removal / Irregular sweeping*).
4. **Narrative & Evidence:** `Subject` + `Detailed Description` + `Geo-tagged Photo / PDF`.

## 3. High-Value Round 2 Scope (For 48h Build)
For Round 2 (`Nov 27–29`), verify exact public form field schemas for the **top 6 civic portals** (`Mudhalvarin Mugavari`, `GCC PGRS`, `CMWSSB`, `TWAD PUNAL`, `TANGEDCO CCMS`, `TNPDS`) + load **Chennai/TN Zone & Ward lookup data + landmark disambiguation**, ensuring zero login/CAPTCHA automation and 100% live interactive routing in the browser.
