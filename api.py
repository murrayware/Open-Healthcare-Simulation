import io
import os
import json
import math
import random
import numpy as np
import pandas as pd
import simpy
from typing import Any, Dict, Callable

from flask import Flask, request, jsonify, Response, send_file, send_from_directory, g, current_app
from flask_cors import CORS

from auth import auth_bp, init_auth, login_required
from database.users_table import get_user_by_id
from database import outputs_table, compare_table
from sqlalchemy import text
from database.users_table import engine

import mimetypes

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# --- Your internal modules ---
from edems.utils import u
from edems.eventlog import EventLog
from edems.hospital import Hospital
from edems.config import (
    SimConfig, AreaConfig, NurseModelConfig, DoctorConfig,
    ArrivalsConfig, EMSConfig, TriageWeights, OrdersConfig,
    # ConsultConfig,
    DispositionConfig, CapabilitiesConfig,
    InpatientUnitSpec, InpatientConfig, FastTrackConfig
)
from edems.analytics import summarize_patients

def _clean_numpy_scalar(x):
    """Convert numpy scalars to plain Python and NaN to None."""
    try:
        if pd.isna(x):   # catches NaN/NaT
            return None
    except Exception:
        pass
    if isinstance(x, (np.generic,)):
        return x.item()
    return x

def _to_minutes_if_timedelta(s: pd.Series) -> pd.Series:
    """Convert timedelta series to minutes; otherwise return as-is."""
    if pd.api.types.is_timedelta64_dtype(s):
        return s.dt.total_seconds() / 60.0
    return s

def _numeric_series_stats(s: pd.Series) -> dict:
    """
    Compute distribution + stats for a numeric (or convertible) series.
    Returns list_times + metrics dict. Uses sample variance (ddof=1).
    """
    # Normalize dtype (convert timedeltas, coerce to numeric)
    s = _to_minutes_if_timedelta(s)
    s = pd.to_numeric(s, errors="coerce")

    # Drop NaNs; keep original order
    vals = s.dropna().astype(float).tolist()
    n = len(vals)

    out = {
        "list_times": vals,  # already plain Python floats
        "metrics": {
            "count": n,
            "mean": None,
            "median": None,
            "variance": None,   # sample variance (ddof=1)
            "p75": None,
            "p90": None,
            "min": None,
            "max": None,
        }
    }

    if n == 0:
        return out

    v = np.array(vals, dtype=float)
    out["metrics"]["mean"]    = float(np.mean(v))
    out["metrics"]["median"]  = float(np.percentile(v, 50))
    out["metrics"]["p75"]     = float(np.percentile(v, 75))
    out["metrics"]["p90"]     = float(np.percentile(v, 90))
    out["metrics"]["min"]     = float(np.min(v))
    out["metrics"]["max"]     = float(np.max(v))
    # variance: sample variance if n>1 else 0.0 (or None—choose 0.0 for convenience)
    out["metrics"]["variance"] = float(np.var(v, ddof=1)) if n > 1 else 0.0

    return out

def make_numeric_metrics_payload(df: pd.DataFrame, include_columns: list[str] | None = None) -> dict:
    """
    Build { column_name: { list_times: [...], metrics: {...} } } for numeric-ish columns.
    If include_columns is provided, only compute for those columns (if present).
    Also converts any timedelta columns to minutes first.
    """
    if df is None or len(df) == 0:
        return {}

    # Normalize timedeltas to minutes for detection
    df_norm = df.copy()
    for col in df_norm.columns:
        if pd.api.types.is_timedelta64_dtype(df_norm[col]):
            df_norm[col] = _to_minutes_if_timedelta(df_norm[col])

    # Decide which columns to include
    if include_columns:
        cols = [c for c in include_columns if c in df_norm.columns]
    else:
        # All numeric columns after normalization
        cols = df_norm.select_dtypes(include=[np.number]).columns.tolist()

        # Heuristic: also grab columns that *look* like durations by name
        # even if pandas didn't infer numeric (edge cases)
        for c in df.columns:
            name = c.lower()
            if any(k in name for k in ["mins", "minutes", "sec", "seconds", "wait", "delay", "time", "los"]):
                if c not in cols:
                    # Try to coerce—if at least 1 numeric present after coercion, include it
                    test = pd.to_numeric(_to_minutes_if_timedelta(df[c]), errors="coerce")
                    if test.notna().any():
                        cols.append(c)

    payload = {}
    for c in cols:
        payload[c] = _numeric_series_stats(df[c])

    return payload


def build_physician_metrics(df: pd.DataFrame) -> dict:
    """
    Build physician-specific metrics from the detailed patient dataframe.
    Returns a dict with structure:
    {
        "physician_name": {
            "doc_to_disp": [list of times],
            "bed_to_doc": [list of times],
            "treatment_start": [list of times]
        }
    }
    """
    if df is None or len(df) == 0 or 'doctor' not in df.columns:
        return {}

    physicians = {}
    
    # Group by doctor
    for doctor_name, group in df.groupby('doctor'):
        # Skip null/None doctor names
        if pd.isna(doctor_name) or doctor_name is None:
            continue
        
        physician_data = {}
        
        # Extract doc_to_disp times (filter out NaN values)
        if 'doc_to_disp' in group.columns:
            doc_to_disp_values = group['doc_to_disp'].dropna().tolist()
            physician_data['doc_to_disp'] = [float(v) for v in doc_to_disp_values]
        else:
            physician_data['doc_to_disp'] = []
        
        # Extract bed_to_doc times (filter out NaN values)
        if 'bed_to_doc' in group.columns:
            bed_to_doc_values = group['bed_to_doc'].dropna().tolist()
            physician_data['bed_to_doc'] = [float(v) for v in bed_to_doc_values]
        else:
            physician_data['bed_to_doc'] = []
        
        # Extract treatment_start times (filter out NaN values)
        if 'treatment_start' in group.columns:
            treatment_start_values = group['treatment_start'].dropna().tolist()
            physician_data['treatment_start'] = [float(v) for v in treatment_start_values]
        else:
            physician_data['treatment_start'] = []
        
        physicians[str(doctor_name)] = physician_data
    print(physicians)
    return physicians


