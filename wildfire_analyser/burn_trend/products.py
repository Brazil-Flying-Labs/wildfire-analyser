# SPDX-License-Identifier: MIT
#
# Processing node implementations for burn trend pipeline.

from typing import Callable, Dict, Any, List
import math
import logging
import re
import io
from datetime import datetime, UTC
import ee

from wildfire_analyser.burn_trend.dependencies import Dependency
from wildfire_analyser.burn_trend.time_windows import month_windows
from wildfire_analyser.burn_trend.sentinel2 import gather_collection, COLLECTION_ID
from wildfire_analyser.burn_trend import utils
from wildfire_analyser.burn_trend.exporters.gcs import upload_bytes_to_gcs

ProductExecutor = Callable[[Any], Any]
PRODUCT_REGISTRY: Dict[Dependency, ProductExecutor] = {}
logger = logging.getLogger(__name__)


def register(dep: Dependency):
    def decorator(func: ProductExecutor):
        PRODUCT_REGISTRY[dep] = func
        return func
    return decorator


def _build_monthly_composite(collection: ee.ImageCollection, strategy: str) -> ee.Image:
    strategy = (strategy or "median").lower()

    if strategy == "median":
        return collection.median()

    if strategy == "medoid":
        bands = ["B2_refl", "B4_refl", "B8_refl", "B11_refl", "B12_refl"]
        median = collection.select(bands).median()

        def add_dist(img: ee.Image) -> ee.Image:
            diff = img.select(bands).subtract(median).pow(2).reduce("sum")
            inv = diff.multiply(-1).rename("inv_dist")
            return img.addBands(inv)

        return (
            collection.map(add_dist)
            .qualityMosaic("inv_dist")
            .select(collection.first().bandNames())
        )

    raise ValueError(f"Unknown monthly composite strategy: {strategy}")


def _compute_index_images(
    composite: ee.Image,
    indices_to_compute: List[str] | None = None,
) -> Dict[str, ee.Image]:
    requested = set(indices_to_compute or ["NDVI", "NBR", "NDFI", "EVI"])
    nir = composite.select("B8_refl")
    red = composite.select("B4_refl")
    blue = composite.select("B2_refl")

    result: Dict[str, ee.Image] = {}

    if "NDVI" in requested:
        result["NDVI"] = nir.subtract(red).divide(nir.add(red)).rename("ndvi")

    if "NBR" in requested or "NDFI" in requested:
        b12 = composite.select("B12_refl").resample("bilinear").reproject(
            nir.projection()
        )

    if "NBR" in requested:
        result["NBR"] = nir.subtract(b12).divide(nir.add(b12)).rename("nbr")

    if "EVI" in requested:
        result["EVI"] = (
            nir.subtract(red)
            .multiply(2.5)
            .divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1))
            .rename("evi")
        )

    if "NDFI" in requested:
        # NDFI via SMA (fractions).
        b3 = composite.select("B3_refl")
        b11 = composite.select("B11_refl").resample("bilinear").reproject(
            nir.projection()
        )
        sma_bands = ee.Image.cat([blue, b3, red, nir, b11, b12])

        endmembers = [
            [0.0119, 0.0475, 0.0169, 0.625, 0.2399, 0.0675],  # GV
            [0.1514, 0.1597, 0.1421, 0.3053, 0.7707, 0.1975],  # NPV
            [0.1799, 0.2479, 0.3158, 0.5437, 0.7707, 0.6646],  # Soil
            [0.4031, 0.8714, 0.79, 0.8989, 0.7002, 0.6607],   # Cloud
        ]
        fractions = sma_bands.unmix(endmembers).rename(["GV", "NPV", "Soil", "Cloud"])
        gv = fractions.select("GV")
        npv = fractions.select("NPV")
        soil = fractions.select("Soil")
        cloud = fractions.select("Cloud")

        shade = ee.Image(1).subtract(gv.add(npv).add(soil).add(cloud)).max(0)
        gvshade = gv.divide(ee.Image(1).subtract(shade))

        result["NDFI"] = (
            gvshade.subtract(npv.add(soil))
            .divide(gvshade.add(npv).add(soil))
            .rename("ndfi")
        )

    return result


