// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

use crate::collection::Collection;
use crate::error;

impl crate::services::SpeedrunService for Collection {
    fn topic_mastery(
        &mut self,
        input: anki_proto::speedrun::TopicMasteryRequest,
    ) -> error::Result<anki_proto::speedrun::TopicMasteryResponse> {
        self.topic_mastery_report(input)
    }

    fn deck_mastery(
        &mut self,
        input: anki_proto::speedrun::DeckMasteryRequest,
    ) -> error::Result<anki_proto::speedrun::DeckMasteryResponse> {
        self.deck_mastery_report(input)
    }
}
