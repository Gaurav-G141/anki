// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Speedrun PGRE (fork-specific): a read-only per-topic mastery query plus an
//! honest, range-bearing memory score.
//!
//! See PRD.md / SPECS.md (S2/S3). The taxonomy here mirrors
//! `speedrun/taxonomy.py`; keep the two in sync.

mod service;
#[cfg(test)]
mod tests_correctness;
#[cfg(test)]
mod tests_perf;

use std::collections::HashMap;

use anki_proto::speedrun::AppliedThresholds;
use anki_proto::speedrun::DeckMastery;
use anki_proto::speedrun::DeckMasteryRequest;
use anki_proto::speedrun::DeckMasteryResponse;
use anki_proto::speedrun::TopicMastery;
use anki_proto::speedrun::TopicMasteryRequest;
use anki_proto::speedrun::TopicMasteryResponse;
use fsrs::FSRS;
use fsrs::FSRS5_DEFAULT_DECAY;

use crate::prelude::*;
use crate::revlog::RevlogReviewKind;
use crate::search::SortMode;

// ------------------------------------------------------------------ taxonomy

/// One PGRE content area. Mirrors `speedrun/taxonomy.py`.
struct Subject {
    key: &'static str,
    name: &'static str,
    weight: f32,
}

const SUBJECTS: [Subject; 9] = [
    Subject {
        key: "classical_mechanics",
        name: "Classical Mechanics",
        weight: 0.20,
    },
    Subject {
        key: "electromagnetism",
        name: "Electromagnetism",
        weight: 0.18,
    },
    Subject {
        key: "quantum_mechanics",
        name: "Quantum Mechanics",
        weight: 0.12,
    },
    Subject {
        key: "atomic_physics",
        name: "Atomic Physics",
        weight: 0.10,
    },
    Subject {
        key: "thermo_stat_mech",
        name: "Thermodynamics & Statistical Mechanics",
        weight: 0.10,
    },
    Subject {
        key: "optics_waves",
        name: "Optics & Waves",
        weight: 0.09,
    },
    Subject {
        key: "specialized_topics",
        name: "Specialized Topics",
        weight: 0.09,
    },
    Subject {
        key: "special_relativity",
        name: "Special Relativity",
        weight: 0.06,
    },
    Subject {
        key: "lab_methods",
        name: "Laboratory Methods",
        weight: 0.06,
    },
];

/// A subject counts as "high weight" (its absence forces an abstain) at/above
/// this exam weight.
const HIGH_WEIGHT: f32 = 0.10;

const DEFAULT_MASTERED_THRESHOLD: f32 = 0.9;
const DEFAULT_REVIEW_FLOOR: u32 = 20;
const DEFAULT_COVERAGE_FLOOR: f32 = 0.40;

/// Latency outliers are capped before taking the median.
const LATENCY_CAP_MS: u32 = 60_000;

impl Subject {
    fn tag(&self) -> String {
        format!("pgre::{}", self.key)
    }
}

// ----------------------------------------------------------- accumulation

#[derive(Default)]
struct Accum {
    total_cards: u32,
    cards_with_state: u32,
    mastered: u32,
    sum_r: f64,
    sum_stability: f64,
    reviews: u32,
    latencies: Vec<u32>,
}

// ------------------------------------------------------------- scoring math

/// Wilson score interval at 95% for a binomial proportion `k/n`.
/// Returns (low, high), each clamped to [0, 1]. `n == 0` => (0, 0).
pub(crate) fn wilson_95(k: u64, n: u64) -> (f64, f64) {
    if n == 0 {
        return (0.0, 0.0);
    }
    const Z: f64 = 1.959_963_984_540_054; // 97.5th percentile of N(0,1)
    let n = n as f64;
    let p = k as f64 / n;
    let z2 = Z * Z;
    let denom = 1.0 + z2 / n;
    let center = p + z2 / (2.0 * n);
    let margin = Z * ((p * (1.0 - p) + z2 / (4.0 * n)) / n).sqrt();
    let low = ((center - margin) / denom).clamp(0.0, 1.0);
    let high = ((center + margin) / denom).clamp(0.0, 1.0);
    (low, high)
}

