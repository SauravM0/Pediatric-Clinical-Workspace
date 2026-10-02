/**
 * useServerCalc -- fetch a clinical calculation from the backend (step 2).
 *
 * eGFR, FIB-4, blood pressure and QRISK3 used to be computed in this bundle. They
 * now come from tested backend modules (backend/renal, hepatic, vitals, cvd), so
 * there is one implementation of each and its age limits are enforced there.
 *
 * The one property that matters: the hook NEVER returns a result for inputs
 * other than the current ones. Each response is tagged with the request that
 * produced it and discarded unless that is still the request in force, so a
 * slow reply for the previous creatinine cannot land under the new one, and
 * while a request is pending the caller sees `loading`, not a stale number.
 *
 * `request` is null when the inputs are incomplete: no call is made.
 */
const { useState, useEffect } = React;

const DEBOUNCE_MS = 200;

function useServerCalc(request) {
  // request: null | { url, body? }  (a body makes it a JSON POST)
  const key = request ? request.url + '|' + (request.body ? JSON.stringify(request.body) : '') : null;
  const [state, setState] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    if (!key) return undefined;
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      const init = request.body
        ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request.body) }
        : { method: 'GET' };
      fetch(request.url, { ...init, signal: ctrl.signal })
        .then(async (r) => {
          const d = await r.json().catch(() => null);
          if (!r.ok) {
            const detail = d && d.detail;
            throw new Error(typeof detail === 'string' ? detail : `request failed (HTTP ${r.status})`);
          }
          return d;
        })
        .then((d) => setState({ key, data: d, error: null }))
        .catch((e) => { if (e.name !== 'AbortError') setState({ key, data: null, error: String(e.message || e) }); });
    }, DEBOUNCE_MS);
    return () => { clearTimeout(timer); ctrl.abort(); };
  }, [key]);   // eslint-disable-line react-hooks/exhaustive-deps -- key encodes request

  const current = key !== null && state.key === key;
  return {
    data: current ? state.data : null,
    error: current ? state.error : null,
    loading: key !== null && !current,
  };
}

// Build "path?a=1&b=2", dropping null/undefined/"" so an absent optional input
// is absent from the request rather than sent as an empty string.
function withQuery(path, params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') q.append(k, String(v));
  });
  return `${path}?${q.toString()}`;
}

export { useServerCalc, withQuery };