def build_di_metrics(df: pd.DataFrame) -> dict:
    """
    Build diagnostic imaging (DI) test-specific metrics from the detailed patient dataframe.
    Returns a dict with structure:
    {
        "di_modality_name": {
            "di_minutes": [list of times]
        }
    }
    """
    if df is None or len(df) == 0 or 'di_modality' not in df.columns:
        return {}

    di_tests = {}
    
    # Group by di_modality
    for modality_name, group in df.groupby('di_modality'):
        # Skip null/None modality names
        if pd.isna(modality_name) or modality_name is None:
            continue
        
        di_data = {}
        
        # Extract di_minutes times (filter out NaN values)
        if 'di_minutes' in group.columns:
            di_minutes_values = group['di_minutes'].dropna().tolist()
            di_data['di_minutes'] = [float(v) for v in di_minutes_values]
        else:
            di_data['di_minutes'] = []
        
        di_tests[str(modality_name)] = di_data
    
    return di_tests


def _jsonable(v):
    # normalize numpy scalars and NaNs
    if isinstance(v, (np.floating, np.integer, np.bool_)):
        return v.item()
    if isinstance(v, (pd.Timestamp, pd.Timedelta)):
        return v.isoformat() if isinstance(v, pd.Timestamp) else v.total_seconds()
    try:
        # pd.isna works for numpy/pandas dtypes; avoid for pure python objects
        if pd.isna(v):  # noqa: E402
            return None
    except Exception:
        pass
    return v


def df_to_records_clean(obj):
    """
    Accepts a DataFrame OR a Series and returns a list[dict] with NaN->None
    and numpy scalars coerced to Python types.
    """
    if obj is None:
        return []

    # If it's already a Series, make it a single-row DataFrame
    if isinstance(obj, pd.Series):
        obj = obj.to_frame().T

    if isinstance(obj, pd.DataFrame):
        # Replace NaN/NaT with None for JSON
        df = obj.where(pd.notnull(obj), None)
        records = df.to_dict(orient="records")
        return [{k: _jsonable(v) for k, v in rec.items()} for rec in records]

    # Fallbacks for odd inputs
    if isinstance(obj, dict):
        return [{k: _jsonable(v) for k, v in obj.items()}]
    if hasattr(obj, "to_dict"):
        d = obj.to_dict()
        if isinstance(d, dict):
            return [{k: _jsonable(v) for k, v in d.items()}]
    return [_jsonable(obj)]


# app = Flask(__name__)
# CORS(app)

mimetypes.add_type('application/javascript', '.js')

# Load root .env if python-dotenv is available.
if load_dotenv:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def _normalize_build_env(value: str | None) -> str:
    if value is None:
        return "dev"
    normalized = value.strip().strip("\"").strip("'").lower()
    if normalized not in {"dev", "prod"}:
        return "dev"
    return normalized


# Dynamically set the static folder based on BUILD_ENV (dev/prod)
build_env = _normalize_build_env(os.environ.get("BUILD_ENV", "dev"))
static_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client", "dist", build_env)

app = Flask(__name__, static_folder=static_folder_path, static_url_path='')

CORS(app)

import secrets, os

# prefer explicit env var; fall back to a stable dev secret so tokens remain valid across restarts
secret = os.environ.get("FLASK_SECRET")
if not secret:
    secret = os.environ.get("DEV_FLASK_SECRET", "dev-secret")  # set DEV_FLASK_SECRET if you want custom dev secret
    app.logger.warning("FLASK_SECRET not set — using fallback dev secret (tokens persist across restarts only if you set an env var).")

app.config["SECRET_KEY"] = secret
app.config["USER_DB_PATH"] = os.path.join(os.path.dirname(__file__), "users.db")


app.register_blueprint(auth_bp)
init_auth(app)

app.logger.info("BUILD_ENV=%s static_folder=%s", build_env, static_folder_path)


def _serve_spa_index_or_help():
    index_path = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, "index.html")

    return (
        jsonify({
            "error": "Frontend build not found",
            "build_env": build_env,
            "expected_index": index_path,
            "how_to_build": [
                "cd client",
                "npm run build:dev  # for BUILD_ENV=dev",
                "npm run build:prod # for BUILD_ENV=prod",
            ],
        }),
        503,
    )


# --------------- Helpers ---------------

def _const(x: float) -> Callable[[], float]:
    return lambda: float(x)

def _int_const(x: int) -> Callable[[], int]:
    return lambda: int(x)

