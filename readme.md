# Emergency Department Simulation Engine (ED-EMS)

[![Live Demo](https://img.shields.io/badge/Live-Demo-blue)](https://edsim.warewebsolutions.ca)  
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Authors:** Murray Ware, Anton Massinger  
**License:** MIT  

---

## Disclaimer

This project is an independent, open-source initiative.

- It is not affiliated with, endorsed by, or developed for any specific healthcare organization
- It contains no proprietary, confidential, or identifiable data
- All configurations, parameters, and examples are synthetic or generalized

---

## Live Demo

A fully interactive web version of the simulation is available:

https://edsim.warewebsolutions.ca

The demo includes:

- Predefined example templates (synthetic)
- Baseline vs adjusted scenario comparison
- Persistent saved simulations
- Multi-user login
- Operational metrics visualization
- EMS offload modeling

---

# Overview

Open Healthcare Simulation is a modular, event-driven simulation framework for modeling patient flow and operational dynamics in emergency departments.

Built with SimPy, it is designed as a general-purpose engine for:

- scenario testing  
- system behavior exploration  
- operational modeling  

---

## What It Models

- Walk-in arrivals  
- EMS arrivals and offload processes  
- Multi-area flow (e.g., fast-track vs higher-acuity streams)  
- Physician workflows (1-, 2-, and 3-touch models)  
- Nursing assessment patterns  
- Laboratory and diagnostic workflows  
- Consult and disposition logic  
- Inpatient admission and boarding  
- LWBS (leave without being seen) behavior  
- Capacity constraints and resource contention  

---

## Project Structure

The project includes:

- Simulation engine (SimPy-based, modular design)
- Flask API backend
- React frontend
- Persistence layer for scenarios and outputs

---

# System Architecture

```

React Frontend
│
▼
Flask API
│
├── Simulation Engine (edems/)
│      ├── Modular Components
│      ├── Policies
│      └── Config Objects
│
├── Persistence Layer
│
└── Metrics & Analytics

````

---

# Simulation Engine Design

The core simulation uses a mixin-based architecture, where each operational domain is isolated and composable.

## Core Class

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
````

### Design Principles

* Separation of concerns
* Modular extensibility
* Reproducibility
* Clear operational boundaries

---

# Component Architecture

Each module in `edems/` encapsulates a specific domain:

### Patient Generation

* Arrival processes (walk-in + EMS)
* Acuity assignment
* Routing logic

### Treatment Flow

* Bed assignment
* Assessment and reassessment
* Multi-touch workflows

### Orders / Diagnostics

* Lab and imaging probabilities
* Time-based diagnostic delays (no explicit queues)

### EMS Offload

* Ambulance arrivals
* Offload capacity constraints
* Staffing profiles
* Crew time modeling

### Inpatient Flow

* Consult logic
* Admission decisions
* Boarding time delays

### Physician Management

* Scheduling
* Signup limits
* Panel constraints

---

# Patient Flow (Conceptual)

```
Arrival → Triage → Wait → Assessment → Diagnostics → Reassessment → Disposition → Admission → Boarding
```

---

# Detailed Patient Flow (System-Level)

```
                ┌────────────────────┐
                │   Patient Arrival   │
                │ (Walk-in or EMS)    │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │       Triage        │
                └─────────┬──────────┘
                          │
              ┌───────────┴────────────┐
              │                        │
              ▼                        ▼
   ┌──────────────────┐     ┌────────────────────┐
   │ Waiting Room Queue│     │ EMS Offload Queue  │
   │ (LWBS possible)   │     │ (Crew constrained) │
   └─────────┬────────┘     └─────────┬──────────┘
             │                        │
             └──────────┬─────────────┘
                        ▼
              ┌────────────────────┐
              │   Area Assignment   │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │   Bed Allocation    │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │   MD Queue          │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │   Assessment        │
              │   (Touch 1)         │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────────────┐
              │ Diagnostics Waiting Time    │
              │ (Labs / Imaging delays)     │
              └─────────┬──────────────────┘
                        │
                        ▼
          ┌──────────────────────────────┐
          │ Reassessment Queue            │
          └─────────┬────────────────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Reassessment        │
          │ (Touch 2 / loops)   │
          └─────────┬──────────┘
                    │
        ┌───────────┼──────────────┐
        │           │              │
        ▼           ▼              ▼
   Discharge    More Orders     Consult
                    │              │
                    ▼              ▼
             (back to delays)   Admission
                                      │
                                      ▼
                              ┌────────────────────┐
                              │ Boarding Time Delay │
                              └────────────────────┘
```

---

# Physician Workflow Model (3-Touch System)

```
                ┌────────────────────┐
                │   Patient in Bed    │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Touch 1: Assessment │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Waiting (Diagnostics)
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Touch 2: Reassess   │
                └─────────┬──────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   Discharge        More Orders         Consult
                        │                 │
                        ▼                 ▼
                (returns to delays)   Admission
                          │
                          ▼
                ┌────────────────────┐
                │ Touch 2 (repeat)    │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Touch 3: Disposition│
                └─────────┬──────────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
           Discharge           Admission
```

---

# Queue Interaction Diagram

```
          [Waiting Room Queue]
                    │
                    ▼
               [Bed Allocation]
                    │
                    ▼
                 [MD Queue]
                    │
                    ▼
                (Touch 1)
                    │
                    ▼
        [Diagnostics Waiting Time]
                    │
                    ▼
           [Reassessment Queue]
                    │
                    ▼
                (Touch 2)
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
 Discharge     More Orders     Consult
                    │             │
                    ▼             ▼
        [Diagnostics Waiting]   Admission
                    │             │
                    ▼             ▼
           [Reassessment Queue]   │
                    │             │
                    └──────┬──────┘
                           ▼
                     (Touch 3)
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
      Discharge                  Boarding Time
```

---

## Key System Insight

This model explicitly captures:

* True operational queues (waiting room, MD, reassessment, EMS offload)
* Time-based delays (diagnostics, boarding)
* Interruptible physician workflows
* Feedback loops between queues
* Resource constraints driving congestion

---

# Outputs & Metrics

The simulation produces:

* Per-patient timelines
* Aggregate statistics
* Distribution metrics
* Resource utilization indicators

Example outputs:

* `door_to_doc`
* `bed_to_doc`
* `doc_to_disp`
* `los_minutes`
* `consult_minutes_total`
* `download_minutes`

Outputs are returned as structured JSON and can be persisted for comparison.

---

# Scenario Comparison

Supports structured comparison of scenarios:

* Baseline vs adjusted configurations
* Stored outputs for side-by-side analysis

---

# API

### POST `/simulate`

Runs a simulation with provided configuration.

Input:

* simulation parameters
* scenario metadata

Output:

* metrics
* distributions
* optional comparison linkage

---

# Frontend

The React frontend supports:

* Scenario configuration
* Parameter editing
* Comparison visualization
* Historical run tracking

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

# Limitations

* This is a simulation framework, not a predictive system
* Results depend entirely on input assumptions
* Not intended for direct operational or clinical decision-making without validation

---

# License

MIT License
© 2025 Murray Ware and Anton Massinger
- that’s where this becomes *dangerously convincing* 😄
```
