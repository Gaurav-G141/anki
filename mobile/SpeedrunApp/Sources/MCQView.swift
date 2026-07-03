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
            struct Root: Codable { let questions: [QuizQuestion] }
            guard let url = Bundle.main.url(forResource: "pgre_mcq", withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let root = try? JSONDecoder().decode(Root.self, from: data) else { return [] }
            return root.questions
        }

        /// The page's `window.QUIZ`: every question plus its optimal-approach
        /// explanation (from the key) and the global `ai_on` flag.
        func embeddedJSON() -> String {
            let fallback = "{\"questions\":[],\"ai_on\":false}"
            guard let url = Bundle.main.url(forResource: "pgre_mcq", withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  var questions = root["questions"] as? [[String: Any]] else { return fallback }
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
        """
        <!doctype html>
        <html>
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <!-- No custom MathJax config: the defaults already typeset \\(…\\) / \\[…\\],
             exactly like the review card webview. -->
        <script src="mathjax/tex-chtml-full.js" async></script>
        <style>
          :root { color-scheme: light dark; }
          body { font-family: -apple-system, system-ui, sans-serif; margin: 0;
                 padding: 14px 16px 40px; color: #111; }
          @media (prefers-color-scheme: dark) { body { color: #eee; } }
          #hdr { display: flex; justify-content: space-between; align-items: baseline;
                 font-size: 13px; opacity: 0.7; margin-bottom: 6px; }
          #subject { font-size: 12px; opacity: 0.6; margin-bottom: 10px; }
          #stmt { font-size: 19px; line-height: 1.5; margin-bottom: 14px; overflow-wrap: anywhere; }
          #frqLabel { font-size: 13px; opacity: 0.75; margin: 4px 0 6px; }
          #reason { width: 100%; box-sizing: border-box; min-height: 66px; font: inherit;
                    font-size: 16px; padding: 10px; border-radius: 10px; margin-bottom: 6px;
                    border: 1px solid rgba(128,128,128,0.4); background: rgba(128,128,128,0.06);
                    color: inherit; -webkit-tap-highlight-color: transparent; }
          .choice { display: block; width: 100%; text-align: left; margin: 8px 0; padding: 13px 14px;
                    border-radius: 10px; border: 1px solid rgba(128,128,128,0.4);
                    background: rgba(128,128,128,0.08); color: inherit; font: inherit;
                    font-size: 17px; -webkit-tap-highlight-color: transparent; }
          .choice .lab { font-weight: 700; margin-right: 8px; }
          .choice.correct { background: rgba(40,170,90,0.28); border-color: rgba(40,170,90,0.9); }
          .choice.wrong   { background: rgba(220,60,60,0.24); border-color: rgba(220,60,60,0.9); }
          #verdict { font-size: 17px; font-weight: 600; margin: 16px 0 6px; }
          #solution { font-size: 15px; line-height: 1.5; opacity: 0.9; overflow-wrap: anywhere;
                      border-left: 3px solid rgba(128,128,128,0.4); padding-left: 12px; }
          .card { margin-top: 14px; padding: 12px 14px; border-radius: 10px;
                  background: rgba(128,128,128,0.08); overflow-wrap: anywhere; }
          .card .t { font-weight: 700; margin-bottom: 6px; }
          .badge { display: inline-block; padding: 3px 10px; border-radius: 999px;
                   font-size: 13px; font-weight: 600; margin-bottom: 8px; }
          .muted { opacity: 0.6; }
          .missed { margin: 8px 0 0 18px; }
          .btn { margin-top: 18px; padding: 13px 22px; font-size: 16px; font-weight: 600;
                 border-radius: 10px; border: none; background: #2e6ce0; color: #fff; }
          #summary { text-align: center; padding-top: 40px; }
          #summary .big { font-size: 46px; font-weight: 700; }
          mjx-container { font-size: 108% !important; max-width: 100%; overflow-x: auto; }
        </style>
        </head>
        <body>
        <div id="hdr"><span id="progress"></span><span id="score"></span></div>
        <div id="subject"></div>
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
          shuffle(DATA);
          var idx = 0, answered = 0, correct = 0, locked = false;
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
            if (idx >= DATA.length) { return done(); }
            locked = false;
            var q = DATA[idx];
            document.getElementById("summary").style.display = "none";
            document.getElementById("feedback").innerHTML = "";
            document.getElementById("frq").style.display = "block";
            document.getElementById("frqLabel").textContent =
              AI_ON ? "How would you solve this? (type your approach — you'll get AI coaching on it)"
                    : "How would you solve this? (jot your approach, then check it against the fastest route)";
            var ta = document.getElementById("reason"); ta.value = ""; ta.disabled = false;
            document.getElementById("progress").textContent = "Question " + (idx+1) + " / " + DATA.length;
            score();
            document.getElementById("subject").textContent = q.subject || "";
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
            var q = DATA[idx];
            var reasoning = (document.getElementById("reason").value || "").trim();
            document.getElementById("reason").disabled = true;
            var ok = letter === q.answer;
            answered++; if (ok) { correct++; }
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
              html += "<div class='card' id='fast'><div class='t'>⚡ Fastest approach</div><div>" +
                      mathify(q.optimal.explanation) + "</div></div>";
            }
            // Personalised AI coaching only when a key is baked in AND the student wrote something.
            if (AI_ON && reasoning) {
              html += "<div class='card' id='coach'><div class='t'>🧠 Coaching your approach…</div>" +
                      "<div class='muted'>Grading how you tackled it…</div></div>";
            }
            html += "<button class='btn' id='nextBtn'>Next question →</button>";
            var fb = document.getElementById("feedback"); fb.innerHTML = html;
            document.getElementById("nextBtn").onclick = function(){ idx++; render(); };
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
              optimal:      ["⚡ Optimal approach", "rgba(40,170,90,0.25)"],
              valid_slower: ["✅ Valid — a faster route exists", "rgba(46,108,224,0.2)"],
              overcomputed: ["🧮 You over-solved it", "rgba(224,160,46,0.25)"],
              guessed:      ["🎲 Let's make it rigorous", "rgba(224,160,46,0.25)"],
              flawed:       ["⚠️ Reasoning slip", "rgba(220,60,60,0.2)"]
            };
            var b = badges[res.verdict];
            var inner = "<div class='t'>🧠 Your approach</div>";
            if (b) { inner += "<span class='badge' style='background:" + b[1] + "'>" + b[0] + "</span>"; }
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
            document.getElementById("progress").textContent = "Finished";
            document.getElementById("score").textContent = "";
            var sm = document.getElementById("summary"); sm.style.display = "block";
            var pct = answered ? Math.round(100*correct/answered) : 0;
            sm.innerHTML = "<div>Performance on real GR9277 questions</div><div class='big'>" + pct +
              "%</div><div>" + correct + " / " + answered + " correct</div>" +
              "<button class='btn' id='againBtn'>Try again</button>";
            document.getElementById("againBtn").onclick = function(){ shuffle(DATA); idx=0; answered=0; correct=0; render(); };
          }
          if (!DATA.length) { document.getElementById("stmt").textContent = "No questions available."; }
          else { render(); }
        })();
        </script>
        </body>
        </html>
        """
    }
}
