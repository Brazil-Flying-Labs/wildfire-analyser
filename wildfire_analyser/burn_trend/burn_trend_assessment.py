# SPDX-License-Identifier: MIT
#
# Burn trend pipeline orchestration.

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, date
import calendar
import json
import ee
import logging

from wildfire_analyser.burn_trend.auth import authenticate_gee
from wildfire_analyser.burn_trend.resolver import DAGExecutionContext, execute_dag
from wildfire_analyser.burn_trend.deliverables import Deliverable
from wildfire_analyser.burn_trend import utils


class BurnTrendAssessment:
    DEFAULT_SCALE = utils.DEFAULT_SCALE

    def __init__(
        self,
        gee_key_json: str,
        geojson_path: str,
        start_date: str,
        end_date: str,
        cloud_threshold: int | None,
        monthly_composite: str,
        gcs_bucket: str,
        max_images_per_month: int = 3,
        burn_threshold: float = 0.10,
        burn_rbr_threshold: float = 0.15,
        burn_post_nbr_threshold: float = -0.20,
        cfdi_w1: float = 0.4,
        cfdi_w2: float = 0.7,
        cfdi_w3: float = 2.4,
        cfdi_w4: float = 0.4,
        cfdi_min_valid_coverage: float = 0.6,
        cfdi_burn_evidence_reference: float = 0.10,
        stats_only: bool = False,
        verbose: bool = False,
    ) -> None:
        level = logging.INFO if verbose else logging.WARNING
        logging.getLogger("wildfire_analyser").setLevel(level)

        authenticate_gee(gee_key_json)

        start = self._parse_date(start_date, "start_date", is_end=False)
        end = self._parse_date(end_date, "end_date", is_end=True)
        if start > end:
            raise ValueError(
                f"start_date must be <= end_date (got {start_date} > {end_date})"
            )
        start_norm = start.strftime("%Y-%m-%d")
        end_norm = end.strftime("%Y-%m-%d")

        self.roi = self._load_geojson(Path(geojson_path))
        self.roi_name = Path(geojson_path).stem
        self.start_date = start_norm
        self.end_date = end_norm

        self.context = DAGExecutionContext(
            roi=self.roi,
            roi_name=self.roi_name,
            start_date=start_norm,
            end_date=end_norm,
            cloud_threshold=cloud_threshold,
            max_images_per_month=max_images_per_month,
            burn_threshold=burn_threshold,
            burn_rbr_threshold=burn_rbr_threshold,
            burn_post_nbr_threshold=burn_post_nbr_threshold,
            cfdi_w1=cfdi_w1,
            cfdi_w2=cfdi_w2,
            cfdi_w3=cfdi_w3,
            cfdi_w4=cfdi_w4,
            cfdi_min_valid_coverage=cfdi_min_valid_coverage,
            cfdi_burn_evidence_reference=cfdi_burn_evidence_reference,
            monthly_composite=monthly_composite,
            stats_only=stats_only,
            gcs_bucket=gcs_bucket,
        )

    def run(self) -> Dict[str, Any]:
        outputs = execute_dag([Deliverable.REPORT], self.context)
        return outputs[Deliverable.REPORT]

    @staticmethod
    def _load_geojson(path: Path) -> ee.Geometry:
        with open(path) as handle:
            geojson = json.load(handle)
        return ee.Geometry(geojson["features"][0]["geometry"])

    @staticmethod
    def _parse_date(value: str, field_name: str, is_end: bool) -> date:
        try:
            month_only = datetime.strptime(value, "%Y-%m").date()
            if month_only.strftime("%Y-%m") != value:
                raise ValueError
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be in YYYY-MM format (got '{value}')"
            ) from exc

        if is_end:
            last_day = calendar.monthrange(month_only.year, month_only.month)[1]
            return date(month_only.year, month_only.month, last_day)
        return date(month_only.year, month_only.month, 1)

    @staticmethod
    def generate_object_name(prefix: str, start_date: str, end_date: str) -> str:
        return utils.generate_object_name(prefix, start_date, end_date)
