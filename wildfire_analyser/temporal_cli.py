# SPDX-License-Identifier: MIT
#
# Command-line interface for burn trend pipeline.

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from wildfire_analyser.burn_trend.burn_trend_assessment import (
    BurnTrendAssessment,
)

LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"
root_handler = logging.StreamHandler()
root_handler.setFormatter(logging.Formatter(LOG_FORMAT))
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.addHandler(root_handler)
root_logger.setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _validate_year_month(value: str, field_name: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be in YYYY-MM format (got '{value}')"
        ) from exc

    normalized = parsed.strftime("%Y-%m")
    if normalized != value:
        raise ValueError(
            f"{field_name} must be in YYYY-MM format (got '{value}')"
        )
    return value


def main() -> None:
    load_dotenv()

    gee_key_json = os.getenv("GEE_PRIVATE_KEY_JSON")
    if not gee_key_json:
        raise RuntimeError("GEE_PRIVATE_KEY_JSON not set")

    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not gcs_bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME not set")

    parser = argparse.ArgumentParser(
        description="Temporal burn disturbance monitoring (CFDI)"
    )

    parser.add_argument("--roi", required=True, help="Path to ROI GeoJSON")
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date YYYY-MM",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date YYYY-MM",
    )

    parser.add_argument(
        "--cloud-threshold",
        type=int,
        default=35,
        help="Max CLOUDY_PIXEL_PERCENTAGE (default: 35)",
    )

    parser.add_argument(
        "--max-images-per-month",
        type=int,
        default=3,
        help="How many least-cloudy images to keep per month (default: 3)",
    )

    parser.add_argument(
        "--monthly-composite",
        default="median",
        choices=["median", "medoid"],
        help="Monthly composite strategy (median|medoid)",
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Skip chart generation and return JSON statistics only.",
    )

    parser.add_argument(
        "--burn-threshold",
        type=float,
        default=0.10,
        help="Monthly dNBR threshold for burned fraction (default: 0.10)",
    )
    parser.add_argument(
        "--burn-rbr-threshold",
        type=float,
        default=0.15,
        help="Monthly RBR threshold for burned fraction confirmation (default: 0.15)",
    )
    parser.add_argument(
        "--burn-post-nbr-threshold",
        type=float,
        default=-0.20,
        help="Post-month NBR threshold for burned pixel confirmation (default: -0.20)",
    )
    parser.add_argument("--cfdi-w1", type=float, default=0.4, help="CFDI weight w1 (shock)")
    parser.add_argument("--cfdi-w2", type=float, default=0.7, help="CFDI weight w2 (abrupt drop)")
    parser.add_argument("--cfdi-w3", type=float, default=2.4, help="CFDI weight w3 (burn fraction)")
    parser.add_argument("--cfdi-w4", type=float, default=0.4, help="CFDI weight w4 (recovery)")
    parser.add_argument(
        "--cfdi-min-valid-coverage",
        type=float,
        default=0.6,
        help="Minimum pairwise valid coverage for full CFDI confidence (default: 0.6)",
    )
    parser.add_argument(
        "--cfdi-burn-evidence-reference",
        type=float,
        default=0.10,
        help="Burn-fraction reference used to gate shock/drop contributions (default: 0.10)",
    )

    args = parser.parse_args()

    roi_path = Path(args.roi).expanduser().resolve()
    if not roi_path.exists():
        raise FileNotFoundError(f"GeoJSON not found: {roi_path}")

    _validate_year_month(args.start_date, "start_date")
    _validate_year_month(args.end_date, "end_date")

    runner = BurnTrendAssessment(
        gee_key_json=gee_key_json,
        geojson_path=str(roi_path),
        start_date=args.start_date,
        end_date=args.end_date,
        cloud_threshold=args.cloud_threshold,
        max_images_per_month=args.max_images_per_month,
        burn_threshold=args.burn_threshold,
        burn_rbr_threshold=args.burn_rbr_threshold,
        burn_post_nbr_threshold=args.burn_post_nbr_threshold,
        cfdi_w1=args.cfdi_w1,
        cfdi_w2=args.cfdi_w2,
        cfdi_w3=args.cfdi_w3,
        cfdi_w4=args.cfdi_w4,
        cfdi_min_valid_coverage=args.cfdi_min_valid_coverage,
        cfdi_burn_evidence_reference=args.cfdi_burn_evidence_reference,
        monthly_composite=args.monthly_composite,
        gcs_bucket=gcs_bucket_name,
        stats_only=args.stats_only,
        verbose=True,
    )

    report = runner.run()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
