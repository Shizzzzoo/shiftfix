import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
fs.mkdirSync("/tmp/shiftfix-operations", { recursive: true });
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } });
const p = await ctx.newPage();
const errors = [];
p.on("pageerror", (e) => errors.push(e.message));
let calls = [];
const users = [
  { id: "a", name: "Sahl Baig", email: "qa@example.invalid", role: "admin" },
  {
    id: "w",
    name: "Ravi Kumar",
    email: "worker@example.invalid",
    role: "worker",
  },
];
const machines = [
  { id: "M-012", name: "Hydraulic press", location: "Assembly · Bay 01" },
];
const cat = {
  assets: [],
  asset_types: [],
  categories: [],
  locations: [],
  zones: [],
  subzones: [],
  teams: [],
  vendors: [],
  parts: [
    {
      id: "p",
      name: "Bearing",
      sku: "BR-01",
      quantity: 5,
      minQuantity: 2,
      version: 1,
      archived: false,
      unit: "pieces",
    },
  ],
  part_types: [],
  part_locations: [],
  purchases: [],
  meters: [
    {
      id: "m",
      name: "Press temperature",
      assetId: "M-012",
      unit: "°C",
      minValue: 10,
      maxValue: 70,
      version: 1,
      archived: false,
    },
  ],
  inspection_templates: [
    {
      id: "t",
      name: "Daily safety",
      assetId: "M-012",
      questions: ["Guard secure?"],
      archived: false,
    },
  ],
  inspection_responses: [],
  plans: [],
  automations: [],
  life_tracking: [],
};
const items = [
  {
    id: "j",
    number: "SF-102",
    title: "Press belt vibration",
    machineId: "M-012",
    machineName: "Hydraulic press",
    status: "open",
    category: "Mechanical",
    priority: "high",
    assigneeId: "w",
    assigneeName: "Ravi Kumar",
    createdAt: "2026-11-14T09:00:00Z",
    version: 1,
  },
];
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
  const path = new URL(r.request().url()).pathname;
  const body = r.request().postDataJSON();
  calls.push({ path, body });
  let d =
    path === "/me"
      ? { ...users[0], onboardingComplete: true }
      : path === "/users"
        ? { items: users }
        : path === "/machines"
          ? { items: [...machines, ...cat.assets] }
          : path === "/workorders"
            ? { items }
            : path === "/catalog"
              ? { catalog: cat }
              : path === "/settings/workflow"
                ? {
                    ackMinutes: 60,
                    repairMinutes: 240,
                    verifyMinutes: 120,
                    version: 0,
                  }
                : { items: [] };
  let status = 200;
  if (body && path === "/catalog/vendors") {
    const row = { ...body, id: "v", version: 1, archived: false };
    cat.vendors.push(row);
    d = row;
  }
  if (body && path === "/catalog/assets") {
    const row = { ...body, id: "machine2", version: 1, archived: false };
    cat.assets.push(row);
    d = row;
  }
  if (body && path.endsWith("/adjust")) {
    if (body.delta < -5) {
      status = 400;
      d = { message: "Stock cannot become negative" };
    } else {
      cat.parts[0].quantity += body.delta;
      cat.parts[0].version++;
      d = { part: cat.parts[0] };
    }
  }
  if (body && path === "/catalog/inspection_responses") {
    cat.inspection_responses.push({
      ...body,
      id: "r",
      name: "Daily safety inspection",
      createdAt: new Date().toISOString(),
    });
    d = { id: "r" };
  }
  await r.fulfill({ status, json: d });
});
await p.addInitScript(() =>
  sessionStorage.setItem("shiftfix-token", "LOCAL_FIXTURE_ONLY"),
);
await p.goto("http://localhost:5174");
await p
  .getByRole("heading", { name: "Work order statistics", exact: true })
  .waitFor();
