// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// The Practice-MCQs (Performance) screen: real released Physics-GRE questions
// (GR9277) with A–E choices, graded against the answer key, plus the Stage-2 AI
// Heuristic Coach — the student types HOW they'd solve it and (when a key is
// baked in) gpt-4o grades the approach; otherwise the precomputed "fastest
// approach" is shown. Same data + logic as the desktop dialog.
//
// The quiz renders fully client-side from embedded data (so it always renders);
// only the "grade my approach" round-trip uses a WKScriptMessageHandler bridge —
// mirroring the desktop's embedded-data render + pycmd-only grade.

import SwiftUI
import WebKit

/// Reduce the MCQ pool to ONE surface variant per concept, rotating the choice
/// across calls (the fluency-illusion fix — mirrors desktop
/// `pgre_quiz.select_variants`). A `source:"reworded"` item groups with its seed
/// via `seed_id`; a real seed and any *novel* generated item stay independent
/// (keyed by their own `id`). Within a group the seed is first (the real bank
/// precedes the generated bank), so rotation 0 serves the original and later
/// sessions cycle the rewordings. Rotation persists in `defaults`. Top-level (not
/// nested) so the test target reaches it via `@testable import`.
func selectMCQVariants(_ questions: [[String: Any]], defaults: UserDefaults) -> [[String: Any]] {
    var groups: [String: [[String: Any]]] = [:]
    var order: [String] = []
    for q in questions {
        let source = q["source"] as? String
        let key = ((source == "reworded" ? q["seed_id"] as? String : q["id"] as? String)
            ?? q["id"] as? String) ?? ""
        if groups[key] == nil { groups[key] = []; order.append(key) }
        groups[key]?.append(q)
    }
    var rotation = (defaults.dictionary(forKey: "pgreRewordRotation") as? [String: Int]) ?? [:]
    var selected: [[String: Any]] = []
    for key in order {
        guard let members = groups[key] else { continue }
        if members.count == 1 { selected.append(members[0]); continue }
        let idx = (rotation[key] ?? 0) % members.count
        selected.append(members[idx])
        rotation[key] = (rotation[key] ?? 0) + 1
    }
    defaults.set(rotation, forKey: "pgreRewordRotation")
    return selected
}

struct MCQView: View {
    var body: some View {
        MCQWebView()
            .navigationTitle("Practice MCQs")
            .navigationBarTitleDisplayMode(.inline)
    }
}

