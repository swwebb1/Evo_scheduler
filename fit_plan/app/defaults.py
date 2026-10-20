"""Default plan content: Steve's 6-week plan (Oct–Nov 2026) and the exercise library.

Exercise descriptions and cues were checked against published technique guidance (October 2026):
ACE Exercise Library, NSCA (Kinetic Select / Exercise Technique Manual), NASM, StrongFirst,
Stuart McGill's "Big 3" for back health, and university / physio exercise sheets. Each exercise
carries its source links so they can be opened from the app.
"""
import copy

SRC = {
    "ace_kb": {"label": "ACE: getting started with kettlebells", "url": "https://www.acefitness.org/education-and-resources/professional/expert-articles/5269/how-to-get-started-with-kettlebells"},
    "ace_swing": {"label": "ACE: kettlebell swing", "url": "https://www.acefitness.org/acefit/exercise-library-details/0/391/"},
    "nsca_swing": {"label": "NSCA: two-arm kettlebell swing", "url": "https://www.nsca.com/education/articles/kinetic-select/two-arm-kettlebell-swing/"},
    "sf_swing": {"label": "StrongFirst: don't lean back at the top", "url": "https://www.strongfirst.com/?p=67216"},
    "nasm_dl": {"label": "NASM: kettlebell deadlift", "url": "https://www.nasm.org/resource-center/exercise-library/kettlebell-deadlift"},
    "nsca_rdl": {"label": "NSCA: Romanian deadlift", "url": "https://www.nsca.com/education/articles/kinetic-select/romanian-deadlift-rdl/"},
    "nsca_press": {"label": "NSCA: one-arm kettlebell press", "url": "https://us.humankinetics.com/blogs/excerpt/one-arm-kettlebell-press"},
    "ace_clean": {"label": "ACE: clean and press", "url": "https://www.acefitness.org/resources/everyone/exercise-library/383/clean-and-press/"},
    "nsca_tgu": {"label": "NSCA: Turkish get-up", "url": "https://www.nsca.com/education/articles/kinetic-select/turkish-get-up"},
    "nuffield_tgu": {"label": "Nuffield Health: Turkish get-up", "url": "https://www.nuffieldhealth.com/article/how-to-kettlebell-turkish-get-up"},
    "ace_sideplank": {"label": "ACE: side plank (modified)", "url": "https://www.acefitness.org/resources/everyone/exercise-library/100/side-plank-modified"},
    "mcgill": {"label": "McGill Big 3 for back health", "url": "https://www.ptprogress.com/big-3-exercises-for-back-pain/"},
    "nasm_birddog": {"label": "NASM: bird dog", "url": "https://www.nasm.org/exercise-library/bird-dog"},
    "ace_plank": {"label": "ACE: front plank", "url": "https://acefitness.org/resources/everyone/exercise-library/32/front-plank/"},
    "ace_halo": {"label": "ACE: halo", "url": "https://www.acefitness.org/education-and-resources/lifestyle/exercise-library/394/halo"},
    "catalyst_pushup": {"label": "Catalyst Athletics: push-up", "url": "https://catalystathletics.com/exercise/869/Push-Up/"},
    "ace_lunge": {"label": "ACE: reverse lunge", "url": "https://acefitness.org/resources/everyone/exercise-library/319/reverse-lunge"},
    "ace_row": {"label": "ACE: bent-over row", "url": "https://www.acefitness.org/resources/everyone/exercise-library/12/bent-over-row/"},
    "physitrack_press": {"label": "Physitrack: floor press", "url": "https://au.physitrack.com/home-exercise-video/floor-press"},
    "sussex_deadbug": {"label": "Univ. of Sussex Sport: dead bug", "url": "https://www.sussex.ac.uk/sport/documents/dead-bug.pdf"},
    "motra_hp": {"label": "Motra: kettlebell high pull", "url": "https://motra.com/exercises/kettlebellHighPull"},
    "nfpt_carry": {"label": "NFPT: suitcase carry", "url": "https://nfpt.com/suitcase-carries-how-to-do/"},
}


def _s(*keys):
    return [dict(SRC[k]) for k in keys]