def normalize_dist_spec(spec: Any) -> Any:
    """
    Convert CSV template format {"type": "uniform", "low": X, "high": Y}
    to nested format {"uniform": [X, Y]} for draw_from_spec.
    """
    if not isinstance(spec, dict):
        return spec
    
    dist_type = spec.get("type")
    if not dist_type:
        return spec  # Already in nested format
    
    if dist_type == "uniform":
        return {"uniform": [spec.get("low", 0), spec.get("high", 1)]}
    elif dist_type == "lognormal":
        return {"lognormal": {"mean": spec.get("mean", 4.5), "sigma": spec.get("sigma", 0.35)}}
    elif dist_type == "normal":
        return {"normal": {"mu": spec.get("mu", 0), "sigma": spec.get("sd", 1)}}
    elif dist_type == "constant":
        return spec.get("value", 0)
    else:
        return spec  # Unknown type, pass through

def draw_from_spec(spec: Any) -> Callable[[], float]:
    """
    Convert a JSON-friendly distribution spec into a callable draw() -> float.

    Accepted forms:
      - number -> constant draw
      - {"uniform":[a,b]}
      - {"randint":[a,b]}  # inclusive
      - {"lognormal":{"mean":m,"sigma":s}}  # returns minutes
      - {"choice":[v1,v2,...]}             # choose one of listed constants
    """
    if spec is None:
        return _const(0.0)

    if isinstance(spec, (int, float)):
        return _const(spec)

    if isinstance(spec, dict):
        if "uniform" in spec:
            a, b = spec["uniform"]
            return lambda: float(np.random.uniform(a, b))
        if "randint" in spec:
            a, b = spec["randint"]
            return lambda: int(np.random.randint(a, b + 1))
        if "lognormal" in spec:
            params = spec["lognormal"]
            m = params.get("mean", 4.5)
            s = params.get("sigma", 0.35)
            return lambda: float(np.random.lognormal(mean=m, sigma=s))
        if "choice" in spec:
            arr = list(spec["choice"])
            return lambda: float(random.choice(arr))

    raise ValueError(f"Unsupported draw spec: {spec}")

def di_time_map_from_spec(spec_map: Dict[str, Any]) -> Dict[str, Callable[[], float]]:
    out = {}
    for k, v in spec_map.items():
        out[k] = draw_from_spec(v)
    return out

def safe_bool(d: Dict, key: str, default: bool) -> bool:
    if key not in d: return default
    v = d[key]
    if isinstance(v, bool): return v
    if isinstance(v, str): return v.lower() in ("1", "true", "yes", "y", "on")
    return bool(v)

# --------------- Config Builders ---------------

def build_inpatient(cfg: Dict[str, Any]) -> InpatientConfig:
    units_json = cfg.get("units", {
        "Medicine": {"beds": 20, "los_draw": {"lognormal": {"mean": 4.5, "sigma": 0.35}}},
        "Surgery":  {"beds": 12, "los_draw": {"lognormal": {"mean": 4.2, "sigma": 0.40}}},
        "ICU":      {"beds": 6,  "los_draw": {"uniform": [12*60, 72*60]}},
    })

    units = {}
    for name, ucfg in units_json.items():
        beds = int(ucfg.get("beds", 10))
        los_draw_spec = ucfg.get("los_draw", {"uniform":[240, 600]})
        
        # Extract consult parameters
        consult_p = float(ucfg.get("consult_p", 0.0))
        consult_admit_p = float(ucfg.get("consult_admit_p", 0.0))
        consult_time_spec = ucfg.get("consult_time_dist")
        consult_time_draw = draw_from_spec(normalize_dist_spec(consult_time_spec)) if consult_time_spec else None
        
        units[name] = InpatientUnitSpec(
            name=name,
            beds=beds,
            los_draw=draw_from_spec(los_draw_spec),
            consult_p=consult_p,
            consult_admit_p=consult_admit_p,
            consult_time_draw=consult_time_draw
        )

    # map services to units (simple demo mapping if not provided)
    svc_map = cfg.get("service_to_unit", None)
    if svc_map and isinstance(svc_map, dict):
        # build a closure that uses this dict (keys are strings of service_id or ranges)
        mapping = {}
        for k, v in svc_map.items():
            mapping[k] = v
        def service_to_unit(service_id: int) -> str:
            key = str(service_id)
            if key in mapping: return mapping[key]
            # fallback: buckets by mod
            mod = service_id % 10
            if mod in (1,2,3,4,5): return "Medicine"
            if mod in (6,7,8):     return "Surgery"
            return "ICU"
    else:
        def service_to_unit(service_id: int) -> str:
            mod = service_id % 10
            if mod in (1,2,3,4,5): return "Medicine"
            if mod in (6,7,8):     return "Surgery"
            return "ICU"

    return InpatientConfig(
        units=units,
        service_to_unit=service_to_unit,
        direct_admits_enabled=safe_bool(cfg, "direct_admits_enabled", True),
        direct_admit_hours=int(cfg.get("direct_admit_hours", 12)),
        direct_admit_hourly_lambda=cfg.get("direct_admit_hourly_lambda", {
            "Medicine": [2,2,3,3,4,4,4,4,3,3,2,2],
            "Surgery":  [1,1,1,2,2,2,2,2,2,1,1,1],
            "ICU":      [0.2]*12
        })
    )