def _compute_baseline(monthly_stats: List[Dict[str, Any]]) -> Dict[int, float]:
    grouped: Dict[int, List[float]] = {}
    for item in monthly_stats:
        if item.get("mean") is None:
            continue
        grouped.setdefault(item["month_num"], []).append(item["mean"])

    baseline = {}
    for month_num, values in grouped.items():
        if values:
            baseline[month_num] = sum(values) / len(values)
    return baseline


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    try:
        num = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(num):
        return float(default)
    return num


def _plot_cfdi_series(
    monthly_series: List[Dict[str, Any]],
    roi_name: str,
    start_date: str,
    end_date: str,
) -> bytes:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError("matplotlib is required for plotting") from exc

    months = [item["month"] for item in monthly_series]
    cfdi = [item["index_values"]["CFDI"]["mean"] for item in monthly_series]
    burn_fraction = [item["index_values"]["BURN_FRACTION"]["mean"] for item in monthly_series]
    nbr = [item["index_values"]["NBR"]["mean"] for item in monthly_series]
    tick_positions = list(range(0, len(months), 6))
    tick_labels = [months[i] for i in tick_positions]

    fig, ax1 = plt.subplots(figsize=(16, 7), dpi=180)
    ax1.plot(months, cfdi, label="CFDI", linewidth=2.6, color="#d62728")
    ax1.plot(months, nbr, label="NBR (observed)", linewidth=1.3, color="#1f77b4", alpha=0.8)
    ax1.set_ylabel("CFDI / NBR")
    ax1.set_xlabel("Month")
    ax1.grid(alpha=0.25)
    ax1.axhline(0.0, color="black", linewidth=0.8, alpha=0.6)

    ax2 = ax1.twinx()
    ax2.bar(months, burn_fraction, width=0.8, alpha=0.15, color="#ff7f0e", label="BurnFraction")
    ax2.set_ylabel("BurnFraction")
    ax2.set_ylim(0.0, 1.0)

    ax1.set_xticks(tick_positions, tick_labels, rotation=45)
    fig.suptitle(f"CFDI | ROI: {roi_name} | Period: {start_date} to {end_date}")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc="upper left")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def _normalize_scene_id(scene_index: str | None) -> str | None:
    if not scene_index:
        return scene_index
    # Drops EE-derived prefixes like "1_1_..._" and keeps the canonical S2 scene tail.
    match = re.search(r"(20\d{6}T\d{6}_[0-9]{8}T[0-9]{6}_T[0-9A-Z]{5})$", scene_index)
    if match:
        return match.group(1)
    return scene_index


def _build_imagery_catalog(collection: ee.ImageCollection) -> Dict[str, Any]:
    rows = (
        collection
        .reduceColumns(
            reducer=ee.Reducer.toList(3),
            selectors=["system:index", "CLOUDY_PIXEL_PERCENTAGE", "system:time_start"],
        )
        .get("list")
        .getInfo()
    ) or []

    selected_images: List[Dict[str, Any]] = []
    for row in rows:
        image_index = _normalize_scene_id(row[0])
        cloud_pct = row[1]
        time_start_ms = row[2]

        acquired_on = None
        if time_start_ms is not None:
            acquired_on = datetime.fromtimestamp(
                float(time_start_ms) / 1000.0,
                tz=UTC,
            ).strftime("%Y-%m-%d")

        selected_images.append({
            "gee_image_id": f"{COLLECTION_ID}/{image_index}",
            "acquired_on": acquired_on,
            "cloudy_pixel_percentage": cloud_pct,
        })

    selected_images.sort(
        key=lambda item: (
            item.get("acquired_on") or "",
            item.get("gee_image_id") or "",
        )
    )

    return {
        "source_collection": COLLECTION_ID,
        "image_count": len(selected_images),
        "selected_images": selected_images,
    }


