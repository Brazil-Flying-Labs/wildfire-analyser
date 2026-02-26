# Composite Fire Disturbance Pipeline

Temporal monitoring pipeline for fire disturbance and vegetation recovery using monthly Sentinel-2 composites.

## Core Outputs

- `analysis`: monthly time-series report (`mean`, `delta_from_prev`, `anomaly`) for:
  - `NDVI`
  - `NBR`
  - `BURN_FRACTION`
  - `VALID_COVERAGE`
  - `CFDI`
- `imagery_catalog`: selected Sentinel-2 scenes actually used in processing, with:
  - `gee_image_id`
  - `acquired_on`
  - `cloudy_pixel_percentage`

## CFDI Formulation

### Monthly NBR

`NBR_t = (NIR - SWIR2) / (NIR + SWIR2)`

### Monthly dNBR approximation (for burned fraction)

`dNBR_t = NBR_(t-1) - NBR_t`

### Burn Fraction (aligned with fire_assessment threshold logic)

Pixel is considered burned when:

`dNBR_t >= burn_threshold`
`RBR_t >= burn_rbr_threshold`, where `RBR_t = dNBR_t / (NBR_(t-1) + 1.001)`
`NBR_t <= burn_post_nbr_threshold`

Default:

`burn_threshold = 0.10`
`burn_rbr_threshold = 0.15`
`burn_post_nbr_threshold = -0.20`

Then (pairwise month validity):

- `valid_pair_t = valid_(t-1) AND valid_t`
- `VALID_COVERAGE_t = valid_pair_pixels / total_roi_pixels`
- `BURN_FRACTION_t = burned_pixels_in_valid_pair / valid_pair_pixels`

This avoids treating cloud-masked pixels as unburned.

### Standardized NBR signal

`Z_NBR_t = (NBR_t - mean_month(NBR)) / std_month(NBR)`

If `std_month(NBR) = 0`, fallback to `0`.

### Components

- `Shock_t = max(0, -Z_NBR_t)`
- `AbruptDrop_t = max(0, -(NBR_t - NBR_(t-1)))`
- `Recovery_t = max(0, Z_NBR_t)`

### Composite Fire Disturbance Index

`CFDI_t = w1*Shock_t + w2*AbruptDrop_t + w3*BurnFraction_t - w4*Recovery_t`

Quality scaling by pairwise valid coverage:

`CFDI_t = CFDI_t * min(1, VALID_COVERAGE_t / cfdi_min_valid_coverage)`

Default:

`cfdi_min_valid_coverage = 0.6`

Default weights:

- `w1 = 0.4`
- `w2 = 0.7`
- `w3 = 2.4`
- `w4 = 0.4`
- `cfdi_min_valid_coverage = 0.6`
- `cfdi_burn_evidence_reference = 0.10`

Interpretation:

- `CFDI >> 0`: disturbance/fire impact
- `CFDI ~ 0`: stable
- `CFDI < 0`: recovery

### Practical meaning of key tuning parameters

- `cfdi_burn_evidence_reference`:
  - Controls how much burned-area evidence is needed before `Shock` and `AbruptDrop` can fully contribute.
  - Example: `0.10` means shock/drop reach full weight when `BURN_FRACTION >= 10%`.
  - Lower values make CFDI react faster to likely fire signals.
- `w3` (`cfdi-w3`):
  - Direct weight of `BURN_FRACTION` in CFDI.
  - Increasing `w3` emphasizes spatial burned extent over spectral fluctuations.

## CLI Examples

### 1. Stats-only (fast JSON only)

```bash
python -m wildfire_analyser.temporal_cli \
  --roi polygons/eejatai.geojson \
  --start-date 2019-01 \
  --end-date 2025-12 \
  --stats-only
```

### 2. CFDI chart + upload

```bash
python -m wildfire_analyser.temporal_cli \
  --roi polygons/eejatai.geojson \
  --start-date 2019-01 \
  --end-date 2025-12
```

