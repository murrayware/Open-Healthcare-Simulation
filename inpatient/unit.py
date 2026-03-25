import simpy


class InpatientUnit:
    def __init__(self, env, spec, eventlog):
        self.env = env
        self.spec = spec
        self.eventlog = eventlog

        self.resource = simpy.Resource(env, capacity=spec.beds)

    def admit(self, patient):
        # Patient requests a bed (FIFO queue handled by SimPy)
        self.eventlog.add(self.env.now, "bed_request", pid=patient.pid, unit=self.spec.name)

        with self.resource.request() as req:
            yield req  # ← THIS is your boarding queue

            # Got bed
            self.eventlog.add(self.env.now, "bed_assigned", pid=patient.pid, unit=self.spec.name)

            # Length of stay
            los = self.spec.los_draw()

            yield self.env.timeout(los)

            # Discharge
            self.eventlog.add(self.env.now, "discharged", pid=patient.pid, unit=self.spec.name)
