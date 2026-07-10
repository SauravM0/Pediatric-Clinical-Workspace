"""Regression guard for the combined growth chart's Y-axis ceiling
(GrowthChartCombined in frontend/index.html).

The reference WHO 2006 + IAP 2015 wall chart uses a *different* top gridline
per sex (195 for boys, 175 for girls) -- not derivable from one generic
"round the tallest curve value up to the next multiple of 5" rule, which
happens to reproduce 195 for boys but overshoots to 180 for girls (see
growth-chart-codebase-investigation-report.md, S6/S9). The fix pins both
values explicitly in a COMBINED_CHART_YMAX constant. This test parses that
constant straight out of the frontend source so a future edit that changes it
back to a dynamic-only computation (or otherwise drifts the girls value away
from 175) fails loudly, without needing a browser/JS test runner.
"""
import re
from pathlib import Path

from backend.growth import curve_builder

_INDEX_HTML = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


def _extract_combined_chart_ymax() -> dict[str, int]:
    src = _INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(r"COMBINED_CHART_YMAX\s*=\s*\{([^}]*)\}", src)
    assert m, "COMBINED_CHART_YMAX constant not found in frontend/index.html -- has the fix been reverted?"
    body = m.group(1)
    pairs = dict(re.findall(r"(\w+)\s*:\s*(\d+)", body))
    return {k: int(v) for k, v in pairs.items()}


def test_combined_chart_has_fixed_per_sex_yaxis_ceiling():
    ymax = _extract_combined_chart_ymax()
    assert ymax == {"boys": 195, "girls": 175}, (
        f"GrowthChartCombined's Y-axis ceiling changed to {ymax}. "
        "Reference wall chart uses 195 (boys) / 175 (girls) -- see "
        "growth-chart-codebase-investigation-report.md S6/S9 for why the naive "
        "dynamic round-up rule must not be used unconditionally (it produces "
        "180, not 175, for girls)."
    )


def test_girls_yaxis_ceiling_is_not_the_old_buggy_180():
    ymax = _extract_combined_chart_ymax()
    assert ymax["girls"] != 180


def test_fixed_ceilings_are_never_below_the_real_tallest_curve_value():
    """The fixed ceiling must still be tall enough to hold every actual centile
    value (height + weight, 0-18y) for its sex, or the chart's own fallback to
    a dynamic ceiling (frontend/index.html: `dataMax <= fixedYmax`) would kick
    in on every real render -- i.e. this guards that 195/175 are still valid
    given the current growth-engine data, not just correct in isolation."""
    ymax = _extract_combined_chart_ymax()
    for sex in ("boys", "girls"):
        data_max = 0.0
        for measure in ("height", "weight"):
            series = curve_builder.build_chart_series(measure, sex, 0.0, 18.0, 0.5)
            for curve in series.values():
                data_max = max(data_max, float(curve.values.max()))
        assert data_max <= ymax[sex], (
            f"{sex}: tallest real curve value ({data_max}) exceeds the fixed "
            f"Y-axis ceiling ({ymax[sex]}) -- the chart would silently fall back "
            "to the old dynamic round-up rule for every render."
        )