@register(Dependency.COLLECTION_GATHERING)
def collection_gathering(context):
    roi = context.inputs["roi"]
    start_date = context.inputs["start_date"]
    end_date = context.inputs["end_date"]
    cloud_threshold = context.inputs.get("cloud_threshold")

    return gather_collection(roi, start_date, end_date, cloud_threshold)


@register(Dependency.MONTH_WINDOWS)
def build_month_windows(context):
    return month_windows(context.inputs["start_date"], context.inputs["end_date"])


@register(Dependency.MONTHLY_COMPOSITES)
def build_monthly_composites(context):
    collection = context.get(Dependency.COLLECTION_GATHERING)
    windows = context.get(Dependency.MONTH_WINDOWS)
    strategy = context.inputs.get("monthly_composite", "median")
    max_images_per_month = context.inputs.get("max_images_per_month", 3)

    empty = (
        ee.Image.constant([0, 0, 0, 0, 0, 0])
        .rename(["B2_refl", "B3_refl", "B4_refl", "B8_refl", "B11_refl", "B12_refl"])
        .updateMask(ee.Image(0))
    )
    monthly = []

    for win in windows:
        filtered = collection.filterDate(win["start"], win["end"])
        selected = (
            filtered
            .sort("CLOUDY_PIXEL_PERCENTAGE")
            .limit(max_images_per_month)
        )
        count = selected.size()
        composite = ee.Image(
            ee.Algorithms.If(
                count.gt(0),
                _build_monthly_composite(selected, strategy),
                empty,
            )
        )

        monthly.append({
            **win,
            "count": count,
            "selected_collection": selected,
            "composite": composite,
        })

    return monthly


def _compute_index_monthly(monthly_composites: List[Dict[str, Any]],
                           index_name: str) -> List[Dict[str, Any]]:
    results = []
    for item in monthly_composites:
        composite = item.get("composite")
        if composite is None:
            results.append({**item, "index": None})
            continue

        indices = _compute_index_images(composite)
        results.append({**item, "index": indices[index_name]})

    return results


@register(Dependency.NDVI_MONTHLY)
def ndvi_monthly(context):
    monthly = context.get(Dependency.MONTHLY_COMPOSITES)
    return _compute_index_monthly(monthly, "NDVI")


@register(Dependency.NBR_MONTHLY)
def nbr_monthly(context):
    monthly = context.get(Dependency.MONTHLY_COMPOSITES)
    return _compute_index_monthly(monthly, "NBR")


@register(Dependency.NDFI_MONTHLY)
def ndfi_monthly(context):
    monthly = context.get(Dependency.MONTHLY_COMPOSITES)
    return _compute_index_monthly(monthly, "NDFI")


@register(Dependency.EVI_MONTHLY)
def evi_monthly(context):
    monthly = context.get(Dependency.MONTHLY_COMPOSITES)
    return _compute_index_monthly(monthly, "EVI")


def _compute_monthly_stats(context, monthly_index: List[Dict[str, Any]]) -> ee.FeatureCollection:
    roi = context.inputs["roi"]
    include_median = context.inputs.get("include_median", False)
    include_stddev = context.inputs.get("include_stddev", False)
    scale = utils.DEFAULT_SCALE

    reducer = ee.Reducer.mean().combine(
        ee.Reducer.count(), sharedInputs=True
    )

    if include_median:
        reducer = reducer.combine(ee.Reducer.median(), sharedInputs=True)

    if include_stddev:
        reducer = reducer.combine(ee.Reducer.stdDev(), sharedInputs=True)

    features = []
    for item in monthly_index:
        index_image = item.get("index")
        stats = index_image.reduceRegion(
            reducer=reducer,
            geometry=roi,
            scale=scale,
            maxPixels=1e13,
        )

        props = {
            "month": item["month"],
            "year": item["year"],
            "month_num": item["month_num"],
            "count_images": item["count"],
            "mean": stats.get("mean"),
            "valid_count": stats.get("count"),
        }

        if include_median:
            props["median"] = stats.get("median")
        if include_stddev:
            props["stddev"] = stats.get("stdDev")

        features.append(ee.Feature(None, props))

    return ee.FeatureCollection(features)


