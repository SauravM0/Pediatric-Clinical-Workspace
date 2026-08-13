/**
 * Frontend build (M6).
 *
 * Replaces in-browser Babel transpilation. Previously index.html shipped the
 * whole application as `<script type="text/babel">` and a 3.1 MB Babel bundle
 * re-transpiled ~4,000 lines of JSX on every single page load; there was no
 * module system, so no code splitting and no way to unit-test a component.
 *
 * What is deliberately preserved:
 *   - Fully offline. React/ReactDOM stay vendored and are treated as globals,
 *     not bundled, so nothing is fetched at runtime and the vendor files do not
 *     change. `app.js` is COMMITTED, so a fresh clone still runs with one
 *     command and no npm install -- that property matters for a clinical tool
 *     used in low-connectivity clinics and is not traded away for build purity.
 *   - Reviewability. Output is NOT minified. The committed bundle is what
 *     actually executes in front of a patient, so a reviewer must be able to
 *     read it and diff it. That costs a larger artefact and noisier diffs; for
 *     medical software that is the right side of the trade.
 *
 * Usage:
 *   node build.mjs           build once
 *   node build.mjs --watch   rebuild on change (development)
 *   node build.mjs --check   verify the committed artefact matches src/ (CI)
 */
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

import * as esbuild from "esbuild";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const ENTRY = path.join(ROOT, "frontend", "src", "app.jsx");
const OUTFILE = path.join(ROOT, "frontend", "app.js");
const INDEX = path.join(ROOT, "frontend", "index.html");

// The script tag carries the bundle's own hash: `static/app.js?v=<sha12>`.
//
// Without it a rebuilt bundle keeps the same URL, and a browser that already
// cached the old one may never ask again. Measured: after a rebuild, a fresh
// tab still EXECUTED the previous 293,561-byte bundle while a no-store fetch of
// the same URL returned the new 295,729-byte one. Starlette sends ETag and
// Last-Modified but no Cache-Control, so the browser applied heuristic caching
// and skipped revalidation.
//
// For a clinical tool that is a shipping hazard, not a development annoyance: a
// fix could be deployed and clinicians keep running the code it replaced, with
// nothing on screen to say so. The server now also sends `Cache-Control:
// no-cache` (see backend/server.py); this is the half that works even for a
// copy already sitting in a browser cache from before that header existed.
const SCRIPT_RE = /(<script src="static\/app\.js)(\?v=[0-9a-f]+)?(")/;

async function stampIndex(bundle) {
  const html = await readFile(INDEX, "utf8");
  if (!SCRIPT_RE.test(html)) {
    console.error("FAIL: could not find the app.js script tag in index.html");
    process.exit(1);
  }
  const stamped = html.replace(SCRIPT_RE, `$1?v=${sha(bundle)}$3`);
  if (stamped !== html) await writeFile(INDEX, stamped);
  return stamped;
}

const BANNER = `/* GENERATED FILE -- do not edit.
 * Built from frontend/src/ by build.mjs (M6). Edit the source there and run
 * \`npm run build\`. tests/frontend/test_build_artefact.py fails if this file
 * and frontend/src/ have drifted, so an edit here would be reverted anyway.
 */`;

/** @type {import("esbuild").BuildOptions} */
const options = {
  entryPoints: [ENTRY],
  outfile: OUTFILE,
  bundle: true,
  format: "iife",
  platform: "browser",
  target: ["es2020"],
  // React and ReactDOM are vendored UMD globals (see index.html), not npm
  // packages. Marking them external keeps the bundle to our own code and leaves
  // the vendor files untouched.
  external: ["react", "react-dom"],
  jsx: "transform",
  jsxFactory: "React.createElement",
  jsxFragment: "React.Fragment",
  minify: false,
  sourcemap: false,
  legalComments: "inline",
  banner: { js: BANNER },
  logLevel: "info",
};

const sha = (buf) => createHash("sha256").update(buf).digest("hex").slice(0, 12);

if (process.argv.includes("--watch")) {
  const ctx = await esbuild.context({ ...options, logLevel: "info" });
  await ctx.watch();
  console.log(`watching ${path.relative(ROOT, ENTRY)} -> ${path.relative(ROOT, OUTFILE)}`);
} else if (process.argv.includes("--check")) {
  // Build to memory and compare against the committed artefact. Without this a
  // source edit that was never rebuilt would ship silently: the browser runs
  // app.js, so stale output means the reviewed source is NOT what executes.
  const result = await esbuild.build({ ...options, write: false, logLevel: "silent" });
  const fresh = result.outputFiles[0].text;
  let committed;
  try {
    committed = await readFile(OUTFILE, "utf8");
  } catch {
    console.error(`FAIL: ${path.relative(ROOT, OUTFILE)} is missing. Run: npm run build`);
    process.exit(1);
  }
  if (fresh !== committed) {
    console.error(
      `FAIL: frontend/app.js is stale.\n` +
        `  committed sha256[:12] = ${sha(committed)}\n` +
        `  rebuilt   sha256[:12] = ${sha(fresh)}\n` +
        `The browser runs app.js, so the committed source is not what executes.\n` +
        `Run: npm run build`
    );
    process.exit(1);
  }
  // The cache-busting stamp must match the artefact too. A correct bundle
  // behind a stale ?v= is the same failure as a stale bundle: browsers keep
  // serving whatever they cached under the old URL.
  const html = await readFile(INDEX, "utf8");
  const stamp = (html.match(SCRIPT_RE) || [])[2];
  if (stamp !== `?v=${sha(fresh)}`) {
    console.error(
      `FAIL: index.html's script tag is stamped ${stamp || "(nothing)"} but the ` +
        `bundle is ${sha(fresh)}.\nA browser caching the old URL would never ` +
        `fetch the new bundle.\nRun: npm run build`
    );
    process.exit(1);
  }
  console.log(`OK: frontend/app.js matches frontend/src (sha256[:12] ${sha(fresh)})`);
} else {
  await esbuild.build(options);
  const out = await readFile(OUTFILE, "utf8");
  await stampIndex(out);
  console.log(
    `built ${path.relative(ROOT, OUTFILE)} ` +
      `(${(Buffer.byteLength(out) / 1024).toFixed(1)} kB, sha256[:12] ${sha(out)}) ` +
      `· index.html stamped ?v=${sha(out)}`
  );
}
