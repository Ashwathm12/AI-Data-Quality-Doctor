import os
import io
import json
import sqlite3
import time
from datetime import datetime
from functools import wraps

import numpy as np
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "quality_doctor.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                rows_count INTEGER NOT NULL,
                columns_count INTEGER NOT NULL,
                missing_cells INTEGER NOT NULL,
                duplicate_rows INTEGER NOT NULL,
                outlier_rows INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

init_db()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def allowed_file(filename):
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

def detect_outliers(df, method="iqr", contamination="auto", iqr_factor=1.5, random_state=42):
    """
    Detects numeric outliers using either the statistical IQR rule or 
    Scikit-learn's unsupervised Isolation Forest model.
    Flags rows without removing them from the dataset.

    Parameters:
        df (pd.DataFrame): Input dataframe.
        method (str): 'iqr' or 'isolation_forest'.
        contamination (float or 'auto'): Contamination rate for IsolationForest.
            Must be in (0, 0.5] if float, or 'auto'. Default is 'auto'.
        iqr_factor (float): Multiplier for IQR fence (standard Tukey threshold is 1.5).
            Default is 1.5.
        random_state (int): Seed for IsolationForest tree building reproducibility. Default 42.

    Returns:
        outlier_mask (pd.Series): Boolean mask (True for flagged outlier row).
        outlier_details (dict): Metadata/breakdown of flagged items.
        outlier_method_label (str): Human-readable method label.
    """
    numeric = df.select_dtypes(include=[np.number])
    outlier_mask = pd.Series(False, index=df.index)
    outlier_details = {}

    # Safety validation: Ensure there are numeric columns and sufficient rows
    if numeric.empty or len(numeric.columns) == 0:
        return outlier_mask, outlier_details, f"{method.upper()} (No numeric columns found)"

    if len(df) < 2:
        return outlier_mask, outlier_details, f"{method.upper()} (Insufficient rows for outlier detection)"

    if method == "isolation_forest":
        outlier_method_label = "Isolation Forest (Unsupervised ML)"

        # Safe missing-value handling: Impute missing numeric values temporarily for model input
        valid_cols = [c for c in numeric.columns if not numeric[c].isna().all()]
        if not valid_cols:
            return outlier_mask, outlier_details, "Isolation Forest (All numeric values missing)"

        X = numeric[valid_cols].copy()
        imputer = SimpleImputer(strategy="median")
        X_imputed = imputer.fit_transform(X)

        # Validate contamination hyperparameter
        model_contamination = "auto"
        if isinstance(contamination, (int, float)):
            if 0.0 < float(contamination) <= 0.5:
                model_contamination = float(contamination)

        # Train IsolationForest model
        model = IsolationForest(contamination=model_contamination, random_state=random_state)
        predictions = model.fit_predict(X_imputed)

        # Scikit-learn outputs -1 for anomalies/outliers, 1 for inliers
        outlier_mask = pd.Series(predictions == -1, index=df.index)

        outlier_details = {
            "model": "IsolationForest",
            "evaluated_columns": valid_cols,
            "total_outlier_rows": int(outlier_mask.sum()),
            "contamination": model_contamination,
        }
    else:
        # Default: IQR rule
        factor = float(iqr_factor) if isinstance(iqr_factor, (int, float)) and float(iqr_factor) > 0 else 1.5
        outlier_method_label = "Interquartile Range (IQR Rule)"
        for col in numeric.columns:
            values = numeric[col].dropna()
            if len(values) < 4:
                outlier_details[col] = 0
                continue
            q1, q3 = values.quantile([0.25, 0.75])
            iqr = q3 - q1
            if iqr == 0:
                col_mask = (df[col] < q1) | (df[col] > q3)
            else:
                col_mask = (df[col] < q1 - factor * iqr) | (df[col] > q3 + factor * iqr)
            col_mask = col_mask.fillna(False)
            outlier_mask = outlier_mask | col_mask
            outlier_details[col] = int(col_mask.sum())

    return outlier_mask, outlier_details, outlier_method_label