LIBRARY = [
    {
        "name": "Goblet squat",
        "description": "Hold the bell by the horns at chest height, feet about shoulder-width, toes slightly out. Push the hips back and bend the knees to sit down between your heels with your chest up and back straight, then drive up through the whole foot to stand.",
        "cues": ["Elbows forward, inside the knees", "Heels stay down — weight through the heels and mid-foot", "Knees track in line with the toes", "Only go as deep as you can keep your back flat (no tailbone tuck)", "Eyes forward, neck in line"],
        "source": _s("ace_kb"),
    },
    {
        "name": "Single-arm row",
        "description": "Take a split stance and brace the free hand on your front thigh (or a chair). Hinge forward with a flat back and let the bell hang from a straight arm. Pull the elbow back towards your hip, pause, then lower under control.",
        "cues": ["Back flat, neck long — look at the floor just ahead", "Pull the elbow to the hip, not the hand to the chest", "No twisting through the torso", "Pause 1 s at the top, lower slowly"],
        "source": _s("ace_row"),
    },
    {
        "name": "Kettlebell deadlift",
        "description": "Bell on the floor between your feet, in line with the middle of the foot. Push the hips back with a slight knee bend and near-vertical shins, and grip the handle with a flat back. Brace, push the floor away and drive the hips forward to stand tall. Lower by hinging back the same way.",
        "cues": ["Chest up, back flat — never round the lower back", "Shoulders slightly ahead of the bell, arms long", "Weight through the heels and mid-foot, not the toes", "Finish by squeezing the glutes — don't lean back", "Neck in line with your back"],
        "source": _s("nasm_dl", "ace_kb"),
    },
    {
        "name": "Push-up",
        "description": "Hands on the floor under the shoulders, body in one straight line from heels to head. Lower under control until your chest is close to the floor, then press back up to straight arms. Put your hands on a bench or step to make it easier.",
        "cues": ["Glutes and abs tight — hips don't sag or pike", "Elbows about 45° from your sides", "Head in line, eyes just ahead of the hands", "Stop the set when the straight line breaks"],
        "source": _s("catalyst_pushup"),
    },
    {
        "name": "Side plank",
        "description": "Lie on your side with the elbow directly under the shoulder and feet stacked. Brace and lift the hips until your body is straight from feet to head, hold, then lower. To make it easier, bend the knees and lift from the knees. It trains the side of the trunk like a suitcase carry, with very low load on the spine.",
        "cues": ["Elbow directly under the shoulder", "Straight line from feet (or knees) to head", "Head in line with the spine", "Keep breathing — don't hold your breath", "Short holds done well beat long sagging ones"],
        "source": _s("ace_sideplank", "mcgill"),
    },
    {
        "name": "Plank",
        "description": "Forearms on the floor with elbows directly under the shoulders. Brace, lift the body so it forms one stiff line from heels to head, and hold while breathing.",
        "cues": ["Shoulders over elbows, no shrugging", "No sagging low back or hiked hips", "Legs straight, toes tucked", "Stop if you feel low-back pain"],
        "source": _s("ace_plank"),
    },
    {
        "name": "Two-hand swing",
        "description": "A hip hinge, not a squat. Hike the bell back high between the thighs with a flat back and near-vertical shins, then snap the hips forward so the bell floats to chest height — the arms only guide it. Let it fall and hinge again as your forearms meet your hips.",
        "cues": ["Flat back and long neck at the bottom", "Bell passes above the knees on the backswing", "Power from the hips and legs, not the shoulders", "Top: stand tall like a plank — glutes tight, no leaning back", "Knees stay soft and mostly still"],
        "source": _s("ace_swing", "nsca_swing", "sf_swing"),
    },
    {
        "name": "Reverse lunge (goblet)",
        "description": "Hold the bell at the chest, feet hip-width. Step one foot back and lower the back knee towards the floor, sitting back into the front hip with your chest up. Drive through the front foot to return.",
        "cues": ["Chest up, shoulders back", "Front knee stays over the middle of the foot", "Lower straight down, under control", "Back knee lightly touches or hovers above the floor"],
        "source": _s("ace_lunge", "ace_kb"),
    },
    {
        "name": "Floor press",
        "description": "Lie on your back with knees bent and feet flat. Start with the upper arm on the floor, about 45° from your side, the bell resting on the back of the forearm and the wrist straight. Press straight up over the shoulder, then lower slowly until the elbow touches the floor.",
        "cues": ["Wrist straight, knuckles to the ceiling", "Elbow in line with or slightly below the shoulder", "Press over the shoulder, not over the face", "Pause with the elbow down — no bouncing"],
        "source": _s("physitrack_press"),
    },
    {
        "name": "Single-arm overhead press",
        "description": "Start in the rack: bell resting on the forearm, elbow tucked to the ribs, wrist straight. Brace, squeeze the glutes and press straight up until the elbow is fully straight with the bicep by the ear. Lower slowly back to the rack.",
        "cues": ["Neutral spine — no leaning back or to the side", "Free arm by your side, eyes forward", "Lower slowly; don't let the torso fold forward", "If you can't reach vertical without arching, go lighter or press half-kneeling"],
        "source": _s("nsca_press", "ace_clean"),
    },
    {
        "name": "Dead bug",
        "description": "Lie on your back, arms straight up above the shoulders, hips and knees at 90°. Brace with your lower back neutral — not arching. Slowly lower one arm overhead and straighten the opposite leg until it's just above the floor, return, then switch sides.",
        "cues": ["Back stays neutral — stop the range before it arches", "Move slowly; breathe out as you extend", "Don't let the hips hike or the shoulders lift", "Keep the knee bent more to make it easier"],
        "source": _s("sussex_deadbug"),
    },
    {
        "name": "Bird dog",
        "description": "Hands under the shoulders, knees under the hips, spine neutral. Brace, then reach one arm forward and the opposite leg back until they're in line with your body. Hold 8–10 s, return and switch sides.",
        "cues": ["No arching or sagging of the back", "Hips stay level — don't rotate", "Head in line, don't let it drop", "Reach long rather than high"],
        "source": _s("nasm_birddog", "mcgill"),
    },
    {
        "name": "Swing + push-up finisher",
        "description": "One round is 10 two-hand swings, then park the bell and do 5 push-ups. Rest as needed between rounds. Swing form first, speed second.",
        "cues": ["All the swing cues: flat back, hips do the work, no leaning back", "Hinge with a flat back to park the bell before the push-ups", "Straight line heels to head in the push-ups", "Stop if the hinge turns into a squat or your back rounds"],
        "source": _s("ace_swing", "catalyst_pushup"),
    },
    {
        "name": "Halo",
        "description": "Hold the bell upside down by the horns in front of the chest. Circle it slowly around your head, close to the skull, and back to the chest. Change direction each rep. A shoulder warm-up — use a light bell.",
        "cues": ["Light bell", "Back straight, ribs down, glutes tight", "Keep the head still", "Elbows close, slow and smooth"],
        "source": _s("ace_halo"),
    },
    {
        "name": "Kettlebell clean",
        "description": "From the hike, drive the hips forward and, as the bell rises, pull the elbow back towards the ribs so the bell travels close to the body and settles softly in the rack at the shoulder. Let it drop back between the legs to repeat.",
        "cues": ["Flat back on the hike", "Elbow stays close to the body", "Guide the bell around the hand — don't let it flip and bang the forearm", "Rack: elbow on the ribs, wrist straight"],
        "source": _s("ace_clean"),
    },
    {
        "name": "Turkish get-up",
        "description": "Advanced — practise the steps with a shoe balanced on your fist before using a bell. Lying with the bell pressed up and the same-side knee bent: roll to the opposite elbow, then hand, lift the hips, sweep the straight leg back to a half-kneel, lift the torso and stand. Reverse every step to lie back down.",
        "cues": ["Arm locked and vertical throughout", "Eyes on the bell until you're standing", "Move slowly, pausing at each position", "Lower the bell under control — never drop it"],
        "source": _s("nsca_tgu", "nuffield_tgu"),
    },
    {
        "name": "Single-arm swing",
        "description": "As the two-hand swing, but with one hand. Keep the grip arm straight and strong through the arc and resist the twist so your shoulders stay square.",
        "cues": ["Start lighter than your two-hand swing", "Turn the thumb toward the glutes on the backswing", "Same hip snap, same standing plank at the top", "Equal reps each side"],
        "source": _s("ace_kb", "sf_swing"),
    },
    {
        "name": "Romanian deadlift",
        "description": "Stand tall holding the bell in front of the thighs, knees slightly bent. Keeping that knee bend, push the hips back so the bell slides down close to the legs to just below the knees — or until you can't keep a neutral spine — then drive the hips forward to stand.",
        "cues": ["Knees stay slightly bent throughout", "Bell stays close to the legs", "Shoulders over or just in front of the bell", "Stop before your back starts to round", "Squeeze the glutes at the top"],
        "source": _s("nsca_rdl"),
    },
    {
        "name": "Thruster",
        "description": "Squat with the bell in the rack, then drive up and use that momentum to press it overhead in one smooth movement. Bring it back to the rack as you sink into the next squat.",
        "cues": ["Chest up, heels down in the squat", "Press finishes with the bicep by the ear", "Stand tall at the top — no leaning back", "Use a lighter bell than for a strict press"],
        "source": _s("ace_kb", "nsca_press"),
    },
    {
        "name": "High pull",
        "description": "From the hike, drive the hips forward. As the bell reaches chest height, pull the elbow up and out to shoulder level, keeping the bell close and the wrist straight, then guide it back down into the swing.",
        "cues": ["Neutral spine always", "Hips first, then the arm", "Elbow finishes above the wrist", "Keep the bell close to the body"],
        "source": _s("motra_hp"),
    },
    {
        "name": "Suitcase carry",
        "description": "Hinge with a flat back to pick the bell up. Hold it at your side, slightly away from the body, and walk — or march slowly on the spot — standing tall, without leaning toward the bell or shrugging. Switch hands halfway.",
        "cues": ["Pick it up with a hinge — don't round your back", "Shoulders down and level", "Don't lean toward the weight", "Slow, controlled steps"],
        "source": _s("nfpt_carry"),
    },
]

