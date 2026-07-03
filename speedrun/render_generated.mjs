// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Render each AI-generated Physics-GRE MCQ (speedrun/data/generated_mcq.jsonl)
// into a styled PNG "card" with LaTeX typeset offline via MathJax (SVG output),
// screenshotting with the repo's bundled Playwright Chromium. Output folder:
// speedrun/generated_screenshots/. Run from the repo root:
//   PLAYWRIGHT_BROWSERS_PATH=out/playwright-browsers \
//   out/extracted/node/bin/node speedrun/render_generated.mjs

import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium } from "playwright";

const REPO = process.cwd();
const MCQ = join(REPO, "speedrun/data/generated_mcq.jsonl");
const COMP = join(REPO, "speedrun/data/generated_optimal_approaches.jsonl");
const OUTDIR = join(REPO, "speedrun/generated_screenshots");
const MATHJAX = resolve(REPO, "out/node_modules/mathjax/es5/tex-svg-full.js");

function readJsonl(path) {
    if (!existsSync(path)) { return []; }
    return readFileSync(path, "utf-8")
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
        .map((l) => JSON.parse(l));
}

// $$..$$ -> \[..\], $..$ -> \(..\)  (MathJax delimiters)
function toMathjax(s) {
    if (!s) { return ""; }
    s = String(s).replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => `\\[${m}\\]`);
    s = s.replace(/\$([^$]+?)\$/g, (_, m) => `\\(${m}\\)`);
    return s;
}
function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// escape for text, then restore math delimiters and typeset markers
function rich(s) {
    return toMathjax(esc(s));
}

const SUBJECT_LABEL = {
    quantum_mechanics: "Quantum Mechanics",
    classical_mechanics: "Classical Mechanics",
    electromagnetism: "Electromagnetism",
    atomic_physics: "Atomic Physics",
    thermodynamics: "Thermodynamics & Stat Mech",
    optics_waves: "Optics & Waves",
    special_relativity: "Special Relativity",
    lab_methods: "Laboratory Methods",
    specialized: "Specialized Topics",
};

function cardHtml(q, comp) {
    const subj = q.topic || SUBJECT_LABEL[q.subject] || q.subject || "";
    const choices = q.choices
        .map(([l, t]) => {
            const correct = l.toUpperCase() === String(q.answer).toUpperCase();
            return `<li class="choice ${correct ? "correct" : ""}">
        <span class="lbl">${esc(l)}</span>
        <span class="txt">${rich(t)}</span>
        ${correct ? "<span class=\"tick\">✓ correct</span>" : ""}
      </li>`;
        })
        .join("\n");

    let fastest = "";
    if (comp) {
        const elims = (comp.eliminations || [])
            .map((e) => `<li><b>(${esc(e.choice)})</b> ${rich(e.reason)}</li>`)
            .join("");
        fastest = `
      <div class="fastest">
        <div class="fastest-h">⚡ Fastest approach
          <span class="method">${esc((comp.optimal_method || "").replace(/_/g, " "))}</span>
        </div>
        <div class="fastest-body">${rich(comp.student_explanation || "")}</div>
        ${elims ? `<div class="elim-h">Eliminate</div><ul class="elim">${elims}</ul>` : ""}
      </div>`;
    }

    return `<div class="card">
    <div class="top">
      <span class="badge">AI-GENERATED</span>
      <span class="id">${esc(q.id)}</span>
      <span class="seed">variant of ${esc(q.seed_id || "")}</span>
    </div>
    <div class="subj">${esc(subj)}</div>
    <div class="stmt">${rich(q.statement)}</div>
    <ul class="choices">${choices}</ul>
    ${fastest}
    <details class="soln" open><summary>Worked solution</summary><div>${rich(q.solution)}</div></details>
  </div>`;
}

