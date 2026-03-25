from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Tuple


class EDDispatchMixin:
    """Queue scoring, doctor assignment, and bed dispatch only."""

    def _in_download_now(self, p) -> bool:
        return (getattr(p, "download_start", None) is not None) and (
            getattr(p, "download_end", None) is None
        )

    def _acute_rule_bonuses(self, p) -> float:
        EMS_CRIT_BONUS = 5.0
        DOWNLOAD_BONUS = 5.0
        bonus = 0.0

        if getattr(p, "is_ems", False) and getattr(p, "is_critical", False):
            bonus += EMS_CRIT_BONUS
        if self._in_download_now(p):
            bonus += DOWNLOAD_BONUS

        return bonus

    def _eff_acute_score(self, p) -> float:
        a = float(getattr(p, "acuity", 0.0) or 0.0)
        b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)
        r = self._acute_rule_bonuses(p)
        return a + b + r

    def _queue_priority(self, p, area: str, now: float) -> float:
        """
        Priority = base acuity + acuity_bonus
                 + (time_waiting_hours * area_weight * CTAS_multiplier)
                 + optional download_bonus (only for ACUTE).
        """
        base = float(getattr(p, "acuity", 0.0) or 0.0) + float(
            getattr(p, "acuity_bonus", 0.0) or 0.0
        )

        if self._in_download_now(p):
            waited_min = now - getattr(p, "download_start", now)
            in_download = True
        else:
            waited_min = now - getattr(p, "arrival_time", now)
            in_download = False

        waited_hr = max(0.0, float(waited_min)) / 60.0

        qcfg = getattr(self.cfg, "queue", None)
        acute_w = float(getattr(qcfg, "acute_time_weight", 0.8))
        fast_w = float(getattr(qcfg, "fast_time_weight", 0.35))
        dl_w = float(getattr(qcfg, "download_wait_weight", 1.2))
        ctas_mults = getattr(
            qcfg, "ctas_wait_mult", {1: 2.0, 2: 1.6, 3: 1.2, 4: 1.0, 5: 0.8}
        )

        time_w = fast_w if area == getattr(self, "_ft_name", "FAST") else acute_w
        ctas = int(getattr(p, "ctas", 3) or 3)
        c_mul = float(ctas_mults.get(ctas, 1.0))

        download_bonus = (
            (dl_w * waited_hr)
            if (in_download and area != getattr(self, "_ft_name", "FAST"))
            else 0.0
        )

        return base + (time_w * waited_hr * c_mul) + download_bonus

    def _assign_doctor(self, p, area: str):
        doc = self.docmgr.try_signup(area, self.env.now)
        if not doc:
            return None

        p.doctor_name = doc["name"]
        self.eventlog.add(
            self.env.now,
            "doctor_assigned",
            pid=p.id,
            area=area,
            doctor=p.doctor_name,
            doc_active_panel=doc["active_panel"],
        )
        return doc

    def _release_doctor_panel(self, doc):
        self.docmgr.release_panel(doc)

    def _draw_assess_minutes(self, doc):
        return self.docmgr.assess_minutes(doc)

    def _reassess_minutes(self, doc):
        return self.docmgr.reassess_minutes(doc)

    @staticmethod
    def _day_anchor(now_min: float) -> int:
        return (int(now_min) // 1440) * 1440

    def _doc_on_shift(self, doc: Dict[str, Any], now_min: float) -> bool:
        day0 = self._day_anchor(now_min)
        s = day0 + doc["start_min"]
        e = s + doc["shift_min"]
        if doc["shift_min"] >= 1440:
            return True
        if e <= day0 + 1440:
            return s <= now_min < e
        return (now_min >= s) or (now_min < (e - 1440))

    @staticmethod
    def _abs_hour(now_min: float) -> int:
        return int(now_min // 60)

    @staticmethod
    def _hour_of_day(now_min: float) -> int:
        return int((now_min % 1440) // 60)

    def _refresh_acute_queue_once(self):
        seen = set()
        uniq = []

        for pid in list(self.acute_q):
            if pid in seen:
                continue
            p = self.patients.get(pid)
            if p is None:
                continue
            seen.add(pid)
            uniq.append(pid)

        uniq.sort(
            key=lambda pid: (
                -self._eff_acute_score(self.patients[pid]),
                float(getattr(self.patients[pid], "arrival_time", 0.0)),
            )
        )

        if hasattr(self.acute_q, "clear") and hasattr(self.acute_q, "extend"):
            self.acute_q.clear()
            self.acute_q.extend(uniq)
        else:
            self.acute_q = deque(uniq)

        try:
            top = uniq[:5]
            snap = [
                dict(
                    pid=pid,
                    score=self._eff_acute_score(self.patients[pid]),
                    acuity=float(getattr(self.patients[pid], "acuity", 0.0) or 0.0),
                    bonus=float(
                        getattr(self.patients[pid], "acuity_bonus", 0.0) or 0.0
                    ),
                    rules=self._acute_rule_bonuses(self.patients[pid]),
                )
                for pid in top
            ]
            self.eventlog.add(
                self.env.now, "acute_queue_refresh", top5=snap, size=len(uniq)
            )
        except Exception:
            pass

    def _acute_queue_refresher(self):
        while True:
            self._refresh_acute_queue_once()
            yield self.env.timeout(5)

    def _acute_bed_dispatcher(self):
        EMS_CRIT_BONUS = 5.0
        DOWNLOAD_BONUS = 5.0

        while True:
            placed = False

            if self.acute_q:
                cand: List[Tuple[int, str, float, float]] = []

                for pid in list(self.acute_q):
                    p = self.patients.get(pid)
                    if p is None:
                        continue

                    area = p.area
                    if area not in self._cap or self._busy[area] >= self._cap[area]:
                        continue

                    a = float(getattr(p, "acuity", 0.0) or 0.0)
                    b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)
                    emscrit = (
                        EMS_CRIT_BONUS
                        if (
                            getattr(p, "is_ems", False)
                            and getattr(p, "is_critical", False)
                        )
                        else 0.0
                    )
                    dload = DOWNLOAD_BONUS if self._in_download_now(p) else 0.0
                    score = self._queue_priority(p, area, self.env.now)
                    cand.append((pid, area, score, p.arrival_time))

                    self.eventlog.add(
                        self.env.now,
                        "dispatch_cand",
                        pid=pid,
                        area=area,
                        acuity=a,
                        bonus_time=b,
                        bonus_emscrit=emscrit,
                        bonus_download=dload,
                        score=score,
                    )

                if cand:
                    cand.sort(key=lambda t: (-t[2], t[3]))
                    pid, area, score, _ = cand[0]

                    doc = self._assign_doctor(self.patients[pid], area)
                    if doc is None:
                        yield self.env.timeout(1)
                        continue

                    try:
                        self.acute_q.remove(pid)
                    except ValueError:
                        self._release_doctor_panel(doc)
                        yield self.env.timeout(0.1)
                        continue

                    self._busy[area] += 1
                    p = self.patients[pid]
                    p.bed_start = self.env.now

                    if self._in_download_now(p):
                        p.download_end = self.env.now
                        p.download_minutes = p.download_end - p.download_start
                        self._download_busy = max(0, self._download_busy - 1)
                        self.eventlog.add(
                            self.env.now,
                            "download_end",
                            pid=pid,
                            minutes=p.download_minutes,
                            busy=self._download_busy,
                            cap=self._download_cap,
                        )

                    a = float(getattr(p, "acuity", 0.0) or 0.0)
                    b = float(getattr(p, "acuity_bonus", 0.0) or 0.0)
                    emscrit = (
                        EMS_CRIT_BONUS
                        if (
                            getattr(p, "is_ems", False)
                            and getattr(p, "is_critical", False)
                        )
                        else 0.0
                    )
                    dload = DOWNLOAD_BONUS if self._in_download_now(p) else 0.0

                    self.eventlog.add(
                        self.env.now,
                        "bed_start",
                        pid=pid,
                        area=area,
                        busy=self._busy[area],
                        cap=self._cap[area],
                        is_ems=p.is_ems,
                        doctor=p.doctor_name,
                        chosen_acuity=a,
                        chosen_bonus_time=b,
                        chosen_bonus_emscrit=emscrit,
                        chosen_bonus_download=dload,
                        chosen_score=(a + b + emscrit + dload),
                    )

                    if p.download_start is not None and p.download_end is None:
                        p.download_end = self.env.now
                        p.download_minutes = p.download_end - p.download_start
                        self._download_busy = max(0, self._download_busy - 1)
                        if hasattr(self, "_download_patients"):
                            self._download_patients.pop(p.id, None)
                        self.eventlog.add(
                            self.env.now,
                            "download_end",
                            pid=pid,
                            minutes=p.download_minutes,
                            busy=self._download_busy,
                            cap=self._download_cap,
                        )
                        if hasattr(self, "_try_fill_download_from_waitlist"):
                            self._try_fill_download_from_waitlist()

                    self.env.process(
                        self._treat_acute_with_assigned_doctor(p, area, doc)
                    )
                    placed = True

            yield self.env.timeout(0 if placed else 1)

    def _try_fill_download_from_waitlist(self):
        while self._download_busy < self._download_cap and self._download_wait:
            pid_wait = self._download_wait.popleft()
            p_wait = self.patients.get(pid_wait)
            if p_wait is None or p_wait.download_start is not None:
                continue
            self._place_into_download(p_wait)

    def _fasttrack_bed_dispatcher(self):
        while True:
            placed = False

            while self.fasttrack_q and self._ft_busy < self._ft_cap:
                pid = self.fasttrack_q.popleft()
                p = self.patients.get(pid)
                if p is None:
                    continue

                doc = self._assign_doctor(p, self._ft_name)
                if doc is None:
                    self.fasttrack_q.appendleft(pid)
                    yield self.env.timeout(1)
                    continue

                self._ft_busy += 1
                p.bed_start = self.env.now
                self.eventlog.add(
                    self.env.now,
                    "bed_start",
                    pid=pid,
                    area=self._ft_name,
                    busy=self._ft_busy,
                    cap=self._ft_cap,
                    is_ems=p.is_ems,
                    doctor=p.doctor_name,
                )

                self.env.process(
                    self._treat_fast_with_assigned_doctor(p, self._ft_name, doc)
                )
                placed = True

            if not placed:
                yield self.env.timeout(1)
            else:
                yield self.env.timeout(0)
