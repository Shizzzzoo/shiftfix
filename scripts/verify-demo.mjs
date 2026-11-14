// Local populated-state checks. Build .deploy/demo-fixture.json first; Vite on5174.
import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import { MODULES } from "../src/operations-schema.ts";
const data = JSON.parse(fs.readFileSync(".deploy/demo-fixture.json", "utf8"));
const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await ctx.newPage();
let errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const owner = {
  id: "qa",
  name: "Demo reviewer",
  email: "qa@example.invalid",
  role: "admin",
};
await page.route("**/config.json", (r) =>
  r.fulfill({
    json: {
      apiUrl: "https://qa.shiftfix.invalid",
      region: "ap-south-1",
      clientId: "qa",
      userPoolId: "qa",
    },
  }),
);
await page.route("https://qa.shiftfix.invalid/**", async (r) => {
  let path = new URL(r.request().url()).pathname;
  let response =
    path === "/me"
      ? { ...owner, onboardingComplete: true, demoDataset: data.manifest }
      : path === "/machines"
        ? { items: data.catalog.assets.filter((a) => !a.archived) }
        : path === "/users"
          ? { items: [owner, ...data.users] }
          : path === "/workorders"
            ? { items: data.items }
            : path === "/catalog"
              ? { catalog: data.catalog }
              : path === "/settings/workflow"
                ? {
                    ackMinutes: 60,
                    repairMinutes: 240,
                    verifyMinutes: 120,
                    version: 0,
                  }
                : { items: [] };
  if (path.startsWith("/workorders/")) {
    const job = data.items.find((w) => w.id === path.split("/")[2]);
    response = {
      ...job,
      attachments: job.attachments.map((a) => ({
        ...a,
        url: "/assets/factory-floor.jpg",
      })),
      activity: data.rows.filter(
        (x) => x.PK === job.PK && x.SK.startsWith("EVENT#"),
      ),
    };
  }
  if (path.endsWith("/history")) {
    let id = path.split("/")[3];
    response = {
      items: data.rows.filter(
        (x) => x.PK === "CAT#parts" && x.SK.startsWith("AUDIT#" + id + "#"),
      ),
    };
  }
  if (path.endsWith("/readings")) {
    let id = path.split("/")[3];
    response = { items: data.rows.filter((x) => x.PK === "METER#" + id) };
  }
  await r.fulfill({ json: response });
});
await page.addInitScript(() =>
  sessionStorage.setItem("shiftfix-token", "LOCAL_FIXTURE_ONLY"),
);
await page.goto("http://localhost:5174");
await page
  .getByRole("heading", { name: "Work order statistics", exact: true })
  .waitFor();
await page
  .getByRole("region", { name: "Demo data notice" })
  .waitFor()
  .catch(() => page.locator(".demo-disclosure").waitFor());
const screenshotDir = "/tmp/shiftfix-populated";
fs.mkdirSync(screenshotDir, { recursive: true });
await page.screenshot({
  path: screenshotDir + "/overview.png",
  fullPage: true,
});
async function axe(label) {
  const a = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  console.log(
    label,
    JSON.stringify(
      a.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => ({
          html: n.html,
          summary: n.failureSummary,
        })),
      })),
    ),
  );
  if (a.violations.length) throw Error(label + " accessibility failures");
}
await axe("Populated overview");
for (const title of Object.keys(MODULES)) {
  await page.getByRole("button", { name: title, exact: true }).click();
  await page.locator("h1").filter({ hasText: title }).waitFor();
  await page.locator(".data-table tbody tr").first().waitFor();
  if ((await page.locator(".data-table tbody tr").count()) === 0)
    throw Error(title + " empty");
  console.log("Populated", title);
}
for (const title of [
  "Upcoming",
  "Asset monitoring",
  "Requests",
  "Workflows",
  "Inspection responses",
  "Users",
  "Download centre",
  "Billing & usage",
  "Bulk archive",
  "Archive",
]) {
  await page.getByRole("button", { name: title, exact: true }).click();
  await page.locator("h1").filter({ hasText: title }).waitFor();
  if (title === "Upcoming") {
    await page.getByText("Paused", { exact: false }).first().waitFor();
    await page.locator(".upcoming-row").first().waitFor();
    if ((await page.locator(".upcoming-row").count()) !== 6)
      throw Error("Paused upcoming plans missing");
    await axe("Upcoming plans");
  }
  if (title === "Users") {
    await page
      .getByText("Demo person · no login or access permissions")
      .first()
      .waitFor();
    if (await page.locator(".role-select").count())
      throw Error("Demo people expose role mutation");
    await axe("Demo people");
  }
  if (title === "Inspection responses") {
    await page.locator(".inspection-history").first().waitFor();
    if ((await page.locator(".inspection-history").count()) !== 28)
      throw Error("Missing inspections");
  }
  console.log("Populated", title);
}
await page.getByRole("button", { name: "Parts", exact: true }).click();
await page
  .getByRole("button", { name: "History", exact: true })
  .first()
  .click();
await page.locator(".history-entry").first().waitFor();
await page.getByRole("button", { name: "Meters", exact: true }).click();
await page
  .getByRole("button", { name: "Record reading", exact: true })
  .first()
  .click();
await page.locator(".history-entry").first().waitFor();
await page.getByRole("button", { name: "Work orders", exact: true }).click();
await page.locator(".list .request-button").first().click();
await page
  .getByText("Simulated report recorded", { exact: false })
  .first()
  .waitFor();
await page.getByRole("button", { name: "Overview", exact: true }).click();
await page.setViewportSize({ width: 390, height: 844 });
await page
  .getByRole("heading", { name: "Work order statistics", exact: true })
  .waitFor();
await page.screenshot({ path: screenshotDir + "/mobile.png", fullPage: true });
if (
  await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
)
  throw Error("Mobile overflow");
await axe("Populated mobile");
if (errors.length) throw Error(errors.join("\n"));
console.log(
  "PASS every catalog, requests/history, paused plans, read-only demo people, stock/meter histories, activity, desktop/mobile accessibility.",
);
await browser.close();
