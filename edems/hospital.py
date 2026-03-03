import simpy
from .eventlog import EventLog
from .ed import SingleSiteSim

class Hospital:
    """
    Minimal wrapper around SingleSiteSim so runner & API don’t change.
    """
    def __init__(self, env: simpy.Environment, cfg, eventlog: EventLog):
        self.env = env
        self.cfg = cfg
        self.eventlog = eventlog

        # Only ED skeleton for now
        self.ed = SingleSiteSim(cfg, external_env=self.env, external_eventlog=self.eventlog)

    def results(self):
        return self.ed.results()
