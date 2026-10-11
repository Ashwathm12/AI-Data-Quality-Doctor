# Anomaly Detection Benchmark Methodology & Evaluation Guide

This document details the scientific methodology, experimental design, and reproducibility steps for the **Anomaly Detection Evaluation Dashboard** in the *AI Data Quality Doctor* project.

---

## 1. Experimental Design & Architecture

### 1.1 Objective
To empirically compare the detection performance, robustness, and execution latency of two distinct anomaly detection paradigms on tabular numerical data:
1. **Interquartile Range (IQR) Rule:** A deterministic, parametric statistical boundary method (univariate).
2. **Isolation Forest:** An unsupervised tree ensemble machine learning method that isolates anomalies in multidimensional feature space (multivariate).

### 1.2 Synthetic Ground-Truth Isolation
* **Controlled Evaluation:** In real-world uploaded datasets, true anomaly status is unknown. To measure True Positives (TP), False Positives (FP), True Negatives (TN), and False Negatives (FN), the benchmark generates a controlled synthetic dataset where ground-truth labels (`y_true`) are known.
* **Strict Information Barrier:** Ground-truth labels are kept in a separate `pd.Series` and are **never** passed to `detect_outliers()`. Both detection algorithms receive only the numeric feature matrix `df`.
* **Identical Test Beds:** For every experiment trial, both methods evaluate the exact same matrix of numerical features.

---

## 2. Mathematical Consistency & Evaluation Metrics

For every trial, the confusion matrix elements are calculated:
* **True Positives (TP):** Flagged rows that are actual injected anomalies.
* **False Positives (FP):** Flagged rows that are normal data points (false alarms).
* **True Negatives (TN):** Unflagged rows that are normal data points.
* **False Negatives (FN):** Unflagged rows that are actual injected anomalies.

Total data points satisfy:
$$\text{Total Samples } (N) = \text{TP} + \text{FP} + \text{TN} + \text{FN}$$

### Core Metrics
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}} \quad (\text{if } \text{TP} + \text{FP} > 0 \text{ else } 0.0)$$

$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}} \quad (\text{if } \text{TP} + \text{FN} > 0 \text{ else } 0.0)$$

$$\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} \quad (\text{if } \text{Precision} + \text{Recall} > 0 \text{ else } 0.0)$$

$$\text{Accuracy} = \frac{\text{TP} + \text{TN}}{N} \quad (\text{if } N > 0 \text{ else } 0.0)$$

$$\text{Latency} = \Delta t = (t_{\text{end}} - t_{\text{start}}) \times 1000 \text{ ms}$$

### Multi-Trial Statistical Aggregation
To evaluate stability across seed variations, experiments are repeated across $K$ trials (default $K=5$). For each metric $X \in \{\text{Precision}, \text{Recall}, \text{F1}, \text{Accuracy}, \text{Latency}\}$:
$$\text{Mean} (\mu) = \frac{1}{K} \sum_{i=1}^{K} X_i$$

$$\text{Sample Standard Deviation} (s) = \sqrt{\frac{1}{K - 1} \sum_{i=1}^{K} (X_i - \mu)^2} \quad (\text{for } K > 1)$$

---

## 3. Configurable Parameters & Hyperparameters

| Parameter | Default | Range / Type | Description |
| :--- | :--- | :--- | :--- |
| `n_samples` | 200 | 20 to 2,000 | Total rows generated per trial |
| `n_anomalies` | 20 | 0 to 50% of $N$ | Injected ground-truth anomalies |
| `random_seed` | 42 | 0 to 999,999 | Base seed for the random number generator |
| `n_runs` | 5 | 1 to 10 | Number of repeated seed trials |
| `iqr_factor` | 1.5 | float $> 0$ | Tukey's boundary factor ($Q_1 - 1.5\text{IQR}, Q_3 + 1.5\text{IQR}$) |
| `contamination` | `"auto"` | float $\in (0, 0.5]$ or `"auto"` | Expected outlier proportion for `IsolationForest` |

---

## 4. Empirical Scaling Sweeps

The evaluation dashboard automatically runs parameter sweeps on the base seed:
1. **Dataset Size Sweep ($N$):** Evaluated at $N \in [100, 250, 500, 1000]$ at fixed 10% contamination rate.
2. **Contamination Proportion Sweep:** Evaluated at contamination rates $\in [2\%, 5\%, 10\%, 15\%, 20\%]$ at fixed $N = 250$ rows.

---

## 5. Academic Limitations & Real-World Considerations

1. **Synthetic vs. Real-World Distributions:**
   Synthetic datasets model normal data as Gaussian clusters with uniform shifted noise. Real business datasets frequently feature skewed non-normal distributions, categorical covariates, multimodal clusters, and missing values.
2. **Univariate vs. Multivariate Nature:**
   * **IQR:** Analyzes each feature in isolation. It cannot detect multivariate anomalies (points whose individual feature values are within typical ranges, but whose joint combination is anomalous).
   * **Isolation Forest:** Analyzes all numeric features jointly in multidimensional space. It can detect subtle multivariate anomalies, but requires higher computational overhead.
3. **Non-Destructive Principle:**
   Neither algorithm should automatically delete flagged rows in production. In real-world data, automated flags serve strictly as prioritization markers for human subject-matter experts.

---

## 6. How to Reproduce Experiments

### Running in Browser
1. Log in to the application at `http://127.0.0.1:5000/`.
2. Navigate to **Evaluation** in the navbar.
3. Enter desired parameters (e.g. $N=200$, Anomalies=20, Seed=42, Trials=5).
4. Click **Run Benchmark**.
5. Click **Export Benchmark CSV** to download all raw trial data.

### Running Automated Test Suite
From the project folder in PowerShell:
```powershell
python -c "import unittest; loader = unittest.TestLoader(); suite = loader.discover('C:/Users/ashwa/.gemini/antigravity-ide/brain/eb23d912-c4ef-475a-a77e-bb2734039da5/scratch', pattern='test_evaluation.py'); runner = unittest.TextTestRunner(verbosity=2); res = runner.run(suite); exit(0 if res.wasSuccessful() else 1)"
```
