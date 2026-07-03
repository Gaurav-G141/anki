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
            guard message.name == "grade",
                  let body = message.body as? [String: Any],
                  let id = body["id"] as? String,
                  let chosen = body["chosen"] as? String,
                  let reasoning = body["reasoning"] as? String,
                  let question = byId[id] else { return }
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
            cur = pickNext();
            if (cur < 0) { return done(); }
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
            document.getElementById("progress").textContent = "Question " + served + " / " + DATA.length;
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
            html += "<button class='btn' id='nextBtn'>Next question →</button>";
            var fb = document.getElementById("feedback"); fb.innerHTML = html;
            document.getElementById("nextBtn").onclick = function(){ render(); };
            typeset(fb);
            if (AI_ON && reasoning) {
              window.webkit.messageHandlers.grade.postMessage({ id: q.id, chosen: letter, reasoning: reasoning });
            }
          }
          // Called from Swift (HeuristicCoach.grade) with the coaching result.
          window.showCoach = function(res){
            var coach = document.getElementById("coach");
            if (!coach) { return; }
            if (!res || !res.ok) { coach.parentNode.removeChild(coach); return; }
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