await p.screenshot({
  path: "/tmp/shiftfix-operations/overview-desktop.png",
  fullPage: true,
});
async function axe(label) {
  let a = await new AxeBuilder({ page: p })
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
  if (a.violations.length) throw Error(label + " accessibility failure");
}
await axe("Dashboard");
await p.getByRole("button", { name: "Filters", exact: true }).click();
await p.getByLabel("Asset", { exact: true }).selectOption("M-012");
await p.getByRole("button", { name: "Apply filters", exact: true }).click();
await p.getByRole("button", { name: "Clear all", exact: true }).click();
await p.getByRole("button", { name: "Vendors", exact: true }).click();
await p.getByRole("button", { name: "Add record", exact: true }).click();
await p.getByLabel("Name *", { exact: true }).fill("Precision Spares");
await p.getByLabel("Contact email").fill("spares@example.invalid");
await axe("Vendor editor");
await p.getByRole("button", { name: "Save record", exact: true }).click();
await p.getByRole("cell", { name: "Precision Spares", exact: true }).waitFor();
await p.getByRole("button", { name: "Assets", exact: true }).click();
await p.getByRole("button", { name: "Add record", exact: true }).click();
await p.getByLabel("Asset code *").fill("PRESS-02");
await p.getByLabel("Name *", { exact: true }).fill("Assembly press");
await p.getByRole("button", { name: "Save record", exact: true }).click();
await p.getByRole("cell", { name: "PRESS-02", exact: true }).waitFor();
await p.getByRole("button", { name: "Parts", exact: true }).click();
await p.getByRole("button", { name: "Adjust stock" }).click();
await p.getByLabel("Quantity change").fill("-6");
await p.getByLabel("Reason", { exact: true }).fill("Issued for repair");
await p.getByRole("button", { name: "Confirm stock change" }).click();
await p
  .getByRole("alert")
  .filter({ hasText: "Stock cannot become negative" })
  .waitFor();
await p.getByLabel("Quantity change").fill("-2");
await p.getByRole("button", { name: "Confirm stock change" }).click();
await p.getByRole("status").filter({ hasText: "Changes saved" }).waitFor();
if (cat.parts[0].quantity !== 3) throw Error("Adjustment missing");
await p
  .getByRole("button", { name: "Inspection responses", exact: true })
  .click();
await p.getByLabel("Inspection template", { exact: true }).selectOption("t");
await p.getByLabel(/^pass$/i).check();
await p.getByLabel("Observation").fill("All guards secure");
await axe("Inspection");
await p.getByRole("button", { name: "Submit inspection" }).click();
await p.getByText("Daily safety inspection ·").waitFor();
await p.getByRole("button", { name: "Workflows", exact: true }).click();
await p.getByLabel("Acknowledgment deadline (minutes)").fill("45");
await p.getByRole("button", { name: "Save deadline policy" }).click();
if (
  !calls.some(
    (x) =>
      x.path === "/settings/workflow" &&
      x.body?.ackMinutes === 45 &&
      x.body.version === 0,
  )
)
  throw Error("Workflow save incorrect");
await p.getByRole("button", { name: "Download centre", exact: true }).click();
let download = p.waitForEvent("download");
await p.getByRole("button", { name: "Work orders CSV", exact: true }).click();
let file = await download;
if (!file.suggestedFilename().endsWith(".csv"))
  throw Error("CSV export failed");
await p.setViewportSize({ width: 390, height: 844 });
await p.getByRole("button", { name: "Overview", exact: true }).click();
await p
  .getByRole("heading", { name: "Work order statistics", exact: true })
  .waitFor();
await p.screenshot({
  path: "/tmp/shiftfix-operations/overview-mobile.png",
  fullPage: true,
});
if (await p.evaluate(() => document.documentElement.scrollWidth > innerWidth))
  throw Error("Mobile overflow");
await axe("Mobile dashboard");
if (errors.length) throw Error(errors.join("\n"));
console.log(
  "PASS dashboard filters, vendor/asset creation, stock error recovery, inspection submission, versioned workflow policy, CSV download, mobile layout.",
);
await b.close();
