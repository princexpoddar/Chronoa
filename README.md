# CHRONOS: Calibrated Harmonic Representation Of Norm-deviations in Observed Scenes

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61DAFB.svg)](https://vitejs.dev)
[![Deployment](https://img.shields.io/badge/Deployment-100%25%20Air--Gapped%20Sovereign-green.svg)](PROVENANCE.md)
[![Tests](https://img.shields.io/badge/Tests-48%20Passed%20%28100%25%29-brightgreen.svg)](tests/)

> **Problem Statement 26227 (Ministry of Defence / Smart India Hackathon)**  
> *Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery*

---

## 1. Executive Summary & Operational Challenge

Earth-observation (EO) archives are expanding exponentially, capturing multi-spectral, multi-temporal, and multi-sensor imagery across vast sovereign territories. Conventional catalog search relies on rigid metadata (acquisition time, sensor platform, bounding box coordinates), forcing defense and intelligence analysts to already know *where* and *when* an event occurred before inspecting pixels.

Existing automated change detection systems suffer from a fatal flaw: **arbitrary pixel-difference thresholding**. When an algorithm simply flags deviations in spectral reflectance, it triggers thousands of false alarms caused by:
- **Seasonal phenological breathing**: Crops greening, monsoons, and harvest cycles.
- **Atmospheric confounding factors**: Haze, thin cirrus clouds, aerosol scattering, and sensor illumination angles.
- **Viewing geometry & co-registration jitter**: Sub-pixel misregistration between successive satellite passes.

**CHRONOS** solves this challenge through a mathematically grounded, air-gapped Earth Observation Intelligence Engine. Instead of comparing isolated pairs of pixels, CHRONOS evaluates the **complete trajectory of time**:
1. It fits a **harmonic embedding field** to model natural seasonal rhythms.
2. It constructs a **Difference-in-Differences (DiD) spatial cohort** to cancel out regional atmospheric and illumination shifts.
3. It tracks structural anomalies through an **anytime-valid Conformal Martingale E-Process**, mathematically bounded by **Ville's Inequality**. This guarantees that the False Alarm Rate will strictly satisfy $\text{FAR} \le \alpha$ (e.g., $\le 5\%$) regardless of continuous monitoring and stopping times.

---

## 2. Core Capabilities Matrix (PS 26227 Compliance)

| PS Requirement | Capability | CHRONOS Technical Implementation |
| :--- | :--- | :--- |
| **2.2.1 Semantic Retrieval** | Natural-language and image-to-image search | **Neuro-Symbolic Query Compiler** translates compound English prompts into Typed Query Algebra $\mathcal{Q} ::= \text{Sem} \wedge \text{Chg} \wedge \text{Spa}$, compiling into PostGIS spatial pushdown filters (`ST_DWithin`) and pgvector cosine similarity search. |
| **2.2.2 Multi-Temporal Change** | Detection, classification & earliest observation | Dual-mode detection: **Mode A (Sequential)** tracks real-time change-points via Martingale e-processes with optimal stopping time $\tau$; **Mode C (Bi-Temporal)** utilizes cross-attention difference embeddings for rapid two-epoch triage. |
| **2.2.3 False-Alarm Suppression** | Atmospheric, seasonal & sensor normalization | Three-stage filtering: (1) Robust iteratively reweighted least squares (IRLS) harmonic phenology fitting, (2) spatial Difference-in-Differences cohort adjustment, and (3) Conformal Calibration with Ledoit-Wolf shrinkage. |
| **2.2.4 Unsupervised Discovery** | Cluster similar anomalous sites across regions | **HDBSCAN clustering** in joint representation space $[\mathbf{v}_{sem}, \mathbf{v}_{phen}]$; supports query-by-example (k-NN) to discover recurring military or infrastructure installations without re-querying. |
| **2.2.5 Analyst Workflow & Audit** | Triage queue, review decisions & provenance | Interactive tactical workstation with bi-temporal satellite visualizer (RGB vs False-Color NIR/NDVI), review actions (Verify/Reject), and a **SHA-256 cryptographic hash-chained audit log** guaranteeing non-repudiation. |
| **2.2.6 Sovereign Ingestion** | Air-gapped operation & incremental ingestion | **100% offline operational capability** with zero external cloud dependencies. Ingests raw Cloud-Optimized GeoTIFFs (COGs) and Sentinel-2 L2A multi-spectral rasters directly into local PostGIS/pgvector storage. |

---

## 3. Mathematical Architecture

### 3.1 Robust Harmonic Phenology Field
For any spatial tile $s$, the baseline phenological cycle across fractional year $t$ is modeled as a truncated Fourier expansion with linear trend:

$$f(t; \boldsymbol{\theta}) = \theta_0 + \theta_1 t + \sum_{k=1}^{K} \left[ \theta_{2k} \cos(k \omega t) + \theta_{2k+1} \sin(k \omega t) \right]$$

where $\omega = 2\pi$, $K = 3$ harmonics, and $\boldsymbol{\theta} \in \mathbb{R}^{2K+2}$. Parameters are solved via Iteratively Reweighted Least Squares (IRLS) with Huber loss to suppress cloud and shadow contamination. Incremental satellite acquisitions update $\boldsymbol{\theta}$ in $\mathcal{O}(d \cdot m^2)$ time using Sherman–Morrison rank-1 recursive covariance updates.

### 3.2 Difference-in-Differences (DiD) Cohort Normalization
To isolate local human-induced ground modifications from regional atmospheric variation, CHRONOS computes spatial cohort deviations:

$$\Delta_{DiD}(s, t) = \left( Y(s, t) - \hat{f}(s, t) \right) - \frac{1}{|\mathcal{C}(s)|} \sum_{c \in \mathcal{C}(s)} \left( Y(c, t) - \hat{f}(c, t) \right)$$

where $\mathcal{C}(s)$ is a stable cohort of nearby invariant terrain tiles. If a monsoon cloud or dust storm impacts the basin, the cohort baseline shifts equally, driving $\Delta_{DiD}(s, t) \to 0$ and eliminating the false alarm.

### 3.3 Anytime-Valid Conformal Martingale E-Process
To evaluate whether a sequence of residual deviations is genuine, CHRONOS evaluates non-conformity using Ledoit-Wolf shrunk Mahalanobis distances $S_t = \sqrt{\mathbf{r}_t^\top \hat{\boldsymbol{\Sigma}}^{-1} \mathbf{r}_t}$. Conformal calibration converts $S_t$ into smoothed uniform $p$-values $p_t \sim \mathcal{U}(0, 1)$ under the null hypothesis $\mathcal{H}_0$.

The test martingale (e-process) accumulates evidence across successive observations:

$$E_t = \prod_{i=1}^{t} \varsigma_\kappa(p_i), \quad \text{where } \varsigma_\kappa(p) = \kappa p^{\kappa - 1} \quad (\kappa \in (0, 1))$$

By **Ville's Inequality**, for any stopping time $\tau$:

$$\mathbb{P}_{\mathcal{H}_0}\left( \sup_{t \ge 1} E_t \ge \frac{1}{\alpha} \right) \le \alpha$$

Setting $\alpha = 0.05$ yields Ville's boundary threshold $1/\alpha = 20.0$. Even under continuous multi-year surveillance, the false alarm probability is mathematically guaranteed to remain below $5\%$.

```
Evidence E(t)
     ^
  40 |                                  * [CONFIRMED CHANGE: Stopping Time τ]
     |                                 *
  20 |--------------------------------*----------------- Ville's Boundary (1/α = 20)
     |                               *
   5 |                  /\          *
   1 |---/\--/\--------/--\--------/-------------------- Baseline E_0 = 1.0 (Random Walk)
   0 +---|---|---|---|---|---|---|---|---|---|---> Time (Passes)
        T1  T2  T3  T4  T5  T6  T7  T8  T9  T10
```

---

## 4. Repository Structure

```
chronoa/
├── chronos/                     # Core CHRONOS Python Library
│   ├── core/                   # Mathematical engines
│   │   ├── harmonics.py        # Truncated Fourier IRLS & Sherman-Morrison updates
│   │   ├── did.py              # Difference-in-Differences cohort normalization
│   │   ├── conformal.py        # Ledoit-Wolf covariance & conformal calibration
│   │   ├── eprocess.py         # Power-family betting martingale & Ville inequality
│   │   └── types.py            # Strictly-typed dataclasses & arrays
│   ├── engine/                 # System orchestration & retrieval
│   │   ├── query_compiler.py   # Neuro-symbolic NL -> Typed Algebra -> PostGIS SQL
│   │   ├── change_engine.py    # Mode A (Sequential) & Mode C (Bi-Temporal) pipelines
│   │   ├── discovery.py        # HDBSCAN unsupervised clustering & k-NN query
│   │   ├── field_fitter.py     # Parallel tile phenology fitting
│   │   ├── indexer.py          # Spatial tile indexing & ingestion
│   │   └── morphology.py       # Binary morphological filtering & perimeter metrics
│   ├── data/                   # Data processing & synthetic benchmarks
│   │   ├── download_real_data.py # STAC/Copernicus Sentinel-2 ingest
│   │   ├── coregistration.py   # Phase-correlation sub-pixel alignment
│   │   ├── masking.py          # SCL cloud/shadow quality mask weighting
│   │   ├── synthetic.py        # Multi-temporal benchmark generator
│   │   └── tiling.py           # MGRS / GeoTIFF window tiling
│   ├── db/                     # Data persistence & security
│   │   ├── schema.sql          # PostGIS + pgvector database DDL
│   │   ├── database.py         # SQLAlchemy & psycopg connection manager
│   │   └── audit.py            # SHA-256 tamper-evident hash chain logger
│   ├── features/               # Embedding & representation extractors
│   │   ├── physical_tier1.py   # Physical spectral indices (NDVI, NDWI, NDBI)
│   │   └── encoders_tier2.py   # RemoteCLIP & Prithvi foundation model encoders
│   └── evaluation/             # Test harness & benchmark reporter
│       ├── harness.py          # Monte Carlo false alarm & detection latency tests
│       └── report_generator.py # Markdown evaluation report generator
├── data/raw/                   # Downloaded Sentinel-2 L2A scenes (Sutlej Basin)
├── tests/                      # Comprehensive pytest test suite (48 tests)
│   ├── test_harmonics.py
│   ├── test_did.py
│   ├── test_conformal.py
│   └── test_eprocess.py
├── ui/                         # Analyst Console & Defense HUD
│   ├── api.py                  # FastAPI REST backend
│   └── frontend/               # React 19 + Vite tactical frontend
│       ├── src/
│       │   ├── App.jsx         # Command console workstation
│       │   ├── index.css       # Tactical defense design system
│       │   └── main.jsx
│       └── package.json
├── EVALUATION_REPORT.md        # Empirical validation metrics
├── PRESENTATION_SCRIPT.md      # 5-minute SIH presentation walkthrough
├── PROVENANCE.md               # Model & dataset licensing declarations
├── start_demo.ps1              # Unified one-click launch script
└── requirements.txt            # Python dependencies
```

---

## 5. System Requirements & Setup

### 5.1 Prerequisites
- **Operating System**: Windows 10/11, Linux (Ubuntu 22.04+), or macOS (Apple Silicon supported).
- **Python**: Version 3.10 to 3.13.
- **Node.js**: Version 18.0 or higher.
- **Geospatial Binaries** *(optional for production db)*: PostgreSQL 15+ with PostGIS and pgvector extensions.

### 5.2 Python Virtual Environment Setup
```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt
```

### 5.3 Frontend Dependencies Setup
```powershell
cd ui\frontend
npm install
cd ..\..
```

---

## 6. Running the System

### Option A: One-Click Launch Script (Recommended)
Run the automated launcher from PowerShell:
```powershell
.\start_demo.ps1
```
This automatically boots:
- The **FastAPI Intelligence Engine** on `http://localhost:8000`
- The **Tactical Analyst Console** on `http://localhost:5173`

### Option B: Manual Execution

**Terminal 1 — FastAPI Intelligence Engine:**
```powershell
cd ui
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — React Defense Workstation:**
```powershell
cd ui\frontend
npm run dev
```
Navigate to `http://localhost:5173` in your browser.

---

## 7. Operational Workstation Features

The CHRONOS UI is engineered as an authentic **Defense & Earth Observation Tactical Workstation**, discarding generic AI chat styling for mission-critical situational awareness:

1. **Target Triage & Queue**:
   - Natural language neuro-symbolic query compilation (e.g., *"newly built structures near a river"*).
   - Real-time compiler inspection showing typed algebra AST:
     `Sem("built structures") ∧ Chg("construction") ∧ Spa(ST_DWithin, waterway=*, 500m)`.
   - Direct translation to PostGIS SQL pushdown filters before vector indexing.
2. **Interactive Bi-Temporal Satellite Visualizer**:
   - Inspect Sentinel-2 acquisitions side-by-side or in split-slider view (Pre-Event T1 vs Post-Event T2).
   - Multispectral band toggles:
     - **True Color (RGB)**: Sentinel-2 bands B04 (Red), B03 (Green), B02 (Blue).
     - **False Color Infrared (NIR)**: Bands B08 (NIR), B04 (Red), B03 (Green) — highlights canopy loss and structural displacement.
     - **NDVI Anomaly Heatmap**: Normalized difference vegetation difference mask overlay.
3. **Sequential Martingale Evidence Workbench**:
   - Live interactive Recharts plot of the anytime-valid e-process trajectory.
   - Dynamic Ville's Boundary adjustment slider ($\alpha = 0.01, 0.05, 0.10 \implies 1/\alpha = 100, 20, 10$).
   - Dual trace showing Harmonic seasonal model vs actual observed signal.
   - Conformal calibration $p$-value distribution and DiD cohort adjustment metrics.
4. **Cryptographic SHA-256 Audit Trail**:
   - Tamper-evident hash-chained ledger storing every analyst action (`VERIFIED_CHANGE` / `FALSE_ALARM_SUPPRESSED`).
   - Displays Genesis hash, Block height, Analyst ID, Timestamp, Previous Hash, and Current Hash.
   - Closed-loop conformal feedback: rejecting a candidate immediately recalibrates the nonconformity threshold.
5. **Unsupervised Discovery & HDBSCAN Clusters**:
   - Discovers spatial clusters of similar anomalies across the Sutlej Basin in joint $[\mathbf{v}_{sem}, \mathbf{v}_{phen}]$ space.
6. **Air-Gapped Sovereign Telemetry**:
   - Real-time monitoring of local multi-spectral Sentinel-2 GeoTIFF scenes (20 files, >3.2 GB in Sutlej River Basin) with zero internet access required.

---

## 8. Verification & Test Suite

CHRONOS includes an exhaustive automated test suite covering exact parameter recovery, outlier resistance, martingale convergence, and false-alarm bounds:

```powershell
# Run the complete test suite
python -m pytest -q
```
*Expected output: `48 passed in ~64s (100% pass rate)`.*

### Test Suite Coverage:
- `tests/test_harmonics.py`: Tests design matrix creation, noise-free parameter recovery, IRLS outlier rejection (clouds/shadows), and Sherman–Morrison recursive updates ($< 10^{-6}$ error).
- `tests/test_did.py`: Tests synthetic cohort generation, atmospheric perturbation cancellation, and local change signal isolation.
- `tests/test_conformal.py`: Tests Ledoit-Wolf covariance shrinkage, Mahalanobis non-conformity scoring, empirical coverage on held-out null, and Benjamini–Yekutieli FDR control.
- `tests/test_eprocess.py`: Tests power betting martingale property ($\mathbb{E}[\varsigma(p)] = 1$ under $\mathcal{H}_0$), Ville's inequality bound ($\text{FAR} \le \alpha$), and persistent signal detection under $\mathcal{H}_1$.

---

## 9. Provenance, Licensing & Air-Gapped Declaration

In compliance with Ministry of Defence requirements for sovereign operational systems (PS 26227 §2.2.7):
- **100% Air-Gapped**: Runs entirely on local compute without external network requests or proprietary cloud APIs.
- **Satellite Data**: Sentinel-2 L2A multi-spectral rasters provided under the European Commission / ESA Copernicus Open Access Policy.
- **Foundation Models**: RemoteCLIP and Prithvi-EO-2.0 packaged locally under Apache 2.0.
- **Codebase**: Built with open-source MIT/Apache 2.0 components (FastAPI, React, Recharts, NumPy, SciPy, PostGIS).

Refer to [PROVENANCE.md](PROVENANCE.md) and [EVALUATION_REPORT.md](EVALUATION_REPORT.md) for full audit reports.

---

## 10. Contributors & Acknowledgements
- Developed for **Smart India Hackathon (SIH)** — Problem Statement 26227.
- Dedicated to sovereign geospatial intelligence, verifiable change detection, and false-alarm suppression for Defense and National Remote Sensing agencies.
