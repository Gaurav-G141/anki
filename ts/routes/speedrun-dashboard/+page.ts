// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import { topicMastery } from "@generated/backend";

import type { PageLoad } from "./$types";

// Zero fields tell the backend to fall back to its documented defaults
// (see proto/anki/speedrun.proto TopicMasteryRequest).
export const load = (async () => ({
    resp: await topicMastery({ masteredThreshold: 0, reviewFloor: 0, coverageFloor: 0 }),
})) satisfies PageLoad;
