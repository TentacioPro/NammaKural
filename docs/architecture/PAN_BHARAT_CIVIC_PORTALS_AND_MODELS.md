# Pan-Bharat Multilingual Civic Portals, Dialects & Sovereign Model Matrix — NammaKural

> Architecture extension scaling **NammaKural (*நம்ம குரல்*)** from its live **Tamil Nadu Round 2 showcase** to a modular **Pan-Bharat Voice Grievance Fabric** via pluggable State Packs (`state_packs/<state_code>.json`) while preserving strictly Bharat-safe Sovereign & Open-Weight AI models (zero Chinese-origin weights).

---

## 1. Pluggable State-Pack Architecture (Tamil Nadu Live Showcase → Pan-India Rollout)

Instead of hardcoding regional logic into Python routing, every Indian State / Municipal Corporation ships as a declarative **State Pack**:
```text
state_packs/
  ├── in_central.json   # CPGRAMS (pgportal.gov.in), Swachhata-MoHUA (1969), RailMadad (139)
  ├── tn_tamilnadu.json # LIVE SHOWCASE: GCC PGRS (1913), CM Cell (1100), CMWSSB/TWAD (1916), TANGEDCO (1912), TNPDS (1967)
  ├── ka_karnataka.json # iPGRS / Janaspandana, Seva Sindhu, BBMP Sahaaya 2.0
  ├── mh_maha.json      # Aaple Sarkar, Mumbai BMC MARG
  └── ...               # 28 States + UTs pluggable via identical Workflow FSM + Code>LLM HITL Guard
```
- **What changes per State:** GIS Ward GeoJSON boundaries, Portal field schema + official WhatsApp/Helpline bridges, and **STT Hotword / Phonetic Normalization Lexicon** (e.g., *Tanglish* `"saakkadai/eriyala"` vs *Hinglish* `"naali/batti"` vs *Kanglish* `"charandi/current illa"`).
- **What stays 100% identical across India:** Duplex WebRTC + `coturn` audio pipeline, Pre-LLM PII & Verhoeff Aadhaar Firewall, 6-state Tool-Calling Workflow FSM, Citizen Mobile OTP / DigiLocker Auth, 24h Ward Cooldown, and Native Spoken Dual-Confirm HITL Seal.

---

## 2. Central & Pan-India Civic Grievance Portals

| Jurisdiction | Portal / System | Verified Official Portal URL | Official Helpline / Scope |
|---|---|---|---|
| **Central Ministries & Participating States/UTs** | **CPGRAMS** *(Centralised Public Grievance Redress & Monitoring System)* | `https://pgportal.gov.in/` | `24×7` lodging, appeal options & real-time tracking |
| **National Urban Sanitation (MoHUA)** | **Swachhata — MoHUA** | Swachh Bharat Urban portal / app ecosystem | **`1969`** *(Ward sanitary complaints: garbage dumps, drains, public toilets)* |
| **Indian Railways (Pan-India)** | **RailMadad** | `https://railmadad.indianrailways.gov.in` | **`139`** *(`24×7` train/station cleanliness, water, safety & medical grievances)* |

---

## 3. State & UT Civic Grievance Portals Registry (Verified Public Endpoints)

### A. South India *(Live Showcase: Tamil Nadu)*

| State / UT | State & Municipal Portal(s) | Verified Portal URL(s) | Verified Helpline / Schema Notes |
|---|---|---|---|
| **Tamil Nadu (Live Demo)** | **GCC PGRS**, **Mudhalvarin Mugavari**, **CMWSSB GMS**, **TWAD PUNAL**, **TANGEDCO CCMS**, **TNPDS** | See exact DOM inspection matrix in [docs/TN_CIVIC_PORTALS.md](../TN_CIVIC_PORTALS.md) | `1913`, `1100` (`cmcell@tn.gov.in`), `1916`, `1912` (`94987 94987`), `1967` |
| **Karnataka** | **Janaspandana (`iPGRS`)**, **Seva Sindhu**, **BBMP (`Sahaaya 2.0`)** | `https://ipgrs.karnataka.gov.in` · `https://sevasindhu.karnataka.gov.in/` · `https://bbmp.gov.in` | State PGRS + Bengaluru ULB ward grievance routing |
| **Andhra Pradesh** | **PGRS (`Spandana`)** | `https://pgrs.ap.gov.in` · `https://meekosam.ap.gov.in` | **`1902`** integrated state grievance helpline |
| **Telangana** | **Prajavani**, **GHMC (Hyderabad)** | `https://prajavani.cgg.gov.in` · `https://www.ghmc.gov.in` | State Prajavani + Greater Hyderabad municipal workflows |
| **Kerala** | **CMO Public Grievance** | `https://cmo.kerala.gov.in` | **`1076`** state CMO helpline channel |
| **Puducherry (UT)** | **Puducherry UT & CPGRAMS** | `https://py.gov.in/` · `https://pgportal.gov.in/` | Routed via UT portal & central CPGRAMS |

### B. North & Central India

