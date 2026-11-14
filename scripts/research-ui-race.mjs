// Isolated local fixture only. Demonstrates out-of-order detail requests.
import { chromium } from "@playwright/test";
import fs from "node:fs";
const fixture = JSON.parse(
  fs.readFileSync(".deploy/demo-fixture.json", "utf8"),
);
const jobs = fixture.items.slice(1, 3);
const b = await chromium.launch();
const c = await b.newContext();
const p = await c.newPage();
let requested = [];
await p.route("**/config.json", (r) =>
  r.fulfill({
    json: {
      apiUrl: "https://qa.shiftfix.invalid",
      region: "ap-south-1",
      clientId: "qa",
      userPoolId: "qa",
    },
  }),
);
await p.route("https://qa.shiftfix.invalid/**", async (r) => {
  let path = new URL(r.request().url()).pathname;
  let body =
    path === "/me"
      ? { id: "qa", name: "QA", role: "admin", onboardingComplete: true }
      : path === "/workorders"
        ? { items: jobs }
        : path === "/machines"
          ? { items: fixture.catalog.assets }
          : path === "/users"
            ? { items: [] }
            : path === "/catalog"
              ? { catalog: fixture.catalog }
              : { items: [] };
  if (path.startsWith("/workorders/")) {
    const j = jobs.find((j) => j.id === path.split("/")[2]);
    requested.push(j.id);
    await new Promise((resolve) =>
      setTimeout(resolve, j.id === jobs[0].id ? 800 : 25),
    );
    body = { ...j, activity: [] };
  }
  await r.fulfill({ json: body });
});
await p.addInitScript(() =>
  sessionStorage.setItem("shiftfix-token", "LOCAL_FIXTURE_ONLY"),
);
await p.goto("http://localhost:5174");
await p.getByRole("button", { name: "Work orders", exact: true }).click();
await p.locator(".list .request-button").first().click();
await p.locator(".list .request-button").nth(1).click();
await p.waitForTimeout(1200);
const shown = await p.locator(".detail-title h2").textContent();
const result = {
  mode: "local fixture only",
  requested,
  lastRequested: jobs[1].title,
  displayed: shown,
  staleDetailWon: shown === jobs[0].title,
};
fs.writeFileSync(
  "docs/research/2026-11-14-ui-race-probe.json",
  JSON.stringify(result, null, 2),
);
console.log(result);
await b.close();
