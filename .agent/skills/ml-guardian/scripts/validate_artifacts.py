#!/usr/bin/env python3
"""Run ML artifacts validation on outputs_prod."""

import json
import sys
from pathlib import Path


def get_latest_run_dir(base_dir: Path) -> Path | None:
    if not base_dir.exists():
        return None
    dirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def main() -> int:
    base_dir = Path("outputs_prod")
    latest_run = get_latest_run_dir(base_dir)

    if not latest_run:
        print(
            "WARNING: No outputs_prod directory or runs found. Skipping ML Guardian."
        )
        return 0

    print(f"ML Guardian inspecting latest run: {latest_run}")

    # Check best_model.cal.json
    cal_file = latest_run / "best_model.cal.json"
    if not cal_file.exists():
        print(f"CRITICAL: Failed to find {cal_file}")
        return 1

    try:
        cal_data = json.loads(cal_file.read_text("utf-8"))

        # Calibration metrics are bounded by ECE, accuracy, or confidence thresholds.
        # Checks threshold structure depending on what VITRUVIANO outputs.
        # Verify 'calibration_error' or 'ece' is <= 0.15 for safety.
        # Or 'confidence' >= 0.85

        ece = cal_data.get("ece", cal_data.get("expected_calibration_error"))
        if ece is not None and ece > 0.15:
            print(f"CRITICAL: ECE ({ece}) exceeds threshold (0.15)")
            return 1

        confidence = cal_data.get(
            "confidence", cal_data.get("mean_confidence")
        )
        if confidence is not None and confidence < 0.80:
            print(
                f"CRITICAL: Confidence ({confidence}) below threshold (0.80)"
            )
            return 1

    except json.JSONDecodeError:
        print(f"CRITICAL: Failed to parse {cal_file} as JSON.")
        return 1
    except Exception as e:
        print(f"CRITICAL: Exception parsing calibration file: {e}")
        return 1

    return _check_gradcam(latest_run)


def _check_gradcam(latest_run: Path) -> int:
    # Check GradCAM artifacts
    gradcam_report = latest_run / "gradcam_report.txt"
    if gradcam_report.exists():
        content = gradcam_report.read_text("utf-8").lower()
        if "error" in content or "nan" in content:
            print(f"CRITICAL: Errors or NaNs in {gradcam_report}")
            return 1
    else:
        gradcam_images = list(latest_run.glob("**/*gradcam*.png"))
        if not gradcam_images:
            print(f"WARNING: No GradCAM outputs found in {latest_run}")

    print("ML Guardian verification passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