| State / UT | State & Municipal Portal(s) | Verified Portal URL(s) | Verified Helpline / Schema Notes |
|---|---|---|---|
| **Uttar Pradesh** | **Jansunwai (`IGRS`)** | `https://jansunwai.up.nic.in/` | **`1076`** (CM Helpline) |
| **Delhi (NCT)** | **CM Jan Sunwai Portal** | `https://cmjansunwai.delhi.gov.in/` | Integrated Delhi state civic petitions |
| **Haryana** | **SARAL Haryana**, **CM Window** | `https://saralharyana.gov.in/` · `https://cmharyanacell.nic.in/` | Integrated district/ULB resolution network |
| **Rajasthan** | **Rajasthan Sampark** | `https://sampark.rajasthan.gov.in/` | **`181`** toll-free state grievance line |
| **Madhya Pradesh** | **CM Helpline** | `https://cmhelpline.mp.gov.in/` | **`181`** unified citizen grievance number |
| **Punjab** | **Punjab Connect (`PGRS / DiGi Punjab`)** | `https://connect.punjab.gov.in/` | Unified citizen service & grievance desk |
| **Chhattisgarh** | **Janshikayat / `NIDAAN 1100`** | `https://janshikayat.cg.nic.in/` · `https://nidaan.cg.gov.in/` | District/urban grievance tracking |
| **Uttarakhand** | **CM Helpline (`1905`)** | `https://cmhelpline.uk.gov.in/` | **`1905`** state helpline |
| **Himachal Pradesh** | **Mukhyamantri Seva Sankalp** | `https://cmsankalp.hp.gov.in/` | **`1100`** hill-state citizen helpline |
| **Jammu & Kashmir (UT)** | **JK-IGRAMS (`JK Samadhan`)** | `https://jkgrievance.in/` | Unified UT grievance portal |
| **Chandigarh (UT)** | **Chandigarh Administration & CPGRAMS** | `https://chandigarh.gov.in/` · `https://pgportal.gov.in/` | UT grievance module + CPGRAMS |

### C. West & East India

| State / UT | State Portal(s) | Verified Portal URL(s) | Notes |
|---|---|---|---|
| **Maharashtra** | **Aaple Sarkar**, **Mumbai BMC (`MARG`)** | `https://aaplesarkar.mahaonline.gov.in` · `https://grievances.maharashtra.gov.in/` · `https://portal.mcgm.gov.in` · `https://marg.mcgm.gov.in` | State RTS + Mumbai civic pothole/drainage tracking |
| **Gujarat** | **SWAGAT Online** | Gujarat CMO SWAGAT online state infrastructure | State-Wide Attention on Grievances by Application of Technology |
| **Goa** | **CM Helpline / `DPG Goa`** | `https://cmhelpline.dpg.goa.gov.in/` · `https://dpg.goa.gov.in/` | Directorate of Public Grievances portal |
| **Odisha** | **Jana Sunani** | `https://janasunani.odisha.gov.in/` | State CMO unified grievance portal |
| **Bihar** | **Bihar Lok Shikayat** | `https://lokshikayat.bihar.gov.in/` | Statutory Public Grievance Redressal Act portal |
| **Jharkhand** | **Mukhyamantri Jan Samvad / ULB e-Gov** | `https://cm.jharkhand.gov.in/write-to-cm` · `https://jharkhandegovernance.com/` | **`181`** Jan Samvad + urban civic services |
| **West Bengal** | **PGMS / CPGRAMS Integration** | `https://excise.wb.gov.in/pgms/page/login.aspx` · `https://pgportal.gov.in/` | Departmental PGMS + central CPGRAMS routing |

### D. North-East India

| State | State Portal(s) | Verified Portal URL(s) |
|---|---|---|
| **Assam** | **Sewa Setu (`RTPS`)** | `https://sewasetu.assam.gov.in/` |
| **Tripura** | **CPGRAMS Tripura** | `https://grievance.tripura.gov.in` |
| **Manipur** | **GovConnect Manipur / e-Services** | `https://govconnectmanipur.mn.gov.in` · `http://eservicesmanipur.gov.in` |
| **Meghalaya** | **SPGRS / CM Connect** | `http://megpgrams.gov.in` |
| **Nagaland** | **NIIS Nagaland** | `https://niisnagaland.in` |
| **Mizoram** | **Mipui Aw** | `https://mipuiaw.mizoram.gov.in` |
| **Arunachal Pradesh** | **EODB / PHE&WS Dept Grievances** | `https://eodb.arunachal.gov.in` · `https://www.aphedsw.arunachal.gov.in` |
| **Sikkim** | **Online Grievance Redressal (`RDD`)** | `https://grievancerdd.sikkim.gov.in` |

---

## 4. Languages, Code-Mixing & Regional Accent Coverage Across Bharat

Urban and rural Indian citizens almost never speak textbook formal prose into civic helplines — they speak **rapid code-mixed speech** blending regional grammar with English civic nouns (`"pipe"`, `"wire"`, `"ward"`, `"ration"`, `"garbage"`, `"meter"`, `"road"`).

