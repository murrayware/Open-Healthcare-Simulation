import numpy as np
import simpy
import random

class ArrivalPolicy:
    """
    Walk-in arrival generator (REPEATS every 24 hours).
    - Requires cfg.arrivals.walkin_hourly_lambda length == 24.
    - Cycles daily: hour N uses index (N % 24).
    """
    def __init__(self, cfg):
        self.cfg = cfg

    def start(self, env: simpy.Environment, *, make_patient_cb):
        env.process(self._walkins(env, make_patient_cb))

    def _walkins(self, env, make_patient_cb):
        hourly = self.cfg.arrivals.walkin_hourly_lambda
        assert len(hourly) == 24, "walkin_hourly_lambda must have length 24 (one day)."
        lwbs_draw = self.cfg.arrivals.lwbs_threshold_draw
        hour_idx = 0

        while True:
            k = int(np.random.poisson(hourly[hour_idx % 24]))
            offsets = sorted(np.random.randint(0, 60, size=k).tolist())
            for off in offsets:
                yield env.timeout(max(0, off - (env.now % 60)))
                make_patient_cb(ctas=None, is_ems=False, lwbs_draw=lwbs_draw)

            if env.now % 60 != 0:
                yield env.timeout(60 - (env.now % 60))
            hour_idx += 1

class EMSArrivalPolicy:
    """
    EMS arrival generator (REPEATS every 24 hours).
    - Requires cfg.ems.hourly_lambda length == 24.
    - Uses cfg.ems.ctas_mix to sample CTAS.
    - For EMS, LWBS threshold draw can be overridden by cfg.ems.lwbs_threshold_draw.
    - Cycles daily: hour N uses index (N % 24).
    """
    def __init__(self, cfg):
        self.cfg = cfg

    def start(self, env: simpy.Environment, *, make_patient_cb):
        env.process(self._ems(env, make_patient_cb))

    def _ems(self, env, make_patient_cb):
        hourly = self.cfg.ems.hourly_lambda
        assert len(hourly) == 24, "ems.hourly_lambda must have length 24 (one day)."
        ctas_mix = self.cfg.ems.ctas_mix
        ctas_keys = sorted(ctas_mix.keys())
        probs = np.array([ctas_mix[k] for k in ctas_keys], dtype=float)
        probs = probs / probs.sum() if probs.sum() > 0 else np.ones(len(ctas_keys))/len(ctas_keys)
        lwbs_draw = getattr(self.cfg.ems, "lwbs_threshold_draw", None) or self.cfg.arrivals.lwbs_threshold_draw
        hour_idx = 0

        while True:
            k = int(np.random.poisson(hourly[hour_idx % 24]))
            offsets = sorted(np.random.randint(0, 60, size=k).tolist())
            for off in offsets:
                yield env.timeout(max(0, off - (env.now % 60)))
                ctas_val = int(np.random.choice(ctas_keys, p=probs))
                make_patient_cb(ctas=ctas_val, is_ems=True, lwbs_draw=lwbs_draw)

            if env.now % 60 != 0:
                yield env.timeout(60 - (env.now % 60))
            hour_idx += 1