def build_areas(cfg: Dict[str, Any]) -> Dict[str, AreaConfig]:
    """
    areas: {
      "A": {"beds": 10, "nurse_model":{"model":"ratio","ratio":2,"lab_support":true}},
      "B": {"beds": 8,  "nurse_model":{"model":"team","team_nurses":3,"lab_support":false}}
    }
    """
    areas = {}
    for name, acfg in cfg.items():
        nm = acfg.get("nurse_model", {})
        nurse_model = NurseModelConfig(
            model=nm.get("model", "ratio"),
            ratio=nm.get("ratio", 2),
            team_nurses=nm.get("team_nurses", 2),
            lab_support=safe_bool(nm, "lab_support", True),
        )
        areas[name] = AreaConfig(
            name=name,
            beds=int(acfg.get("beds", 8)),
            nurse_model=nurse_model
        )
    return areas

def build_doctors(cfg_list: Any) -> list:
    """
    doctors: [
      {
        "name":"DrA1","area":"A","start_minute":480,"shift_minutes":600,
        "hourly_max_signups":[3,3,2,2,2,1,1,1,1,1],
        "max_active_panel": 8,
        "assess_time_draw":{"uniform":[15,100]},
        "reassess_time_draw":{"uniform":[15,100]}
      },
      ...
    ]
    """
    out = []
    for d in cfg_list:
        out.append(DoctorConfig(
            name=d["name"],
            area=d["area"],
            start_minute=int(d.get("start_minute", 8*60)),
            shift_minutes=int(d.get("shift_minutes", 10*60)),
            hourly_max_signups=list(d.get("hourly_max_signups", [3,3,2,2,2,1,1,1,1,1])),
            max_active_panel=int(d.get("max_active_panel", 8)),
            assess_time_draw=draw_from_spec(d.get("assess_time_draw", {"uniform":[15,100]})),
            reassess_time_draw=draw_from_spec(d.get("reassess_time_draw", {"uniform":[15,100]})),
        ))
    return out

def build_arrivals(cfg: Dict[str, Any]) -> ArrivalsConfig:
    return ArrivalsConfig(
        hours=int(cfg.get("hours", 12)),
        walkin_hourly_lambda=list(cfg.get("walkin_hourly_lambda", [6,8,10,12,14,16,18,16,14,12,10,8])),
        lwbs_threshold_draw=draw_from_spec(cfg.get("lwbs_threshold_draw", {"uniform":[60,240]}))
    )

def build_ems(cfg: Dict[str, Any]) -> EMSConfig:
    return EMSConfig(
        enabled=safe_bool(cfg, "enabled", True),
        internal_generation=safe_bool(cfg, "internal_generation", True),
        hours=int(cfg.get("hours", 12)),
        hourly_lambda=list(cfg.get("hourly_lambda", [2,3,4,5,6,7,7,6,5,4,3,2])),
        ctas_mix=cfg.get("ctas_mix", {1:0.03,2:0.12,3:0.45,4:0.35,5:0.05}),
        p_critical=float(cfg.get("p_critical", 0.01)),
        p_direct_to_bed=float(cfg.get("p_direct_to_bed", 0.30)),
        download_capacity=int(cfg.get("download_capacity", 12)),
        offload_service_time_draw=draw_from_spec(cfg.get("offload_service_time_draw", {"uniform":[8,18]})),
        offload_nurses_per_hour=list(cfg.get("offload_nurses_per_hour", [1,1,2,2,3,3,3,3,2,2,1,1])),
        crew_hospital_time_draw=draw_from_spec(cfg.get("crew_hospital_time_draw", 25.0))
    )

def build_triage_weights(cfg: Dict[str, Any]) -> TriageWeights:
    return TriageWeights(
        w_age=float(cfg.get("w_age", 0.05)),
        w_temp=float(cfg.get("w_temp", 0.15)),
        w_o2=float(cfg.get("w_o2", 0.25)),
        w_bp=float(cfg.get("w_bp", 0.10)),
        w_gcs=float(cfg.get("w_gcs", 0.25)),
        w_complaint=float(cfg.get("w_complaint", 0.10)),
        w_flags=float(cfg.get("w_flags", 0.10)),
        ctas_bonus=cfg.get("ctas_bonus", {1:1.2,2:0.8,3:0.4,4:0.0,5:-0.2}),
    )

def build_orders(cfg: Dict[str, Any]) -> OrdersConfig:
    return OrdersConfig(
        proc_prob=float(cfg.get("proc_prob", 0.30)),
        lab_prob=float(cfg.get("lab_prob", 0.55)),
        di_prob=float(cfg.get("di_prob", 0.35)),
        proc_work_draw=lambda: int(np.random.randint(3,9)),
        proc_time_draw=draw_from_spec(cfg.get("proc_time_draw", {"uniform":[10,40]})),
        lab_work_draw=lambda: int(np.random.randint(2,6)),
        lab_time_draw=draw_from_spec(cfg.get("lab_time_draw", {"uniform":[30,120]})),
        di_work_draw=lambda: int(np.random.randint(2,6)),
        di_time_draw_map=di_time_map_from_spec(cfg.get("di_time_draw_map", {
            "Xray": {"uniform":[20,60]},
            "CT":   {"uniform":[40,120]},
            "US":   {"uniform":[30,120]},
        })),
        p_one_touch=float(cfg.get("p_one_touch", 0.15)),
        p_three_touch=float(cfg.get("p_three_touch", 0.25))
    )

# def build_consults(cfg: Dict[str, Any]) -> ConsultConfig:
#     # admit_prob_by_service: allow constant for now
#     admit_const = float(cfg.get("admit_prob", 0.5))
#     return ConsultConfig(
#         service_count=int(cfg.get("service_count", 40)),
#         request_prob=float(cfg.get("request_prob", 0.25)),
#         admit_prob_by_service=lambda s: admit_const,
#         local_boarding_time_draw=draw_from_spec(cfg.get("local_boarding_time_draw", {"uniform":[180,300]})),
#     )