| Language Cluster | States Covered | Code-Mix Spoken Form & Sample Civic Triggers | Key Accents / Dialect Challenges |
|---|---|---|---|
| **Tamil** *(Round 2 Showcase)* | Tamil Nadu, Puducherry | **Tanglish:** *"saakkadai overflow"*, *"eriyala"*, *"kudineer varala"*, *"kuppai close pannitanga"* | Chennai/Madras colloquial, Madurai/Southern, Kongu/Coimbatore, Tirunelveli, Cauvery Delta |
| **Hindi + Indo-Aryan Belt** | UP, Bihar, MP, Rajasthan, Haryana, Delhi, HP, UK, CG, JH | **Hinglish:** *"gali ki light band hai"*, *"naali jaam"*, *"paani nahi aa raha"*, *"kachra nahi utha"* | Bhojpuri, Maithili, Awadhi, Haryanvi, Marwari, Pahadi tonal & vowel shifts |
| **Kannada** | Karnataka | **Kanglish:** *"street light barthilla"*, *"charandi block aagide"*, *"kasa thogondu hogilla"* | Bengaluru urban code-mix, North Karnataka (Hubballi/Kalaburagi), Coastal/Mangaluru |
| **Telugu** | Andhra Pradesh, Telangana | **Tenglish:** *"current wire tegindi"*, *"drainage pongutundi"*, *"chetha teesukellatledu"* | Coastal Andhra, Rayalaseema, Telangana/Hyderabadi Dakhini-mixed Telugu |
| **Marathi** | Maharashtra, Goa | **Marathilish:** *"rastyavar khadde aahet"*, *"gatar tutla aahe"*, *"paani yet nahi"* | Puneri, Mumbai tapori/code-mix, Vidarbha, Konkani influence |
| **Malayalam** | Kerala | **Manglish:** *"street light kathunnilla"*, *"vellam varunnilla"*, *"maalinyam kidakkunnu"* | Travancore, Kochi/Central, Malabar/Kozhikode rapid consonant clusters |
| **Bengali / Odia / Assamese** | West Bengal, Tripura, Odisha, Assam | **Benglish / Odia-mix / Axomiya:** *"nala jaam"*, *"rashta kharap"*, *"pali batti nei"* | Rural East coastal vs Kolkata/Bhubaneswar/Guwahati speech speeds |
| **22 Eighth Schedule Languages Complete** | Pan-India (`Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu`) | Supported through sovereign **Sarvam AI `Saaras`** & **AI4Bharat `IndicConformer` / `IndicTrans2`** | Requires per-State Pack acoustic hotword biasing (`Ward/Tehsil/Gram Panchayat` names) |

---

## 5. Bharat-Safe Model Stack Per Language Tier (Zero Chinese Weights)

| Pipeline Stage | Sovereign Indian Cloud Stack *(Production Primary)* | Open-Weight Self-Hosted Stack *(NIC MeghRaj / GPU)* | Keyless Round 2 Docker / Browser Mode |
|---|---|---|---|
| **STT (ASR)** | **Sarvam AI `Saaras` (v4)** — 22 Scheduled languages + English, 8 kHz telephony tuned, built-in `codemix` | **AI4Bharat `IndicConformer` / `IndicWhisper`** (IIT Madras, 22 languages) + **`Systran/faster-whisper-small`** fine-tuned on regional LoRAs | **Wispr Flow Hotkey Dictation** + Web Speech (`ta-IN` / `en-IN`) |
| **Reasoning & Tool FSM** | **Sarvam Sovereign LLM** or India-region **Gemini 2.5 Flash** *(optional key, zero free-tier training retention)* | **Google `Gemma-4-E2B-it`** / **NVIDIA `Nemotron-3.5-Bolt-E4B`** / **Microsoft `Phi-4-mini-reasoning`** *(Unsloth LoRA fine-tuned on State Packs)* | Deterministic Python NLU (`backend/nlu.py`) + **Unsloth Local Studio** (`127.0.0.1:8888`) |
| **TTS (Voice Reply)** | **Sarvam `Bulbul` (`v3` / `v4 Flash`)** — expressive native Indian voices + CDN-cached static `.opus` prompts | **AI4Bharat `Indic-Parler-TTS`** (22 Indic language prosody/speaker control) | Web Speech `ta-IN` / phonetic Indian-English fallback |
| **Embeddings / RAG** *(Scheme & Dept Lookup)* | India-hosted Sovereign Embeddings | **`sentence-transformers/all-MiniLM-L6-v2`** / Indic BERT *(IIT Madras / AI4Bharat)* | Exact deterministic GIS & JSON State-Pack lookup |

> **Why Tamil Nadu Now, Bharat Next:** Demonstrating **deep end-to-end Tamil Nadu accuracy** (with live Tanglish NLU, Ward `102`/`103`/`175`/`178`/`44`/`32` disambiguation, `CMWSSB` 200-char limits, `GCC <1 MB` photo stamping, and Tamil `உறுதி` HITL) proves every hard component works in production — so scaling to Karnataka (`BBMP`/`iPGRS`), Maharashtra (`BMC`/`Aaple Sarkar`), or UP (`Jansunwai 1076`) requires **only adding a new `state_packs/<state>.json` config + lexicon**, never rewriting the voice engine.
