import simpy
import random
import numpy as np
import pandas as pd
from collections import deque

results = []
patient_id_counter = 0
import logging

# Set up logging
logging.basicConfig(
    filename='simulation_log.txt',  # Output file
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger()
last_queue_log_time = -999  # ensure it logs at time 0

def format_queue(queue):
    return [f"{p.name} (arrived: {t})" for t, p in queue]


class Physician:
    def __init__(self, name, start_minute, max_new_signups, assess_time1=31, assess_time2=40):
        self.name = name
        self.start_minute = start_minute
        self.max_new_signups = max_new_signups
        self.signup_log = {}
        self.assess_time1 = assess_time1
        self.assess_time2 = assess_time2
        self.resource = None  # Assigned in simulation setup

    def can_accept(self, current_minute):
        total_minutes = current_minute
        day = total_minutes // (24 * 60)
        day_minute = total_minutes % (24 * 60)
        hour_index = (day_minute - self.start_minute) // 60

        if hour_index < 0 or hour_index >= len(self.max_new_signups):
            return False

        key = (day, hour_index)
        return self.signup_log.get(key, 0) < self.max_new_signups[hour_index]

    def register_patient(self, current_minute):
        total_minutes = current_minute
        day = total_minutes // (24 * 60)
        day_minute = total_minutes % (24 * 60)
        hour_index = (day_minute - self.start_minute) // 60

        if hour_index < 0 or hour_index >= len(self.max_new_signups):
            return

        key = (day, hour_index)
        self.signup_log[key] = self.signup_log.get(key, 0) + 1


class Patient:
    def __init__(self, env, name, lab_prob=0.55, di_probs=None, assess1_prob=0.93, long_stay_prob=0.04):
        self.env = env
        self.name = name
        self.arrival_time = env.now
        self.extra_assess_time1 = random.randint(-20, 20)
        self.extra_assess_time2 = random.randint(-20, 20)
        self.lab_time = self.lab_start_time = self.lab_end_time = None
        self.di_time = self.di_start_time = self.di_end_time = None

        self.assess1_req = random.random() < assess1_prob
        self.req_lab = False
        self.req_diagnostic = False
        self.diagnostic_type = None
        self.assess2_req = False
        self.long_treatment = False

        self.LAB_TIME_DIST = None
        self.DI_TIME_DIST_MAP = None
        self.LONG_TREATMENT_TIME_DIST = None
        self.LWBS_THRESHOLD_DIST = None

        if self.assess1_req:
            self.req_lab = random.random() < lab_prob
            di_probs_local = di_probs or {'ultrasound': 0.10, 'CT': 0.1448, 'Xray': 0.2976}
            rnd, cum = random.random(), 0
            for k, p in di_probs_local.items():
                cum += p
                if rnd < cum:
                    self.req_diagnostic = True
                    self.diagnostic_type = k
                    break
            self.assess2_req = self.req_lab or self.req_diagnostic
            self.long_treatment = self.req_lab and self.req_diagnostic and self.assess2_req and random.random() < long_stay_prob

        self.assess1_complete = self.assess2_complete = self.treatment_complete = False
        self.assess1_time = self.assess2_time = None
        self.assess1_phys = self.assess2_phys = None
        self.lwbs_true = False
        self.time_wait_lwbs = None
        self.long_treatment_time = None

def log_patient(p):
    return {
        "name": p.name,
        "arrival": p.arrival_time,
        "assess1_time": p.assess1_time,
        "assess2_time": p.assess2_time,
        "assess1_phys": p.assess1_phys.name if p.assess1_phys else None,
        "assess2_phys": p.assess2_phys.name if p.assess2_phys else None,
        "lwbs": p.lwbs_true,
        "lab_ordered": p.req_lab,
        "lab_time": p.lab_time,
        "lab_start_time": p.lab_start_time,
        "lab_end_time": p.lab_end_time,
        "lab_actual_duration": (p.lab_end_time - p.lab_start_time) if p.lab_start_time and p.lab_end_time else None,
        "di_ordered": p.req_diagnostic,
        "di_type": p.diagnostic_type,
        "di_time": p.di_time,
        "di_start_time": p.di_start_time,
        "di_end_time": p.di_end_time,
        "di_actual_duration": (p.di_end_time - p.di_start_time) if p.di_start_time and p.di_end_time else None
    }

def wait_for_physician(env, physicians):
    while True:
        for phys in physicians:
            if phys.can_accept(env.now):
                req = phys.resource.request()
                yield req
                return phys, req
        yield env.timeout(1)

def patient_process(env, patient, waiting_queue, reassess_queue, physicians):
    global results, assessment_spaces
    log_entries = []
    log_file = open("sim_debug.log", "a")

    def log(msg):
        log_entries.append((env.now, msg))

    yield env.timeout(random.randint(0, 10))  # Random arrival jitter

    patient.time_wait_lwbs = patient.LWBS_THRESHOLD_DIST()
    if patient.long_treatment:
        patient.long_treatment_time = patient.LONG_TREATMENT_TIME_DIST()

    arrival_time = env.now
    log(f"{patient.name} arrives (LWBS threshold: {patient.time_wait_lwbs:.1f})")
    waiting_queue.append((arrival_time, patient))

    while True:
        if patient.lwbs_true or getattr(patient, "processed", False):
            log(f"{patient.name} already LWBS or processed, exiting")
            log_file.close()
            return

        # --- LWBS TIMEOUT ---
        if (env.now - arrival_time) > patient.time_wait_lwbs and not patient.assess1_complete:
            filtered_waiting = [(t, p) for t, p in waiting_queue if p.name != patient.name]
            waiting_queue.clear()
            waiting_queue.extend(filtered_waiting)

            filtered_reassess = [(t, p) for t, p in reassess_queue if p.name != patient.name]
            reassess_queue.clear()
            reassess_queue.extend(filtered_reassess)

            patient.lwbs_true = True
            log(f"{patient.name} LWBS triggered")
            results.append(log_patient(patient))
            log_file.close()
            return


        # --- REASSESSMENT BLOCK ---
        if reassess_queue and assessment_spaces.count < assessment_spaces.capacity:
            _, reassess_patient = reassess_queue.popleft()
            if reassess_patient.lwbs_true or getattr(reassess_patient, "processed", False):
                continue

            with assessment_spaces.request() as req:
                yield req
                reassess_patient.assess2_time = env.now
                reassess_patient.assess2_phys = reassess_patient.assess1_phys
                yield env.timeout(max(1, reassess_patient.assess2_phys.assess_time2 + reassess_patient.extra_assess_time2))
                reassess_patient.assess2_complete = True

                if reassess_patient.long_treatment:
                    yield env.timeout(reassess_patient.long_treatment_time)

                results.append(log_patient(reassess_patient))
                reassess_patient.processed = True
                log(f"{reassess_patient.name} completed reassessment")
                continue

        # --- INITIAL ASSESSMENT BLOCK ---
        elif waiting_queue and assessment_spaces.count < assessment_spaces.capacity:
            _, next_patient = waiting_queue.popleft()

            if next_patient.lwbs_true or not next_patient.assess1_req or getattr(next_patient, "processed", False):
                continue

            with assessment_spaces.request() as req:
                result = yield req | env.timeout(next_patient.time_wait_lwbs)
                if req not in result:
                    next_patient.lwbs_true = True
                    new_waiting = [(t, p) for t, p in waiting_queue if p.name != patient.name]
                    waiting_queue.clear()
                    waiting_queue.extend(new_waiting)

                    new_reassess = [(t, p) for t, p in reassess_queue if p.name != patient.name]
                    reassess_queue.clear()
                    reassess_queue.extend(new_reassess)

                    results.append(log_patient(next_patient))
                    next_patient.processed = True
                    log(f"{next_patient.name} LWBS during wait for assessment")
                    log_file.close()
                    return

                # Acquire physician
                wait_start = env.now
                phys = None

                while env.now - wait_start < next_patient.time_wait_lwbs:
                    for candidate in physicians:
                        if candidate.can_accept(env.now):
                            req_phys = candidate.resource.request()
                            yield req_phys
                            candidate.register_patient(env.now)
                            phys = candidate
                            break
                    if phys:
                        break
                    yield env.timeout(1)

                if not phys:
                    next_patient.lwbs_true = True
                    results.append(log_patient(next_patient))
                    next_patient.processed = True
                    log(f"{next_patient.name} could not find physician in time")
                    log_file.close()
                    return

                # Start assessment
                next_patient.assess1_phys = phys
                next_patient.assess1_time = env.now
                log(f"{next_patient.name} assigned to {phys.name} for initial assessment")

                with req_phys:
                    yield env.timeout(max(1, phys.assess_time1 + next_patient.extra_assess_time1))
                next_patient.assess1_complete = True

                # --- LAB TEST ---
                if next_patient.req_lab:
                    next_patient.lab_time = next_patient.LAB_TIME_DIST()
                    next_patient.lab_start_time = env.now
                    log(f"{next_patient.name} requires lab test, starting at {env.now:.1f}, will take {next_patient.lab_time:.1f} mins")
                    yield env.timeout(next_patient.lab_time)
                    next_patient.lab_end_time = env.now
                    log(f"{next_patient.name}'s lab results returned at {env.now:.1f}")

                # --- DIAGNOSTIC TEST ---
                if next_patient.req_diagnostic:
                    next_patient.di_time = next_patient.DI_TIME_DIST_MAP[next_patient.diagnostic_type]()
                    next_patient.di_start_time = env.now
                    log(f"{next_patient.name} requires {next_patient.diagnostic_type} imaging, starting at {env.now:.1f}, will take {next_patient.di_time:.1f} mins")
                    yield env.timeout(next_patient.di_time)
                    next_patient.di_end_time = env.now
                    log(f"{next_patient.name}'s {next_patient.diagnostic_type} results returned at {env.now:.1f}")


                if next_patient.assess2_req:
                    reassess_queue.append((env.now, next_patient))
                else:
                    results.append(log_patient(next_patient))
                    next_patient.processed = True
                    log(f"{next_patient.name} discharged after assessment")
                    log_file.close()
                    return

        yield env.timeout(1)
    with open("sim_debug.log", "a") as f:
        for t, msg in sorted(log_entries, key=lambda x: x[0]):
            f.write(f"[{t:.1f}] {msg}\n")




def run_fifo_simulation(
    hours,
    arrival_trend,
    physicians,
    lab_time_dist,
    di_time_dist_map,
    long_treatment_time_dist,
    lwbs_threshold_dist,
    assessment_spaces_amount,
    patient_kwargs
):
    global results, assessment_spaces
    results = []
    env = simpy.Environment()
    assessment_spaces = simpy.Resource(env, capacity=assessment_spaces_amount)
    waiting_queue = deque()
    reassess_queue = deque()

    for phys in physicians:
        phys.resource = simpy.Resource(env, capacity=1)

    def patient_generator(env):
        global patient_id_counter
        hour = 0
        while env.now < hours * 60:
            count = np.random.poisson(arrival_trend[hour % len(arrival_trend)])
            arrival_offsets = sorted(np.random.randint(0, 60, size=count))
            for offset in arrival_offsets:
                yield env.timeout(max(0, offset - (env.now % 60)))
                patient = Patient(env, f"Patient_{patient_id_counter}", **patient_kwargs)
                patient.LAB_TIME_DIST = lab_time_dist
                patient.DI_TIME_DIST_MAP = di_time_dist_map
                patient.LONG_TREATMENT_TIME_DIST = long_treatment_time_dist
                patient.LWBS_THRESHOLD_DIST = lwbs_threshold_dist
                env.process(patient_process(env, patient, waiting_queue, reassess_queue, physicians))
                patient_id_counter += 1
            if env.now % 60 != 0:
                yield env.timeout(60 - (env.now % 60))
            hour += 1

    env.process(patient_generator(env))
    env.run()
    return pd.DataFrame(results)
