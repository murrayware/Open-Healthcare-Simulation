Perfect — here’s a **clean, corrected, GitHub-ready README** with a properly aligned ASCII flow diagram that reflects:

 LWBS (Leave Without Being Seen) happens *before* treatment starts,
 Fast-Track patients can still have labs and DI (diagnostics) but **no consults or admits**,
 Acute patients can have 1-, 2-, or 3-touch flows with possible consult/admit,
 The layout is easy to read directly in Markdown without wrapping errors.

---

#  Emergency Department Simulation (ED-EMS)

**Author:** Murray Ware
**License:** MIT (Open Source – freely usable and modifiable)

---

## Overview

This project simulates the operations of a hospital **Emergency Department (ED)** and its interaction with **inpatient units** using **SimPy**.
It models realistic patient flow, physician–nurse coordination, diagnostics, consults, and admissions in an event-driven system.

The framework is modular, reproducible, and entirely open source — anyone can run, extend, or modify it.

---

##  Key Features

* Walk-in and EMS arrivals with configurable hourly curves
* Separate **Fast Track** and **Acute** areas
* 1-Touch, 2-Touch, and 3-Touch physician logic
* Concurrent **nursing**, **labs**, and **diagnostic imaging (DI)**
* Consult and inpatient admission logic (Acute only)
* Inpatient capacity, boarding, and LOS modelling
* LWBS (Leave Without Being Seen) behaviour with configurable thresholds
* Full event log and CSV-based analytics

---

##  How the Example Runner Works

### 1. Initialization

`run.py` builds a single hospital model using SimPy.
Configuration objects define the full environment: arrivals, physicians, nurse ratios, labs, DI, and inpatient units.

Example:

```python
hospital = Hospital(env, sim_cfg, elog)
env.run(until=END_MINUTES)
```

---

### 2. Patient Generation

Each simulated patient receives:

* A **CTAS acuity score**
* Route to **Fast Track** or **Acute**
* Assigned **touch count** (1-, 2-, or 3-touch)
* Orders for **labs** and/or **diagnostic imaging (DI)**
* LWBS threshold (maximum waiting time before leaving)

Patients may leave **before assessment** if the LWBS threshold expires.
EMS arrivals always route to Acute.

---

### 3. Treatment Logic

####  Fast-Track Patients

* Can be **1-touch** or **2-touch**
* May receive **labs** or **diagnostic imaging**
* No consults or inpatient admissions
* Shorter treatment times and faster physician turnover

####  Acute Patients

* May be **1-touch**, **2-touch**, or **3-touch**
* Labs and DI may run concurrently with nursing
* Consults may trigger inpatient admissions
* Admitted patients may board in the ED if no inpatient bed is available

---

## System Flow Diagram

Below is a flow diagram reflecting all possible patient pathways — including LWBS before bed assignment, diagnostics in both areas, and consult/admit logic for Acute only.

