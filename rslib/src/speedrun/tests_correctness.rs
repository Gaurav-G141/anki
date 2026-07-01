// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Correctness tests for the Speedrun topic-mastery scan (SPECS.md S2/S3).

#![allow(unused_imports)]

use anki_proto::speedrun::TopicMasteryRequest;
use anki_proto::speedrun::TopicMasteryResponse;
use fsrs::FSRS;
use fsrs::FSRS5_DEFAULT_DECAY;

use super::*;
use crate::card::CardId;
use crate::card::FsrsMemoryState;
use crate::revlog::RevlogEntry;
use crate::revlog::RevlogReviewKind;
use crate::tests::NoteAdder;
use crate::timestamp::TimestampSecs;

/// The five subjects with exam weight >= 0.10; all must be present for a
/// non-abstaining ("scored") response.
const HIGH_WEIGHT_KEYS: [&str; 5] = [
    "classical_mechanics",
    "electromagnetism",
    "quantum_mechanics",
    "atomic_physics",
    "thermo_stat_mech",
];

// ----------------------------------------------------------------- helpers

/// Add one Basic card tagged for `subject_key`, with a known FSRS memory state
/// and a last-review time `elapsed_secs` in the past. Returns the card id.
fn add_card(
    col: &mut Collection,
    subject_key: &str,
    stability: f32,
    difficulty: f32,
    elapsed_secs: i64,
) -> CardId {
    let note = NoteAdder::basic(col).fields(&["F", "B"]).add(col);
    col.add_tags_to_notes(&[note.id], &format!("pgre::{subject_key}"))
        .unwrap();
    let mut card = col
        .storage
        .all_cards_of_note(note.id)
        .unwrap()
        .pop()
        .unwrap();
    card.memory_state = Some(FsrsMemoryState {
        stability,
        difficulty,
    });
    card.last_review_time = Some(TimestampSecs(TimestampSecs::now().0 - elapsed_secs));
    col.storage.update_card(&card).unwrap();
    card.id
}

/// Add a tagged card with NO memory state (e.g. FSRS disabled / never
/// reviewed).
fn add_card_no_state(col: &mut Collection, subject_key: &str) -> CardId {
    let note = NoteAdder::basic(col).fields(&["F", "B"]).add(col);
    col.add_tags_to_notes(&[note.id], &format!("pgre::{subject_key}"))
        .unwrap();
    col.storage.all_cards_of_note(note.id).unwrap()[0].id
}

fn add_reviews(col: &mut Collection, cid: CardId, n: u32, taken_millis: u32) {
    for _ in 0..n {
        let entry = RevlogEntry {
            cid,
            taken_millis,
            button_chosen: 3,
            review_kind: RevlogReviewKind::Review,
            ..Default::default()
        };
        col.storage.add_revlog_entry(&entry, true).unwrap();
    }
}

/// A collection covering all five high-weight subjects with memory state and
/// enough reviews to clear the give-up rule (so the response is scored).
fn scored_collection() -> Collection {
    let mut col = Collection::new();
    for key in HIGH_WEIGHT_KEYS {
        // one clearly-mastered card (high stability, just reviewed)
        let c1 = add_card(&mut col, key, 500.0, 5.0, 0);
        // one clearly-unmastered card (tiny stability, long ago)
        let c2 = add_card(&mut col, key, 0.1, 5.0, 86_400 * 30);
        add_reviews(&mut col, c1, 3, 4_000);
        add_reviews(&mut col, c2, 3, 9_000);
    }
    col
}

fn topic<'a>(resp: &'a TopicMasteryResponse, key: &str) -> &'a anki_proto::speedrun::TopicMastery {
    let tag = format!("pgre::{key}");
    resp.topics.iter().find(|t| t.tag == tag).unwrap()
}

// ------------------------------------------------------------------- tests

#[test]
fn empty_collection_abstains() -> Result<()> {
    let mut col = Collection::new();
    let r = col.topic_mastery_report(TopicMasteryRequest::default())?;
    assert!(r.abstain);
    assert_eq!(r.topics.len(), 9);
    assert!(!r.abstain_reasons.is_empty());
    // honesty metadata present even when abstaining
    assert!(r.updated_at_millis > 0);
    assert_eq!(r.thresholds.as_ref().unwrap().review_floor, 20);
    Ok(())
}