LIB = {x["name"]: x for x in LIBRARY}


def _ex(eid, name, sets, reps, rest, load="", notes=""):
    lib = LIB[name]
    return {"id": eid, "name": name, "sets": sets, "reps": reps, "rest": rest, "load": load,
            "notes": notes, "description": lib["description"], "cues": list(lib["cues"]),
            "source": copy.deepcopy(lib["source"])}


SESSIONS = [
    {
        "id": "A",
        "name": "Session A",
        "subtitle": "Strength · ~40 min",
        "warmup": "5 min: halos, hip hinges, bodyweight squats, arm circles",
        "exercises": [
            _ex("a1", "Goblet squat", "4", "8–12", "90 s"),
            _ex("a2", "Single-arm row", "3", "10–12 each side", "60 s"),
            _ex("a3", "Kettlebell deadlift", "4", "10–12", "90 s"),
            _ex("a4", "Push-up", "3", "8–15", "60 s", notes="Hands raised if needed"),
            _ex("a5", "Side plank", "3", "20–30 s each side", "30 s", notes="Bend the knees to make it easier"),
            _ex("a6", "Plank", "3", "30–45 s", "30 s"),
        ],
    },
    {
        "id": "B",
        "name": "Session B",
        "subtitle": "Power & conditioning · ~40 min",
        "warmup": "5 min: halos, hip hinges, bodyweight squats, light swings",
        "exercises": [
            _ex("b1", "Two-hand swing", "10 (EMOM)", "10–15", "Rest of the minute",
                notes="EMOM: start each minute with the reps, rest until the next minute"),
            _ex("b2", "Reverse lunge (goblet)", "3", "8–10 each leg", "60 s"),
            _ex("b3", "Floor press", "3", "8–12 each arm", "60 s"),
            _ex("b4", "Single-arm overhead press", "3", "6–10 each arm", "60 s"),
            _ex("b5", "Dead bug", "3", "10 each side", "30 s"),
            _ex("b6", "Swing + push-up finisher", "5 rounds", "10 swings + 5 push-ups", "As needed"),
        ],
    },
]

