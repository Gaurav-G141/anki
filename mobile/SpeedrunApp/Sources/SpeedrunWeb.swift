// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Shared WebView styling for the two WKWebView surfaces (review cards in
// ReviewView, the MCQ console in MCQView). One Observatory token block +
// document scaffold so a card looks identical on both, and identical to the
// desktop hero pages (qt/aqt/data/web/css/pgre.scss). The WebViews render
// transparent over the SwiftUI ObservatoryBackground, so bodies are transparent
// and only carry light-on-dark text + component chrome.

import Foundation

enum SpeedrunWeb {
    /// Observatory design tokens + base document styling. Mirrors pgre.scss.
    static let baseCSS = """
    :root {
      color-scheme: dark;
      --pg-panel: rgba(18,21,32,0.72);
      --pg-panel-2: rgba(24,28,42,0.92);
      --pg-line: rgba(150,170,220,0.16);
      --pg-line-strong: rgba(150,170,220,0.34);
      --pg-text: #EAF0FF;
      --pg-text-dim: rgba(234,240,255,0.62);
      --pg-text-faint: rgba(234,240,255,0.36);
      --pg-accent: #4CE0FF;
      --pg-accent-2: #8A7CFF;
      --pg-ok: #3DD68C;
      --pg-warn: #F5B14C;
      --pg-bad: #FF5C6C;
      --pg-info: #6AA8FF;
      --pg-radius: 14px;
      --pg-radius-sm: 10px;
      --pg-pill: 999px;
      --pg-font: -apple-system, system-ui, sans-serif;
      --pg-mono: ui-monospace, "SF Mono", Menlo, monospace;
    }
    body {
      font-family: var(--pg-font); background: transparent; color: var(--pg-text);
      -webkit-text-size-adjust: 100%; letter-spacing: -0.01em;
    }
    a { color: var(--pg-accent); }
    hr { border: none; border-top: 1px solid var(--pg-line); margin: 18px 0; }
    img { max-width: 100%; height: auto; }
    mjx-container { max-width: 100%; overflow-x: auto; }
    .pg-eyebrow {
      font-family: var(--pg-mono); text-transform: uppercase; letter-spacing: 0.14em;
      font-size: 11px; color: var(--pg-text-dim);
    }
    """

    /// Component chrome shared by the MCQ console (choices, badges, coaching cards).
    static let componentCSS = """
    .choice {
      display: block; width: 100%; text-align: left; margin: 9px 0; padding: 13px 15px;
      border-radius: var(--pg-radius-sm); border: 1px solid var(--pg-line);
      background: var(--pg-panel); color: var(--pg-text); font: inherit;
      font-family: var(--pg-font); font-size: 17px; -webkit-tap-highlight-color: transparent;
      transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
    }
    .choice .lab { font-family: var(--pg-mono); font-weight: 700; margin-right: 10px; color: var(--pg-text-dim); }
    .choice.correct {
      border-color: var(--pg-ok); background: rgba(61,214,140,0.18);
      box-shadow: 0 0 18px rgba(61,214,140,0.4);
    }
    .choice.correct .lab { color: var(--pg-ok); }
    .choice.wrong { border-color: rgba(255,92,108,0.7); background: rgba(255,92,108,0.14); opacity: 0.72; }
    .choice.wrong .lab { color: var(--pg-bad); }
    .badge {
      display: inline-block; font-family: var(--pg-mono); font-size: 12px; letter-spacing: 0.06em;
      padding: 4px 11px; border-radius: var(--pg-pill); border: 1px solid var(--pg-line-strong);
      margin-bottom: 8px;
    }
    .card {
      margin-top: 14px; padding: 13px 15px; border-radius: var(--pg-radius-sm);
      background: var(--pg-panel); border: 1px solid var(--pg-line); overflow-wrap: anywhere;
    }
    .card .t { font-weight: 700; margin-bottom: 6px; }
    .card.coach { border-color: rgba(138,124,255,0.55); box-shadow: 0 0 22px rgba(138,124,255,0.4); }
    .card.fast { border-color: rgba(76,224,255,0.45); }
    .muted { color: var(--pg-text-faint); }
    .missed { margin: 8px 0 0 18px; }
    """

    /// Build a full offline HTML document: charset + viewport + tokens + caller CSS,
    /// the shared MathJax include, and the body.
    static func document(bodyHTML: String, css: String, mjxScale: Int = 112) -> String {
        """
        <!doctype html><html><head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        \(baseCSS)
        mjx-container { font-size: \(mjxScale)% !important; }
        \(css)
        </style>
        <script src="mathjax/tex-chtml-full.js" async></script>
        </head><body>
        \(bodyHTML)
        </body></html>
        """
    }
}