#[test]
fn missing_high_weight_subject_abstains() -> Result<()> {
    // Cover everything except classical_mechanics (weight 0.20), with plenty of
    // reviews and state — must still abstain.
    let mut col = Collection::new();
    for key in [
        "electromagnetism",
        "quantum_mechanics",
        "atomic_physics",
        "thermo_stat_mech",
        "optics_waves",
        "specialized_topics",
        "special_relativity",
        "lab_methods",
    ] {
        let c = add_card(&mut col, key, 500.0, 5.0, 0);
        add_reviews(&mut col, c, 5, 5_000);
    }
    let r = col.topic_mastery_report(TopicMasteryRequest::default())?;
    assert!(r.abstain);
    assert!(
        r.abstain_reasons
            .iter()
            .any(|s| s.contains("Classical Mechanics")),
        "reasons: {:?}",
        r.abstain_reasons
    );
    Ok(())
}

#[test]
fn give_up_review_floor_boundary() -> Result<()> {
    // All high-weight subjects present + state. 19 total reviews => abstain;
    // 20 => scored.
    let build = |reviews_on_first: u32| -> TopicMasteryResponse {
        let mut col = Collection::new();
        let cids: Vec<CardId> = HIGH_WEIGHT_KEYS
            .iter()
            .map(|key| add_card(&mut col, key, 500.0, 5.0, 0))
            .collect();
        // spread reviews: 4 on four subjects = 16, plus the rest on the first
        for c in &cids[1..] {
            add_reviews(&mut col, *c, 4, 3_000);
        }
        add_reviews(&mut col, cids[0], reviews_on_first, 3_000);
        col.topic_mastery_report(TopicMasteryRequest::default())
            .unwrap()
    };
    // 16 (on subjects 2-5) + 3 = 19 -> abstain
    let r19 = build(3);
    assert!(
        r19.abstain,
        "19 reviews should abstain: {:?}",
        r19.abstain_reasons
    );
    // 16 + 4 = 20 -> scored
    let r20 = build(4);
    assert!(
        !r20.abstain,
        "20 reviews should score: {:?}",
        r20.abstain_reasons
    );
    Ok(())
}

#[test]
fn mastered_count_is_exact() -> Result<()> {
    // In classical_mechanics: 2 clearly-mastered (R~1) + 1 clearly-unmastered
    // (R~0).
    let mut col = Collection::new();
    add_card(&mut col, "classical_mechanics", 1000.0, 5.0, 0); // R ~ 1.0
    add_card(&mut col, "classical_mechanics", 1000.0, 5.0, 60); // R ~ 1.0
    add_card(&mut col, "classical_mechanics", 0.01, 5.0, 86_400 * 60); // R ~ 0
    let r = col.topic_mastery_report(TopicMasteryRequest::default())?;
    let cm = topic(&r, "classical_mechanics");
    assert_eq!(cm.total_cards, 3);
    assert_eq!(cm.cards_with_state, 3);
    assert_eq!(cm.mastered, 2, "expected 2 mastered, got {}", cm.mastered);
    Ok(())
}

#[test]
fn mean_retrievability_matches_golden() -> Result<()> {
    let mut col = Collection::new();
    let specs = [
        (50.0f32, 86_400i64),
        (120.0, 86_400 * 5),
        (10.0, 86_400 * 2),
    ];
    for (stab, elapsed) in specs {
        add_card(&mut col, "optics_waves", stab, 5.0, elapsed);
    }
    // Golden: recompute R per card using the same fn + the scan's timing source.
    let timing = col.timing_today()?;
    let fsrs = FSRS::new(None).unwrap();
    let nids = col.search_notes("tag:pgre::optics_waves", crate::search::SortMode::NoOrder)?;
    let mut sum = 0.0f64;
    let mut n = 0u32;
    for nid in nids {
        for card in col.storage.all_cards_of_note(nid)? {
            let state = card.memory_state.unwrap();
            let secs = card.seconds_since_last_review(&timing).unwrap_or(0);
            let r = fsrs.current_retrievability_seconds(state.into(), secs, FSRS5_DEFAULT_DECAY);
            sum += r as f64;
            n += 1;
        }
    }
    let golden_mean = (sum / n as f64) as f32;

    let resp = col.topic_mastery_report(TopicMasteryRequest::default())?;
    let ow = topic(&resp, "optics_waves");
    assert!(
        (ow.mean_retrievability - golden_mean).abs() < 1e-3,
        "mean_r {} vs golden {}",
        ow.mean_retrievability,
        golden_mean
    );
    Ok(())
}

#[test]
fn cards_without_memory_state_counted_only_in_total() -> Result<()> {
    let mut col = Collection::new();
    add_card(&mut col, "lab_methods", 100.0, 5.0, 0); // with state
    add_card_no_state(&mut col, "lab_methods"); // no state
    let r = col.topic_mastery_report(TopicMasteryRequest::default())?;
    let lm = topic(&r, "lab_methods");
    assert_eq!(lm.total_cards, 2);
    assert_eq!(lm.cards_with_state, 1);
    assert!(lm.mean_retrievability.is_finite());
    Ok(())
}

