"""Server-side PDF export for the growth chart.

Drives a headless Chromium (Playwright) to the app's own ``?report=1`` URL and
calls Chrome's native ``Page.printToPDF`` -- NOT the interactive browser print
dialog that ``window.print()`` opens. That distinction is the whole point of
this module: the interactive dialog's "Headers and footers" checkbox (which
injects the date, page title, ``about:blank``-style URL, and page number into
every printed page) is a Chrome UI feature with no web-facing API -- a page
cannot suppress it with CSS or JS, and a user has to remember to uncheck it
every time. Headless ``Page.printToPDF`` has a real ``displayHeaderFooter``
flag, so this path can guarantee a clean, chrome-free PDF outright.

This module does not duplicate the chart's rendering or clinical math -- it
loads the exact same live SPA (frontend/index.html) that a doctor would use
interactively, in "report mode" (see the ``.report-mode`` CSS and the
``?report=1`` bootstrap effect in frontend/index.html), so the exported PDF
goes through the identical fetch/state/render/validation pipeline (including
the sex/measure identity guard and the height-reference sanity check) as the
on-screen chart. If that pipeline ever refuses to render (wrong sex, failed
sanity check, etc.), the chart's `<svg>` never appears and this endpoint
fails the export instead of shipping a bad PDF.
"""
from __future__ import annotations

import json
from typing import Literal

from fastapi import Depends, APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.security.deps import clinical_access

# Every route in this router requires an authenticated user with at least
# read access; mutating methods require write access (security phase, C.1).
# Applied at the router so a route added later is protected by construction.
router = APIRouter(prefix="/api/growth", tags=["growth-report"], dependencies=[Depends(clinical_access)])

_VALID_SEXES = ("boys", "girls")

# How long to wait for the chart's <svg> (or its refusal-to-render error div)
# to appear before giving up on the export.
_RENDER_TIMEOUT_MS = 20_000


class ReportRequest(BaseModel):
    sex: Literal["boys", "girls"]
    age: float = Field(..., ge=0.0, le=19.0)
    height: float = Field(0.0, ge=0.0)
    weight: float = Field(0.0, ge=0.0)
    patient_name: str = Field("", max_length=200)
    patient_mrn: str = Field("", max_length=100)
    exam_date: str = Field("", max_length=40)


@router.post("/report.pdf")
async def get_growth_report_pdf(request: Request, body: ReportRequest) -> Response:
    """Render the growth chart report to a clean A4 PDF via headless Chromium.

    A POST, and the patient never travels in a URL. It used to be a GET with
    patient_name, MRN and measurements in the query string -- which then sat in
    the server's access log, in the browser history, and in the headless page's
    own URL. The payload now goes in the request body, and reaches the report
    page through an init script (window.__PCW_REPORT__) rather than its address.
    """
    sex = body.sex

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise HTTPException(
            500,
            "Server-side PDF export requires the 'playwright' package "
            "(pip install playwright && playwright install chromium).",
        ) from exc

    # Optional patient identity is passed straight through to the same
    # ?report=1 render so the exported PDF is attributable to a patient
    # (empty values simply render as a placeholder -- no new clinical inputs).
    # Self-navigation to this same server, same-origin, no external network
    # call. Only the MODE is in the URL; the data is injected before any page
    # script runs, as a JSON literal; json.dumps escapes quotes and backslashes,
    # and < is escaped too so no value can ever read as markup.
    target_url = f"{str(request.base_url).rstrip('/')}/?report=1"
    payload = json.dumps(body.model_dump()).replace("<", "\\u003c")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 900, "height": 1200})
            await page.add_init_script(f"window.__PCW_REPORT__ = {payload};")
            await page.goto(target_url, wait_until="networkidle")

            # #growth-chart-print always contains SOME <div> from the very first
            # paint (the "Loading reference data..." placeholder, before the
            # /api/growth/chart fetches even resolve) -- so a plain
            # wait_for_selector("#growth-chart-print svg, ... div") resolves
            # immediately on that placeholder and tells us nothing. Instead,
            # poll in-page until the chart reaches a TERMINAL state: either the
            # real <svg> appeared, or the component's own identity/sanity
            # guards produced their refusal-to-render error text (see
            # GrowthChartCombined in frontend/index.html) -- and only then
            # decide whether to export or fail.
            try:
                await page.wait_for_function(
                    """() => {
                        const el = document.getElementById('growth-chart-print');
                        if (!el) return false;
                        if (el.querySelector('svg')) return true;
                        const t = el.textContent || '';
                        return t.includes('refusing to render');
                    }""",
                    timeout=_RENDER_TIMEOUT_MS,
                )
            except Exception as exc:
                raise HTTPException(
                    502, f"Growth chart did not reach a final render state in time for PDF export ({exc})"
                ) from exc

            # If the chart component refused to render (identity guard or the
            # height-reference sanity check failing), #growth-chart-print
            # contains an error <div>, not an <svg>. Fail the export loudly
            # rather than produce a PDF with no chart / the wrong chart.
            has_svg = await page.locator("#growth-chart-print svg").count()
            if not has_svg:
                error_text = (await page.locator("#growth-chart-print").inner_text()).strip()
                raise HTTPException(
                    502, f"Growth chart failed validation -- refusing to export PDF: {error_text}"
                )

            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                display_header_footer=False,
                margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
            )
        finally:
            await browser.close()

    filename = f"growth-report-{sex}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
