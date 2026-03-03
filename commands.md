# ED + EMS + Inpatient (Single/Multi-Hospital) Simulation

A discrete-event (SimPy) simulation that models:
- ED with acuity-based bed allocation (A/B areas), doctors with shift/quotas/panel caps, nurse execution (team/ratio).
- EMS offload with offload nurses, download area, direct-to-bed logic, crew hospital time.
- Inpatient units (Medicine/Surgery/ICU) with real admission queues and LOS-based discharges.
- ED boarding until inpatient bed is ready.
- Optional direct admits per inpatient unit (Poisson by hour).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_system.py