/// Confidence label from review volume and exam coverage.
pub(crate) fn confidence(total_reviews: u32, coverage: f32) -> &'static str {
    if coverage >= 0.8 && total_reviews >= 200 {
        "high"
    } else if coverage >= 0.5 && total_reviews >= 50 {
        "medium"
    } else {
        "low"
    }
}

/// Median of latencies in ms via O(n) selection; 0 when empty.
fn median_ms(v: &mut [u32]) -> u32 {
    if v.is_empty() {
        return 0;
    }
    let n = v.len();
    let mid = n / 2;
    v.select_nth_unstable(mid);
    let hi = v[mid];
    if n % 2 == 1 {
        hi
    } else {
        let lo = *v[..mid].iter().max().unwrap();
        ((lo as u64 + hi as u64) / 2) as u32
    }
}

// --------------------------------------------------------------- the query

impl Collection {
    /// Read-only scan over PGRE-tagged cards producing per-topic mastery plus
    /// an honest memory score (mastered fraction + Wilson 95% interval), or
    /// an abstaining response when there is not enough data.
    pub(crate) fn topic_mastery_report(
        &mut self,
        req: TopicMasteryRequest,
    ) -> Result<TopicMasteryResponse> {
        let mastered_threshold = if req.mastered_threshold > 0.0 {
            req.mastered_threshold
        } else {
            DEFAULT_MASTERED_THRESHOLD
        };
        let review_floor = if req.review_floor > 0 {
            req.review_floor
        } else {
            DEFAULT_REVIEW_FLOOR
        };
        let coverage_floor = if req.coverage_floor > 0.0 {
            req.coverage_floor
        } else {
            DEFAULT_COVERAGE_FLOOR
        };

        let timing = self.timing_today()?;
        let fsrs = FSRS::new(None)?;

        let mut accums: [Accum; 9] = std::array::from_fn(|_| Accum::default());
        let subject_tags: [String; 9] = std::array::from_fn(|i| SUBJECTS[i].tag());
        // Precomputed "pgre::<key>::" child prefixes so a parent tag matches its
        // hierarchical children (e.g. pgre::classical_mechanics::small_osc).
        let subject_child: [String; 9] = std::array::from_fn(|i| format!("{}::", subject_tags[i]));

        // One scan for all PGRE-tagged cards (+ their revlog), instead of one
        // full tag scan per subject. Each card is bucketed into its subject via
        // its note's tags, looked up by id (indexed) rather than re-scanned.
        let guard = self.search_cards_into_table("tag:pgre::*", SortMode::NoOrder)?;
        let cards = guard.col.storage.all_searched_cards()?;
        let revlog = guard
            .col
            .storage
            .get_revlog_entries_for_searched_cards_in_card_order()?;
        drop(guard);

        // Map note -> subject via one streamed pass over note tags (no temp
        // table / per-id inserts): cheaper than looking up each note id, and the
        // predicate skips the (usually many) non-PGRE notes up front.
        let mut note_subject: HashMap<NoteId, usize> = HashMap::new();
        for nt in self
            .storage
            .get_note_tags_by_predicate(|tags| tags.contains("pgre::"))?
        {
            if let Some(idx) = subject_index_for_tags(&nt.tags, &subject_tags, &subject_child) {
                note_subject.insert(nt.id, idx);
            }
        }

        // Per-card stats; also remember each card's subject for the revlog pass.
        let mut card_subject: HashMap<CardId, usize> = HashMap::with_capacity(cards.len());
        for card in &cards {
            let Some(&idx) = note_subject.get(&card.note_id) else {
                continue;
            };
            card_subject.insert(card.id, idx);
            let acc = &mut accums[idx];
            acc.total_cards += 1;
            if let Some(state) = card.memory_state {
                let secs = card.seconds_since_last_review(&timing).unwrap_or(0);
                let decay = card.decay.unwrap_or(FSRS5_DEFAULT_DECAY);
                let r = fsrs.current_retrievability_seconds(state.into(), secs, decay);
                acc.cards_with_state += 1;
                acc.sum_r += r as f64;
                acc.sum_stability += state.stability as f64;
                if r >= mastered_threshold {
                    acc.mastered += 1;
                }
            }
        }
        for e in &revlog {
            let Some(&idx) = card_subject.get(&e.cid) else {
                continue;
            };
            if matches!(
                e.review_kind,
                RevlogReviewKind::Learning
                    | RevlogReviewKind::Review
                    | RevlogReviewKind::Relearning
            ) {
                let acc = &mut accums[idx];
                acc.reviews += 1;
                if e.taken_millis > 0 {
                    acc.latencies.push(e.taken_millis.min(LATENCY_CAP_MS));
                }
            }
        }

        // Build per-topic rows + collect aggregates.
        let mut topics = Vec::with_capacity(SUBJECTS.len());
        let mut covered_weight = 0.0f32;
        let mut missing_high_weight: Vec<&str> = Vec::new();
        let mut total_reviews = 0u32;
        let mut mastered_total = 0u64;
        let mut with_state_total = 0u64;

        for (i, subject) in SUBJECTS.iter().enumerate() {
            let acc = &mut accums[i];
            total_reviews += acc.reviews;
            mastered_total += acc.mastered as u64;
            with_state_total += acc.cards_with_state as u64;
            if acc.total_cards > 0 {
                covered_weight += subject.weight;
            } else if subject.weight >= HIGH_WEIGHT {
                missing_high_weight.push(subject.name);
            }
            let mean_r = if acc.cards_with_state > 0 {
                (acc.sum_r / acc.cards_with_state as f64) as f32
            } else {
                0.0
            };
            let mean_stability = if acc.cards_with_state > 0 {
                (acc.sum_stability / acc.cards_with_state as f64) as f32
            } else {
                0.0
            };
            topics.push(TopicMastery {
                tag: subject.tag(),
                name: subject.name.to_string(),
                weight: subject.weight,
                total_cards: acc.total_cards,
                cards_with_state: acc.cards_with_state,
                mastered: acc.mastered,
                mean_retrievability: mean_r,
                mean_stability,
                median_latency_ms: median_ms(&mut acc.latencies),
            });
        }

        // Weights sum to 1.0, so covered_weight is already the weighted coverage.
        let coverage = covered_weight;

        // Give-up rule.
        let mut abstain_reasons: Vec<String> = Vec::new();
        if total_reviews < review_floor {
            abstain_reasons.push(format!(
                "only {total_reviews} graded reviews (need {review_floor})"
            ));
        }
        if coverage < coverage_floor {
            abstain_reasons.push(format!(
                "topic coverage {:.0}% (need {:.0}%)",
                coverage * 100.0,
                coverage_floor * 100.0
            ));
        }
        if !missing_high_weight.is_empty() {
            abstain_reasons.push(format!(
                "missing high-weight subject(s): {}",
                missing_high_weight.join(", ")
            ));
        }
        if with_state_total == 0 {
            abstain_reasons
                .push("no FSRS memory-state data yet (enable FSRS and review)".to_string());
        }

        let thresholds = Some(AppliedThresholds {
            mastered_threshold,
            review_floor,
            coverage_floor,
        });
        let updated_at_millis = TimestampMillis::now().0;

        if !abstain_reasons.is_empty() {
            return Ok(TopicMasteryResponse {
                abstain: true,
                abstain_reasons,
                memory_score: 0.0,
                score_low: 0.0,
                score_high: 0.0,
                coverage,
                total_reviews,
                confidence: "low".to_string(),
                reasons: Vec::new(),
                updated_at_millis,
                thresholds,
                topics,
            });
        }

        let (low, high) = wilson_95(mastered_total, with_state_total);
        let memory_score = mastered_total as f32 / with_state_total as f32;
        let reasons = weakest_reasons(&topics);

        Ok(TopicMasteryResponse {
            abstain: false,
            abstain_reasons: Vec::new(),
            memory_score,
            score_low: low as f32,
            score_high: high as f32,
            coverage,
            total_reviews,
            confidence: confidence(total_reviews, coverage).to_string(),
            reasons,
            updated_at_millis,
            thresholds,
            topics,
        })
    }

