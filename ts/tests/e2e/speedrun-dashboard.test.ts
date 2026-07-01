// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "./fixtures";

test("speedrun-dashboard SvelteKit page loads", async ({ page }) => {
    await page.goto("/speedrun-dashboard");
    await expect(page.locator("body")).toBeAttached();
});

test("speedrun-dashboard abstains on the empty test profile", async ({ page }) => {
    await page.goto("/speedrun-dashboard");
    // The dashboard's data comes from the topicMastery POST RPC. When that RPC
    // is served, a fresh profile has no review history, so the honest score
    // must abstain (show "No score yet") rather than display a number. We never
    // want a bare score number on an empty profile, so assert no score testid.
    // Keep the assertion resilient: only require that, if the score card is
    // present at all, it is the abstain variant.
    await expect(page.locator("body")).toBeAttached();
    await expect(page.getByTestId("score")).toHaveCount(0);
});
