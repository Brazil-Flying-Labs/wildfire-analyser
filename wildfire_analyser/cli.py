# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# CLI entry point for wildfire-analyser.
# Supports normal runs and predefined paper presets.


import logging
import os
from dotenv import load_dotenv
import argparse
from pathlib import Path

from wildfire_analyser.fire_assessment.post_fire_assessment import PostFireAssessment
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.mosaic_strategies import MosaicStrategy


# Logging setup

LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"

root_handler = logging.StreamHandler()
root_handler.setFormatter(logging.Formatter(LOG_FORMAT))

root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.addHandler(root_handler)

# Root quiet by default (library logs controlled separately)
root_logger.setLevel(logging.WARNING)

# Client logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Library logger (controlled via verbose flag)
lib_logger = logging.getLogger("wildfire_analyser")
lib_logger.setLevel(logging.WARNING)
lib_logger.propagate = True


# Paper preset definition

PAPER_PRESETS = {
    "PAPER_DENIZ_FUSUN_RAMAZAN": {
        "deliverables": [
            Deliverable.RGB_PRE_FIRE_VISUAL,
            Deliverable.RGB_POST_FIRE_VISUAL,
            Deliverable.DNBR_VISUAL,
            Deliverable.DNDVI_VISUAL,
            Deliverable.RBR_VISUAL,
            Deliverable.DNBR_AREA_STATISTICS,
            Deliverable.DNDVI_AREA_STATISTICS,
            Deliverable.RBR_AREA_STATISTICS,
        ],
        "runs": [
            {
                "name": "Area_1_July_Fire",
                "roi": "polygons/ccanakkale01.geojson",
                "start_date": "2023-07-01",
                "end_date": "2023-07-21",
                "days_before_after": 0,
            },
            {
                "name": "Area_2_August_Fire",
                "roi": "polygons/ccanakkale02.geojson",
                "start_date": "2023-07-31",
                "end_date": "2023-08-30",
                "days_before_after": 0,
            },
        ],
    },
}

# Paper reference statistics (Table 7 - Sentinel-2)
# Units: hectares (ha)
# Source:
#   "Spatial and statistical analysis of burned areas: 2023 Canakkale
#    forest fires"

PAPER_REFERENCE_STATS = {
    "PAPER_DENIZ_FUSUN_RAMAZAN": {
        "Area_1_July_Fire": {
            "DNBR_AREA_STATISTICS": {
                "Unburned": 504.98,
                "Low Severity": 782.86,
                "Moderate Severity": 1194.22,
                "High Severity": 614.84,
                "Very High Severity": 215.18,
                "Total Burned Area": 2807.10,
                "Total Area": 3312.08,
            },
            "DNDVI_AREA_STATISTICS": {
                "Unburned": 772.44,
                "Low Severity": 1203.05,
                "Moderate Severity": 698.01,
                "High Severity": 329.38,
                "Very High Severity": 309.20,
                "Total Burned Area": 2539.64,
                "Total Area": 3312.08,
            },
            "RBR_AREA_STATISTICS": {
                "Unburned": 602.75,
                "Low Severity": 1040.66,
                "Moderate Severity": 1279.64,
                "High Severity": 387.88,
                "Very High Severity": 1.15,
                "Total Burned Area": 2709.33,
                "Total Area": 3312.08,
            },
        },
        "Area_2_August_Fire": {
            "DNBR_AREA_STATISTICS": {
                "Unburned": 607.73,
                "Low Severity": 888.34,
                "Moderate Severity": 1229.69,
                "High Severity": 937.45,
                "Very High Severity": 781.82,
                "Total Burned Area": 3837.3,
                "Total Area": 4445.03,
            },
            "DNDVI_AREA_STATISTICS": {
                "Unburned": 1075.14,
                "Low Severity": 940.87,
                "Moderate Severity": 703.67,
                "High Severity": 681.89,
                "Very High Severity": 1043.46,
                "Total Burned Area": 3369.89,
                "Total Area": 4445.03,
            },
            "RBR_AREA_STATISTICS": {
                "Unburned": 687.17,
                "Low Severity": 1248.86,
                "Moderate Severity": 1378.75,
                "High Severity": 1128.05,
                "Very High Severity": 2.20,
                "Total Burned Area": 3757.86,
                "Total Area": 4445.03,
            },
        },
    },
}


def compare_with_paper_table_7(computed: dict, reference: dict):
    """Compare computed area statistics with Table 7 reference values.

    Percent error is calculated relative to the paper's total area, not to the
    area of each individual class.
    """
    result = {}

    total_area = reference.get("Total Area")
    if not total_area or total_area <= 0:
        raise RuntimeError("Paper reference Total Area not found or invalid")

    for cls, values in computed.items():
        if cls not in reference:
            continue

        ref_area = reference[cls]
        comp_area = values["area_ha"]

        abs_error = comp_area - ref_area
        pct_error = (abs_error / total_area) * 100

        result[cls] = {
            **values,
            "paper_area_ha": ref_area,
            "abs_error_ha": round(abs_error, 2),
            "percent_error": round(pct_error, 3),
        }

    return result