@register(Dependency.NDVI_STATS)
def ndvi_stats(context):
    return _compute_monthly_stats(context, context.get(Dependency.NDVI_MONTHLY))


@register(Dependency.NBR_STATS)
def nbr_stats(context):
    return _compute_monthly_stats(context, context.get(Dependency.NBR_MONTHLY))


@register(Dependency.NDFI_STATS)
def ndfi_stats(context):
    return _compute_monthly_stats(context, context.get(Dependency.NDFI_MONTHLY))


@register(Dependency.EVI_STATS)
def evi_stats(context):
    return _compute_monthly_stats(context, context.get(Dependency.EVI_MONTHLY))


@register(Dependency.REPORT_JSON)
def build_report(context):
    monthly = context.get(Dependency.MONTHLY_COMPOSITES)
    roi = context.inputs["roi"]
    base_scale = utils.DEFAULT_SCALE

    stats_only = context.inputs.get("stats_only", False)
    burn_threshold = float(context.inputs.get("burn_threshold", 0.10))
    burn_rbr_threshold = float(context.inputs.get("burn_rbr_threshold", 0.15))
    burn_post_nbr_threshold = float(context.inputs.get("burn_post_nbr_threshold", -0.20))
    cfdi_min_valid_coverage = float(context.inputs.get("cfdi_min_valid_coverage", 0.6))
    cfdi_burn_evidence_reference = float(context.inputs.get("cfdi_burn_evidence_reference", 0.10))
    cfdi_w1 = float(context.inputs.get("cfdi_w1", 0.4))
    cfdi_w2 = float(context.inputs.get("cfdi_w2", 0.7))
    cfdi_w3 = float(context.inputs.get("cfdi_w3", 2.4))
    cfdi_w4 = float(context.inputs.get("cfdi_w4", 0.4))

    all_indices = ["NDVI", "NBR"]
    computed_indices = all_indices
    if stats_only:
        base_scale = 240

    def _reduce_region_with_retry(image: ee.Image, reducer: ee.Reducer):
        scales = [base_scale, 120, 240, 480] if stats_only else [base_scale, 20, 30, 60, 120]
        last_exc = None
        for scale in scales:
            try:
                stats = image.reduceRegion(
                    reducer=reducer,
                    geometry=roi,
                    scale=scale,
                    maxPixels=1e13,
                    bestEffort=stats_only,
                    tileScale=4,
                ).getInfo()
                return stats, scale
            except ee.ee_exception.EEException as exc:
                if "User memory limit exceeded" not in str(exc):
                    raise
                last_exc = exc
        if last_exc is not None:
            raise last_exc

    reducer = ee.Reducer.mean()
    if not stats_only:
        reducer = reducer.combine(ee.Reducer.count(), sharedInputs=True)

    if not monthly:
        raise RuntimeError("No monthly composites available to compute report.")

    monthly_with_indices: List[Dict[str, Any]] = []
    for item in monthly:
        monthly_with_indices.append({
            **item,
            "indices": _compute_index_images(
                item["composite"],
                indices_to_compute=computed_indices,
            ),
        })

    total_count_by_scale: Dict[int, float] = {}
    indices_stats: Dict[str, List[Dict[str, Any]]] = {key: [] for key in all_indices}

    for idx_name in computed_indices:
        batch_size = 6 if stats_only else len(monthly_with_indices)
        for start in range(0, len(monthly_with_indices), batch_size):
            batch = monthly_with_indices[start:start + batch_size]
            bands_image = None
            for item in batch:
                band_name = f"{idx_name}_{item['month']}"
                band = item["indices"][idx_name].rename(band_name)
                bands_image = ee.Image(band) if bands_image is None else bands_image.addBands(band)

            if bands_image is None:
                continue

            stats_raw, used_scale = _reduce_region_with_retry(bands_image, reducer)
            if used_scale not in total_count_by_scale and not stats_only:
                total_count_by_scale[used_scale] = (
                    ee.Image(1)
                    .reduceRegion(
                        ee.Reducer.sum(),
                        roi,
                        used_scale,
                        maxPixels=1e13,
                        bestEffort=True,
                        tileScale=4,
                    )
                    .get("constant")
                ).getInfo()

            total_count = total_count_by_scale.get(used_scale, 1.0)
            for item in batch:
                month_id = item["month"]
                year = item["year"]
                month_num = item["month_num"]
                band = f"{idx_name}_{month_id}"
                mean = stats_raw.get(f"{band}_mean")
                if mean is None:
                    mean = stats_raw.get(band)
                count = None if stats_only else stats_raw.get(f"{band}_count")
                valid_ratio = (
                    1.0 if stats_only
                    else (count / total_count) if (count is not None and total_count) else 0.0
                )
                if mean is None or valid_ratio < 0.10:
                    mean = None

                indices_stats[idx_name].append({
                    "month": month_id,
                    "year": year,
                    "month_num": month_num,
                    "mean": mean,
                    "valid_ratio": valid_ratio,
                })

    burn_fraction_by_month: Dict[str, float] = {}
    valid_coverage_by_month: Dict[str, float] = {}
    burn_reducer = ee.Reducer.mean()
    if monthly_with_indices:
        burn_fraction_by_month[monthly_with_indices[0]["month"]] = 0.0
        valid_coverage_by_month[monthly_with_indices[0]["month"]] = 0.0

    monthly_pairs: List[Dict[str, Any]] = []
    for idx in range(1, len(monthly_with_indices)):
        monthly_pairs.append({
            "month": monthly_with_indices[idx]["month"],
            "prev_nbr": monthly_with_indices[idx - 1]["indices"]["NBR"],
            "curr_nbr": monthly_with_indices[idx]["indices"]["NBR"],
        })

    batch_size = 6 if stats_only else len(monthly_pairs)
    for start in range(0, len(monthly_pairs), batch_size):
        batch = monthly_pairs[start:start + batch_size]
        burn_bands = None
        for pair in batch:
            burn_band_name = f"BURN_{pair['month']}"
            valid_band_name = f"VALID_{pair['month']}"
            valid_pair = pair["prev_nbr"].mask().gt(0).And(pair["curr_nbr"].mask().gt(0))
            dnbr_month = pair["prev_nbr"].subtract(pair["curr_nbr"])
            # Relative burn ratio (RBR) helps suppress high dNBR in naturally low-biomass periods.
            rbr_month = dnbr_month.divide(pair["prev_nbr"].add(1.001))
            burn_condition = (
                dnbr_month.gte(burn_threshold)
                .And(rbr_month.gte(burn_rbr_threshold))
                .And(pair["curr_nbr"].lte(burn_post_nbr_threshold))
            )
            burn_img = (
                burn_condition
                .updateMask(valid_pair)
                .unmask(0)
                .rename(burn_band_name)
            )
            valid_img = valid_pair.unmask(0).rename(valid_band_name)
            two_bands = ee.Image.cat([burn_img, valid_img])
            burn_bands = ee.Image(two_bands) if burn_bands is None else burn_bands.addBands(two_bands)

        if burn_bands is None:
            continue

        burn_stats, _ = _reduce_region_with_retry(burn_bands, burn_reducer)
        for pair in batch:
            burn_band_name = f"BURN_{pair['month']}"
            valid_band_name = f"VALID_{pair['month']}"
            burn_val = burn_stats.get(f"{burn_band_name}_mean")
            if burn_val is None:
                burn_val = burn_stats.get(burn_band_name)
            valid_val = burn_stats.get(f"{valid_band_name}_mean")
            if valid_val is None:
                valid_val = burn_stats.get(valid_band_name)
            valid_cov = max(0.0, min(1.0, _safe_float(valid_val, 0.0)))
            burn_cov = max(0.0, min(1.0, _safe_float(burn_val, 0.0)))
            burn_over_valid = 0.0 if valid_cov <= 0.0 else burn_cov / valid_cov
            valid_coverage_by_month[pair["month"]] = valid_cov
            burn_fraction_by_month[pair["month"]] = max(0.0, min(1.0, _safe_float(burn_over_valid, 0.0)))

    baseline = {}
    for index_name, stats in indices_stats.items():
        baseline[index_name] = _compute_baseline(stats)

    burn_grouped: Dict[int, List[float]] = {}
    for item in monthly:
        burn_value = burn_fraction_by_month.get(item["month"], 0.0)
        burn_grouped.setdefault(item["month_num"], []).append(burn_value)
    burn_baseline = {
        month_num: (sum(values) / len(values)) if values else 0.0
        for month_num, values in burn_grouped.items()
    }

    nbr_grouped: Dict[int, List[float]] = {}
    for item in indices_stats["NBR"]:
        if item.get("mean") is None:
            continue
        nbr_grouped.setdefault(item["month_num"], []).append(_safe_float(item.get("mean"), 0.0))
    nbr_month_mean = {
        month_num: (sum(values) / len(values)) if values else 0.0
        for month_num, values in nbr_grouped.items()
    }
    nbr_month_std = {}
    for month_num, values in nbr_grouped.items():
        if len(values) < 2:
            nbr_month_std[month_num] = 0.0
            continue
        mu = nbr_month_mean[month_num]
        var = sum((v - mu) ** 2 for v in values) / len(values)
        nbr_month_std[month_num] = math.sqrt(var) if var > 0 else 0.0

    monthly_series = []
    months = indices_stats["NDVI"]
    previous_cfdi = 0.0

    for idx, month_item in enumerate(months):
        record = {
            "month": month_item["month"],
            "index_values": {},
        }

        for index_name, stats in indices_stats.items():
            item = stats[idx]
            mean = item.get("mean")
            month_num = item["month_num"]

            prev_mean = None
            if idx > 0:
                prev_mean = stats[idx - 1].get("mean")

            delta = None
            if mean is not None and prev_mean is not None:
                delta = mean - prev_mean

            anomaly = None
            if mean is not None and month_num in baseline[index_name]:
                anomaly = mean - baseline[index_name][month_num]

            safe_mean = _safe_float(mean, 0.0)
            safe_delta = _safe_float(delta, 0.0)
            safe_anomaly = _safe_float(anomaly, 0.0)

            record["index_values"][index_name] = {
                "mean": safe_mean,
                "delta_from_prev": safe_delta,
                "anomaly": safe_anomaly,
            }

        month_id = month_item["month"]
        month_num = month_item["month_num"]
        nbr_mean = _safe_float(indices_stats["NBR"][idx].get("mean"), 0.0)
        prev_nbr_mean = nbr_mean
        if idx > 0:
            prev_nbr_mean = _safe_float(indices_stats["NBR"][idx - 1].get("mean"), nbr_mean)
        delta_nbr = nbr_mean - prev_nbr_mean

        mu_nbr = _safe_float(nbr_month_mean.get(month_num, 0.0), 0.0)
        sigma_nbr = _safe_float(nbr_month_std.get(month_num, 0.0), 0.0)
        z_nbr = 0.0 if sigma_nbr == 0.0 else (nbr_mean - mu_nbr) / sigma_nbr

        shock = max(0.0, -z_nbr)
        abrupt_drop = max(0.0, -delta_nbr)
        recovery = max(0.0, z_nbr)
        burn_fraction = _safe_float(burn_fraction_by_month.get(month_id, 0.0), 0.0)
        valid_coverage = _safe_float(valid_coverage_by_month.get(month_id, 0.0), 0.0)
        coverage_factor = min(1.0, valid_coverage / cfdi_min_valid_coverage) if cfdi_min_valid_coverage > 0 else 1.0
        burn_evidence = min(1.0, burn_fraction / cfdi_burn_evidence_reference) if cfdi_burn_evidence_reference > 0 else 1.0

        cfdi = (
            cfdi_w1 * shock * burn_evidence
            + cfdi_w2 * abrupt_drop * burn_evidence
            + cfdi_w3 * burn_fraction
            - cfdi_w4 * recovery
        )
        cfdi = _safe_float(cfdi, 0.0) * coverage_factor
        cfdi_delta = cfdi - previous_cfdi if idx > 0 else 0.0
        previous_cfdi = cfdi

        burn_anomaly = burn_fraction - _safe_float(burn_baseline.get(month_num, 0.0), 0.0)
        record["index_values"]["BURN_FRACTION"] = {
            "mean": burn_fraction,
            "delta_from_prev": _safe_float(
                burn_fraction - _safe_float(
                    burn_fraction_by_month.get(months[idx - 1]["month"], burn_fraction),
                    burn_fraction,
                ),
                0.0,
            ) if idx > 0 else 0.0,
            "anomaly": _safe_float(burn_anomaly, 0.0),
        }
        record["index_values"]["VALID_COVERAGE"] = {
            "mean": valid_coverage,
            "delta_from_prev": _safe_float(
                valid_coverage - _safe_float(
                    valid_coverage_by_month.get(months[idx - 1]["month"], valid_coverage),
                    valid_coverage,
                ),
                0.0,
            ) if idx > 0 else 0.0,
            "anomaly": 0.0,
        }
        record["index_values"]["CFDI"] = {
            "mean": cfdi,
            "delta_from_prev": _safe_float(cfdi_delta, 0.0),
            "anomaly": _safe_float(cfdi, 0.0),
        }

        monthly_series.append(record)

    report_start = context.inputs["start_date"][:7]
    report_end = context.inputs["end_date"][:7]

    plots = {}
    if not stats_only:
        bucket = context.inputs.get("gcs_bucket")
        start_date = context.inputs["start_date"]
        end_date = context.inputs["end_date"]

        cfdi_object_name = utils.generate_object_name(
            "plot_cfdi", start_date, end_date
        ) + ".png"
        try:
            cfdi_png = _plot_cfdi_series(
                monthly_series,
                context.inputs["roi_name"],
                report_start,
                report_end,
            )
            cfdi_upload = upload_bytes_to_gcs(cfdi_png, bucket, cfdi_object_name)
            plots["CFDI"] = {"url": cfdi_upload["url"]}
        except Exception as exc:
            logger.warning("Plot upload failed for CFDI: %s", exc)
            plots["CFDI"] = {"upload_error": str(exc)}

    report = {
        "roi_name": context.inputs["roi_name"],
        "start_date": report_start,
        "end_date": report_end,
        "indices": ["NDVI", "NBR", "BURN_FRACTION", "VALID_COVERAGE", "CFDI"],
        "cfdi_config": {
            "burn_threshold": burn_threshold,
            "burn_rbr_threshold": burn_rbr_threshold,
            "burn_post_nbr_threshold": burn_post_nbr_threshold,
            "cfdi_min_valid_coverage": cfdi_min_valid_coverage,
            "cfdi_burn_evidence_reference": cfdi_burn_evidence_reference,
            "weights": {
                "w1_shock": cfdi_w1,
                "w2_abrupt_drop": cfdi_w2,
                "w3_burn_fraction": cfdi_w3,
                "w4_recovery": cfdi_w4,
            },
        },
        "monthly_series": monthly_series,
        "plots": plots,
    }

    merged_selected = ee.ImageCollection([])
    for item in monthly:
        merged_selected = merged_selected.merge(item["selected_collection"])

    return {
        "analysis": report,
        "imagery_catalog": _build_imagery_catalog(merged_selected),
    }