def analyze_dataframe(df, outlier_method="iqr"):
    missing_by_column = df.isna().sum().to_dict()
    duplicate_count = int(df.duplicated().sum())
    missing_cells = int(df.isna().sum().sum())

    outlier_mask, outlier_details, method_label = detect_outliers(df, method=outlier_method)
    outlier_rows = int(outlier_mask.sum())

    total_cells = int(df.shape[0] * df.shape[1])
    completeness = round(100 * (1 - missing_cells / total_cells), 2) if total_cells else 100.0
    duplicate_rate = round(100 * duplicate_count / len(df), 2) if len(df) else 0.0

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_cells": missing_cells,
        "missing_by_column": {str(k): int(v) for k, v in missing_by_column.items()},
        "duplicate_rows": duplicate_count,
        "outlier_rows": outlier_rows,
        "outlier_details": outlier_details,
        "completeness": completeness,
        "duplicate_rate": duplicate_rate,
        "outlier_method": method_label,
        "column_names": [str(c) for c in df.columns],
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "preview": df.head(8).fillna("").astype(str).to_dict(orient="records"),
    }

def clean_dataframe(df):
    cleaned = df.copy()
    # Fill numeric missing values with the median and categorical missing values with the mode.
    numeric_cols = cleaned.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = cleaned.select_dtypes(exclude=[np.number]).columns.tolist()

    if numeric_cols:
        imputer = SimpleImputer(strategy="median")
        cleaned[numeric_cols] = imputer.fit_transform(cleaned[numeric_cols])

    for col in categorical_cols:
        if cleaned[col].isna().any():
            mode_values = cleaned[col].mode(dropna=True)
            replacement = mode_values.iloc[0] if not mode_values.empty else "Unknown"
            cleaned[col] = cleaned[col].fillna(replacement)

    before = len(cleaned)
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    removed_duplicates = before - len(cleaned)
    return cleaned, removed_duplicates

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db() as conn:
        reports = conn.execute(
            "SELECT * FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (session["user_id"],)
        ).fetchall()
        total_runs = len(reports)
        total_rows_processed = sum(r["rows_count"] for r in reports) if reports else 0
        total_outliers_flagged = sum(r["outlier_rows"] for r in reports) if reports else 0

    return render_template(
        "index.html",
        username=session.get("username"),
        reports=reports,
        total_runs=total_runs,
        total_rows_processed=total_rows_processed,
        total_outliers_flagged=total_outliers_flagged
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 8:
            flash("Use a username of at least 3 characters and a password of at least 8 characters.", "danger")
            return render_template("register.html")
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), datetime.now().isoformat(timespec="seconds"))
                )
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username is already taken.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    uploaded = request.files.get("dataset")
    if not uploaded or not uploaded.filename:
        flash("Choose a dataset file first.", "danger")
        return redirect(url_for("index"))
    if not allowed_file(uploaded.filename):
        flash("Upload a supported file format (.csv, .xlsx, or .xls).", "danger")
        return redirect(url_for("index"))

    outlier_method = request.form.get("outlier_method", "iqr")

    try:
        raw = uploaded.read()
        file_ext = os.path.splitext(uploaded.filename.lower())[1]
        if file_ext in {".xlsx", ".xls"}:
            df = pd.read_excel(io.BytesIO(raw))
        else:
            df = pd.read_csv(io.BytesIO(raw))

        if df.empty:
            flash("The dataset has no data rows.", "danger")
            return redirect(url_for("index"))
        if len(df.columns) < 1:
            flash("No columns were found in the dataset.", "danger")
            return redirect(url_for("index"))
        if df.shape[0] > 100000 or df.shape[1] > 200:
            flash("Dataset is too large for this prototype (limit: 100,000 rows and 200 columns).", "danger")
            return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Could not read this file. Check its format. Details: {exc}", "danger")
        return redirect(url_for("index"))

    report = analyze_dataframe(df, outlier_method=outlier_method)
    cleaned_df, removed_duplicates = clean_dataframe(df)
    # Store the most recent result in the session for the download route.
    session["last_cleaned_csv"] = cleaned_df.to_csv(index=False)
    session["last_report"] = {
        "filename": uploaded.filename,
        "report": report,
        "removed_duplicates": int(removed_duplicates),
        "cleaned_rows": int(len(cleaned_df)),
    }
    with get_db() as conn:
        conn.execute("""
            INSERT INTO reports
            (user_id, filename, rows_count, columns_count, missing_cells, duplicate_rows, outlier_rows, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], uploaded.filename, report["rows"], report["columns"],
            report["missing_cells"], report["duplicate_rows"], report["outlier_rows"],
            datetime.now().isoformat(timespec="seconds")
        ))
    return render_template("results.html", data=session["last_report"])

@app.route("/download-cleaned")
@login_required
def download_cleaned():
    csv_text = session.get("last_cleaned_csv")
    if not csv_text:
        flash("Analyze a dataset before downloading a cleaned file.", "warning")
        return redirect(url_for("index"))
    return send_file(
        io.BytesIO(csv_text.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="cleaned_dataset.csv"
    )

@app.route("/download-report")
@login_required
def download_report():
    last_report = session.get("last_report")
    if not last_report:
        flash("Analyze a dataset before downloading a report.", "warning")
        return redirect(url_for("index"))
    report_text = json.dumps(last_report, indent=2, ensure_ascii=False)
    return send_file(
        io.BytesIO(report_text.encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name="data_quality_report.json"
    )

def generate_evaluation_dataset(n_samples=200, n_anomalies=20, random_state=42):
    """
    Generates a reproducible synthetic dataset with numeric features and
    deliberately injected ground-truth anomalies.
    Returns:
        df: pd.DataFrame with numeric columns only (no labels)
        y_true: pd.Series of booleans (True for injected anomaly, False for normal)
    """
    n_samples = max(10, min(int(n_samples), 5000))
    n_anomalies = max(0, min(int(n_anomalies), n_samples - 1))
    n_normal = n_samples - n_anomalies

    rng = np.random.RandomState(random_state)

    # Synthetic normal cluster distributions
    # Feature 1: e.g. Attendance/Score (~Normal(50, 10))
    f1_norm = rng.normal(loc=50.0, scale=10.0, size=n_normal)
    # Feature 2: e.g. Measurement/HeartRate (~Normal(100, 15))
    f2_norm = rng.normal(loc=100.0, scale=15.0, size=n_normal)
    # Feature 3: e.g. Duration/Hours (~Normal(25, 5))
    f3_norm = rng.normal(loc=25.0, scale=5.0, size=n_normal)

    if n_anomalies > 0:
        # Generate distinct outliers outside typical distribution
        f1_anom = rng.choice([-1.0, 1.0], size=n_anomalies) * rng.uniform(35.0, 60.0, size=n_anomalies) + 50.0
        f2_anom = rng.choice([-1.0, 1.0], size=n_anomalies) * rng.uniform(45.0, 80.0, size=n_anomalies) + 100.0
        f3_anom = rng.choice([-1.0, 1.0], size=n_anomalies) * rng.uniform(20.0, 35.0, size=n_anomalies) + 25.0

        f1 = np.concatenate([f1_norm, f1_anom])
        f2 = np.concatenate([f2_norm, f2_anom])
        f3 = np.concatenate([f3_norm, f3_anom])
        labels = np.concatenate([np.zeros(n_normal, dtype=bool), np.ones(n_anomalies, dtype=bool)])
    else:
        f1, f2, f3 = f1_norm, f2_norm, f3_norm
        labels = np.zeros(n_normal, dtype=bool)

    # Shuffle rows using the fixed seed so anomalies are distributed throughout
    indices = rng.permutation(n_samples)
    df = pd.DataFrame({
        "feature_1": np.round(f1[indices], 2),
        "feature_2": np.round(f2[indices], 2),
        "feature_3": np.round(f3[indices], 2)
    }).reset_index(drop=True)

    y_true = pd.Series(labels[indices], index=df.index)
    return df, y_true

def evaluate_detection_method(df, y_true, method="iqr", contamination="auto", iqr_factor=1.5, random_state=42):
    """
    Evaluates an anomaly detection method against synthetic ground-truth labels.
    Reuses existing detect_outliers logic and safely handles division by zero.
    """
    start_time = time.perf_counter()
    outlier_mask, outlier_details, method_label = detect_outliers(
        df,
        method=method,
        contamination=contamination,
        iqr_factor=iqr_factor,
        random_state=random_state
    )
    exec_time_ms = max(0.0, round((time.perf_counter() - start_time) * 1000, 2))

    y_pred = outlier_mask.to_numpy(dtype=bool)
    y_actual = y_true.to_numpy(dtype=bool)

    tp = int(np.sum(y_pred & y_actual))
    fp = int(np.sum(y_pred & ~y_actual))
    tn = int(np.sum(~y_pred & ~y_actual))
    fn = int(np.sum(~y_pred & y_actual))

    total = tp + fp + tn + fn
    predicted_positives = tp + fp
    actual_positives = tp + fn

    precision = round(tp / predicted_positives, 4) if predicted_positives > 0 else 0.0
    recall = round(tp / actual_positives, 4) if actual_positives > 0 else 0.0

    if (precision + recall) > 0:
        f1 = round(2 * (precision * recall) / (precision + recall), 4)
    else:
        f1 = 0.0

    accuracy = round((tp + tn) / total, 4) if total > 0 else 0.0

    return {
        "method_key": method,
        "method_label": method_label,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "precision_pct": round(precision * 100, 1),
        "recall": recall,
        "recall_pct": round(recall * 100, 1),
        "f1": f1,
        "f1_pct": round(f1 * 100, 1),
        "accuracy": accuracy,
        "accuracy_pct": round(accuracy * 100, 1),
        "exec_time_ms": exec_time_ms,
        "flagged_count": int(np.sum(y_pred)),
    }

def compute_summary_stats(trials):
    """
    Computes sample mean and sample standard deviation (ddof=1) for metrics.
    """
    keys = ["precision", "recall", "f1", "accuracy", "exec_time_ms", "tp", "fp", "tn", "fn"]
    summary = {}
    n = len(trials)
    for k in keys:
        vals = [t[k] for t in trials]
        mean_val = float(np.mean(vals)) if vals else 0.0
        std_val = float(np.std(vals, ddof=1)) if n > 1 else 0.0
        summary[k] = {
            "mean": round(mean_val, 4),
            "std": round(std_val, 4),
            "mean_pct": round(mean_val * 100, 1),
            "std_pct": round(std_val * 100, 1),
        }
    return summary

def run_repeated_benchmark(n_samples=200, n_anomalies=20, base_seed=42, n_runs=5, contamination="auto", iqr_factor=1.5):
    """
    Runs repeated benchmark experiments across multiple deterministic seeds.
    Computes mean and standard deviation for both detection methods.
    Returns:
        iqr_summary: dict of aggregated mean & std stats
        iso_summary: dict of aggregated mean & std stats
        iqr_runs: list of individual trial results
        iso_runs: list of individual trial results
        all_trials: combined list for CSV export
    """
    iqr_runs = []
    iso_runs = []
    all_trials = []

    for idx in range(n_runs):
        current_seed = int(base_seed) + idx * 17
        df, y_true = generate_evaluation_dataset(
            n_samples=n_samples,
            n_anomalies=n_anomalies,
            random_state=current_seed
        )

        m_iqr = evaluate_detection_method(df, y_true, method="iqr", iqr_factor=iqr_factor)
        m_iqr["run_index"] = idx + 1
        m_iqr["seed"] = current_seed

        m_iso = evaluate_detection_method(
            df,
            y_true,
            method="isolation_forest",
            contamination=contamination,
            random_state=current_seed
        )
        m_iso["run_index"] = idx + 1
        m_iso["seed"] = current_seed

        iqr_runs.append(m_iqr)
        iso_runs.append(m_iso)

        all_trials.append({
            "run_index": idx + 1,
            "seed": current_seed,
            "n_samples": n_samples,
            "n_anomalies": n_anomalies,
            "contamination_rate_pct": round(100 * n_anomalies / n_samples, 1) if n_samples else 0.0,
            "method": "IQR Rule (Statistical)",
            "tp": m_iqr["tp"],
            "fp": m_iqr["fp"],
            "tn": m_iqr["tn"],
            "fn": m_iqr["fn"],
            "precision": m_iqr["precision"],
            "recall": m_iqr["recall"],
            "f1_score": m_iqr["f1"],
            "accuracy": m_iqr["accuracy"],
            "exec_time_ms": m_iqr["exec_time_ms"],
        })
        all_trials.append({
            "run_index": idx + 1,
            "seed": current_seed,
            "n_samples": n_samples,
            "n_anomalies": n_anomalies,
            "contamination_rate_pct": round(100 * n_anomalies / n_samples, 1) if n_samples else 0.0,
            "method": "Isolation Forest (Unsupervised ML)",
            "tp": m_iso["tp"],
            "fp": m_iso["fp"],
            "tn": m_iso["tn"],
            "fn": m_iso["fn"],
            "precision": m_iso["precision"],
            "recall": m_iso["recall"],
            "f1_score": m_iso["f1"],
            "accuracy": m_iso["accuracy"],
            "exec_time_ms": m_iso["exec_time_ms"],
        })

    iqr_summary = compute_summary_stats(iqr_runs)
    iso_summary = compute_summary_stats(iso_runs)

    return iqr_summary, iso_summary, iqr_runs, iso_runs, all_trials

def run_sweep_evaluations(base_seed=42, contamination="auto", iqr_factor=1.5):
    """
    Evaluates both methods across:
    1. Varying dataset sizes (100, 250, 500, 1000) at fixed 10% anomaly rate.
    2. Varying anomaly proportions (2%, 5%, 10%, 15%, 20%) at fixed 250 rows.
    """
    size_sweep = []
    sizes = [100, 250, 500, 1000]
    for s in sizes:
        anom = max(1, int(s * 0.10))
        df, y_true = generate_evaluation_dataset(n_samples=s, n_anomalies=anom, random_state=base_seed)
        m_iqr = evaluate_detection_method(df, y_true, method="iqr", iqr_factor=iqr_factor)
        m_iso = evaluate_detection_method(
            df, y_true, method="isolation_forest", contamination=contamination, random_state=base_seed
        )
        size_sweep.append({
            "size": s,
            "anomalies": anom,
            "iqr_f1": m_iqr["f1_pct"],
            "iso_f1": m_iso["f1_pct"],
            "iqr_prec": m_iqr["precision_pct"],
            "iso_prec": m_iso["precision_pct"],
            "iqr_rec": m_iqr["recall_pct"],
            "iso_rec": m_iso["recall_pct"],
            "iqr_time": m_iqr["exec_time_ms"],
            "iso_time": m_iso["exec_time_ms"],
        })

    prop_sweep = []
    proportions = [2, 5, 10, 15, 20]
    fixed_size = 250
    for p in proportions:
        anom = max(1, int(fixed_size * (p / 100.0)))
        df, y_true = generate_evaluation_dataset(n_samples=fixed_size, n_anomalies=anom, random_state=base_seed)
        m_iqr = evaluate_detection_method(df, y_true, method="iqr", iqr_factor=iqr_factor)
        m_iso = evaluate_detection_method(
            df, y_true, method="isolation_forest", contamination=contamination, random_state=base_seed
        )
        prop_sweep.append({
            "rate_pct": p,
            "anomalies": anom,
            "iqr_f1": m_iqr["f1_pct"],
            "iso_f1": m_iso["f1_pct"],
            "iqr_prec": m_iqr["precision_pct"],
            "iso_prec": m_iso["precision_pct"],
            "iqr_rec": m_iqr["recall_pct"],
            "iso_rec": m_iso["recall_pct"],
            "iqr_time": m_iqr["exec_time_ms"],
            "iso_time": m_iso["exec_time_ms"],
        })

    return size_sweep, prop_sweep

@app.route("/evaluation", methods=["GET", "POST"])
@login_required
def evaluation():
    # Read configurable parameters
    if request.method == "POST":
        raw_samples = request.form.get("n_samples", "200")
        raw_anomalies = request.form.get("n_anomalies", "20")
        raw_seed = request.form.get("random_seed", "42")
        raw_runs = request.form.get("n_runs", "5")
    else:
        raw_samples = request.args.get("n_samples", "200")
        raw_anomalies = request.args.get("n_anomalies", "20")
        raw_seed = request.args.get("random_seed", "42")
        raw_runs = request.args.get("n_runs", "5")

    try:
        n_samples = max(20, min(int(raw_samples), 2000))
    except (ValueError, TypeError):
        n_samples = 200

    try:
        n_anomalies = max(0, min(int(raw_anomalies), int(n_samples * 0.5)))
    except (ValueError, TypeError):
        n_anomalies = 20

    try:
        random_seed = max(0, min(int(raw_seed), 999999))
    except (ValueError, TypeError):
        random_seed = 42

    try:
        n_runs = max(1, min(int(raw_runs), 10))
    except (ValueError, TypeError):
        n_runs = 5

    # Run multi-seed repeated benchmark
    iqr_summary, iso_summary, iqr_runs, iso_runs, _ = run_repeated_benchmark(
        n_samples=n_samples,
        n_anomalies=n_anomalies,
        base_seed=random_seed,
        n_runs=n_runs
    )

    # Run size & proportion sweep evaluations
    size_sweep, prop_sweep = run_sweep_evaluations(base_seed=random_seed)

    # Preview rows from first seed
    preview_df, y_first = generate_evaluation_dataset(
        n_samples=n_samples,
        n_anomalies=n_anomalies,
        random_state=random_seed
    )
    preview_df = preview_df.head(6).copy()
    preview_df["is_anomaly"] = y_first.head(6).map({True: "Yes (Anomaly)", False: "No (Normal)"})
    preview_rows = preview_df.to_dict(orient="records")

    params = {
        "n_samples": n_samples,
        "n_anomalies": n_anomalies,
        "n_normal": n_samples - n_anomalies,
        "anomaly_rate": round(100 * n_anomalies / n_samples, 1) if n_samples else 0.0,
        "random_seed": random_seed,
        "n_runs": n_runs,
    }

    return render_template(
        "evaluation.html",
        iqr_summary=iqr_summary,
        iso_summary=iso_summary,
        iqr_runs=iqr_runs,
        iso_runs=iso_runs,
        size_sweep=size_sweep,
        prop_sweep=prop_sweep,
        params=params,
        preview_rows=preview_rows
    )

@app.route("/export-evaluation-csv")
@login_required
def export_evaluation_csv():
    try:
        n_samples = max(20, min(int(request.args.get("n_samples", 200)), 2000))
    except (ValueError, TypeError):
        n_samples = 200

    try:
        n_anomalies = max(0, min(int(request.args.get("n_anomalies", 20)), int(n_samples * 0.5)))
    except (ValueError, TypeError):
        n_anomalies = 20

    try:
        random_seed = max(0, min(int(request.args.get("random_seed", 42)), 999999))
    except (ValueError, TypeError):
        random_seed = 42

    try:
        n_runs = max(1, min(int(request.args.get("n_runs", 5)), 10))
    except (ValueError, TypeError):
        n_runs = 5

    _, _, _, _, all_trials = run_repeated_benchmark(
        n_samples=n_samples,
        n_anomalies=n_anomalies,
        base_seed=random_seed,
        n_runs=n_runs
    )

    trials_df = pd.DataFrame(all_trials)
    csv_buffer = io.StringIO()
    trials_df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"benchmark_results_n{n_samples}_a{n_anomalies}_seed{random_seed}.csv"
    )

@app.errorhandler(413)
def too_large(_error):
    flash("File is too large. The upload limit is 10 MB.", "danger")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