def requires_gcs_bucket(deliverables: list[Deliverable]) -> bool:
    return any(
        not d.name.endswith("_VISUAL")
        and not d.name.endswith("_AREA_STATISTICS")
        for d in deliverables
    )


def validate_roi_only_args(args):
    if (
        args.roi_only_bg_color is not None
        and not args.roi_only
    ):
        raise ValueError(
            "--roi-only-bg-color is only valid when --roi-only is also provided"
        )
# Main

def main():
    load_dotenv()

    gee_key_json = os.getenv("GEE_PRIVATE_KEY_JSON")
    if not gee_key_json:
        raise RuntimeError("GEE_PRIVATE_KEY_JSON not set")

    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")

    parser = argparse.ArgumentParser(
        description="Post-fire assessment using Google Earth Engine"
    )

    parser.add_argument("--roi", help="Path to ROI GeoJSON file")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")

    parser.add_argument(
        "--deliverables",
        nargs="+",
        help=(
            "List of deliverables to generate OR a paper preset name. "
            "Example: --deliverables DNBR_VISUAL DNBR_AREA_STATISTICS "
            "or --deliverables PAPER_DENIZ_FUSUN_RAMAZAN"
        ),
    )

    parser.add_argument(
        "--days-before-after",
        type=int,
        default=30,
        help="Number of days before and after the event date (default: 30)",
    )

    parser.add_argument(
        "--cloud-threshold",
        type=int,
        default=100,
        help="Maximum allowed scene cloud percentage (default: 100).",
    )
    parser.add_argument(
        "--fire-mosaic-strategy",
        default=MosaicStrategy.BEST_AVAILABLE_PER_TILE_MOSAIC.value,
        choices=[s.value for s in MosaicStrategy],
        help=(
            "Mosaic strategy for pre- and post-fire composites "
            f"(default: {MosaicStrategy.BEST_AVAILABLE_PER_TILE_MOSAIC.value})"
        ),
    )
    parser.add_argument(
        "--roi-only",
        action="store_true",
        help=(
            "Render visual thumbnails only inside the ROI. By default, the "
            "full ROI bounding box is shown, including rendered pixels "
            "outside the ROI."
        ),
    )
    parser.add_argument(
        "--roi-only-bg-color",
        default=None,
        help=(
            "Background color outside the ROI when --roi-only is enabled "
            "(default: black). Accepts values such as 'black', 'white', "
            "or hex colors like '#ffffff'."
        ),
    )

    args = parser.parse_args()
    validate_roi_only_args(args)

    roi_only_bg_color = args.roi_only_bg_color or "black"

    # Paper preset mode

    if (
        args.deliverables
        and len(args.deliverables) == 1
        and args.deliverables[0].upper() in PAPER_PRESETS
    ):
        preset_name = args.deliverables[0].upper()
        preset = PAPER_PRESETS[preset_name]
        preset_deliverables = preset["deliverables"]
        if requires_gcs_bucket(preset_deliverables) and not gcs_bucket_name:
            raise RuntimeError(
                "GCS_BUCKET_NAME not set for scientific deliverables"
            )

        logger.info("Running paper preset: %s", preset_name)

        runs = preset.get("runs")
        if not runs:
            raise RuntimeError(
                f"Paper preset '{preset_name}' has no runs configured"
            )

        logger.info("Number of runs: %d", len(runs))

        for cfg in runs:
            logger.info("────────────────────────────────────")
            logger.info("Processing %s", cfg["name"])

            roi_path = Path(cfg["roi"]).expanduser().resolve()
            if not roi_path.exists():
                raise FileNotFoundError(f"GeoJSON not found: {roi_path}")

            runner = PostFireAssessment(
                gee_key_json=gee_key_json,
                geojson_path=str(roi_path),
                start_date=cfg["start_date"],
                end_date=cfg["end_date"],
                deliverables=preset_deliverables,
                days_before_after=cfg["days_before_after"],
                cloud_threshold=100,
                pre_fire_mosaic_strategy = MosaicStrategy.BEST_DATE_MASKED_MOSAIC,
                post_fire_mosaic_strategy = MosaicStrategy.BEST_DATE_MASKED_MOSAIC,
                roi_only=args.roi_only,
                roi_only_bg_color=roi_only_bg_color,
                gcs_bucket=gcs_bucket_name,
                verbose=True,
            )

            result = runner.run()

            prov = result.get("provenance", {})

            pre_fire_images = prov.get("pre_fire", {}).get("images", [])
            if pre_fire_images:
                logger.info("Pre-fire images used:")
                for img in pre_fire_images:
                    logger.info(
                        "  %s | %s | cloud=%.1f",
                        img["date"],
                        img["id"],
                        img["cloud_percent"],
                    )

            post_fire_images = prov.get("post_fire", {}).get("images", [])
            if post_fire_images:
                logger.info("Post-fire images used:")
                for img in post_fire_images:
                    logger.info(
                        "  %s | %s | cloud=%.1f",
                        img["date"],
                        img["id"],
                        img["cloud_percent"],
                    )

            logger.info("Visual outputs:")
            for name, item in result["visual"].items():
                logger.info("  %s -> %s", name, item["url"])

            logger.info("Statistics:")
            for stat_name, stat_value in result["statistics"].items():
                paper_ref = (
                    PAPER_REFERENCE_STATS
                    .get(preset_name, {})
                    .get(cfg["name"], {})
                    .get(stat_name)
                )

                if paper_ref:
                    stat_value = compare_with_paper_table_7(
                        stat_value, paper_ref)

                logger.info("  %s:", stat_name)

                for cls, values in stat_value.items():
                    if "abs_error_ha" in values:
                        logger.info(
                            "    %-20s | "
                            "Calc (ha): %8.2f | "
                            "Paper (ha): %8.2f | "
                            "Abs Err (ha): %7.2f | "
                            "Err (%%): %6.2f",
                            cls,
                            values["area_ha"],
                            values["paper_area_ha"],
                            values["abs_error_ha"],
                            values["percent_error"],
                        )
                    else:
                        logger.info(
                            "    %-20s | Area (ha): %8.2f | Ratio (%%): %6.2f",
                            cls,
                            values["area_ha"],
                            values["ratio_percent"],
                        )

    else: 

        # Normal mode

        if args.deliverables:
            deliverables = [Deliverable[name.upper()]
                            for name in args.deliverables]
        else:
            deliverables = list(Deliverable)

        if requires_gcs_bucket(deliverables) and not gcs_bucket_name:
            raise RuntimeError(
                "GCS_BUCKET_NAME not set for scientific deliverables"
            )

        if not args.roi or not args.start_date or not args.end_date:
            raise ValueError("--roi, --start-date and --end-date are required")

        geojson_path = Path(args.roi).expanduser().resolve()
        if not geojson_path.exists():
            raise FileNotFoundError(f"GeoJSON not found: {geojson_path}")

        runner = PostFireAssessment(
            gee_key_json=gee_key_json,
            geojson_path=str(geojson_path),
            start_date=args.start_date,
            end_date=args.end_date,
            days_before_after=args.days_before_after,
            cloud_threshold=args.cloud_threshold,
            deliverables=deliverables,
            pre_fire_mosaic_strategy=args.fire_mosaic_strategy,
            post_fire_mosaic_strategy=args.fire_mosaic_strategy,
            roi_only=args.roi_only,
            roi_only_bg_color=roi_only_bg_color,
            gcs_bucket=gcs_bucket_name,
            verbose=True,
        )

        result = runner.run()

        prov = result.get("provenance", {})

        pre_fire_images = prov.get("pre_fire", {}).get("images", [])
        if not pre_fire_images:
            raise RuntimeError(
                "No pre-fire images found for the selected period and cloud threshold."
            )
        logger.info("Pre-fire images used:")
        for img in pre_fire_images:
            logger.info(
                "  %s | %s | cloud=%.1f",
                img["date"],
                img["id"],
                img["cloud_percent"],
            )

        post_fire_images = prov.get("post_fire", {}).get("images", [])
        if not post_fire_images:
            raise RuntimeError(
                "No post-fire images found for the selected period and cloud threshold."
            )
        logger.info("Post-fire images used:")
        for img in post_fire_images:
            logger.info(
                "  %s | %s | cloud=%.1f",
                img["date"],
                img["id"],
                img["cloud_percent"],
            )

        if result["scientific"]:
            logger.info("Scientific outputs:")
            for name, item in result["scientific"].items():
                logger.info(
                    "  %s -> %s (gee_task_id=%s)",
                    name,
                    item["url"],
                    item.get("gee_task_id"),
                )

        logger.info("Visual outputs:")
        for name, item in result["visual"].items():
            logger.info("  %s -> %s", name, item["url"])

        logger.info("Statistics:")
        for stat_name, stat_value in result["statistics"].items():
            logger.info("  %s:", stat_name)
            for cls, values in stat_value.items():
                logger.info(
                    "    %-20s | Area (ha): %8.2f | Ratio (%%): %6.2f",
                    cls,
                    values["area_ha"],
                    values["ratio_percent"],
                )

    
if __name__ == "__main__":
    SUCCESS_MSG = (
        "\nSUCCESS: Request processed successfully.\n"
        "All deliverables were generated as expected.\n"
    )
    main()
    print(SUCCESS_MSG)
