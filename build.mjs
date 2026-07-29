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
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

import * as esbuild from "esbuild";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const ENTRY = path.join(ROOT, "frontend", "src", "app.jsx");
const OUTFILE = path.join(ROOT, "frontend", "app.js");

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
  console.log(`OK: frontend/app.js matches frontend/src (sha256[:12] ${sha(fresh)})`);
} else {
  await esbuild.build(options);
  const out = await readFile(OUTFILE, "utf8");
  console.log(
    `built ${path.relative(ROOT, OUTFILE)} ` +
      `(${(Buffer.byteLength(out) / 1024).toFixed(1)} kB, sha256[:12] ${sha(out)})`
  );
}