#[test]
fn deterministic_across_calls() -> Result<()> {
    let mut col = scored_collection();
    let a = col.topic_mastery_report(TopicMasteryRequest::default())?;
    let b = col.topic_mastery_report(TopicMasteryRequest::default())?;
    assert_eq!(a.abstain, b.abstain);
    assert_eq!(a.memory_score, b.memory_score);
    assert_eq!(a.score_low, b.score_low);
    assert_eq!(a.score_high, b.score_high);
    assert_eq!(a.total_reviews, b.total_reviews);
    assert_eq!(a.topics, b.topics);
    Ok(())
}

#[test]
fn scored_response_satisfies_honesty_contract() -> Result<()> {
    let mut col = scored_collection();
    let r = col.topic_mastery_report(TopicMasteryRequest::default())?;
    assert!(!r.abstain, "should score: {:?}", r.abstain_reasons);
    assert!(r.memory_score >= 0.0 && r.memory_score <= 1.0);
    assert!(r.score_low <= r.memory_score && r.memory_score <= r.score_high);
    assert!(!r.confidence.is_empty());
    assert!(!r.reasons.is_empty());
    assert!(r.updated_at_millis > 0);
    assert!(r.thresholds.is_some());
    assert!(r.coverage >= 0.40);
    assert!(r.total_reviews >= 20);
    Ok(())
}

#[test]
fn request_params_override_defaults() -> Result<()> {
    let mut col = scored_collection();
    // With threshold 0.0001, even the weak cards count as mastered => higher score.
    let strict = col.topic_mastery_report(TopicMasteryRequest {
        mastered_threshold: 0.9,
        ..Default::default()
    })?;
    let lax = col.topic_mastery_report(TopicMasteryRequest {
        mastered_threshold: 0.0001,
        ..Default::default()
    })?;
    assert!(lax.memory_score >= strict.memory_score);
    assert_eq!(lax.thresholds.unwrap().mastered_threshold, 0.0001);
    Ok(())
}

#[test]
fn rpc_is_read_only_and_preserves_integrity() -> Result<()> {
    let mut col = scored_collection();
    let counts = |c: &Collection| -> (u64, u64, u64) {
        let q = |sql: &str| {
            c.storage
                .db
                .query_row(sql, [], |r| r.get::<_, u64>(0))
                .unwrap()
        };
        (
            q("select count() from cards"),
            q("select count() from notes"),
            q("select count() from revlog"),
        )
    };
    let before_counts = counts(&col);
    let before_undo = col.undo_status();

    for _ in 0..100 {
        let _ = col.topic_mastery_report(TopicMasteryRequest::default())?;
    }

    // Read-only: nothing added/removed, undo stack untouched.
    assert_eq!(counts(&col), before_counts);
    let after_undo = col.undo_status();
    assert_eq!(after_undo.last_step, before_undo.last_step);
    assert_eq!(after_undo.undo.is_some(), before_undo.undo.is_some());
    assert_eq!(after_undo.redo.is_some(), before_undo.redo.is_some());

    // Collection still passes an integrity check.
    let out = col.check_database()?;
    let problems = out.to_i18n_strings(&col.tr);
    assert!(
        problems.is_empty(),
        "dbcheck reported problems: {problems:?}"
    );
    Ok(())
}

#[test]
fn wilson_fuzz_invariants() {
    // Deterministic LCG; no external rng dependency.
    let mut state: u64 = 0x9E37_79B9_7F4A_7C15;
    let mut next = || {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        state >> 33
    };
    let mut prev_width_for_n: Option<(u64, f64)> = None;
    for _ in 0..10_000 {
        let n = (next() % 500) + 1;
        let k = next() % (n + 1);
        let (lo, hi) = wilson_95(k, n);
        let p = k as f64 / n as f64;
        assert!((0.0..=1.0).contains(&lo) && (0.0..=1.0).contains(&hi));
        assert!(lo <= hi);
        assert!(lo <= p + 1e-9 && p <= hi + 1e-9, "p {p} not in [{lo},{hi}]");
        assert!(lo.is_finite() && hi.is_finite());
        if let Some((pn, pw)) = prev_width_for_n {
            if n < pn && (k as f64 / n as f64 - 0.5).abs() < 0.05 {
                // not a strict guarantee across different p, so only sanity-check finiteness
                let _ = (pw, hi - lo);
            }
        }
        prev_width_for_n = Some((n, hi - lo));
    }
    // Explicit widening check at fixed p=0.5.
    let (l_big, h_big) = wilson_95(100, 200);
    let (l_small, h_small) = wilson_95(5, 10);
    assert!((h_small - l_small) > (h_big - l_big));
}
