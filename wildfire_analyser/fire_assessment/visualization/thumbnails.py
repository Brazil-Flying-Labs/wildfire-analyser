# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Earth Engine thumbnail generation helpers.


import ee

BACKGROUND_COLOR_MAP = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
}


def _parse_background_color(color: str) -> tuple[int, int, int]:
    normalized = color.strip().lower()

    if normalized in BACKGROUND_COLOR_MAP:
        return BACKGROUND_COLOR_MAP[normalized]

    if normalized.startswith("#"):
        normalized = normalized[1:]

    if len(normalized) == 3:
        normalized = "".join(ch * 2 for ch in normalized)

    if len(normalized) != 6:
        raise ValueError(
            f"Invalid roi_only_bg_color '{color}'. "
            "Use a named color such as 'black' or 'white', or a hex color."
        )

    try:
        return tuple(
            int(normalized[i:i + 2], 16)
            for i in (0, 2, 4)
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid roi_only_bg_color '{color}'. "
            "Use a named color such as 'black' or 'white', or a hex color."
        ) from exc


def _build_background_image(color: str) -> ee.Image:
    red, green, blue = _parse_background_color(color)
    return ee.Image.constant([red, green, blue]).toByte()


def _roi_outline_palette(color: str) -> list[str]:
    red, green, blue = _parse_background_color(color)
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return ["000000"] if luminance >= 128 else ["ffffff"]


def _build_roi_outline(roi: ee.Geometry, color: str) -> ee.Image:
    outline = ee.Image().byte().paint(
        featureCollection=ee.FeatureCollection(roi),
        color=1,
        width=4,
    )
    return outline.visualize(palette=_roi_outline_palette(color))


def get_visual_thumbnail_url(
    image: ee.Image,
    roi: ee.Geometry,
    roi_only: bool = False,
    roi_only_bg_color: str = "black",
) -> str:
    bounds = roi.bounds()

    if roi_only:
        background = _build_background_image(roi_only_bg_color).clip(bounds)
        image = background.blend(image.clip(roi))
    else:
        image = image.clip(bounds)

    image = image.blend(_build_roi_outline(roi, roi_only_bg_color))

    return image.getThumbURL({
        "dimensions": 1024,
        "format": "jpg",
        "region": bounds,
    })
