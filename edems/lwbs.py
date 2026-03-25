class LwbsMixin:
    def _lwbs_draw_fallback(self, is_ems: bool):
        if is_ems and getattr(self.cfg.ems, "lwbs_threshold_draw", None):
            return self.cfg.ems.lwbs_threshold_draw
        return self.cfg.arrivals.lwbs_threshold_draw

    def _lwbs_watch(self, p: "Patient", is_fast: bool):
        if getattr(p, "is_ems", False):
            return
        if getattr(p, "seeded", False):
            return

        # one-shot wait; if the patient gets a bed before this fires, we abort below

        yield self.env.timeout(p.lwbs_threshold)

        # already placed or in protected EMS download → don’t LWBS
        if p.bed_start is not None:
            return
        if p.is_ems and (p.download_start is not None) and (p.download_end is None):
            return

        removed = False
        qname = "FAST" if is_fast else "ACUTE"
        if is_fast:
            try:
                self.fasttrack_q.remove(p.id)
                removed = True
                qlen = len(self.fasttrack_q)
            except ValueError:
                qlen = len(self.fasttrack_q)
        else:
            try:
                self.acute_q.remove(p.id)
                removed = True
                qlen = len(self.acute_q)
            except ValueError:
                qlen = len(self.acute_q)

        if removed:
            p.lwbs = 1
            p.disp_name = "lwbs"
            p.disposition_time = self.env.now
            p.los_minutes = p.disposition_time - p.arrival_time
            self.eventlog.add(
                self.env.now,
                "lwbs",
                pid=p.id,
                queue=qname,
                qlen=qlen,
                area=p.area,
                is_ems=p.is_ems,
            )

    @staticmethod
    def draw_lwbs_threshold_minutes(cfg, p, is_fast: bool) -> float:
        # FAST: short fuse (eg 0.5–2h)
        if is_fast:
            if getattr(cfg, "lwbs", None) and callable(cfg.lwbs.fast_threshold_draw):
                return float(cfg.lwbs.fast_threshold_draw())
            return 90.0  # fallback

        # ACUTE: scale by CTAS (walk-ins only)
        ctas = int(getattr(p, "ctas", 3) or 3)
        if getattr(cfg, "lwbs", None) and callable(cfg.lwbs.acute_threshold_draw):
            base = float(cfg.lwbs.acute_threshold_draw())  # use your config default as center
        else:
            base = 420.0  # ~7h default center

        # widen based on acuity (CTAS 1–2 practically don't LWBS)
        if ctas <= 2:
            return 24*60  # effectively never
        elif ctas == 3:
            return max(150.0, base + 60.0)  # ~7–9h
        else:  # CTAS 4–5
            return max(100.0, base - 60.0)  # ~5–7h
