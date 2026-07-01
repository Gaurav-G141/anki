// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Performance test for the Speedrun topic-mastery scan (SPECS.md S2-T10).

#![allow(unused_imports)]

use std::time::Instant;

use super::*;
use crate::card::FsrsMemoryState;
use crate::revlog::RevlogEntry;
use crate::revlog::RevlogReviewKind;
use crate::tests::NoteAdder;
use crate::timestamp::TimestampSecs;

/// Percentile (0..=100) of an ascending-sorted slice via nearest-rank.
fn percentile(sorted: &[f64], pct: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let rank = (pct / 100.0 * (sorted.len() as f64 - 1.0)).round() as usize;
    sorted[rank.min(sorted.len() - 1)]
}

/// SPECS.md S2-T10: build a ~50k-card PGRE collection spread across all 9
/// subjects (coverage = 100%), warm the cache, then time the read-only
/// `topic_mastery_report` scan over many runs and assert p95 < 150 ms and
/// p99 < 250 ms, printing a p50/p95/p99 table.
///
/// `#[ignore]` because building 50k cards is slow; run explicitly with:
///   cargo test -p anki speedrun::tests_perf -- --ignored --nocapture
#[test]
#[ignore]
fn perf_topic_mastery_50k() -> Result<()> {
    const TARGET_CARDS: usize = 50_000;

    let mut col = Collection::new();

    let keys: [&str; 9] = [
        "classical_mechanics",
        "electromagnetism",
        "quantum_mechanics",
        "atomic_physics",
        "thermo_stat_mech",
        "optics_waves",
        "specialized_topics",
        "special_relativity",
        "lab_methods",
    ];

    // A fixed last-review time 1 day in the past, reused for every card so the
    // FSRS retrievability math has realistic (non-zero) input.
    let last_review = TimestampSecs(TimestampSecs::now().0 - 86_400);

    // ---- build phase (single transaction for speed) ----
    let build_start = Instant::now();

    // We need at least ~30 graded reviews spread across some cards so the
    // response is *scored* (not abstaining). Add a handful per subject to the
    // first card we create in each subject.
    let reviews_per_subject = 4; // 9 * 4 = 36 graded reviews total

    col.storage.db.execute_batch("begin")?;
    let mut built: usize = 0;
    'outer: for (si, key) in keys.iter().enumerate() {
        let tag = format!("pgre::{key}");
        // Spread the cards as evenly as possible across the 9 subjects.
        let target_for_subject =
            TARGET_CARDS / keys.len() + usize::from(si < TARGET_CARDS % keys.len());
        for j in 0..target_for_subject {
            let note = NoteAdder::basic(&mut col).fields(&["F", "B"]).add(&mut col);
            col.add_tags_to_notes(&[note.id], tag.as_str())?;
            let mut card = col.storage.all_cards_of_note(note.id)?.pop().unwrap();
            card.memory_state = Some(FsrsMemoryState {
                stability: 200.0,
                difficulty: 5.0,
            });
            card.last_review_time = Some(last_review);
            col.storage.update_card(&card)?;

            // Add a few graded reviews to the first card of each subject.
            if j == 0 {
                for _ in 0..reviews_per_subject {
                    let e = RevlogEntry {
                        cid: card.id,
                        taken_millis: 5000,
                        button_chosen: 3,
                        review_kind: RevlogReviewKind::Review,
                        ..Default::default()
                    };
                    col.storage.add_revlog_entry(&e, true)?;
                }
            }

            built += 1;
            if built >= TARGET_CARDS {
                break 'outer;
            }
        }
    }
    col.storage.db.execute_batch("commit")?;

    let build_elapsed = build_start.elapsed();
    println!(
        "built {built} cards across {} subjects in {:.2}s",
        keys.len(),
        build_elapsed.as_secs_f64()
    );

    // ---- warm-up (untimed) ----
    for _ in 0..3 {
        let req = TopicMasteryRequest::default();
        let resp = col.topic_mastery_report(req)?;
        let _ = resp;
    }

    // Sanity check the response shape once (don't abstain; full coverage).
    {
        let resp = col.topic_mastery_report(TopicMasteryRequest::default())?;
        assert_eq!(resp.topics.len(), 9, "expected 9 topic rows");
        assert!(
            (resp.coverage - 1.0).abs() < 1e-6,
            "expected full coverage, got {}",
            resp.coverage
        );
        assert!(
            !resp.abstain,
            "expected a scored (non-abstaining) response, reasons: {:?}",
            resp.abstain_reasons
        );
    }

    // ---- timed runs ----
    const RUNS: usize = 50;
    let mut durations_ms: Vec<f64> = Vec::with_capacity(RUNS);
    for _ in 0..RUNS {
        let req = TopicMasteryRequest::default();
        let start = Instant::now();
        let resp = col.topic_mastery_report(req)?;
        let elapsed = start.elapsed();
        let _ = resp;
        durations_ms.push(elapsed.as_secs_f64() * 1000.0);
    }

    durations_ms.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let p50 = percentile(&durations_ms, 50.0);
    let p95 = percentile(&durations_ms, 95.0);
    let p99 = percentile(&durations_ms, 99.0);
    let min = durations_ms.first().copied().unwrap_or(0.0);
    let max = durations_ms.last().copied().unwrap_or(0.0);

    // The Speedrun §10 targets (p95 < 150 ms, p99 < 250 ms on 50k) are *release*
    // numbers. A debug build is ~2-3x slower, so asserting the release target
    // against debug would be a flaky false negative. We therefore assert the real
    // target only in release, and apply a generous sanity bound in debug to still
    // catch gross regressions. Run `cargo test -p anki --release ...` for the
    // production figure (observed p95 ~51 ms).
    let release = !cfg!(debug_assertions);
    let (p95_budget, p99_budget) = if release {
        (150.0, 250.0)
    } else {
        (500.0, 800.0)
    };
    let profile = if release { "release" } else { "debug" };

    println!();
    println!("topic_mastery_report latency over {RUNS} warm runs ({built} cards, {profile} build)");
    println!("  {:<8} {:>10}", "stat", "ms");
    println!("  {:-<8} {:->10}", "", "");
    println!("  {:<8} {:>10.3}", "min", min);
    println!("  {:<8} {:>10.3}", "p50", p50);
    println!("  {:<8} {:>10.3}", "p95", p95);
    println!("  {:<8} {:>10.3}", "p99", p99);
    println!("  {:<8} {:>10.3}", "max", max);
    println!("  budget(p95/p99): {p95_budget}/{p99_budget} ms ({profile})");
    println!();

    assert!(
        p95 < p95_budget,
        "p95 {p95:.3} ms exceeded {p95_budget} ms ({profile} build)"
    );
    assert!(
        p99 < p99_budget,
        "p99 {p99:.3} ms exceeded {p99_budget} ms ({profile} build)"
    );

    Ok(())
}
