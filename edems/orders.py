# edems/orders.py
from __future__ import annotations
import random

class OrdersMixin:
    """Orders logic: assign flags at arrival; run labs/DI when required."""

    def _init_orders(self):
        # --- Labs ---
        self._lab_prob = float(getattr(self.cfg.orders, "lab_prob", 0.0) or 0.0)
        self._lab_critical_prob = float(getattr(self.cfg.orders, "lab_critical_prob", 0.10) or 0.0)
        self._lab_time_draw = getattr(self.cfg.orders, "lab_time_draw", None)
        self._lab_work_draw = getattr(self.cfg.orders, "lab_work_draw", None)  # reserved for later

        # --- DI ---
        self._di_prob = float(getattr(self.cfg.orders, "di_prob", 0.0) or 0.0)
        self._di_time_draw_map = getattr(self.cfg.orders, "di_time_draw_map", {}) or {}
        self._di_modalities = list(self._di_time_draw_map.keys())

    def _orders_on_arrival(self, p):
        # Labs flag
        try:
            p.requires_lab = 1 if (random.random() < self._lab_prob) else 0
        except Exception:
            p.requires_lab = 0

        # DI flag + modality
        try:
            if random.random() < self._di_prob and self._di_modalities:
                p.requires_di = 1
                p.di_modality = random.choice(self._di_modalities)
            else:
                p.requires_di = 0
                p.di_modality = None
        except Exception:
            p.requires_di = 0
            p.di_modality = None


        self.eventlog.add(
            self.env.now, "orders_on_arrival",
            pid=p.id,
            requires_lab=p.requires_lab, lab_prob=self._lab_prob,
            requires_di=p.requires_di, di_prob=self._di_prob, di_modality=p.di_modality
        )

    # -------------------------
    # Labs (blocking for patient)
    # -------------------------
    def _run_labs(self, p):
        p.lab_start = self.env.now
        self.eventlog.add(self.env.now, "lab_start", pid=p.id)

        tat = 0.0
        try:
            if callable(self._lab_time_draw):
                tat = float(self._lab_time_draw())
        except Exception:
            pass
        if tat <= 0:
            tat = 45.0

        yield self.env.timeout(tat)

        p.lab_end = self.env.now
        p.lab_minutes = p.lab_end - p.lab_start
        try:
            p.lab_is_critical = 1 if (random.random() < self._lab_critical_prob) else 0
        except Exception:
            p.lab_is_critical = 0

        self.eventlog.add(self.env.now, "lab_end", pid=p.id, minutes=p.lab_minutes, critical=p.lab_is_critical)

    # -------------------------
    # Diagnostic Imaging (blocking for patient)
    # -------------------------
    def _run_di(self, p):
        """Run DI for the patient (single modality chosen at arrival)."""
        if not getattr(p, "requires_di", 0) or not getattr(p, "di_modality", None):
            return  # nothing to do

        p.di_start = self.env.now
        self.eventlog.add(self.env.now, "di_start", pid=p.id, modality=p.di_modality)

        dur = 0.0
        try:
            draw = self._di_time_draw_map.get(p.di_modality)
            if callable(draw):
                dur = float(draw())
        except Exception:
            pass
        if dur <= 0:
            # fallback if modality missing or draw misconfigured
            dur = 45.0

        yield self.env.timeout(dur)

        p.di_end = self.env.now
        p.di_minutes = p.di_end - p.di_start
        self.eventlog.add(self.env.now, "di_end", pid=p.id, modality=p.di_modality, minutes=p.di_minutes)