    /// Read-only per-deck mastered-card counts, for the Stats "Mastered" view.
    /// One row per deck that has at least one card. General-purpose (not
    /// PGRE-specific): "mastered" = current FSRS recall >= threshold.
    pub(crate) fn deck_mastery_report(
        &mut self,
        req: DeckMasteryRequest,
    ) -> Result<DeckMasteryResponse> {
        let mastered_threshold = if req.mastered_threshold > 0.0 {
            req.mastered_threshold
        } else {
            DEFAULT_MASTERED_THRESHOLD
        };
        let timing = self.timing_today()?;
        let fsrs = FSRS::new(None)?;

        #[derive(Default)]
        struct DeckAcc {
            total: u32,
            with_state: u32,
            mastered: u32,
            sum_r: f64,
        }
        let mut by_deck: HashMap<DeckId, DeckAcc> = HashMap::new();

        // One scan over the whole collection, grouped by the card's deck.
        {
            let guard = self.search_cards_into_table("", SortMode::NoOrder)?;
            let cards = guard.col.storage.all_searched_cards()?;
            drop(guard);
            for card in &cards {
                let acc = by_deck.entry(card.deck_id).or_default();
                acc.total += 1;
                if let Some(state) = card.memory_state {
                    let secs = card.seconds_since_last_review(&timing).unwrap_or(0);
                    let decay = card.decay.unwrap_or(FSRS5_DEFAULT_DECAY);
                    let r = fsrs.current_retrievability_seconds(state.into(), secs, decay);
                    acc.with_state += 1;
                    acc.sum_r += r as f64;
                    if r >= mastered_threshold {
                        acc.mastered += 1;
                    }
                }
            }
        }

        let mut decks = Vec::with_capacity(by_deck.len());
        for (did, acc) in by_deck {
            let deck_name = self
                .get_deck(did)?
                .map(|d| d.human_name())
                .unwrap_or_default();
            let mean_retrievability = if acc.with_state > 0 {
                (acc.sum_r / acc.with_state as f64) as f32
            } else {
                0.0
            };
            decks.push(DeckMastery {
                deck_id: did.0,
                deck_name,
                total_cards: acc.total,
                cards_with_state: acc.with_state,
                mastered: acc.mastered,
                mean_retrievability,
            });
        }
        decks.sort_by(|a, b| a.deck_name.cmp(&b.deck_name));

        Ok(DeckMasteryResponse {
            decks,
            mastered_threshold,
        })
    }
}

