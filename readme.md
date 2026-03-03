
# Emergency Department Simulation (ED-EMS)

[![Live Demo](https://img.shields.io/badge/Live-Demo-blue)](https://edsim.warewebsolutions.ca)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Authors:** Murray Ware and Anton Massinger
**License:** MIT

---

##  Live Demo

A fully interactive web version of the simulation is available here:

 **[https://edsim.warewebsolutions.ca](https://edsim.warewebsolutions.ca)**

The demo includes:

* Predefined hospital templates
* Baseline vs adjusted scenario comparison
* Persistent saved simulations
* Multi-user login
* Full operational metrics visualization
* EMS offload modeling

---

# Overview

ED-EMS is a modular, event-driven simulation of Emergency Department (ED) operations built with **SimPy**.

It models:

* Walk-in arrivals
* EMS arrivals and offload
* Fast Track and Acute areas
* Physician 1-, 2-, and 3-touch workflows
* Nursing assessment models
* Labs and Diagnostic Imaging (DI)
* Consult logic
* Inpatient admissions and boarding
* LWBS (Leave Without Being Seen)
* EMS download capacity constraints
* Offload nurse staffing profiles

The project includes:

* A **React frontend**
* A **Flask API backend**
* A **modular SimPy engine**
* A **database for users, saved configurations, and scenario comparisons**

---

# System Architecture

```
React Frontend
        │
        ▼
Flask API (api.py)
        │
        ├── Simulation Engine (edems/)
        │      ├── Modular Mixins
        │      ├── Policies
        │      └── Config Objects
        │
        ├── Database Layer
        │      ├── users
        │      ├── inputs
        │      ├── outputs
        │      └── compares
        │
        └── Analytics + Metrics
```

---

# Simulation Engine Design

The simulation core is built using a **mixin-based architecture**.

Each major operational domain is isolated in its own module and composed into a single site simulation class.

## Core Class

`edems/ed.py`

```python
class SingleSiteSim(
    EMSOffloadMixin,
    EDTreatmentMixin,
    PatientGenerationMixin,
    LwbsMixin,
    OrdersMixin,
    InpatientFlowMixin,
    DoctorManager,
)
```

This design provides:

* Separation of responsibilities
* Clean extension points
* Testable components
* Modular feature enablement
* Clear operational boundaries

---

# Mixin Architecture

Each `.py` file in `edems/` encapsulates its own logic.

## PatientGenerationMixin

* Walk-in arrivals
* EMS arrivals
* CTAS scoring
* Acuity generation
* Area routing (Fast vs Acute)

## LwbsMixin

* Waiting room logic
* LWBS thresholds
* Time-based patient exits

## EDTreatmentMixin

* Bed assignment
* Treatment start
* Reassessment flows
* Touch logic (1-, 2-, 3-touch)

## OrdersMixin

* Lab probability
* DI probability
* Lab/DI work generation
* Concurrent test execution

## EMSOffloadMixin

* Ambulance arrival
* Download capacity limits
* Offload nurse scheduling
* Offload acuity watchdog
* Crew hospital time modeling

## InpatientFlowMixin

* Consult ordering
* Admit decision logic
* Service mapping
* Inpatient LOS
* Boarding if full

## DoctorManager

* Physician scheduling
* Shift start times
* Hourly signup caps
* Panel size limits

Each module is self-contained and responsible only for its operational domain.

---

# Operational Flow

## Global ED Flow

```
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
         │   └─────────┬─────────┘              │
         │             │                        │
         │   ┌─────────▼─────────┐              │
         │   │   Disposition     │              │
         │   └───────────────────┘              │
         │                                      │
         │                    ┌─────────────────▼────────────────┐
         │                    │   Consult Ordered? (Acute only)  │
         │                    └─────────────────┬────────────────┘
         │                                      │
         │                    ┌─────────────────▼────────────────┐
         │                    │  Admit / Discharge               │
         │                    └─────────────────┬────────────────┘
         │                                      │
         │                ┌─────────────────────▼────────────────────┐
         │                │  Inpatient LOS + Boarding (if full)     │
         │                └──────────────────────────────────────────┘
```

---

# EMS Offload Logic

The EMS system models:

* Download capacity
* Offload nurse staffing by hour
* Crew hospital time
* Acuity escalation watchdog
* Bed assignment after download

It supports 24-hour repeating staffing profiles.

---

# Metrics & Outputs

The simulation returns:

* Per-patient metrics
* Distribution statistics
* Physician performance metrics
* DI modality metrics
* EMS timing metrics
* Inpatient LOS metrics

Sample fields:

* `door_to_doc`
* `doc_to_disp`
* `bed_to_doc`
* `los_minutes`
* `consult_minutes_total`
* `download_minutes`
* `inpatient_los_minutes`

Results are returned as structured JSON and optionally stored in database.

---

# Baseline vs Adjusted Scenarios

The system supports structured comparison.

### Default Run

* Creates new comparison
* Stores as baseline (`output_1`)
* Marks first input

### Adjusted Run

* Attaches to existing comparison
* Stores as adjusted (`output_2`)

Comparison model:

```
compare
 ├── output_1  (baseline)
 └── output_2  (adjusted)
```

---

# API

### POST `/simulate` (Authenticated)

Runs simulation and stores results.

Request includes:

* Full configuration
* Run parameters
* Scenario metadata

Returns:

* Metrics
* Distributions
* Compare ID (if baseline)

---

# Frontend

React frontend supports:

* Hospital selection
* Config editing
* Baseline vs adjusted comparison
* Scenario saving
* Metrics visualization
* Historical run retrieval

Build output is served by Flask.

---

# Running Locally

## Backend

```
pip install -r requirements.txt
python api.py
```

## Frontend

```
cd client
npm install
npm run build
```

---

# License

MIT License
© 2025 Murray Ware and Anton Massinger

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files to deal in the Software without restriction.