```text
             ┌─────────────────────────────┐
             │       Patient Arrives       │
             └──────────────┬──────────────┘
                            │
                   ┌────────▼────────┐
                   │   Triage & CTAS │
                   └────────┬────────┘
                            │
                 ┌──────────▼──────────┐
                 │ Wait / LWBS Timer   │
                 │ (Leaves if over     │
                 │  threshold)         │
                 └──────────┬──────────┘
                            │
                   ┌────────▼────────┐
                   │  Routed To Area │
                   │ (FAST / ACUTE)  │
                   └────────┬────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                                      │
 ┌───────▼───────┐                       ┌──────▼───────┐
 │  FAST TRACK   │                       │    ACUTE     │
 └───────┬───────┘                       └──────┬───────┘
         │                                      │
         │  ┌─────────────────────┐             │
         │  │ Initial Assessment  │             │
         │  └──────────┬──────────┘             │
         │             │                        │
         │  ┌──────────▼──────────┐             │
         │  │ Nursing + Labs + DI │             │
         │  │ (Concurrent)        │             │
         │  └──────────┬──────────┘             │
         │             │                        │
         │   ┌─────────▼─────────┐              │
         │   │  Reassessment(s)  │              │
         │   │ (2-Touch Patients)│              │
         │   └─────────┬─────────┘              │
         │             │                        │
         │   ┌─────────▼─────────┐              │
         │   │   Treatment Time  │              │
         │   └─────────┬─────────┘              │
         │             │                        │
         │   ┌─────────▼─────────┐              │
         │   │   Disposition     │              │
         │   │ (Discharge)       │              │
         │   └───────────────────┘              │
         │                                      │
         │                    ┌─────────────────▼────────────────┐
         │                    │   Consult Ordered? (30% Acute)   │
         │                    └─────────────────┬────────────────┘
         │                                      │
         │                    ┌─────────────────▼────────────────┐
         │                    │  Consult Outcome (Admit / Not)   │
         │                    └──────────────┬───────────────────┘
         │                                   │
         │          ┌────────────────────────▼────────────────────────┐
         │          │  Admit → Wait for Inpatient Bed (if full)       │
         │          │  → Transfer to Unit → Inpatient LOS Ends        │
         │          └────────────────────────────────────────────────┘
         │
         └───────────────────────────────┐
                                         │
                             ┌───────────▼───────────┐
                             │     Simulation End    │
                             └───────────────────────┘
```



                     ┌─────────────────────────────┐
                     │      ACUTE AREA ENTRY       │
                     └──────────────┬──────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │ Initial Assessment│
                          │   (Touch #1)      │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │ Nursing + Labs +  │
                          │ Diagnostics (DI)  │
                          │ (Concurrent)      │
                          └─────────┬─────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  Reassessment #1    │
                         │   (Touch #2)        │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  Reassessment #2    │
                         │   (Touch #3)        │
                         └──────────┬──────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  Consult Ordered?  │
                          │   (≈30% chance)    │
                          └─────────┬──────────┘
                                    │
                     ┌──────────────▼──────────────┐
                     │   Consult Attends (30–90m)  │
                     │   Uses consult_time_draw    │
                     └──────────────┬──────────────┘
                                    │
                     ┌──────────────▼──────────────┐
                     │   Consult Outcome           │
                     │ ┌──────────────┬──────────┐ │
                     │ │ No Admit     │ Admit    │ │
                     │ └──────┬───────┴─────┬────┘ │
                     └────────┼─────────────┼──────┘
                              │             │
                 ┌────────────▼───┐   ┌─────▼───────────────────────────┐
                 │  Treatment &   │   │ Admitted to Inpatient Unit      │
                 │  Discharge     │   │ (Medicine, Surgery, ICU, etc.)  │
                 │  (ED complete) │   │ If unit full → board in ED bed  │
                 └───────┬────────┘   │ until inpatient bed available   │
                             │        │                                 │
                 ┌───────────▼────────┴──────────────┐
                 │  Inpatient LOS (via los_draw)     │
                 │  After LOS complete → discharged  │
                 └───────────────────────────────────┘




            ┌─────────────────────────┐
            │     FAST TRACK ENTRY    │
            └─────────────┬───────────┘
                          │
                (LWBS timer running in WR
                 until a bed becomes free)
                          │
                 ┌────────▼────────┐
                 │  Bed Assigned   │   ← LWBS no longer applies after this
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │ Initial MD Ax   │  Touch #1
                 │  (assess_start) │
                 └────────┬────────┘
                          │
          ┌───────────────▼────────────────┐
          │  Nursing Assessment (FIFO/ratio)│
          │      + Labs (if ordered)        │
          │      + Diagnostics (if ordered) │
          │      (labs & DI may run         │
          │       concurrently here)        │
          └───────────────┬────────────────┘
                          │
                 ┌────────▼────────┐
                 │ Reassessment     │  Touch #2
                 │  (reassess_start)│
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │  Treatment       │  ~60 minutes
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │   Discharge      │  (ED complete)
                 └──────────────────┘


---

##  Outputs

All simulation results are saved to CSVs in the `outputs/` directory:

| File                               | Description                                     |
| ---------------------------------- | ----------------------------------------------- |
| `patients.csv`                     | Per-patient summary (arrival → discharge/admit) |
| `events.csv`                       | Chronological event log of all processes        |
| `summary_hourly.csv`               | Hourly performance metrics                      |
| `debug/doctor_patient_traces.csv`  | Event traces for 3 patients per doctor          |
| `debug/patients_numeric_means.csv` | Mean of numeric columns in patients.csv         |

---

##  Analytics

Example quick summary:

```python
from edems.analytics import summarize_patients
detailed, summary = summarize_patients(patients_df, events_df)
```

This yields:

* Mean LOS by area and touch type
* Consult vs. non-consult comparisons
* Boarding time distributions
* LWBS rate before treatment

---

##  Future Extensions

* Introduce multi-site transfer and overflow routing
* Implement staff scheduling optimization via Pyomo or pulp
* Integrate full inpatient logic
* Create full EMS dispatcher handeling EMS pickups using simulated geo-location for pickup

---

##  License

**MIT License**
Copyright (c) 2025 **Murray Ware**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

