"""
Generate architecture and UML diagrams for AI Data Quality Doctor README.
Uses only PIL (Pillow) — no external dependencies beyond what is already installed.
Run from the project root:  python outputs/generate_diagrams.py
"""
from PIL import Image, ImageDraw, ImageFont
import os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))  # outputs/ folder

# colour palette
BG        = (248, 250, 252)
SURFACE   = (255, 255, 255)
INK       = (15, 23, 42)
MUTED     = (100, 116, 139)
LINE      = (226, 232, 240)
PRIMARY   = (79, 70, 229)
PRIMARY_L = (238, 242, 255)
SUCCESS   = (16, 185, 129)
SUCCESS_L = (236, 253, 245)
WARNING   = (245, 158, 11)
WARNING_L = (255, 251, 235)
DANGER    = (239, 68, 68)
DARK_BG   = (30, 27, 75)

def load_font(size, bold=False):
    candidates = (["arialbd.ttf","Arial Bold.ttf","DejaVuSans-Bold.ttf"] if bold
                  else ["arial.ttf","Arial.ttf","DejaVuSans.ttf"])
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def center_text(draw, x, y, text, font, fill=None, anchor="mm"):
    if fill is None:
        fill = INK
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

def wrap_text(text, max_chars):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ── 1. Architecture ────────────────────────────────────────────────────────────
def make_architecture():
    W, H = 1200, 740
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fB18 = load_font(18, bold=True)
    fB14 = load_font(14, bold=True)
    fR12 = load_font(12)
    fR11 = load_font(11)
    fB22 = load_font(22, bold=True)

    d.rectangle([0, 0, W, 60], fill=DARK_BG)
    center_text(d, W//2, 30, "AI Data Quality Doctor -- System Architecture", fB22, fill=(255,255,255))

    layer_data = [
        (80,  "PRESENTATION LAYER",  PRIMARY_L,  PRIMARY),
        (220, "APPLICATION LAYER",   SUCCESS_L,  (4, 120, 87)),
        (390, "PROCESSING LAYER",    WARNING_L,  (146, 64, 14)),
        (560, "DATA LAYER",          (254,226,226), (153,27,27)),
    ]
    for (y, lbl, bg, tc) in layer_data:
        d.rectangle([20, y, W-20, y+130], fill=bg, outline=LINE, width=1)
        d.text((30, y+8), lbl, font=fR11, fill=tc)

    boxes_p = [
        (80,  100, "Login / Register",  "Auth"),
        (280, 100, "Dashboard",         "index.html"),
        (490, 100, "Results Report",    "results.html"),
        (700, 100, "Evaluation",        "evaluation.html"),
        (920, 100, "Navigation",        "base.html"),
    ]
    for (x, y, lbl, sub) in boxes_p:
        rounded_rect(d, [x, y, x+170, y+100], 10, SURFACE, PRIMARY, 2)
        center_text(d, x+85, y+32, lbl, fB14)
        center_text(d, x+85, y+58, sub, fR12, fill=MUTED)

    app_boxes = [
        (60,  240, "Flask App\n(app.py)",          PRIMARY),
        (250, 240, "Auth Routes\n/login /register", SUCCESS),
        (440, 240, "Analyze Route\n/analyze",       SUCCESS),
        (630, 240, "Download Routes\n/download-*",  SUCCESS),
        (820, 240, "Evaluation Route\n/evaluation", SUCCESS),
        (1010,240, "login_required\nDecorator",     MUTED),
    ]
    for (x, y, lbl, bc) in app_boxes:
        rounded_rect(d, [x, y, x+160, y+90], 10, SURFACE, bc, 2)
        for i, line in enumerate(lbl.split("\n")):
            center_text(d, x+80, y+25+i*22, line, fB14 if i==0 else fR12,
                        fill=bc if i==0 else INK)

    proc_boxes = [
        (60,  410, "analyze_dataframe()\nProfile Quality Metrics",     (146,64,14)),
        (300, 410, "detect_outliers()\nIQR + Isolation Forest",         (79,70,229)),
        (540, 410, "clean_dataframe()\nImpute + Deduplicate",           SUCCESS),
        (780, 410, "generate_evaluation_dataset()\nSynthetic Ground-Truth", (146,64,14)),
        (1020,410, "run_repeated_benchmark()\nMulti-seed Statistics",   (14,116,144)),
    ]
    for (x, y, lbl, bc) in proc_boxes:
        rounded_rect(d, [x, y, x+190, y+100], 10, SURFACE, bc, 2)
        for i, line in enumerate(lbl.split("\n")):
            center_text(d, x+95, y+22+i*22, line, fB14 if i==0 else fR11,
                        fill=bc if i==0 else INK)

    data_boxes = [
        (80,  580, "SQLite DB\nquality_doctor.db",    (153,27,27)),
        (310, 580, "users table\nAccounts & Hashes",  (153,27,27)),
        (520, 580, "reports table\nAnalysis History", (153,27,27)),
        (730, 580, "Session Store\nCleaned CSV + Report", (153,27,27)),
        (940, 580, "uploads/\nTemp File Storage",    MUTED),
    ]
    for (x, y, lbl, bc) in data_boxes:
        rounded_rect(d, [x, y, x+190, y+90], 10, SURFACE, bc, 2)
        for i, line in enumerate(lbl.split("\n")):
            center_text(d, x+95, y+20+i*22, line, fB14 if i==0 else fR11,
                        fill=bc if i==0 else INK)

    import math
    def arrow(x1, y1, x2, y2, c=MUTED):
        d.line([(x1,y1),(x2,y2)], fill=c, width=2)
        ang = math.atan2(y2-y1, x2-x1)
        for da in (0.4, -0.4):
            ex = x2 - 12*math.cos(ang-da)
            ey = y2 - 12*math.sin(ang-da)
            d.line([(x2,y2),(int(ex),int(ey))], fill=c, width=2)

    for cx in [165, 365, 575, 785, 1005]:
        arrow(cx, 200, cx, 238, PRIMARY)
    for cx in [140, 330, 520, 710, 900]:
        arrow(cx, 330, cx, 408, SUCCESS)
    for cx in [155, 395, 635, 875, 1035]:
        arrow(cx, 510, cx, 578, (146,64,14))

    img.save(os.path.join(OUT, "architecture.png"))
    print("architecture.png saved")

# ── 2. Use-Case ────────────────────────────────────────────────────────────────
def make_usecase():
    W, H = 1100, 780
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fB20 = load_font(20, bold=True)
    fB13 = load_font(13, bold=True)
    fR12 = load_font(12)
    fR11 = load_font(11)

    d.rectangle([0,0,W,55], fill=DARK_BG)
    center_text(d, W//2, 27, "AI Data Quality Doctor -- Use-Case Diagram", fB20, fill=(255,255,255))

    d.rectangle([200, 70, 1060, 750], outline=PRIMARY, width=2)
    d.text((210, 74), "system: AI Data Quality Doctor", font=fR12, fill=PRIMARY)

    def actor(x, y, label):
        d.ellipse([x-14, y-50, x+14, y-22], outline=INK, width=2)
        d.line([(x, y-22),(x, y+10)], fill=INK, width=2)
        d.line([(x-22, y-10),(x+22, y-10)], fill=INK, width=2)
        d.line([(x, y+10),(x-18, y+38)], fill=INK, width=2)
        d.line([(x, y+10),(x+18, y+38)], fill=INK, width=2)
        center_text(d, x, y+55, label, fB13)

    actor(90, 240, "Visitor")
    actor(90, 560, "Registered\nUser")

    ucs = [
        (230, 90,  200, 50, "Register Account",           PRIMARY),
        (230, 160, 200, 50, "Log In",                     PRIMARY),
        (230, 290, 200, 50, "Upload CSV / Excel",         SUCCESS),
        (230, 360, 200, 50, "Select Outlier Method",      SUCCESS),
        (230, 430, 200, 50, "View Quality Report",        SUCCESS),
        (230, 500, 200, 50, "Download Cleaned CSV",       SUCCESS),
        (230, 570, 200, 50, "Download JSON Report",       SUCCESS),
        (230, 640, 200, 50, "View Analysis History",      SUCCESS),
        (500, 270, 220, 50, "Detect Missing Values",      (146,64,14)),
        (500, 340, 220, 50, "Detect Duplicate Rows",      (146,64,14)),
        (500, 410, 220, 50, "IQR Outlier Detection",      (146,64,14)),
        (500, 480, 220, 50, "Isolation Forest Detection", (79,70,229)),
        (500, 550, 220, 50, "Impute & Clean Dataset",     SUCCESS),
        (790, 300, 220, 50, "Run Benchmark",              (79,70,229)),
        (790, 370, 220, 50, "Multi-seed Trials",          (79,70,229)),
        (790, 440, 220, 50, "Size & Rate Sweep",          (79,70,229)),
        (790, 510, 220, 50, "Export Benchmark CSV",       (79,70,229)),
        (790, 580, 220, 50, "View Confusion Matrix",      (79,70,229)),
    ]
    for (x, y, w, h, lbl, c) in ucs:
        d.ellipse([x, y, x+w, y+h], fill=SURFACE, outline=c, width=2)
        center_text(d, x+w//2, y+h//2, lbl, fR12)

    for (x, y, w, h, _, _) in ucs[:2]:
        d.line([(134, 240), (x, y+h//2)], fill=INK, width=1)
    for (x, y, w, h, _, _) in ucs[2:8]:
        d.line([(134, 560), (x, y+h//2)], fill=INK, width=1)
    for (x, y, w, h, _, _) in ucs[8:13]:
        d.line([(430, 315), (x, y+h//2)], fill=SUCCESS, width=1)
    for (x, y, w, h, _, _) in ucs[13:]:
        d.line([(430, 455), (x, y+h//2)], fill=(79,70,229), width=1)

    img.save(os.path.join(OUT, "usecase-uml.png"))
    print("usecase-uml.png saved")

# ── 3. Sequence ────────────────────────────────────────────────────────────────
def make_sequence():
    W, H = 1200, 740
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fB18 = load_font(18, bold=True)
    fB13 = load_font(13, bold=True)
    fR11 = load_font(11)

    d.rectangle([0,0,W,55], fill=DARK_BG)
    center_text(d, W//2, 27, "Sequence: Dataset Upload, Analysis and Cleaning", fB18, fill=(255,255,255))

    lifelines = [
        (100,  "Browser\n(User)",         PRIMARY),
        (290,  "Flask\n/analyze",         SUCCESS),
        (480,  "analyze_\ndataframe()",   (146,64,14)),
        (670,  "detect_\noutliers()",     (79,70,229)),
        (860,  "clean_\ndataframe()",     (14,116,144)),
        (1050, "SQLite\nDB",              (153,27,27)),
    ]
    HEADER_Y = 75
    LINE_START = 130
    for (x, lbl, c) in lifelines:
        rounded_rect(d, [x-60, HEADER_Y, x+60, HEADER_Y+55], 8, c, None)
        for i, line in enumerate(lbl.split("\n")):
            center_text(d, x, HEADER_Y+14+i*18, line, fB13, fill=(255,255,255))
        for y in range(LINE_START, H-30, 8):
            d.line([(x, y),(x, y+4)], fill=LINE, width=2)

    def msg(y, x1, x2, label, ret=False, colour=None):
        if colour is None:
            colour = INK
        xd = -1 if x2 < x1 else 1
        if ret:
            for sx in range(min(x1,x2), max(x1,x2), 8):
                d.line([(sx, y),(sx+4, y)], fill=colour, width=1)
        else:
            d.line([(x1, y),(x2, y)], fill=colour, width=2)
        ah = 7
        d.polygon([(x2,y),(x2-xd*ah,y-ah//2),(x2-xd*ah,y+ah//2)], fill=colour)
        mid = (x1+x2)//2
        d.text((mid-48, y-13), label, font=fR11, fill=colour)

    def act(x, y1, y2, c=None):
        if c is None:
            c = PRIMARY_L
        d.rectangle([x-8, y1, x+8, y2], fill=c, outline=LINE)

    act(290, 148, 645, SUCCESS_L)
    act(480, 205, 320, WARNING_L)
    act(670, 235, 265, PRIMARY_L)
    act(860, 348, 405, (204,251,241))
    act(1050, 450, 480, (254,226,226))

    messages = [
        (150,  100,  290,  "POST /analyze  (multipart CSV/XLSX)",    False, INK),
        (175,  290,  290,  "validate file extension & size",          False, SUCCESS),
        (210,  290,  480,  "analyze_dataframe(df, method='iqr'|'if')", False, (146,64,14)),
        (238,  480,  670,  "detect_outliers(df, method, ...)",        False, PRIMARY),
        (263,  670,  480,  "outlier_mask, details, label",            True,  PRIMARY),
        (295,  480,  480,  "compute completeness & duplicate_rate",   False, (146,64,14)),
        (318,  480,  290,  "report dict",                             True,  (146,64,14)),
        (348,  290,  860,  "clean_dataframe(df)",                     False, (14,116,144)),
        (373,  860,  860,  "median/mode impute + drop_duplicates",    False, (14,116,144)),
        (400,  860,  290,  "cleaned_df, removed_dupes",               True,  (14,116,144)),
        (428,  290,  290,  "session['last_cleaned_csv'] = ...",       False, SUCCESS),
        (450,  290, 1050,  "INSERT INTO reports (...)",               False, (153,27,27)),
        (475, 1050,  290,  "rowid OK",                                True,  (153,27,27)),
        (505,  290,  100,  "render_template('results.html')",         True,  INK),
        (540,  100,  290,  "GET /download-cleaned",                   False, INK),
        (563,  290,  100,  "send_file(cleaned.csv)",                  True,  INK),
        (593,  100,  290,  "GET /download-report",                    False, INK),
        (618,  290,  100,  "send_file(quality_report.json)",          True,  INK),
    ]
    for args in messages:
        msg(*args)

    img.save(os.path.join(OUT, "sequence-uml.png"))
    print("sequence-uml.png saved")

# ── 4. Class / Component ──────────────────────────────────────────────────────
def make_class():
    W, H = 1200, 760
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fB18 = load_font(18, bold=True)
    fB13 = load_font(13, bold=True)
    fR11 = load_font(11)
    fR12 = load_font(12)

    d.rectangle([0,0,W,55], fill=DARK_BG)
    center_text(d, W//2, 27, "Component / Module Diagram -- app.py", fB18, fill=(255,255,255))

    def comp(x, y, w, h, title, items, hdr_c=None):
        if hdr_c is None:
            hdr_c = PRIMARY
        rounded_rect(d, [x, y, x+w, y+30], 8, hdr_c, None)
        d.rectangle([x, y+16, x+w, y+30], fill=hdr_c)
        center_text(d, x+w//2, y+15, title, fB13, fill=(255,255,255))
        rounded_rect(d, [x, y+30, x+w, y+h], 8, SURFACE, hdr_c, 2)
        d.rectangle([x+2, y+30, x+w-2, y+36], fill=SURFACE)
        for i, item in enumerate(items):
            d.text((x+8, y+38+i*17), item, font=fR11, fill=INK)

    comp(20, 75, 220, 200, "Flask Application",
         ["app = Flask(__name__)",
          "SECRET_KEY (env var)",
          "MAX_CONTENT: 10 MB",
          "ALLOWED: csv xlsx xls",
          "Werkzeug password hash",
          "Session-based auth",
          "SQLite connection pool",
          "init_db() on startup"], PRIMARY)

    comp(20, 295, 220, 150, "Authentication",
         ["login_required(view)",
          "register()  GET/POST",
          "login()     GET/POST",
          "logout()",
          "generate_password_hash()",
          "check_password_hash()"], (79,70,229))

    comp(260, 75, 260, 200, "Data Profiling",
         ["analyze_dataframe(df, method)",
          " -> rows, columns",
          " -> missing_cells (int)",
          " -> missing_by_column {}",
          " -> duplicate_rows (int)",
          " -> completeness %",
          " -> duplicate_rate %",
          " -> outlier_rows (int)",
          " -> preview list[dict]"], (146,64,14))

    comp(260, 295, 260, 185, "Outlier Detection",
         ["detect_outliers(df, method,",
          "  contamination, iqr_factor,",
          "  random_state)",
          "method='iqr':",
          "  Q1-1.5xIQR per col",
          "method='isolation_forest':",
          "  SimpleImputer(median)",
          "  IsolationForest(sklearn)",
          "returns mask, details, label"], (14,116,144))

    comp(260, 505, 260, 120, "Data Cleaning",
         ["clean_dataframe(df)",
          " -> median impute numeric",
          " -> mode impute categorical",
          " -> drop_duplicates()",
          " -> cleaned_df (DataFrame)",
          " -> removed_dupes (int)"], SUCCESS)

    comp(545, 75, 250, 200, "HTTP Routes",
         ["GET  /             index()",
          "POST /analyze      analyze()",
          "  read CSV/XLSX",
          "  profile + clean + store",
          "  render results.html",
          "GET  /download-cleaned",
          "GET  /download-report",
          "GET  /evaluation",
          "GET  /export-evaluation-csv"], (14,116,144))

    comp(545, 295, 250, 235, "Evaluation Engine",
         ["generate_evaluation_dataset(",
          "  n_samples, n_anomalies,",
          "  random_state)",
          "  -> df, y_true",
          "evaluate_detection_method(",
          "  df, y_true, method)",
          "  -> TP FP TN FN",
          "  -> precision recall F1",
          "  -> accuracy latency_ms",
          "run_repeated_benchmark()",
          "  K seeds x 2 methods",
          "run_sweep_evaluations()",
          "  size+rate sweeps"], (79,70,229))

    comp(820, 75, 220, 165, "Database (SQLite)",
         ["quality_doctor.db",
          "-- users --",
          "  id, username,",
          "  password_hash, created_at",
          "-- reports --",
          "  id, user_id, filename,",
          "  rows_count, cols_count,",
          "  missing, dupes,",
          "  outlier_rows, created_at"], (153,27,27))

    comp(820, 260, 220, 175, "Jinja2 Templates",
         ["base.html  (nav, flash)",
          "login.html",
          "register.html",
          "index.html  (dashboard)",
          "results.html",
          "evaluation.html",
          "",
          "All extend base.html"], MUTED)

    comp(820, 455, 220, 100, "Static Assets",
         ["static/style.css",
          "  1,200+ line design sys",
          "  CSS variables + grid",
          "  Responsive breakpoints"], MUTED)

    for (x1,y1,x2,y2) in [
        (240,175, 260,175), (240,175, 260,390), (240,175, 260,565),
        (520,175, 545,175), (520,390, 545,390), (520,565, 545,415),
        (795,175, 820,160), (795,415, 820,350),
        (240,370, 260,370),
    ]:
        d.line([(x1,y1),(x2,y2)], fill=LINE, width=2)

    img.save(os.path.join(OUT, "class-uml.png"))
    print("class-uml.png saved")

# ── 5. Dataflow ────────────────────────────────────────────────────────────────
def make_dataflow():
    W, H = 1100, 280
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fB15 = load_font(15, bold=True)
    fR12 = load_font(12)

    d.rectangle([0,0,W,50], fill=DARK_BG)
    center_text(d, W//2, 25, "Data-Processing Pipeline", fB15, fill=(255,255,255))

    steps = [
        (55,  "Upload\nCSV/XLSX",       PRIMARY),
        (225, "Profile\nDataFrame",      (146,64,14)),
        (395, "Detect\nOutliers",        (79,70,229)),
        (565, "Clean\nDataFrame",        SUCCESS),
        (735, "Store\nReport",           (153,27,27)),
        (905, "Download\nCSV + JSON",    (14,116,144)),
    ]
    for (x, lbl, c) in steps:
        rounded_rect(d, [x, 65, x+140, 175], 14, c, None)
        for i, line in enumerate(lbl.split("\n")):
            center_text(d, x+70, 100+i*30, line, fB15, fill=(255,255,255))

    annots = [
        (55,  "csv xlsx xls\nmax 10MB"),
        (225, "missing, dupes\ncompleteness %"),
        (395, "IQR or\nIsolation Forest"),
        (565, "median/mode\n+ dedup"),
        (735, "SQLite + session\nstore"),
        (905, "cleaned.csv\nreport.json"),
    ]
    for (x, txt) in annots:
        for i, line in enumerate(txt.split("\n")):
            center_text(d, x+70, 192+i*16, line, fR12, fill=MUTED)

    for i, (x, _, _) in enumerate(steps[:-1]):
        ax = x + 140
        d.polygon([(ax,119),(ax+20,112),(ax+20,127)], fill=MUTED)

    img.save(os.path.join(OUT, "dataflow.png"))
    print("dataflow.png saved")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_architecture()
    make_usecase()
    make_sequence()
    make_class()
    make_dataflow()
    print("\nAll diagrams saved to:", OUT)
