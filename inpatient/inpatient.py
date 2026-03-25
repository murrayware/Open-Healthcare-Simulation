import simpy
from inpatient.unit import InpatientUnit


class InpatientSystem:
    def __init__(self, env, cfg, eventlog):
        self.env = env
        self.cfg = cfg
        self.eventlog = eventlog

        self.units = {
            name: InpatientUnit(env, spec, eventlog)
            for name, spec in cfg.units.items()
        }

    def admit(self, patient, unit_name):
        unit = self.units[unit_name]
        return self.env.process(unit.admit(patient))
