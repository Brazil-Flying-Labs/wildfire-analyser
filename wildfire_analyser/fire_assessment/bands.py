# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Canonical spectral band names for Sentinel-2 processing.

BLUE = "BLUE"
GREEN = "GREEN"
RED = "RED"
NIR = "NIR"
SWIR2 = "SWIR2"

REFLECTANCE_SUFFIX = "_refl"

SENTINEL2_REFLECTANCE_BAND_MAP = {
    "B2": BLUE,
    "B3": GREEN,
    "B4": RED,
    "B8": NIR,
    "B12": SWIR2,
}

def reflectance_band_name(band_acronym: str) -> str:
    """Return the canonical reflectance band name for a band acronym."""
    return f"{band_acronym}{REFLECTANCE_SUFFIX}"