function pageHtml(inner) {
    return `<!doctype html><html><head><meta charset="utf-8">
  <script>
  window.MathJax = {
    tex: { inlineMath: [["\\\\(","\\\\)"]], displayMath: [["\\\\[","\\\\]"]] },
    svg: { fontCache: "none" },
    startup: { pageReady: () => MathJax.startup.defaultPageReady().then(() => { window.__mjdone = true; }) }
  };
  </script>
  <script src="file://${MATHJAX}" id="MathJax-script" async></script>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 24px; background: #eef1f6;
           font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .card { width: 720px; background: #fff; border-radius: 16px; padding: 26px 30px;
            box-shadow: 0 8px 30px rgba(20,30,60,.14); color: #1a2233; }
    .top { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .badge { background: linear-gradient(90deg,#6d28d9,#2563eb); color: #fff; font-size: 11px;
             font-weight: 700; letter-spacing: .06em; padding: 3px 9px; border-radius: 999px; }
    .id { font-weight: 700; font-size: 13px; color: #334; }
    .seed { font-size: 12px; color: #8894a8; margin-left: auto; }
    .subj { color: #2563eb; font-weight: 600; font-size: 13px; margin: 6px 0 14px; }
    .stmt { font-size: 18px; line-height: 1.5; margin-bottom: 18px; }
    ul.choices { list-style: none; padding: 0; margin: 0 0 6px; }
    .choice { display: flex; align-items: center; gap: 12px; padding: 10px 14px; margin: 7px 0;
              border: 1.5px solid #e3e8f0; border-radius: 10px; font-size: 16px; }
    .choice .lbl { font-weight: 700; color: #64748b; width: 20px; }
    .choice.correct { border-color: #16a34a; background: #f0fdf4; }
    .choice.correct .lbl { color: #16a34a; }
    .tick { margin-left: auto; color: #16a34a; font-weight: 700; font-size: 13px; }
    .fastest { margin-top: 16px; background: #fff8ec; border: 1.5px solid #f5d58a;
               border-radius: 12px; padding: 14px 16px; }
    .fastest-h { font-weight: 700; color: #b45309; margin-bottom: 6px; }
    .method { font-weight: 600; font-size: 12px; color: #92600b; background: #fdecc4;
              padding: 2px 8px; border-radius: 999px; margin-left: 6px; }
    .fastest-body { font-size: 15px; line-height: 1.5; }
    .elim-h { font-weight: 700; font-size: 12px; color: #b45309; margin: 8px 0 2px; text-transform: uppercase; }
    ul.elim { margin: 0; padding-left: 18px; font-size: 14px; color: #52413a; }
    ul.elim li { margin: 3px 0; }
    .soln { margin-top: 16px; border-top: 1px dashed #d7deea; padding-top: 12px; }
    .soln summary { cursor: default; font-weight: 700; color: #475569; font-size: 13px; }
    .soln div { font-size: 14px; line-height: 1.5; color: #3a4557; margin-top: 8px; }
    mjx-container { font-size: inherit !important; }
  </style></head>
  <body>${inner}</body></html>`;
}

const problems = readJsonl(MCQ);
const compMap = new Map(readJsonl(COMP).map((r) => [r.id, r]));

if (!problems.length) {
    console.error(`No generated problems found at ${MCQ}. Run gen_eval.py first.`);
    process.exit(1);
}

if (existsSync(OUTDIR)) {
    for (const f of readdirSync(OUTDIR)) { if (f.endsWith(".png") || f.endsWith(".html")) { rmSync(join(OUTDIR, f)); } }
}
mkdirSync(OUTDIR, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 800, height: 1000 }, deviceScaleFactor: 2 });

let n = 0;
for (const q of problems) {
    const html = pageHtml(cardHtml(q, compMap.get(q.id)));
    const tmp = join(OUTDIR, `_tmp.html`);
    writeFileSync(tmp, html, "utf-8");
    await page.goto("file://" + tmp);
    await page.waitForFunction("window.__mjdone === true", { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(150);
    const safe = q.id.replace(/[^A-Za-z0-9._-]/g, "_");
    const file = join(OUTDIR, `${String(++n).padStart(2, "0")}_${safe}.png`);
    const el = await page.$(".card");
    await el.screenshot({ path: file });
    console.log(`  wrote ${file}`);
}
rmSync(join(OUTDIR, "_tmp.html"), { force: true });
await browser.close();

// A simple index so the folder is browsable at a glance.
const rows = problems
    .map((q, i) =>
        `<figure><img src="${String(i + 1).padStart(2, "0")}_${
            q.id.replace(/[^A-Za-z0-9._-]/g, "_")
        }.png"><figcaption>${q.id} — variant of ${q.seed_id || ""}</figcaption></figure>`
    )
    .join("\n");
writeFileSync(
    join(OUTDIR, "index.html"),
    `<!doctype html><meta charset=utf-8><title>Generated problems</title>
  <style>body{font-family:sans-serif;background:#eef1f6;margin:0;padding:24px}
  h1{font-size:20px}figure{margin:0 0 28px}img{max-width:760px;width:100%;box-shadow:0 6px 20px rgba(0,0,0,.12);border-radius:12px}
  figcaption{color:#667;font-size:13px;margin-top:6px}</style>
  <h1>AI-generated Physics-GRE problems (${problems.length})</h1>${rows}`,
    "utf-8",
);
console.log(`\nDone: ${n} PNG(s) + index.html in ${OUTDIR}`);
