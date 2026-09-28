# CHRONOS: Smart India Hackathon Presentation Script (PS 26227)

> **Time Limit**: 5 Minutes. Keep it punchy, visual, and focused on the **math** and **sovereignty**.

---

### **0:00 - 1:00 | The Problem & The Hook**
*(Slide: Problem Statement & Existing Flaws)*
"Good afternoon, Jury. We are tackling Problem Statement 26227 for the Ministry of Defence: *Earth Observation Change Detection*. 
The fundamental flaw in current systems is they use arbitrary distance thresholds. They flag a pixel if the colour changes. But crops change colour every season! A monsoon is not a military construction event. 
Because of this, current systems generate thousands of false alarms, overwhelming the analyst."

### **1:00 - 2:00 | The CHRONOS Solution (The Math)**
*(Slide: The Mathematical Architecture)*
"Our solution is **CHRONOS**: Calibrated Harmonic Representation Of Norm-deviations in Observed Scenes.
We don't look at single pixels. We look at the **trajectory of time**.
1. We fit a robust **Harmonic Field** to learn the natural phenological rhythm (the breathing of the crops).
2. We compare changes against a **Difference-in-Differences** cohort to cancel out atmospheric haze.
3. Most importantly, we use **Ville's Inequality** and a **Martingale E-Process**. This mathematically guarantees that our False Alarm Rate will *never* exceed the threshold we set (e.g. 5%), no matter how many times we look at the data."

### **2:00 - 3:30 | The Live Demo (Air-Gapped Dashboard)**
*(Open the React UI at `http://localhost:5173`)*
"We built the entire system to run **100% air-gapped** without the internet, which is critical for MoD deployments. 
* *Click the Search Bar*: "I can type a natural language query like *'newly built structures near a river'* and our Neuro-Symbolic compiler translates that into PostGIS spatial SQL and semantic vector search."
* *Click a Tile to open the Chart*: "This is the Killer Evidence Panel. Notice the red dotted line—that is Ville's Boundary. As the e-process evaluates the time-series, the evidence stays low during the normal seasons. But the moment a structural change occurs, the evidence line explodes past the boundary, confirming the change."

### **3:30 - 4:30 | The Audit Trail & Security**
*(Slide or UI: Audit Log)*
"When the analyst clicks **Verify Change** or **Reject**, that decision is written to a SHA-256 Hash Chain. It is cryptographically tamper-evident. Furthermore, if they reject a false alarm, our system automatically folds that mistake back into the Conformal Calibration set, so the AI learns and the threshold dynamically tightens in real-time."

### **4:30 - 5:00 | The Deliverables**
*(Open `EVALUATION_REPORT.md` on the screen)*
"Finally, we don't just ask you to trust our math. Our system includes a built-in Evaluation Harness. As you can see in this generated report, we ran it across 100 synthetic tiles and the True False Alarm Rate strictly held below the 5% target. 
CHRONOS is sovereign, mathematically guaranteed, and ready to deploy. Thank you."
