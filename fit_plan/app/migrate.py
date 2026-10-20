"""Upgrade a saved plan to the current version without overwriting the user's own edits.

v1 → v2 (technique review, Oct 2026):
  * exercise text that is still exactly the v1 default is replaced with the reviewed text + source links
  * the suitcase carry in the sessions is replaced by the side plank (back-friendly anti-lateral-flexion)
  * the Russian twist is removed from the library (loaded spinal flexion + rotation); bird dog added
  * daily calorie / protein / step targets removed
"""
import copy

from defaults import LIB, PLAN_VERSION

V1_DESCRIPTIONS = {
    "Goblet squat": "Hold the bell by the horns at chest height, elbows tucked. Sit down between your heels until the hip crease drops below the knee, then drive back up through the whole foot.",
    "Single-arm row": "Hinge forward with a flat back, one hand braced on a knee or chair. Pull the bell from a dead hang up to your hip, squeezing the shoulder blade back, then lower under control.",
    "Kettlebell deadlift": "Bell between the feet. Push the hips back with soft knees, grip the handle, brace, and stand tall by driving the hips forward. Lower by hinging, not squatting.",
    "Push-up": "Hands slightly wider than shoulders, body in one straight line from head to heels. Lower until the chest is a fist from the floor, then press away. Raise the hands on a bench or the bell handles to make it easier.",
    "Suitcase carry": "Hold a heavy bell in one hand by your side and walk tall without leaning towards it. Indoors, march slowly on the spot instead. Excellent for the obliques and deep core.",
    "Plank": "Forearms under shoulders, body in a straight line. Actively pull the elbows towards the toes and squeeze the glutes to make it harder.",
    "Two-hand swing": "A hip hinge done explosively. Hike the bell back between the legs, then snap the hips forward so the bell floats to chest height. The arms are ropes; the power comes from the hips. Let it fall back into the hinge.",
    "Reverse lunge (goblet)": "Hold the bell in the goblet position. Step one foot back and lower the back knee towards the floor, then drive through the front heel to return. Alternate legs or do all reps one side.",
    "Floor press": "Lie on your back, knees bent, bell in one hand with the upper arm on the floor. Press straight up until the arm locks, then lower until the elbow touches the floor again.",
    "Single-arm overhead press": "Start with the bell in the rack position (resting on the forearm at the shoulder). Brace, squeeze the glutes and press straight up until the bicep is by the ear. Lower back to the rack.",
    "Dead bug": "Lie on your back, arms up to the ceiling and knees bent at 90° over the hips. Slowly lower the opposite arm and leg towards the floor while pressing the lower back into the mat, then return.",
    "Swing + push-up finisher": "Alternate 10 two-hand swings with 5 push-ups, back to back, as one round. Rest as needed between rounds but keep the form sharp.",
    "Halo": "Hold the bell upside down by the horns at chest height and circle it slowly around your head, close to the skull. Change direction each rep. Great warm-up for the shoulders.",
    "Kettlebell clean": "From a hinge, swing the bell back then drive the hips to bring it up close to the body into the rack position, guiding it around the hand rather than letting it flip over and bang the forearm.",
    "Turkish get-up": "From lying with the bell pressed overhead, move step by step to standing while keeping the arm locked and eyes on the bell, then reverse back down. Slow, technical, full-body.",
    "Single-arm swing": "As the two-hand swing but with one hand. Resist the rotation and keep the free arm by your side or following the bell.",
    "Romanian deadlift": "Hold the bell (or two) in front of the thighs. Push the hips back, sliding the bell down the legs to just below the knees while keeping a flat back, then drive the hips forward to stand.",
    "Russian twist": "Sit with knees bent, lean back slightly with a straight back and hold the bell at the chest. Rotate the torso side to side, moving the bell across the body.",
    "Thruster": "From the goblet or rack position, squat down, then drive up and use that momentum to press the bell overhead in one smooth movement.",
    "High pull": "Like a single-arm swing, but at the top pull the elbow back and high so the bell finishes beside the chest, then push it back into the swing."
}


def _refresh(item: dict) -> bool:
    """Replace description/cues/source when the item still carries the untouched v1 default text."""
    name = item.get("name")
    if name in LIB and item.get("description") == V1_DESCRIPTIONS.get(name):
        new = LIB[name]
        item["description"] = new["description"]
        item["cues"] = list(new["cues"])
        item["source"] = copy.deepcopy(new["source"])
        return True
    return False


def migrate(plan: dict) -> bool:
    """Mutates `plan` in place. Returns True if anything changed."""
    if plan.get("version", 1) >= PLAN_VERSION:
        return False
    for s in plan.get("sessions", []):
        out = []
        for ex in s.get("exercises", []):
            if ex.get("name") == "Suitcase carry" and ex.get("description") == V1_DESCRIPTIONS["Suitcase carry"]:
                sp = LIB["Side plank"]
                ex = {**ex, "name": "Side plank", "sets": "3", "reps": "20–30 s each side", "rest": "30 s",
                      "notes": "Bend the knees to make it easier", "description": sp["description"],
                      "cues": list(sp["cues"]), "source": copy.deepcopy(sp["source"]), "demo": ""}
            else:
                _refresh(ex)
            out.append(ex)
        s["exercises"] = out
    lib = []
    for x in plan.get("library", []):
        if x.get("name") == "Russian twist" and x.get("description") == V1_DESCRIPTIONS["Russian twist"]:
            continue
        _refresh(x)
        lib.append(x)
    have = {x.get("name") for x in lib}
    for name in ("Side plank", "Bird dog"):
        if name not in have:
            lib.append(copy.deepcopy(LIB[name]))
    lib.sort(key=lambda x: x.get("name", "").lower())
    plan["library"] = lib
    for k in ("kcal", "protein_g", "steps"):
        plan.get("targets", {}).pop(k, None)
    plan["version"] = PLAN_VERSION
    return True