/// Map a note's space-separated tag string to a subject index: a tag matches a
/// subject when it equals the subject tag (`pgre::<key>`) or is one of its
/// hierarchical children (`pgre::<key>::...`). Returns the first match, if any.
/// Non-subject `pgre::*` tags (e.g. `pgre::heuristic::x`) map to nothing.
fn subject_index_for_tags(
    tags: &str,
    subject_tags: &[String; 9],
    subject_child: &[String; 9],
) -> Option<usize> {
    for tag in tags.split_whitespace() {
        for idx in 0..subject_tags.len() {
            if tag == subject_tags[idx].as_str() || tag.starts_with(subject_child[idx].as_str()) {
                return Some(idx);
            }
        }
    }
    None
}

/// Up to three covered subjects with the lowest mean retrievability, ascending.
fn weakest_reasons(topics: &[TopicMastery]) -> Vec<String> {
    let mut covered: Vec<&TopicMastery> =
        topics.iter().filter(|t| t.cards_with_state > 0).collect();
    covered.sort_by(|a, b| {
        a.mean_retrievability
            .partial_cmp(&b.mean_retrievability)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    covered
        .iter()
        .take(3)
        .map(|t| format!("{}: {:.0}% recall", t.name, t.mean_retrievability * 100.0))
        .collect()
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::card::FsrsMemoryState;
    use crate::tests::NoteAdder;

    /// Smoke test: the scan runs on a real collection, returns all 9 topic
    /// rows, counts a tagged card with memory_state, and abstains (no
    /// reviews yet).
    #[test]
    fn scan_runs_and_abstains_without_reviews() -> Result<()> {
        let mut col = Collection::new();
        let note = NoteAdder::basic(&mut col).fields(&["F", "B"]).add(&mut col);
        col.add_tags_to_notes(&[note.id], "pgre::classical_mechanics")?;
        let mut card = col.storage.all_cards_of_note(note.id)?.pop().unwrap();
        card.memory_state = Some(FsrsMemoryState {
            stability: 100.0,
            difficulty: 5.0,
        });
        card.last_review_time = Some(TimestampSecs::now());
        col.storage.update_card(&card)?;

        let resp = col.topic_mastery_report(TopicMasteryRequest::default())?;
        assert_eq!(resp.topics.len(), 9);
        let cm = resp
            .topics
            .iter()
            .find(|t| t.tag == "pgre::classical_mechanics")
            .unwrap();
        assert_eq!(cm.total_cards, 1);
        assert_eq!(cm.cards_with_state, 1);
        // No graded reviews and a high-weight subject missing => abstain.
        assert!(resp.abstain);
        assert!(!resp.abstain_reasons.is_empty());
        Ok(())
    }

    #[test]
    fn taxonomy_weights_sum_to_one() {
        let total: f32 = SUBJECTS.iter().map(|s| s.weight).sum();
        assert!((total - 1.0).abs() < 1e-6, "weights sum to {total}");
        assert_eq!(SUBJECTS.len(), 9);
    }

    #[test]
    fn wilson_reference_values() {
        // n == 0 => (0, 0)
        assert_eq!(wilson_95(0, 0), (0.0, 0.0));
        // k == n: high bound is 1.0
        let (lo, hi) = wilson_95(10, 10);
        assert!(hi >= 0.999, "hi={hi}");
        assert!(lo > 0.6 && lo < 0.8, "lo={lo}"); // ~0.722 for 10/10
                                                  // k == 0: low bound is 0.0
        let (lo, hi) = wilson_95(0, 10);
        assert_eq!(lo, 0.0);
        assert!(hi > 0.2 && hi < 0.35, "hi={hi}"); // ~0.278
                                                   // symmetric midpoint for k = n/2
        let (lo, hi) = wilson_95(50, 100);
        assert!(
            (lo + hi - 1.0).abs() < 1e-9,
            "midpoint not symmetric: {lo},{hi}"
        );
        assert!(lo > 0.40 && lo < 0.41, "lo={lo}"); // ~0.404
    }

    #[test]
    fn wilson_widens_as_n_shrinks() {
        let (l_big, h_big) = wilson_95(50, 100);
        let (l_small, h_small) = wilson_95(5, 10);
        assert!((h_small - l_small) > (h_big - l_big));
    }

    #[test]
    fn confidence_levels() {
        assert_eq!(confidence(500, 0.9), "high");
        assert_eq!(confidence(100, 0.6), "medium");
        assert_eq!(confidence(5, 0.1), "low");
        assert_eq!(confidence(500, 0.4), "low"); // low coverage downgrades
    }

    #[test]
    fn median_odd_even_and_cap_applied_by_caller() {
        let mut empty: [u32; 0] = [];
        assert_eq!(median_ms(&mut empty), 0);
        assert_eq!(median_ms(&mut [5]), 5);
        assert_eq!(median_ms(&mut [30, 10, 20]), 20); // odd
        assert_eq!(median_ms(&mut [10, 20, 30, 40]), 25); // even => (20+30)/2
    }
}