### 3. Stricter cloud filtering + fewer images per month

```bash
python -m wildfire_analyser.temporal_cli \
  --roi polygons/eejatai.geojson \
  --start-date 2019-01 \
  --end-date 2025-12 \
  --cloud-threshold 20 \
  --max-images-per-month 1 \
  --stats-only
```

### 4. CFDI parameter tuning

```bash
python -m wildfire_analyser.temporal_cli \
  --roi polygons/eejatai.geojson \
  --start-date 2019-01 \
  --end-date 2025-12 \
  --burn-threshold 0.10 \
  --burn-rbr-threshold 0.15 \
  --burn-post-nbr-threshold -0.20 \
  --cfdi-w1 0.4 \
  --cfdi-w2 0.7 \
  --cfdi-w3 2.4 \
  --cfdi-w4 0.4 \
  --cfdi-min-valid-coverage 0.6 \
  --cfdi-burn-evidence-reference 0.10 \
  --stats-only
```

## Jatai External Validation

Validation was performed for ROI `eejatai` by comparing CFDI peaks against public records from official agencies and local news (checked on February 26, 2026).

Analyzed peaks from the current output:

- `2020-08` (`CFDI ~= 1.46`) and `2020-09` (`CFDI ~= 0.97`): official records indicate active wildfire response in Luiz Antonio / Estacao Ecologica de Jatai during September 2020, consistent with the Q3/2020 disturbance peak in the time series.
  - https://semil.sp.gov.br/2020/09/equipes-do-governo-de-sp-atuam-em-regiao-de-dificil-acesso-para-combater-incendio-florestal/
  - https://semil.sp.gov.br/2020/09/fundacao-florestal-abre-chamamento-publico-para-doacao-de-bens-e-servicos-em-apoio-ao-combate-a-incendios-florestais/
- `2024-10` (`CFDI ~= 1.09`): strong evidence of active wildfire in Estacao Ecologica de Jatai from late September to early October 2024.
  - https://jovempan.com.br/noticias/brasil/combate-a-incendio-em-estacao-ecologica-no-interior-de-sp-chega-ao-sexto-dia.html
  - https://jornalmensagem.com.br/liderancas-pedem-socorro-contra-o-avanco-do-fogo-na-estacao-ecologica-de-jatai/
- `2022-05` (`CFDI ~= 1.05`): official records indicate prescribed burning operations in Jatai starting May 24, 2022, with continuation in June/July 2022.
  - https://fflorestal.sp.gov.br/2022/05/governo-de-sp-inicia-projeto-piloto-de-queima-prescrita-para-minimizar-danos-de-incendios-florestais/
  - https://semil.sp.gov.br/2022/06/operacao-corta-fogo-governo-de-sp-realiza-terceiro-dia-de-queima-prescrita-piloto-na-estacao-ecologica-de-jatai/
  - https://semil.sp.gov.br/2022/07/governo-de-sp-da-continuidade-ao-projeto-piloto-de-queima-prescrita-na-estacao-ecologica-de-jatai/
- `2021-10` (`CFDI ~= 1.11`): no clear evidence of a new October event was found, but there is official evidence of a major fire episode in early September 2021 in/around Jatai, which can explain spectral/post-fire carry-over into October.
  - https://semil.sp.gov.br/2021/09/operacao-corta-fogo-impede-propagacao-de-incendios-em-areas-de-protecao-ambiental-durante-feriado-prolongado-em-sp/
  - https://semil.sp.gov.br/2021/12/area-atingida-por-incendios-em-unidades-de-conservacao-paulistas-e-41-menor-em-2021/

Additional official reference used for monthly fire context:

- INPE InfoQueima bulletins: https://terrabrasilis.dpi.inpe.br/queimadas/portal/infoqueima/index.html

## Notes

- Dates are required in `YYYY-MM`.
- Graph images are generated in-memory and uploaded directly to GCS (no local file write).
- If `--stats-only` is used, no chart is generated/uploaded.