private struct MCQWebView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(context.coordinator, name: "grade")
        config.userContentController.add(context.coordinator, name: "explain")
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        context.coordinator.webView = webView
        load(into: webView, coordinator: context.coordinator)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    /// Writes the quiz page (questions + optimal-approach + AI flag embedded) to
    /// Documents and loads it with read access so the relative `mathjax/…` script
    /// staged there resolves offline.
    private func load(into webView: WKWebView, coordinator: Coordinator) {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let html = Self.page(embeddedJSON: coordinator.embeddedJSON())
        let dest = docs.appendingPathComponent("quiz.html")
        do {
            try html.write(to: dest, atomically: true, encoding: .utf8)
            webView.loadFileURL(dest, allowingReadAccessTo: docs)
        } catch {
            webView.loadHTMLString(html, baseURL: nil)
        }
    }

    // MARK: - Coordinator (owns the coach; bridges "grade my approach")

    final class Coordinator: NSObject, WKScriptMessageHandler {
        let coach = HeuristicCoach()
        private let byId: [String: QuizQuestion]
        weak var webView: WKWebView?

        override init() {
            byId = Dictionary(Self.loadQuestions().map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
            super.init()
        }

        private static func loadQuestions() -> [QuizQuestion] {
            // Real released GR9277 questions, then the AI-generated (Phase-2) bank
            // (`pgre_mcq_generated.json`) appended to the same pool. Missing files
            // are skipped so the screen still renders the real questions.
            decodeQuestions(resource: "pgre_mcq") + decodeQuestions(resource: "pgre_mcq_generated")
        }

        private static func decodeQuestions(resource: String) -> [QuizQuestion] {
            struct Root: Codable { let questions: [QuizQuestion] }
            guard let url = Bundle.main.url(forResource: resource, withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let root = try? JSONDecoder().decode(Root.self, from: data) else { return [] }
            return root.questions
        }

        /// The page's `window.QUIZ`: every question plus its optimal-approach
        /// explanation (from the key) and the global `ai_on` flag.
        func embeddedJSON() -> String {
            let fallback = "{\"questions\":[],\"ai_on\":false}"
            // Real released questions plus the AI-generated (Phase-2) bank, so the
            // page renders both pools (each generated item carries `source` +
            // `seed_id`, which flow through verbatim to `window.QUIZ`).
            var questions = Self.rawQuestions(resource: "pgre_mcq")
                + Self.rawQuestions(resource: "pgre_mcq_generated")
            if questions.isEmpty { return fallback }
            // Fluency-illusion fix: serve one surface variant per concept, rotating
            // across sessions so a repeated question returns reworded.
            questions = selectMCQVariants(questions, defaults: .standard)
            for i in questions.indices {
                if let id = questions[i]["id"] as? String,
                   let expl = coach.optimalFor(id)?.studentExplanation, !expl.isEmpty {
                    questions[i]["optimal"] = ["explanation": expl]
                }
            }
            let out: [String: Any] = ["questions": questions, "ai_on": coach.aiAvailable]
            guard let d = try? JSONSerialization.data(withJSONObject: out),
                  let s = String(data: d, encoding: .utf8) else { return fallback }
            return s
        }

        /// The raw `questions` array from a bundled MCQ JSON resource (untyped, so
        /// extra keys like `source`/`seed_id` pass straight through). Empty if the
        /// resource is missing.
        private static func rawQuestions(resource: String) -> [[String: Any]] {
            guard let url = Bundle.main.url(forResource: resource, withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let questions = root["questions"] as? [[String: Any]] else { return [] }
            return questions
        }

        func userContentController(_ uc: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let body = message.body as? [String: Any],
                  let id = body["id"] as? String,
                  let question = byId[id] else { return }

            // Andy: fetch the spoken step-by-step script and hand it back to the page.
            if message.name == "explain" {
                Task { [weak self] in
                    guard let self else { return }
                    let payload = await self.coach.explainSteps(question: question).jsPayload()
                    await MainActor.run {
                        self.webView?.evaluateJavaScript("window.showAndySteps(\(payload));", completionHandler: nil)
                    }
                }
                return
            }

            // Stage-2 grading of the student's typed approach.
            guard message.name == "grade",
                  let chosen = body["chosen"] as? String,
                  let reasoning = body["reasoning"] as? String else { return }
            Task { [weak self] in
                guard let self else { return }
                let res = await self.coach.grade(question: question, chosen: chosen, reasoning: reasoning)
                let payload = res.jsPayload()
                await MainActor.run {
                    self.webView?.evaluateJavaScript("window.showCoach(\(payload));", completionHandler: nil)
                }
            }
        }
    }

    // MARK: - Page

    static func page(embeddedJSON: String) -> String {
        // Screen-specific chrome layered on the shared token block + component CSS
        // (SpeedrunWeb.componentCSS supplies .choice/.correct/.wrong, .card.coach,
        // .card.fast, .badge). Body is transparent over the SwiftUI starfield.
        let screenCSS = """
        body { padding: 16px 16px 44px; }
        #hdr { display: flex; justify-content: space-between; align-items: baseline;
               font-family: var(--pg-mono); text-transform: uppercase; letter-spacing: 0.12em;
               font-size: 12px; color: var(--pg-text-dim); margin-bottom: 8px; }
        #progress { color: var(--pg-accent); }
        #score { color: var(--pg-text); font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }
        #subject { font-family: var(--pg-mono); text-transform: uppercase; letter-spacing: 0.14em;
                   font-size: 11px; color: var(--pg-text-faint); margin-bottom: 12px; }
        #aigen { display: none; color: var(--pg-accent); border-color: rgba(76,224,255,0.5);
                 background: rgba(76,224,255,0.12); margin-bottom: 10px; }
        #stmt { font-size: 19px; line-height: 1.5; margin-bottom: 16px; overflow-wrap: anywhere; color: var(--pg-text); }
        #frq { margin-bottom: 4px; }
        #frqLabel { font-size: 13px; color: var(--pg-text-dim); margin: 6px 0 8px; }
        #reason { width: 100%; box-sizing: border-box; min-height: 66px; font-family: var(--pg-font);
                  font-size: 16px; padding: 11px 12px; border-radius: var(--pg-radius-sm); margin-bottom: 6px;
                  border: 1px solid var(--pg-line); background: var(--pg-panel); color: var(--pg-text);
                  -webkit-tap-highlight-color: transparent; }
        #reason::placeholder { color: var(--pg-text-faint); }
        #reason:focus { outline: none; border-color: var(--pg-accent); box-shadow: 0 0 0 1px rgba(76,224,255,0.4); }
        #verdict { font-size: 17px; font-weight: 700; margin: 18px 0 8px; color: var(--pg-text); }
        #solution { font-size: 15px; line-height: 1.5; color: var(--pg-text-dim); overflow-wrap: anywhere;
                    border-left: 2px solid var(--pg-line-strong); padding-left: 12px; }
        .btn { margin-top: 18px; padding: 13px 24px; font-size: 16px; font-weight: 600; font-family: var(--pg-font);
               border-radius: var(--pg-radius-sm); border: 1px solid var(--pg-accent); background: rgba(76,224,255,0.14);
               color: var(--pg-accent); box-shadow: 0 0 18px rgba(76,224,255,0.28); -webkit-tap-highlight-color: transparent; }
        #summary { text-align: center; padding-top: 44px; }
        #summary .big { font-size: 46px; font-weight: 800; font-variant-numeric: tabular-nums;
                        font-feature-settings: "tnum" 1; color: var(--pg-accent); margin: 6px 0; }

        /* ---- Andy the atom: a floating tutor. On a phone he docks bottom-right and
           the choice he's discussing lights up + scrolls into view (so he never
           covers the problem). No color-mix / regex lookbehind (iOS 15 WebKit). */
        #andy { position: fixed; right: 14px; bottom: 16px; width: 46px; height: 46px; z-index: 9999;
                opacity: 0; transform: translateY(18px); pointer-events: none;
                transition: opacity .35s ease, transform .35s ease; }
        #andy.show { opacity: 1; transform: none; }
        .andy-atom { position: absolute; inset: 0; animation: andy-bob 2.6s ease-in-out infinite; }
        .andy-nuc { position: absolute; left: 50%; top: 50%; width: 18px; height: 18px; margin: -9px 0 0 -9px;
                    border-radius: 50%; background: radial-gradient(circle at 34% 30%, #eafcff, #4ce0ff 60%, rgba(76,224,255,0.45));
                    box-shadow: 0 0 12px rgba(76,224,255,0.55), 0 0 22px rgba(76,224,255,0.4); }
        #andy.thinking .andy-nuc { animation: andy-think .9s ease-in-out infinite; }
        .andy-eye { position: absolute; top: 6px; width: 3px; height: 3.6px; border-radius: 50%; background: #0a0d16; }
        .andy-eye.l { left: 4.5px; } .andy-eye.r { right: 4.5px; }
        .andy-orbit { position: absolute; left: 50%; top: 50%; width: 46px; height: 46px; margin: -23px 0 0 -23px; }
        .andy-ew { position: absolute; inset: 0; }
        .andy-e { position: absolute; left: 50%; top: 50%; width: 5px; height: 5px; margin: -2.5px 0 0 -2.5px;
                  border-radius: 50%; background: #4ce0ff; box-shadow: 0 0 6px rgba(76,224,255,0.6);
                  transform: translateX(21px) scaleY(2.5); }
        .andy-orbit.ao1 { transform: rotate(0deg) scaleY(.4); }
        .andy-orbit.ao2 { transform: rotate(60deg) scaleY(.4); }
        .andy-orbit.ao3 { transform: rotate(120deg) scaleY(.4); }
        .ao1 .andy-ew { animation: andy-orbit 2.6s linear infinite; }
        .ao2 .andy-ew { animation: andy-orbit 3.5s linear infinite reverse; }
        .ao3 .andy-ew { animation: andy-orbit 3s linear infinite; }
        .andy-bubble { position: absolute; right: -4px; bottom: calc(100% + 12px);
                       width: max-content; min-width: 120px; max-width: min(74vw, 300px);
                       background: var(--pg-panel-2); color: var(--pg-text); border: 1px solid rgba(76,224,255,0.5);
                       border-radius: 13px; padding: 10px 26px 10px 13px; font-size: 14px; line-height: 1.42;
                       box-shadow: 0 10px 30px rgba(0,0,0,.55), 0 0 16px rgba(76,224,255,0.35);
                       opacity: 0; transform: translateY(6px) scale(.97); transform-origin: bottom right;
                       transition: opacity .25s ease, transform .25s ease; pointer-events: auto; }
        .andy-bubble.show { opacity: 1; transform: none; }
        .andy-bubble::after { content: ""; position: absolute; right: 18px; bottom: -6px; width: 10px; height: 10px;
                              background: var(--pg-panel-2); border-right: 1px solid rgba(76,224,255,0.5);
                              border-bottom: 1px solid rgba(76,224,255,0.5); transform: rotate(45deg); }
        .andy-close { position: absolute; top: 3px; right: 8px; color: var(--pg-text-dim); font-size: 15px;
                      -webkit-tap-highlight-color: transparent; }
        .andy-nav { display: flex; align-items: center; justify-content: space-between; gap: 10px;
                    margin-top: 9px; padding-top: 8px; border-top: 1px solid var(--pg-line); }
        .andy-nav button { background: transparent; border: 1px solid var(--pg-line); color: var(--pg-text-dim);
                           border-radius: 8px; padding: 2px 15px; font-size: 18px; line-height: 1.2;
                           font-family: var(--pg-mono); -webkit-tap-highlight-color: transparent; }
        .andy-nav button:disabled { opacity: .32; }
        .andy-step { font-family: var(--pg-mono); font-size: 12px; color: var(--pg-text-faint); }
        .andy-caret { color: #4ce0ff; }
        .choice.andy-focus, #stmt.andy-focus { border-color: #4ce0ff !important;
                            box-shadow: 0 0 0 1px #4ce0ff, 0 0 20px rgba(76,224,255,0.45) !important; }
        body.andy-on { padding-bottom: 118px; }
        @keyframes andy-orbit { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes andy-bob { 0%,100% { transform: translateY(-2.5px); } 50% { transform: translateY(2.5px); } }
        @keyframes andy-think { 0%,100% { box-shadow: 0 0 10px rgba(76,224,255,0.5); }
                                50% { box-shadow: 0 0 22px #4ce0ff, 0 0 34px rgba(76,224,255,0.5); } }
        @media (prefers-reduced-motion: reduce) {
          .andy-atom, .ao1 .andy-ew, .ao2 .andy-ew, .ao3 .andy-ew, #andy.thinking .andy-nuc { animation: none; }
        }
        """
        let body = """
        <div id="hdr"><span id="progress"></span><span id="score"></span></div>
        <div id="subject"></div>
        <div id="aigen" class="badge">⚛ AI-generated</div>
        <div id="stmt"></div>
        <div id="frq"><div id="frqLabel"></div><textarea id="reason" placeholder="e.g. cross off impossible choices, then estimate…"></textarea></div>
        <div id="choices"></div>
        <div id="feedback"></div>
        <div id="summary" style="display:none"></div>
        <script>
        (function () {
          var ROOT = \(embeddedJSON);
          var DATA = ROOT.questions || [];
          var AI_ON = !!ROOT.ai_on;
          function shuffle(a){ for (var i=a.length-1;i>0;i--){ var j=Math.floor(Math.random()*(i+1)); var t=a[i];a[i]=a[j];a[j]=t; } }
          shuffle(DATA);  // randomises tie-breaks; the actual order is chosen adaptively below
          var answered = 0, correct = 0, locked = false;
          // Adaptive difficulty (Zone of Proximal Development): serve the unanswered
          // question whose 1-5 difficulty is closest to a running ability estimate
          // that rises on a correct answer and falls (faster) on a wrong one.
          var ability = 3.0, served = 0, cur = -1, used = {};
          var coachTimeout = null;  // safety net if AI grading never calls back
          function diffOf(q){ var d = q && q.difficulty; return (typeof d === "number" && d >= 1) ? d : 3; }
          function pickNext(){
            var best = 1e9, cands = [];
            for (var i=0;i<DATA.length;i++){
              if (used[i]) continue;
              var gap = Math.abs(diffOf(DATA[i]) - ability);
              if (gap < best - 1e-9) { best = gap; cands = [i]; }
              else if (gap < best + 1e-9) { cands.push(i); }
            }
            return cands.length ? cands[Math.floor(Math.random()*cands.length)] : -1;
          }
          function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
          function mathify(t){
            if (!t) return "";
            t = t.replace(/\\$\\$([\\s\\S]+?)\\$\\$/g, function(_, m){ return "\\\\[" + m + "\\\\]"; });
            t = t.replace(/\\$([\\s\\S]+?)\\$/g, function(_, m){ return "\\\\(" + m + "\\\\)"; });
            return t;
          }
          function typeset(el){ if (window.MathJax && MathJax.typesetPromise) { MathJax.typesetPromise(el ? [el] : undefined).catch(function(){}); } }
          function score(){ document.getElementById("score").textContent = answered ? (correct + "/" + answered + " (" + Math.round(100*correct/answered) + "%)") : ""; }
          function render(){
            andyStop();
            var prevId = (cur >= 0 && DATA[cur]) ? DATA[cur].id : null;
            cur = pickNext();
            if (cur < 0) {
              // Endless mode: bank exhausted — reshuffle and keep going forever
              // instead of showing a "Finished" screen. Don't repeat the last Q.
              shuffle(DATA); used = {};
              if (prevId && DATA.length > 1) {
                for (var i=0;i<DATA.length;i++){ if (DATA[i].id === prevId) { used[i] = true; break; } }
              }
              cur = pickNext();
              used = {};
            }
            if (cur < 0) { return; }
            used[cur] = true; served++;
            locked = false;
            var q = DATA[cur];
            document.getElementById("summary").style.display = "none";
            document.getElementById("feedback").innerHTML = "";
            document.getElementById("frq").style.display = "block";
            document.getElementById("frqLabel").textContent =
              AI_ON ? "How would you solve this? (type your approach — you'll get AI coaching on it)"
                    : "How would you solve this? (jot your approach, then check it against the fastest route)";
            var ta = document.getElementById("reason"); ta.value = ""; ta.disabled = false;
            var lap = DATA.length ? Math.floor((served - 1) / DATA.length) : 0;
            var pos = DATA.length ? ((served - 1) % DATA.length) + 1 : served;
            document.getElementById("progress").textContent =
              "Question " + pos + " / " + DATA.length + (lap > 0 ? " · lap " + (lap + 1) : "");
            score();
            document.getElementById("subject").textContent = q.subject || "";
            // Badge AI-generated (Phase-2) items only; real questions have no source.
            document.getElementById("aigen").style.display = (q.source === "generated") ? "inline-block" : "none";
            document.getElementById("stmt").innerHTML = mathify(q.statement);
            var box = document.getElementById("choices"); box.innerHTML = "";
            q.choices.forEach(function(c){
              var b = document.createElement("button");
              b.className = "choice"; b.dataset.letter = c[0];
              b.innerHTML = "<span class='lab'>" + c[0] + "</span>" + mathify(c[1]);
              b.onclick = function(){ choose(c[0]); };
              box.appendChild(b);
            });
            typeset();
          }
          function choose(letter){
            if (locked) { return; } locked = true;
            var q = DATA[cur];
            var reasoning = (document.getElementById("reason").value || "").trim();
            document.getElementById("reason").disabled = true;
            var ok = letter === q.answer;
            answered++; if (ok) { correct++; }
            // ZPD: climb on a correct answer, ease down (faster) on a miss.
            ability = ok ? Math.min(5, ability + 0.5) : Math.max(1, ability - 0.8);
            score();
            document.querySelectorAll(".choice").forEach(function(b){
              b.disabled = true;
              if (b.dataset.letter === q.answer) { b.classList.add("correct"); }
              else if (b.dataset.letter === letter) { b.classList.add("wrong"); }
            });
            var html =
              "<div id='verdict'>" + (ok ? "✅ Correct" : "❌ Incorrect — answer is " + q.answer) + "</div>" +
              (q.solution ? "<div id='solution'>" + mathify(q.solution) + "</div>" : "");
            // Always show the fastest expert approach (from the key; no network).
            if (q.optimal && q.optimal.explanation) {
              html += "<div class='card fast' id='fast'><div class='t'>⚡ Fastest approach</div><div>" +
                      mathify(q.optimal.explanation) + "</div></div>";
            }
            // Personalised AI coaching only when a key is baked in AND the student wrote something.
            if (AI_ON && reasoning) {
              html += "<div class='card coach' id='coach'><div class='t'>🧠 Coaching your approach…</div>" +
                      "<div class='muted'>Grading how you tackled it…</div></div>";
            }
            html += "<button class='btn' id='andyBtn' style='margin-right:8px'>⚛ Explain with Andy</button>";
            html += "<button class='btn' id='nextBtn'>Next question →</button>";
            var fb = document.getElementById("feedback"); fb.innerHTML = html;
            document.getElementById("nextBtn").onclick = function(){ render(); };
            document.getElementById("andyBtn").onclick = function(){ andyExplain(DATA[cur]); };
            typeset(fb);
            if (AI_ON && reasoning) {
              window.webkit.messageHandlers.grade.postMessage({ id: q.id, chosen: letter, reasoning: reasoning });
              // Safety net: if grading never calls back (hang/offline), show the fallback.
              coachTimeout = setTimeout(function(){ window.showCoach({ ok: false }); }, 25000);
            }
          }
          // Called from Swift (HeuristicCoach.grade) with the coaching result.
          window.showCoach = function(res){
            var coach = document.getElementById("coach");
            if (!coach) { return; }
            if (coachTimeout) { clearTimeout(coachTimeout); coachTimeout = null; }
            if (!res || !res.ok) {
              // AI coaching unavailable (no key / offline / error / timed out): keep the
              // card but explain, and point to the always-present fastest-approach fallback.
              var hasFast = !!document.getElementById("fast");
              coach.innerHTML =
                "<div class='t'>🧠 Your approach</div>" +
                "<div class='muted'>AI coaching isn't available right now" +
                (hasFast ? " — see the ⚡ Fastest approach above for the quickest route." : ".") +
                "</div>";
              return;
            }
            var badges = {
              optimal:      ["⚡ Optimal approach", "var(--pg-ok)"],
              valid_slower: ["✅ Valid — a faster route exists", "var(--pg-info)"],
              overcomputed: ["🧮 You over-solved it", "var(--pg-warn)"],
              guessed:      ["🎲 Let's make it rigorous", "var(--pg-warn)"],
              flawed:       ["⚠️ Reasoning slip", "var(--pg-bad)"]
            };
            var b = badges[res.verdict];
            var inner = "<div class='t'>🧠 Your approach</div>";
            if (b) { inner += "<span class='badge' style='color:" + b[1] + ";border-color:" + b[1] + "'>" + b[0] + "</span>"; }
            inner += "<div>" + esc(res.feedback) + "</div>";
            if (res.missed && res.missed.length) {
              inner += "<ul class='missed'>";
              res.missed.forEach(function(m){ inner += "<li>" + esc(m) + "</li>"; });
              inner += "</ul>";
            }
            coach.innerHTML = inner; typeset(coach);
          };
          function done(){
            document.getElementById("stmt").innerHTML = "";
            document.getElementById("frq").style.display = "none";
            document.getElementById("choices").innerHTML = "";
            document.getElementById("feedback").innerHTML = "";
            document.getElementById("subject").textContent = "";
            document.getElementById("aigen").style.display = "none";
            document.getElementById("progress").textContent = "Finished";
            document.getElementById("score").textContent = "";
            var sm = document.getElementById("summary"); sm.style.display = "block";
            var pct = answered ? Math.round(100*correct/answered) : 0;
            sm.innerHTML = "<div>Performance on real GR9277 questions</div><div class='big'>" + pct +
              "%</div><div>" + correct + " / " + answered + " correct</div>" +
              "<button class='btn' id='againBtn'>Try again</button>";
            document.getElementById("againBtn").onclick = function(){ shuffle(DATA); used={}; served=0; ability=3.0; answered=0; correct=0; render(); };
          }
          // ---- Andy the atom: narrates the fastest solution step by step. Docks
          // bottom-right; the choice he's discussing lights up + scrolls into view.
          // Steps come from the AI (window.showAndySteps) when a key is baked in,
          // else a client-side script from the baked optimal-approach key.
          var andyEl=null, andyBubble=null, andyPlaying=false, andyPending=false;
          var andyTimers=[], andySteps=[], andyIdx=0, andyManual=false, andyReduced=false;
          try { andyReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch(e){}
          function andyClearTimers(){ andyTimers.forEach(function(t){ clearTimeout(t); }); andyTimers=[]; }
          function andyLater(fn, ms){ var t=setTimeout(fn, ms); andyTimers.push(t); return t; }
          function andyMake(){
            if (andyEl) { return; }
            andyEl = document.createElement("div"); andyEl.id = "andy";
            andyEl.innerHTML =
              '<div class="andy-atom">' +
                '<span class="andy-orbit ao1"><span class="andy-ew"><i class="andy-e"></i></span></span>' +
                '<span class="andy-orbit ao2"><span class="andy-ew"><i class="andy-e"></i></span></span>' +
                '<span class="andy-orbit ao3"><span class="andy-ew"><i class="andy-e"></i></span></span>' +
                '<span class="andy-nuc"><span class="andy-eye l"></span><span class="andy-eye r"></span></span>' +
              '</div>' +
              '<div class="andy-bubble" id="andyBubble"><span class="andy-close" id="andyClose">✕</span>' +
              '<span id="andyText"></span>' +
              '<div class="andy-nav" id="andyNav" style="display:none">' +
                '<button id="andyPrev">‹</button><span class="andy-step" id="andyStep"></span><button id="andyNext">›</button>' +
              '</div></div>';
            document.body.appendChild(andyEl);
            andyBubble = document.getElementById("andyBubble");
            document.getElementById("andyClose").onclick = andyStop;
            document.getElementById("andyPrev").onclick = function(){ andyStepBy(-1); };
            document.getElementById("andyNext").onclick = function(){ andyStepBy(1); };
          }
          function andyTargetEl(focus){
            if (focus === "stem") { return document.getElementById("stmt"); }
            var q = DATA[cur]; if (focus === "answer") { focus = q && q.answer; }
            if (focus){ var list=document.querySelectorAll(".choice");
              for (var i=0;i<list.length;i++){ if (list[i].dataset.letter === focus) { return list[i]; } } }
            return document.getElementById("stmt");
          }
          function andyClearFocus(){ document.querySelectorAll(".andy-focus").forEach(function(e){ e.classList.remove("andy-focus"); }); }
          // He stays docked; the element he's discussing lights up and scrolls into view.
          function andyFocusEl(el){
            andyClearFocus();
            if (el){ el.classList.add("andy-focus"); if (el.scrollIntoView){ el.scrollIntoView({ block: "center", behavior: "smooth" }); } }
          }
          function andyTrySpeak(text){ try { if (!window.speechSynthesis) { return; } window.speechSynthesis.cancel();
            var u=new SpeechSynthesisUtterance(text); u.rate=1.03; u.pitch=1.18; window.speechSynthesis.speak(u); } catch(e){} }
          function andyStopSpeak(){ try { if (window.speechSynthesis) { window.speechSynthesis.cancel(); } } catch(e){} }
          function andyType(text, done){
            var el=document.getElementById("andyText"); andyBubble.classList.add("show"); andyTrySpeak(text);
            if (andyReduced){ el.textContent=text; if (done){ andyLater(done, 10); } return; }
            var i=0;
            (function tick(){ if (!andyPlaying){ return; }
              el.innerHTML = esc(text.slice(0,i)) + "<span class='andy-caret'>▋</span>";
              if (i < text.length){ i++; andyLater(tick, 20); } else { el.textContent=text; if (done){ done(); } } })();
          }
          function andyShowNav(on){ var n=document.getElementById("andyNav"); if (n){ n.style.display = on ? "flex" : "none"; } }
          function andyUpdateNav(){
            var p=document.getElementById("andyPrev"), nx=document.getElementById("andyNext"), st=document.getElementById("andyStep");
            if (st){ st.textContent = (andyIdx+1) + " / " + andySteps.length; }
            if (p){ p.disabled = andyIdx <= 0; } if (nx){ nx.disabled = andyIdx >= andySteps.length-1; }
          }
          function andyRenderStep(i){
            if (!andyPlaying || i < 0 || i >= andySteps.length){ return; }
            andyClearTimers(); andyIdx=i; andyUpdateNav();
            var s=andySteps[i]; andyFocusEl(andyTargetEl(s.focus));
            andyLater(function(){ if (!andyPlaying){ return; }
              andyType(s.say, function(){ if (andyManual){ return; }
                if (andyIdx < andySteps.length-1){ andyLater(function(){ andyRenderStep(andyIdx+1); }, Math.min(4200, 1100 + s.say.length*42)); } });
            }, 360);
          }
          function andyStepBy(d){ andyManual=true; andyStopSpeak(); andyRenderStep(andyIdx + d); }
          function andyPlay(steps){
            andyMake(); andyClearTimers(); andyEl.classList.remove("thinking"); andyEl.classList.add("show");
            andyPlaying=true; andyManual=false; andySteps=steps; andyIdx=0; andyShowNav(steps.length > 1); andyRenderStep(0);
          }
          function andyExcuse(){
            andyMake(); andyClearTimers(); andyEl.classList.remove("thinking"); andyEl.classList.add("show");
            andyPlaying=true; andyManual=true; andySteps=[]; andyShowNav(false); andyClearFocus();
            andyType("Hmm — I can't crack this one right now. Catch you on the next one!", function(){ andyLater(andyStop, 2800); });
          }
          function stripMath(s){
            if (!s){ return ""; }
            var bs = String.fromCharCode(92);  // a single backslash (avoids Swift's \\( interpolation)
            var out = String(s);
            [bs + "(", bs + ")", bs + "[", bs + "]", "$", "{", "}"].forEach(function(t){ out = out.split(t).join(""); });
            out = out.replace(new RegExp(bs + bs + "[a-zA-Z]+", "g"), "");  // drop leftover \\commands
            out = out.replace(new RegExp("\\s+", "g"), " ");
            return out.trim();
          }
          // Sentence split WITHOUT regex lookbehind (unsupported on iOS 15 WebKit).
          function andySentences(s){ return (s.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || []).map(function(x){ return x.trim(); }).filter(Boolean); }
          function andyFocusOf(sentence, answer){
            var m=sentence.match(/\\(([A-E])\\)/g);
            if (m && m.length){ var last=m[m.length-1].charAt(1); if (m.length===1 && last===answer){ return "answer"; } return last; }
            return "stem";
          }
          // Offline: narrate the same fastest-route text the ⚡ card shows, live.
          function andyFallbackSteps(q){
            var steps=[], o=q && q.optimal, ans=q.answer;
            if (o && o.explanation){ andySentences(stripMath(o.explanation)).forEach(function(s){ steps.push({ say:s, focus:andyFocusOf(s, ans) }); }); }
            else if (o && o.eliminations && o.eliminations.length){ o.eliminations.forEach(function(e){ var r=stripMath(e[1]); if (r){ steps.push({ say:"Rule out ("+e[0]+"): "+r, focus:e[0] }); } }); }
            if (!steps.length || steps[steps.length-1].focus !== "answer"){ steps.push({ say:"So the fastest route lands on ("+ans+").", focus:"answer" }); }
            return steps;
          }
          function andyHasMaterial(q){ var o=q && q.optimal; return !!(o && ((o.explanation && o.explanation.trim()) || (o.eliminations && o.eliminations.length))); }
          function andyResolve(res, q){ if (res && res.ok && res.steps && res.steps.length){ andyPlay(res.steps); }
            else if (andyHasMaterial(q)){ andyPlay(andyFallbackSteps(q)); } else { andyExcuse(); } }
          function andyExplain(q){
            if (!q){ return; }
            andyMake(); andyClearTimers(); andyPlaying=true;
            document.body.classList.add("andy-on"); andyEl.classList.add("show","thinking"); andyClearFocus();
            andyShowNav(false); andyBubble.classList.add("show");
            document.getElementById("andyText").textContent = "Let me find the fast route…";
            if (AI_ON){
              andyPending=true;
              window.webkit.messageHandlers.explain.postMessage({ id: q.id });
              andyLater(function(){ if (andyPending){ andyPending=false; andyResolve({ ok:false }, q); } }, 20000);
            } else { andyLater(function(){ andyResolve({ ok:false }, q); }, 650); }
          }
          window.showAndySteps = function(res){ if (!andyPending){ return; } andyPending=false; andyResolve(res, DATA[cur]); };
          function andyStop(){
            andyPlaying=false; andyPending=false; andyClearTimers(); andyStopSpeak(); andyClearFocus();
            document.body.classList.remove("andy-on");
            if (andyEl){ andyEl.classList.remove("show","thinking"); if (andyBubble){ andyBubble.classList.remove("show"); } }
          }

          if (!DATA.length) { document.getElementById("stmt").textContent = "No questions available."; }
          else { render(); }
        })();
        </script>
        """
        return SpeedrunWeb.document(
            bodyHTML: body,
            css: SpeedrunWeb.componentCSS + "\n" + screenCSS,
            mjxScale: 112)
    }
}