SCHEDULE = {
    "Mon": {"kind": "session", "ref": "A", "label": "Kettlebell A"},
    "Tue": {"kind": "run", "ref": "easy", "label": "Easy run"},
    "Wed": {"kind": "session", "ref": "B", "label": "Kettlebell B"},
    "Thu": {"kind": "run", "ref": "quality", "label": "Run (quality from week 3)"},
    "Fri": {"kind": "session", "ref": "A", "label": "Kettlebell A"},
    "Sat": {"kind": "ride", "ref": "ride", "label": "Long ride"},
    "Sun": {"kind": "rest", "ref": "", "label": "Rest · walk · weigh-in & waist"},
}

WEEKS = [
    {"week": 1, "start": "2026-10-19", "easy": "20 min: run 4, walk 1", "quality": "20 min: run 4, walk 1", "ride": "60 min easy", "kb": "Learn the moves, light bell"},
    {"week": 2, "start": "2026-10-26", "easy": "25 min continuous, easy", "quality": "25 min continuous, easy", "ride": "75 min easy", "kb": "Full sessions"},
    {"week": 3, "start": "2026-11-02", "easy": "30 min easy", "quality": "30 min + 6 × 20 s strides", "ride": "90 min, last 20 min steady", "kb": "Add reps"},
    {"week": 4, "start": "2026-11-09", "easy": "25 min easy", "quality": "25 min easy", "ride": "60 min easy", "kb": "2 sets per exercise (lighter week)"},
    {"week": 5, "start": "2026-11-16", "easy": "35 min easy", "quality": "35 min incl. 3 × 5 min tempo", "ride": "90–120 min, some hills", "kb": "Heavier bell or more reps"},
    {"week": 6, "start": "2026-11-23", "easy": "40 min easy", "quality": "5k time trial after 10 min warm-up", "ride": "90 min easy", "kb": "Full sessions, note your best numbers"},
    {"week": 7, "start": "2026-11-30", "easy": "30 min easy", "quality": "30–40 min with strides or tempo", "ride": "60–120 min (or long run)", "kb": "Working-week: A Mon, B Wed, 30 min each"},
]

TARGETS = {
    "start_weight": 76.2,
    "start_date": "2026-10-20",
    "goal_weight": 70.0,
    "weekly_loss": 0.6,
}

PLAN_VERSION = 2


def default_plan() -> dict:
    return copy.deepcopy({
        "version": PLAN_VERSION,
        "targets": TARGETS,
        "schedule": SCHEDULE,
        "sessions": SESSIONS,
        "weeks": WEEKS,
        "library": LIBRARY,
    })


def default_log() -> dict:
    return {"weights": [{"date": "2026-10-20", "kg": 76.2, "waist": None}], "done": []}
