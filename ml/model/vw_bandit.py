# ─────────────────── vw_bandit.py ───────────────────
from pathlib import Path
from random import random, shuffle, sample
from typing import List, Tuple
import hashlib
import base64
from typing import Dict, List, Tuple
from shutil import copyfile


from vowpalwabbit import pyvw

# ---------- CONFIG -----------------------------------------------------------
# MODEL_PATH = Path("timely_cb.model")
ACTIONS = 720  # 30 days horizon
EPSILON = 0.20  # 20 % random exploration
MAX_CHUNK_HRS = 2.0  # split long tasks into 2 h pieces

# ---------- initialise / load model -----------------------------------------
MODEL_DIR = Path("user")
MODEL_DIR.mkdir(exist_ok=True)
BASE_MODEL = Path("timely_cb.model")

# if MODEL_PATH.exists():
#     vw = pyvw.vw(f"-i {MODEL_PATH} --cb_explore {ACTIONS} --quiet")
# else:
#     vw = pyvw.vw(f"--cb_explore {ACTIONS} --quiet")


# ------------------------------------------------------------------- helpers
def _slug_from_uid(uid: str) -> str:
    digest = hashlib.sha256(uid.lower().encode()).digest()
    return base64.urlsafe_b64encode(digest)[:22].decode()


_VW: Dict[str, pyvw.vw] = {}
_PATH: Dict[str, Path] = {}


def _get_vw(uid: str) -> pyvw.vw:
    if uid in _VW:
        return _VW[uid]
    path = MODEL_DIR / f"{_slug_from_uid(uid)}.model"
    if not path.exists() and BASE_MODEL.exists():
        copyfile(BASE_MODEL, path)  # cold‑start clone
    vw = pyvw.vw(
        (f"-i {path} " if path.exists() else "") + f"--cb_explore {ACTIONS} --quiet"
    )
    _VW[uid], _PATH[uid] = vw, path
    print("PATH: ", path)
    return vw


def _ctx_hash(
    task_type: str,
    task_duration: float,
    hrs_until_due: float,
    day_of_week: int,
    num_context_tasks: int,
) -> str:
    """Compact string used as shared features."""
    return (
        f"tt={task_type} dur={task_duration:.1f} "
        f"due={hrs_until_due:.0f} dow={day_of_week} "
        f"ctx={num_context_tasks}"
    )


def _ex(
    task_type: str,
    dur: float,
    hrs_due: int,
    dow: int,
    act: int | None = None,
    cost: int | None = None,
    p: float | None = None,
):
    feat = f"tt={task_type} dur={dur:.1f} hrs_due={hrs_due} dow={dow}"
    if act is None:
        return f"| {feat}"
    if p is None:
        raise ValueError("prob missing")
    return f"{act}:{cost}:{p} | {feat}"


# ---------------------------------------------------------------- recommend
def vw_recommend(
    *,
    uid: str,
    task_type: str,
    task_duration: float,
    hrs_until_due: float,
    day_of_week: int,
    candidate_hours: List[int],
    top_k: int = 6,
    prefer_splitting: bool = True,
) -> List[Tuple[int, float]]:
    """
    Returns up‑to top_k (hour_offset, chunk_dur) tuples.
    """
    vw = _get_vw(uid)
    if not candidate_hours:
        return []

    # ε‑greedy shuffle to break deterministic ties
    shuffle(candidate_hours)

    # build multiline example
    shared = f"shared |s {_ctx_hash(task_type, task_duration, hrs_until_due, day_of_week, 0)}"
    action_lines = [f"|a hr={h}" for h in candidate_hours]

    # Combine shared and action lines into a single string
    example_str = shared + "\n" + "\n".join(action_lines)

    try:
        ex = vw.example(example_str)
        probs = vw.predict(ex)
    except Exception as e:
        print(f"Error in VW prediction: {str(e)}")
        print(f"Example string: {example_str}")
        return []

    # ε‑greedy: with prob ε pick random hours
    ranked = (
        list(range(len(candidate_hours)))
        if random() < EPSILON
        else sorted(range(len(candidate_hours)), key=lambda i: probs[i], reverse=True)
    )

    chosen: List[Tuple[int, float]] = []
    for idx in ranked:
        if len(chosen) >= top_k:
            break
        h = candidate_hours[idx]
        if prefer_splitting and task_duration > MAX_CHUNK_HRS:
            remain = task_duration
            while remain > 0.01 and len(chosen) < top_k:
                chunk = min(MAX_CHUNK_HRS, remain)
                chosen.append((h, chunk))
                remain -= chunk
                h += chunk
        else:
            chosen.append((h, task_duration))

    return chosen


# ---------------------------------------------------------------- feedback
def vw_feedback(
    *,
    uid: str,
    task_type: str,
    task_duration: float,
    hrs_until_due: float,
    day_of_week: int,
    chosen_hour: int,
    cost: float,
    prob: float,
):
    """
    Record IPS feedback for ONE chosen hour (0 good → low cost).
    """
    print("👀 RECORDING FEEDBACK")
    vw = _get_vw(uid)
    shared = f"shared |s {_ctx_hash(task_type, task_duration, hrs_until_due, day_of_week, 0)}"
    cb_line = f"{cost}:{chosen_hour}:{prob} |a hr={chosen_hour}"

    # Combine shared and action line into a single string
    example_str = shared + "\n" + cb_line

    try:
        vw = _get_vw(uid)
        vw.learn(
            vw.example(
                _ex(
                    task_type,
                    task_duration,
                    hrs_until_due,
                    day_of_week,
                    chosen_hour,
                    cost,
                    prob,
                )
            )
        )
        vw.save(str(_PATH[uid]))
    except Exception as e:
        print(f"Error in VW learning: {str(e)}")
        print(f"Example string: {example_str}")

    print(
        f"🔥 Feedback recorded: {task_type} {task_duration} {hrs_until_due} {day_of_week} {chosen_hour} {cost} {prob}"
    )


def save_model(uid: str):
    _get_vw(uid).save(str(_PATH[uid]))


def save_all_models():
    for uid in _VW:
        print(f"💾 Saving model for {uid}")
        save_model(uid)