def build_disposition(cfg: Dict[str, Any]) -> DispositionConfig:
    return DispositionConfig(
        stabilization_draw=draw_from_spec(cfg.get("stabilization_draw", {"uniform":[30,120]})),
        post_discharge_buffer_draw=draw_from_spec(cfg.get("post_discharge_buffer_draw", {"uniform":[60,600]})),
    )

def build_capabilities(cfg: Dict[str, Any]) -> CapabilitiesConfig:
    return CapabilitiesConfig(
        has_Xray=safe_bool(cfg, "has_Xray", True),
        has_CT=safe_bool(cfg, "has_CT", False),
        has_US=safe_bool(cfg, "has_US", True),
        transfer_only_admit=safe_bool(cfg, "transfer_only_admit", False),
        external_di_roundtrip=safe_bool(cfg, "external_di_roundtrip", True),
        external_di_total_time_draw=draw_from_spec(cfg.get("external_di_total_time_draw", {"uniform":[100,180]})),
        admit_transfer_total_time_draw=draw_from_spec(cfg.get("admit_transfer_total_time_draw", {"uniform":[90,180]})),
    )

def build_fasttrack(cfg: Dict[str, Any]) -> FastTrackConfig:
    if not cfg:
        return FastTrackConfig(enabled=False, name="FAST", assessment_spaces=0, route_probability=0.0, route_rule=None)
    # We can’t deserialize an arbitrary Python function for route_rule.
    # Provide a simple built-in rule by parameters, or use route_all / ctas_min flags.
    route_all = safe_bool(cfg, "route_all", False)
    print('cfg.get("ctas_min", 3)   ',cfg.get("ctas_min", 3))
    ctas_min = int(cfg.get("ctas_min", 3))
    no_trauma = safe_bool(cfg, "no_trauma", False)
    min_gcs = int(cfg.get("min_gcs", 13))
    no_critical = safe_bool(cfg, "no_critical_ems", True)

    def built_in_rule(p):
        ok = True
        if not route_all:
            ok &= (p.ctas >= ctas_min)
            if no_trauma: ok &= (not p.is_trauma)
            if min_gcs is not None: ok &= (p.gcs >= min_gcs)
            if no_critical: ok &= (not p.is_critical_ems)
        return ok

    return FastTrackConfig(
        enabled=safe_bool(cfg, "enabled", False),
        name=cfg.get("name", "FAST"),
        assessment_spaces=int(cfg.get("assessment_spaces", 10)),
        route_probability=float(cfg.get("route_probability", 0.5)),
        route_rule=built_in_rule
    )

def build_simconfig(payload: Dict[str, Any]) -> SimConfig:
    areas = build_areas(payload.get("areas", {
        "A": {"beds": 10, "nurse_model":{"model":"ratio","ratio":2,"lab_support":True}},
        "B": {"beds": 10, "nurse_model":{"model":"team","team_nurses":3,"lab_support":False}}
    }))
    doctors = build_doctors(payload.get("doctors", [
        {"name":"DrA1","area":"A","start_minute":8*60,"shift_minutes":10*60,
         "hourly_max_signups":[3,3,2,2,2,1,1,1,1,1],"max_active_panel":8,
         "assess_time_draw":{"uniform":[15,100]},"reassess_time_draw":{"uniform":[15,100]}},
        {"name":"DrB1","area":"B","start_minute":8*60,"shift_minutes":12*60,
         "hourly_max_signups":[4,3,3,2,2,2,1,1,1,1,1,1],"max_active_panel":9,
         "assess_time_draw":{"uniform":[15,100]},"reassess_time_draw":{"uniform":[15,100]}},
        {"name":"DrFT1","area":"FAST","start_minute":8*60,"shift_minutes":10*60,
         "hourly_max_signups":[8,8,7,7,6,6,5,5,4,4],"max_active_panel":20,
         "assess_time_draw":{"uniform":[6,15]},"reassess_time_draw":{"uniform":[3,8]}},
    ]))
    arrivals = build_arrivals(payload.get("arrivals", {}))
    ems      = build_ems(payload.get("ems", {}))
    triage   = build_triage_weights(payload.get("triage_weights", {}))
    orders   = build_orders(payload.get("orders", {}))
    # consults = build_consults(payload.get("consults", {}))
    dispo    = build_disposition(payload.get("disposition", {}))
    caps     = build_capabilities(payload.get("capabilities", {}))
    inpatient= build_inpatient(payload.get("inpatient", {}))
    fast     = build_fasttrack(payload.get("fasttrack", {}))

    return SimConfig(
        areas=areas,
        doctors=doctors,
        arrivals=arrivals,
        ems=ems,
        triage_weights=triage,
        orders=orders,
        consults=None,  # Using embedded consults in InpatientUnitSpec
        disposition=dispo,
        capabilities=caps,
        inpatient=inpatient,
        fasttrack=fast
    )

# --------------- API ---------------

@app.route("/")
def serve_index():
    return _serve_spa_index_or_help()

# Catch-all for React Router (any non-API path should serve index.html)
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api"):
        return jsonify({"error": "Not found"}), 404
    return _serve_spa_index_or_help()


