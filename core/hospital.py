from edems.ed import SingleSiteSim
from inpatient.inpatient import InpatientSystem


class Hospital:
    def __init__(self, env, cfg, eventlog):
        self.env = env
        self.cfg = cfg
        self.eventlog = eventlog

        # ED
        self.ed = SingleSiteSim(
            cfg, external_env=self.env, external_eventlog=self.eventlog
        )

        # Inpatient
        self.inpatient = InpatientSystem(
            env=self.env,
            cfg=cfg.inpatient,
            eventlog=self.eventlog,
        )

    def results(self):
        return self.ed.results()
