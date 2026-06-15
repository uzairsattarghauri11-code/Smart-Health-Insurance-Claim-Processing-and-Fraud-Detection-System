import json
import os
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "smart_insurance_secret_key_2026"

DATA_FILE = "insurance_data.json"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def gen_id(prefix):
    return prefix + "".join(random.choices(string.digits, k=6))


def default_data():
    return {
        "users": {
            "admin": {"password": "admin123", "role": "admin", "name": "System Administrator"},
            "city_hospital": {"password": "hosp123", "role": "hospital", "name": "City General Hospital"},
            "metro_clinic": {"password": "hosp123", "role": "hospital", "name": "Metro Care Clinic"},
            "officer1": {"password": "off123", "role": "officer", "name": "Insurance Officer Ali"},
            "ahmed": {"password": "pol123", "role": "policyholder", "name": "Ahmed Khan", "policy_id": "POL100001"},
            "uzair": {"password": "pol123", "role": "policyholder", "name": "Uzair Sattar", "policy_id": "POL100002"},
        },
        "policies": {
            "POL100001": {
                "holder": "ahmed",
                "holder_name": "Ahmed Khan",
                "coverage_limit": 500000,
                "used_amount": 0,
                "covered_treatments": ["surgery", "consultation", "medication", "diagnostics", "emergency"],
                "active": True,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
            "POL100002": {
                "holder": "uzair",
                "holder_name": "Uzair Sattar",
                "coverage_limit": 300000,
                "used_amount": 0,
                "covered_treatments": ["surgery", "consultation", "medication", "diagnostics", "emergency"],
                "active": True,
                "start_date": "2026-02-01",
                "end_date": "2027-01-31",
            },
        },
        "hospitals": {
            "city_hospital": {"name": "City General Hospital", "eligible": True, "reg_no": "HOSP-001"},
            "metro_clinic": {"name": "Metro Care Clinic", "eligible": True, "reg_no": "HOSP-002"},
        },
        "claims": {},
        "notifications": {},
        "audit_trail": [],
    }


def calculate_fraud_score(data, hospital, policy_id, treatment_type, amount):
    score = 0
    reasons = []
    policy = data["policies"].get(policy_id)

    if not policy:
        return 40, ["Policy not found (+40)"]

    if treatment_type.lower() not in [t.lower() for t in policy["covered_treatments"]]:
        score += 25
        reasons.append("Treatment not covered by policy (+25)")

    remaining = policy["coverage_limit"] - policy["used_amount"]
    if amount > remaining:
        score += 30
        reasons.append("Claim amount exceeds remaining coverage (+30)")

    if amount > policy["coverage_limit"] * 0.8:
        score += 15
        reasons.append("Unusually high claim amount (+15)")

    hosp = data["hospitals"].get(hospital)
    if not hosp or not hosp.get("eligible", False):
        score += 35
        reasons.append("Hospital not eligible or registered (+35)")

    recent = 0
    cutoff = datetime.now() - timedelta(days=7)
    for c in data["claims"].values():
        if c["policy_id"] == policy_id:
            try:
                ctime = datetime.strptime(c["submitted_at"], "%Y-%m-%d %H:%M:%S")
                if ctime >= cutoff:
                    recent += 1
            except ValueError:
                pass
    if recent >= 3:
        score += 20
        reasons.append("Multiple claims in short period (+20)")

    if not policy.get("active", False):
        score += 30
        reasons.append("Policy is inactive (+30)")

    if score == 0:
        reasons.append("No risk indicators found")

    return min(score, 100), reasons


def risk_level(score):
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def log_audit(data, actor, action, details):
    data["audit_trail"].append({
        "timestamp": now_str(),
        "actor": actor,
        "action": action,
        "details": details,
    })


def add_notification(data, username, message):
    data["notifications"].setdefault(username, [])
    data["notifications"][username].append({
        "time": now_str(),
        "message": message,
        "read": False,
    })


def seed_claims(data):
    samples = [
        {"hospital": "city_hospital", "policy_id": "POL100002", "patient": "Uzair Sattar",
         "treatment": "surgery", "amount": 85000, "documents": True, "status": "Approved",
         "reviewed_by": "officer1", "remarks": "Documents verified, claim approved.", "days_ago": 12},
        {"hospital": "city_hospital", "policy_id": "POL100001", "patient": "Ahmed Khan",
         "treatment": "consultation", "amount": 6000, "documents": True, "status": "Approved",
         "reviewed_by": "officer1", "remarks": "Routine consultation approved.", "days_ago": 9},
        {"hospital": "metro_clinic", "policy_id": "POL100002", "patient": "Uzair Sattar",
         "treatment": "diagnostics", "amount": 18000, "documents": True, "status": "Pending Review",
         "reviewed_by": None, "remarks": "", "days_ago": 2},
        {"hospital": "metro_clinic", "policy_id": "POL100001", "patient": "Ahmed Khan",
         "treatment": "cosmetic", "amount": 420000, "documents": False, "status": "Rejected",
         "reviewed_by": "officer1", "remarks": "Treatment not covered and amount abnormally high.", "days_ago": 5},
        {"hospital": "city_hospital", "policy_id": "POL100001", "patient": "Ahmed Khan",
         "treatment": "medication", "amount": 9500, "documents": True, "status": "Pending Review",
         "reviewed_by": None, "remarks": "", "days_ago": 1},
        {"hospital": "metro_clinic", "policy_id": "POL100002", "patient": "Uzair Sattar",
         "treatment": "emergency", "amount": 30000, "documents": False, "status": "Info Requested",
         "reviewed_by": "officer1", "remarks": "Please upload discharge summary and bills.", "days_ago": 3},
    ]
    for s in samples:
        claim_id = gen_id("CLM")
        score, reasons = calculate_fraud_score(data, s["hospital"], s["policy_id"], s["treatment"], s["amount"])
        submitted = (datetime.now() - timedelta(days=s["days_ago"])).strftime("%Y-%m-%d %H:%M:%S")
        data["claims"][claim_id] = {
            "claim_id": claim_id,
            "hospital": s["hospital"],
            "hospital_name": data["users"][s["hospital"]]["name"],
            "policy_id": s["policy_id"],
            "patient": s["patient"],
            "treatment": s["treatment"],
            "amount": float(s["amount"]),
            "documents": s["documents"],
            "fraud_score": score,
            "risk_level": risk_level(score),
            "fraud_reasons": reasons,
            "status": s["status"],
            "submitted_at": submitted,
            "reviewed_by": s["reviewed_by"],
            "remarks": s["remarks"],
        }
        if s["status"] == "Approved":
            policy = data["policies"].get(s["policy_id"])
            if policy:
                policy["used_amount"] += float(s["amount"])
        log_audit(data, s["hospital"], "SUBMIT_CLAIM", f"Claim {claim_id} submitted for {s['policy_id']}")
        if s["reviewed_by"]:
            action = {"Approved": "APPROVE_CLAIM", "Rejected": "REJECT_CLAIM",
                      "Info Requested": "REQUEST_INFO"}.get(s["status"], "REVIEW_CLAIM")
            log_audit(data, s["reviewed_by"], action, f"Claim {claim_id} marked {s['status']}")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    data = default_data()
    seed_claims(data)
    save_data(data)
    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have access to that page.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def unread_count(data, username):
    return sum(1 for n in data["notifications"].get(username, []) if not n["read"])


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = load_data()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = data["users"].get(username)
        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            session["name"] = user["name"]
            log_audit(data, username, "LOGIN", "User logged in")
            save_data(data)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required()
def dashboard():
    role = session.get("role")
    data = load_data()
    username = session["username"]
    unread = unread_count(data, username)

    if role == "hospital":
        claims = [c for c in data["claims"].values() if c["hospital"] == username]
        claims.sort(key=lambda x: x["submitted_at"], reverse=True)
        return render_template("hospital.html", claims=claims, unread=unread)

    if role == "policyholder":
        pid = data["users"][username].get("policy_id")
        claims = [c for c in data["claims"].values() if c["policy_id"] == pid]
        claims.sort(key=lambda x: x["submitted_at"], reverse=True)
        policy = data["policies"].get(pid)
        return render_template("policyholder.html", claims=claims, policy=policy, unread=unread)

    if role == "officer":
        claims = list(data["claims"].values())
        claims.sort(key=lambda x: x["submitted_at"], reverse=True)
        pending = [c for c in claims if c["status"] == "Pending Review"]
        stats = build_stats(data)
        return render_template("officer.html", claims=claims, pending=pending, stats=stats, unread=unread)

    if role == "admin":
        stats = build_stats(data)
        return render_template("admin.html", data=data, stats=stats, unread=unread)

    return redirect(url_for("logout"))


def build_stats(data):
    claims = data["claims"]
    return {
        "total": len(claims),
        "approved": sum(1 for c in claims.values() if c["status"] == "Approved"),
        "rejected": sum(1 for c in claims.values() if c["status"] == "Rejected"),
        "pending": sum(1 for c in claims.values() if c["status"] == "Pending Review"),
        "info": sum(1 for c in claims.values() if c["status"] == "Info Requested"),
        "high": sum(1 for c in claims.values() if c["risk_level"] == "HIGH"),
        "medium": sum(1 for c in claims.values() if c["risk_level"] == "MEDIUM"),
        "low": sum(1 for c in claims.values() if c["risk_level"] == "LOW"),
        "total_amount": sum(c["amount"] for c in claims.values()),
        "approved_amount": sum(c["amount"] for c in claims.values() if c["status"] == "Approved"),
    }


@app.route("/submit-claim", methods=["GET", "POST"])
@login_required(role="hospital")
def submit_claim():
    data = load_data()
    username = session["username"]
    if request.method == "POST":
        policy_id = request.form.get("policy_id", "").strip()
        patient = request.form.get("patient", "").strip()
        treatment = request.form.get("treatment", "").strip()
        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            flash("Invalid claim amount.", "error")
            return redirect(url_for("submit_claim"))
        documents = request.form.get("documents") == "yes"

        if policy_id not in data["policies"]:
            flash("Policy ID does not exist.", "error")
            return redirect(url_for("submit_claim"))

        claim_id = gen_id("CLM")
        score, reasons = calculate_fraud_score(data, username, policy_id, treatment, amount)
        data["claims"][claim_id] = {
            "claim_id": claim_id,
            "hospital": username,
            "hospital_name": data["users"][username]["name"],
            "policy_id": policy_id,
            "patient": patient,
            "treatment": treatment,
            "amount": amount,
            "documents": documents,
            "fraud_score": score,
            "risk_level": risk_level(score),
            "fraud_reasons": reasons,
            "status": "Pending Review",
            "submitted_at": now_str(),
            "reviewed_by": None,
            "remarks": "",
        }
        log_audit(data, username, "SUBMIT_CLAIM", f"Claim {claim_id} submitted for {policy_id}")
        holder = data["policies"][policy_id]["holder"]
        add_notification(data, holder, f"A new claim {claim_id} was submitted under your policy.")
        add_notification(data, username, f"Claim {claim_id} submitted. Status: Pending Review.")
        save_data(data)
        flash(f"Claim {claim_id} submitted. Fraud score: {score}/100 ({risk_level(score)} risk).", "success")
        return redirect(url_for("dashboard"))

    policies = data["policies"]
    return render_template("submit_claim.html", policies=policies)


@app.route("/review/<claim_id>", methods=["POST"])
@login_required(role="officer")
def review_claim(claim_id):
    data = load_data()
    username = session["username"]
    claim = data["claims"].get(claim_id)
    if not claim:
        flash("Claim not found.", "error")
        return redirect(url_for("dashboard"))

    action = request.form.get("action")
    remarks = request.form.get("remarks", "").strip()

    if action == "approve":
        claim["status"] = "Approved"
        policy = data["policies"].get(claim["policy_id"])
        if policy:
            policy["used_amount"] += claim["amount"]
        log_audit(data, username, "APPROVE_CLAIM", f"Claim {claim_id} approved")
        notify_parties(data, claim, f"Claim {claim_id} has been APPROVED.")
        flash(f"Claim {claim_id} approved.", "success")
    elif action == "reject":
        claim["status"] = "Rejected"
        log_audit(data, username, "REJECT_CLAIM", f"Claim {claim_id} rejected")
        notify_parties(data, claim, f"Claim {claim_id} has been REJECTED. Reason: {remarks}")
        flash(f"Claim {claim_id} rejected.", "success")
    elif action == "info":
        claim["status"] = "Info Requested"
        log_audit(data, username, "REQUEST_INFO", f"Info requested for claim {claim_id}")
        notify_parties(data, claim, f"Additional information requested for claim {claim_id}: {remarks}")
        flash(f"Information requested for claim {claim_id}.", "success")

    claim["reviewed_by"] = username
    claim["remarks"] = remarks
    save_data(data)
    return redirect(url_for("dashboard"))


def notify_parties(data, claim, message):
    add_notification(data, claim["hospital"], message)
    holder = data["policies"].get(claim["policy_id"], {}).get("holder")
    if holder:
        add_notification(data, holder, message)


@app.route("/notifications")
@login_required()
def notifications():
    data = load_data()
    username = session["username"]
    notes = data["notifications"].get(username, [])
    for n in notes:
        n["read"] = True
    save_data(data)
    return render_template("notifications.html", notes=list(reversed(notes)))


@app.route("/audit")
@login_required(role="admin")
def audit():
    data = load_data()
    entries = list(reversed(data["audit_trail"]))
    return render_template("audit.html", entries=entries, unread=unread_count(data, session["username"]))


@app.route("/register-hospital", methods=["POST"])
@login_required(role="admin")
def register_hospital():
    data = load_data()
    uname = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "").strip()
    if uname in data["users"]:
        flash("Username already exists.", "error")
        return redirect(url_for("dashboard"))
    reg_no = gen_id("HOSP-")
    data["users"][uname] = {"password": password, "role": "hospital", "name": name}
    data["hospitals"][uname] = {"name": name, "eligible": True, "reg_no": reg_no}
    log_audit(data, session["username"], "REGISTER_HOSPITAL", f"Hospital {uname} registered")
    save_data(data)
    flash(f"Hospital registered with reg no {reg_no}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/register-policy", methods=["POST"])
@login_required(role="admin")
def register_policy():
    data = load_data()
    uname = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "").strip()
    try:
        limit = float(request.form.get("limit", "0"))
    except ValueError:
        flash("Invalid coverage limit.", "error")
        return redirect(url_for("dashboard"))
    if uname in data["users"]:
        flash("Username already exists.", "error")
        return redirect(url_for("dashboard"))
    pid = gen_id("POL")
    data["users"][uname] = {"password": password, "role": "policyholder", "name": name, "policy_id": pid}
    data["policies"][pid] = {
        "holder": uname,
        "holder_name": name,
        "coverage_limit": limit,
        "used_amount": 0,
        "covered_treatments": ["surgery", "consultation", "medication", "diagnostics", "emergency"],
        "active": True,
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
    }
    log_audit(data, session["username"], "REGISTER_POLICY", f"Policy {pid} created for {uname}")
    save_data(data)
    flash(f"Policy created with ID {pid}.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