@app.route("/simulate", methods=["POST"])
@login_required
def simulate():
    req_json = request.get_json(force=True, silent=False)
    print('req_json    ',req_json)

    # read run_type: "default" or "adjusted" (default to "adjusted")
    run_type = (req_json.get("run_type") or "adjusted").lower()
    
    # read compare_id for adjusted runs
    compare_id = req_json.get("compare_id")

    # ---- associate with user ----
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    # ---- seeds ----
    seed = int(req_json.get("seed", 7))
    random.seed(seed); np.random.seed(seed)

    # ---- build config ----
    sim_cfg = build_simconfig(req_json)

    # ---- run cfg ----
    run_cfg = req_json.get("run", {})
    duration_minutes = int(run_cfg.get(
        "duration_minutes",
        192 * 60 if sim_cfg.arrivals else 12*60
    ))
    tail_minutes = int(run_cfg.get("tail_minutes", 240))

    include_events   = bool(run_cfg.get("include_events", False))
    include_metrics  = bool(run_cfg.get("include_metrics", True))
    max_patients     = run_cfg.get("max_patients")
    max_events       = run_cfg.get("max_events")

    # ---- run sim ----
    env = simpy.Environment()
    elog = EventLog()
    hospital = Hospital(env, sim_cfg, elog)
    env.run(until=duration_minutes + tail_minutes)

    patients_df, events_df = hospital.results()
    detailed_df, summary_df = summarize_patients(patients_df, events_df)
    print(detailed_df)

    if isinstance(summary_df, pd.Series):
        summary_df = summary_df.to_frame().T

    detailed_numeric = make_numeric_metrics_payload(detailed_df)
    physician_metrics = build_physician_metrics(detailed_df)
    di_metrics = build_di_metrics(detailed_df)

    results_payload = {
        "metrics_table": df_to_records_clean(detailed_df),
        "distributions": detailed_numeric,
        "physicians": physician_metrics,
        "di": di_metrics,
    }

    # --- save input settings to inputs table first ---
    input_id = None
    try:
        from database import inputs_table
        inputs_table.create_inputs_table()  # Ensure table exists
        
        # Extract simulation metadata first
        simulation_id = req_json.get("simulation_id")
        simulation_name = req_json.get("simulation_name")
        
        # Extract settings from request (everything except run_type, compare_id, run config, simulation_id, simulation_name)
        settings_to_save = {k: v for k, v in req_json.items() if k not in ['run_type', 'compare_id', 'run', 'simulation_id', 'simulation_name']}
        
        # Mark as first run if run_type is "default" OR if no first_run entry exists for this simulation yet
        is_first_run = (run_type == "default")
        
        print(f"[INPUTS] Saving input: simulation_id={simulation_id}, simulation_name='{simulation_name}', run_type={run_type}, is_first_run={is_first_run}")
        
        # Check if this is truly the first run by looking in database
        if not is_first_run and simulation_id:
            existing_first = inputs_table.get_first_input_by_simulation_id(simulation_id)
            if not existing_first:
                # No first run exists yet, so mark this one as first
                is_first_run = True
                print(f"[INPUTS] No first_run entry exists, marking this as first run")
        
        input_id = inputs_table.add_input(
            user_id=int(g.user_id),
            hospital_id=req_json.get("hospital_id", "unknown"),
            settings_json=settings_to_save,
            run_id=req_json.get("run_id"),
            simulation_id=simulation_id,
            simulation_name=simulation_name,
            is_first_run=is_first_run
        )
        print(f"[INPUTS] Input saved successfully: input_id={input_id}")
    except Exception as e:
        print(f"[INPUTS ERROR] Failed to save input: {e}")
        import traceback
        traceback.print_exc()
        current_app.logger.exception("Failed to save input settings for user id %s", g.user_id)

    # --- persist run to outputs table (store the original request as configs and results) ---
    output_id = None
    try:
        output_id = outputs_table.add_output(
            user_id=int(g.user_id),            # use numeric user id
            configs=req_json,
            results=results_payload,
            input_id=input_id  # Link to the saved input
        )
    except Exception:
        current_app.logger.exception("Failed to save output for user id %s", g.user_id)

    # Handle compare table updates based on run_type
    created_compare_id = None
    if output_id is not None:
        try:
            compare_table.create_tables()  # ensure compare table exists (no-op if exists)
            
            if run_type == "default":
                # Create a new compare row for default runs (from Home -> Create)
                hospital_id = req_json.get("hospital_id", "unknown")
                print(f"[COMPARE] Creating compare with simulation_name='{simulation_name}', hospital_id='{hospital_id}' (type: {type(simulation_name).__name__})")
                created_compare_id = compare_table.add_compare(
                    user_id=int(g.user_id), 
                    output_1_id=output_id, 
                    output_2_id=None, 
                    simulation_name=simulation_name,
                    hospital_id=hospital_id
                )
                print(f"[COMPARE] Compare created with id={created_compare_id}")
            elif run_type == "adjusted" and compare_id is not None:
                # Update existing compare row with adjusted simulation output
                compare_table.update_compare_output_2(compare_id=int(compare_id), output_2_id=output_id, user_id=int(g.user_id))
                
        except Exception:
            current_app.logger.exception("Failed to update compare table for user id %s output %s", g.user_id, output_id)

    # Add compare_id to response for default runs so frontend can track it
    if created_compare_id is not None:
        results_payload["compare_id"] = created_compare_id

    return jsonify(results_payload), 200

@app.route("/test_simulate", methods=["POST"])
def test_simulate():
    import os
    from datetime import datetime

    DEBUG_DIR = "sim_debug_runs"
    os.makedirs(DEBUG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(DEBUG_DIR, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    req_json = request.get_json(force=True, silent=False)
    print("req_json:", req_json)

    # ---- seed ----
    seed = int(req_json.get("seed", 7))
    random.seed(seed)
    np.random.seed(seed)

    # ---- build config ----
    sim_cfg = build_simconfig(req_json)

    # ---- run config ----
    run_cfg = req_json.get("run", {})
    duration_minutes = int(
        run_cfg.get(
            "duration_minutes",
            sim_cfg.arrivals.hours * 60 if sim_cfg.arrivals else 12 * 60
        )
    )
    tail_minutes = int(run_cfg.get("tail_minutes", 240))

    # ---- run simulation ----
    env = simpy.Environment()
    elog = EventLog()
    hospital = Hospital(env, sim_cfg, elog)
    env.run(until=48*60 + tail_minutes)

    # ---- results ----
    patients_df, events_df = hospital.results()
    detailed_df, summary_df = summarize_patients(patients_df, events_df)

    if isinstance(summary_df, pd.Series):
        summary_df = summary_df.to_frame().T

    detailed_numeric = make_numeric_metrics_payload(detailed_df)
    physician_metrics = build_physician_metrics(detailed_df)
    di_metrics = build_di_metrics(detailed_df)


    if isinstance(summary_df, pd.Series):
        summary_df = summary_df.to_frame().T
    # Raw simulation outputs
    patients_df.to_csv(os.path.join(run_dir, "patients.csv"), index=False)
    events_df.to_csv(os.path.join(run_dir, "events.csv"), index=False)

    # Processed outputs
    detailed_df.to_csv(os.path.join(run_dir, "detailed_metrics.csv"), index=False)
    summary_df.to_csv(os.path.join(run_dir, "summary_metrics.csv"), index=False)
    results_payload = {
        "metrics_table": df_to_records_clean(detailed_df),
        "distributions": detailed_numeric,
        "physicians": physician_metrics,
        "di": di_metrics,
    }

    return jsonify(results_payload), 200

@app.route("/api/inputs/first/<string:simulation_id>", methods=["GET"])
#@login_required
def get_first_input_settings(simulation_id: str):
    """Get the first input settings for a simulation (marked as is_first_run=True)."""
    try:
        from database import inputs_table
        first_input = inputs_table.get_first_input_by_simulation_id(simulation_id)
        
        if not first_input:
            current_app.logger.info("No first input found for simulation_id %s", simulation_id)
            return jsonify({"error": "No first input found for this simulation"}), 404
        
        # Security check: ensure user owns this input
        # Convert both to int for comparison to avoid type mismatches
        if int(first_input.user_id) != int(g.user_id):
            current_app.logger.warning("Access denied: user %s (type: %s) tried to access input owned by user %s (type: %s)", 
                                     g.user_id, type(g.user_id).__name__, first_input.user_id, type(first_input.user_id).__name__)
            return jsonify({"error": "Access denied"}), 403
        
        return jsonify({
            "input_id": first_input.id,
            "settings": first_input.settings_json,
            "simulation_name": first_input.simulation_name,
            "created": first_input.created.isoformat() if first_input.created else None
        }), 200
    except Exception:
        current_app.logger.exception("Failed to get first input for simulation_id %s", simulation_id)
        return jsonify({"error": "Failed to retrieve first input"}), 500

@app.route("/api/hospitals", methods=["GET"])
def list_default_hospitals():
    """Return a list of hospital names from default_hosps using SQLAlchemy engine."""
    try:
        with engine.connect() as conn:
            stmt = text("SELECT name FROM default_hosps ORDER BY name COLLATE NOCASE")
            res = conn.execute(stmt)
            names = [row[0] for row in res.fetchall()]
        return jsonify({"hospitals": names}), 200
    except Exception:
        current_app.logger.exception("Failed to list default_hosps")
        return jsonify({"error": "failed to list hospitals"}), 500

@app.route("/api/hospitals/<string:name>", methods=["GET"])
def get_default_hospital(name: str):
    """Return the default settings row for a hospital (lookup by name) using SQLAlchemy."""
    try:
        with engine.connect() as conn:
            stmt = text("SELECT * FROM default_hosps WHERE name = :name LIMIT 1")
            res = conn.execute(stmt, {"name": name})
            row = res.mappings().first()
            if not row:
                return jsonify({"error": "hospital not found"}), 404

            out = {}
            for k, v in row.items():
                if isinstance(v, str):
                    try:
                        out[k] = json.loads(v)
                        continue
                    except Exception:
                        pass
                out[k] = v

            # Normalize inpatient_cfg: convert from CSV format to nested format for frontend
            if "inpatient_cfg" in out and isinstance(out["inpatient_cfg"], dict):
                units = out["inpatient_cfg"].get("units", {})
                for unit_name, unit_data in units.items():
                    if isinstance(unit_data, dict):
                        # Convert los_dist from CSV format {"type": "uniform", "low": X, "high": Y}
                        # to nested format {"uniform": [X, Y]} for frontend
                        if "los_dist" in unit_data:
                            los_dist = unit_data.pop("los_dist")
                            if isinstance(los_dist, dict):
                                dist_type = los_dist.get("type")
                                if dist_type == "uniform":
                                    unit_data["los_draw"] = {"uniform": [los_dist.get("low", 0), los_dist.get("high", 1)]}
                                elif dist_type == "lognormal":
                                    unit_data["los_draw"] = {"lognormal": {"mean": los_dist.get("mean", 4.5), "sigma": los_dist.get("sigma", 0.35)}}
                                elif dist_type == "normal":
                                    unit_data["los_draw"] = {"normal": {"mu": los_dist.get("mu", 0), "sigma": los_dist.get("sd", 1)}}
                                elif dist_type == "constant":
                                    unit_data["los_draw"] = los_dist.get("value", 0)
                                else:
                                    # Fallback to uniform
                                    unit_data["los_draw"] = {"uniform": [240, 600]}
                            else:
                                unit_data["los_draw"] = los_dist
                
                # Rename inpatient_cfg -> inpatient for frontend
                out["inpatient"] = out.pop("inpatient_cfg")

        return jsonify({"hospital": out}), 200
    except Exception:
        current_app.logger.exception("Failed to fetch default_hosps row for %s", name)
        return jsonify({"error": "failed to fetch hospital settings"}), 500

@app.route("/api/compares", methods=["GET"])
@login_required
def list_my_compares():
    """Return compare rows that belong to the currently authenticated user."""
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    try:
        compare_table.create_tables()  # ensure compare table exists
        rows = compare_table.get_user_compares(int(g.user_id))
    except Exception:
        current_app.logger.exception("Failed to fetch compares for user id %s", g.user_id)
        return jsonify({"error": "failed to fetch compares"}), 500

    # rows are simple dicts (id, user_id, output_1_id, output_2_id, created)
    return jsonify({"compares": rows}), 200


@app.route("/api/compares/<int:compare_id>", methods=["GET"])
@login_required
def get_compare_with_outputs(compare_id: int):
    """Get a comparison with its associated output data for the authenticated user."""
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    try:
        compare_table.create_tables()  # ensure compare table exists
        # Get the compare row
        compare_row = compare_table.get_compare_by_id(compare_id)
        
        if not compare_row:
            return jsonify({"error": "comparison not found"}), 404
        if compare_row["user_id"] != int(g.user_id):
            return jsonify({"error": "comparison not found"}), 404

        # Get associated outputs
        output_1 = None
        output_2 = None
        
        if compare_row["output_1_id"]:
            output_1 = outputs_table.get_output_by_id(compare_row["output_1_id"])
            if output_1 and output_1.user_id != int(g.user_id):
                output_1 = None  # Security check
        
        if compare_row["output_2_id"]:
            output_2 = outputs_table.get_output_by_id(compare_row["output_2_id"])
            if output_2 and output_2.user_id != int(g.user_id):
                output_2 = None  # Security check

        # Format response
        result = {
            "compare": compare_row,
            "output_1": {
                "id": output_1.id,
                "configs": output_1.configs,
                "results": output_1.results,
                "created_at": output_1.created.isoformat() if output_1.created else None,
            } if output_1 else None,
            "output_2": {
                "id": output_2.id,
                "configs": output_2.configs,
                "results": output_2.results,
                "created_at": output_2.created.isoformat() if output_2.created else None,
            } if output_2 else None,
        }

        return jsonify(result), 200

    except Exception:
        current_app.logger.exception("Failed to fetch compare %s for user %s", compare_id, g.user_id)
        return jsonify({"error": "failed to fetch comparison"}), 500


@app.route("/api/inputs", methods=["POST"])
@login_required
def save_input_settings():
    """Save simulation input settings and return the input ID."""
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    try:
        req_json = request.get_json(force=True, silent=False)
        hospital_id = req_json.get("hospital_id")
        settings_json = req_json.get("settings")
        run_id = req_json.get("run_id")  # Optional

        if not hospital_id or not settings_json:
            return jsonify({"error": "hospital_id and settings are required"}), 400

        # Import inputs_table
        from database import inputs_table
        inputs_table.create_inputs_table()  # Ensure table exists

        # Save the input
        input_id = inputs_table.add_input(
            user_id=int(g.user_id),
            hospital_id=hospital_id,
            settings_json=settings_json,
            run_id=run_id
        )

        return jsonify({"input_id": input_id}), 201

    except Exception:
        current_app.logger.exception("Failed to save input settings for user %s", g.user_id)
        return jsonify({"error": "failed to save input settings"}), 500


@app.route("/api/inputs/<int:input_id>", methods=["GET"])
@login_required
def get_input_settings(input_id: int):
    """Get input settings by ID for the authenticated user."""
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    try:
        from database import inputs_table
        inputs_table.create_inputs_table()  # Ensure table exists

        input_record = inputs_table.get_input_by_id(input_id)
        
        if not input_record:
            return jsonify({"error": "input not found"}), 404
        
        # Security check: ensure input belongs to user
        if input_record.user_id and input_record.user_id != int(g.user_id):
            return jsonify({"error": "input not found"}), 404

        result = {
            "id": input_record.id,
            "hospital_id": input_record.hospital_id,
            "settings": input_record.settings_json,
            "run_id": input_record.run_id,
            "created": input_record.created.isoformat() if input_record.created else None,
        }

        return jsonify(result), 200

    except Exception:
        current_app.logger.exception("Failed to fetch input %s for user %s", input_id, g.user_id)
        return jsonify({"error": "failed to fetch input"}), 500


if __name__ == "__main__":
    # Run with:  python api.py
    # Or: FLASK_APP=api.py flask run --reload
    port = int(os.environ.get("PORT", "5000"))

    app.run(host="0.0.0.0", port=port, debug=False)
