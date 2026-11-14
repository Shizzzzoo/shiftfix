export type Field = {
  key: string;
  label: string;
  type?:
    | "text"
    | "number"
    | "textarea"
    | "select"
    | "ref"
    | "multi"
    | "check"
    | "datetime-local"
    | "questions";
  ref?: string;
  required?: boolean;
  options?: string[];
  min?: number;
  step?: string;
  hint?: string;
};
export type Module = {
  kind: string;
  description: string;
  fields: Field[];
  columns: string[];
};
const name: Field = { key: "name", label: "Name", required: true };
const description: Field = {
  key: "description",
  label: "Description",
  type: "textarea",
};
const ref = (
  key: string,
  label: string,
  kind: string,
  required = false,
): Field => ({ key, label, type: "ref", ref: kind, required });
export const MODULES: Record<string, Module> = {
  Assets: {
    kind: "assets",
    description: "Your machine registry, ownership and location in one place.",
    fields: [
      { key: "code", label: "Asset code", required: true },
      name,
      ref("typeId", "Asset type", "asset_types"),
      ref("categoryId", "Category", "categories"),
      ref("locationId", "Location", "locations"),
      ref("zoneId", "Zone", "zones"),
      ref("subzoneId", "Sub-zone", "subzones"),
      ref("teamId", "Responsible team", "teams"),
      { key: "serial", label: "Serial number" },
      description,
    ],
    columns: ["code", "name", "typeId", "locationId", "teamId"],
  },
  "Asset types": {
    kind: "asset_types",
    description: "Group equipment by its engineering type.",
    fields: [name, description],
    columns: ["name", "description"],
  },
  Categories: {
    kind: "categories",
    description: "A shared vocabulary for maintenance and equipment.",
    fields: [name, description],
    columns: ["name", "description"],
  },
  Locations: {
    kind: "locations",
    description: "Define the buildings and areas within Plant 01.",
    fields: [name, description],
    columns: ["name", "description"],
  },
  Zones: {
    kind: "zones",
    description: "Organize work areas within each location.",
    fields: [
      name,
      ref("locationId", "Parent location", "locations", true),
      description,
    ],
    columns: ["name", "locationId", "description"],
  },
  "Sub-zones": {
    kind: "subzones",
    description: "Identify the specific bays or cells inside a zone.",
    fields: [name, ref("zoneId", "Parent zone", "zones", true), description],
    columns: ["name", "zoneId", "description"],
  },
  Teams: {
    kind: "teams",
    description:
      "Organize people for ownership and reporting. Team membership does not grant access roles.",
    fields: [
      name,
      { key: "memberIds", label: "Team members", type: "multi", ref: "users" },
      description,
    ],
    columns: ["name", "memberIds", "description"],
  },
  Vendors: {
    kind: "vendors",
    description: "Keep supplier contacts ready for your maintenance team.",
    fields: [
      name,
      { key: "email", label: "Contact email" },
      { key: "phone", label: "Contact phone" },
      description,
    ],
    columns: ["name", "email", "phone"],
  },
  "Part types": {
    kind: "part_types",
    description: "Organize consumables, spares and replacement components.",
    fields: [name, description],
    columns: ["name", "description"],
  },
  "Part locations": {
    kind: "part_locations",
    description: "Track where spare parts are stored.",
    fields: [
      name,
      ref("locationId", "Factory location", "locations"),
      description,
    ],
    columns: ["name", "locationId", "description"],
  },
  Parts: {
    kind: "parts",
    description: "Track stock and record every issue or replenishment.",
    fields: [
      name,
      { key: "sku", label: "SKU", required: true },
      ref("typeId", "Part type", "part_types"),
      ref("locationId", "Storage location", "part_locations"),
      ref("vendorId", "Preferred vendor", "vendors"),
      { key: "quantity", label: "Opening quantity", type: "number", min: 0 },
      { key: "minQuantity", label: "Reorder level", type: "number", min: 0 },
      { key: "unit", label: "Unit", hint: "e.g. pieces, litres, sets" },
    ],
    columns: ["sku", "name", "quantity", "minQuantity", "locationId"],
  },
  "Purchase management": {
    kind: "purchases",
    description:
      "Internal purchase records and one-time stock receiving. No order or payment is sent to a supplier.",
    fields: [
      name,
      ref("partId", "Part", "parts", true),
      ref("vendorId", "Vendor", "vendors", true),
      {
        key: "quantity",
        label: "Quantity",
        type: "number",
        min: 1,
        required: true,
      },
      {
        key: "unitCost",
        label: "Unit cost",
        type: "number",
        min: 0,
        step: "0.01",
      },
      {
        key: "currency",
        label: "Currency",
        type: "select",
        options: ["INR", "USD", "EUR"],
      },
    ],
    columns: ["name", "partId", "vendorId", "quantity", "status"],
  },
  Meters: {
    kind: "meters",
    description:
      "Record manual equipment readings and review threshold breaches. No live sensors are connected.",
    fields: [
      name,
      ref("assetId", "Asset", "assets", true),
      { key: "unit", label: "Unit", required: true },
      {
        key: "minValue",
        label: "Minimum threshold",
        type: "number",
        step: "any",
      },
      {
        key: "maxValue",
        label: "Maximum threshold",
        type: "number",
        step: "any",
      },
    ],
    columns: ["name", "assetId", "unit", "latestReading"],
  },
  "Inspection templates": {
    kind: "inspection_templates",
    description: "Create repeatable checklists for your maintenance rounds.",
    fields: [
      name,
      ref("assetId", "Asset (optional)", "assets"),
      {
        key: "questions",
        label: "Checklist questions",
        type: "questions",
        required: true,
        hint: "One inspection item per line. Maximum 20 items.",
      },
    ],
    columns: ["name", "assetId", "questions"],
  },
  Recurrence: {
    kind: "plans",
    description:
      "Preventive maintenance runs every N days. Due plans generate requests for manager review; checked hourly.",
    fields: [
      name,
      ref("assetId", "Asset", "assets", true),
      {
        key: "description",
        label: "Work instructions",
        type: "textarea",
        required: true,
      },
      {
        key: "intervalDays",
        label: "Repeat every (days)",
        type: "number",
        min: 1,
        required: true,
      },
      {
        key: "nextRun",
        label: "Next scheduled run",
        type: "datetime-local",
        required: true,
      },
      {
        key: "priority",
        label: "Priority",
        type: "select",
        options: ["low", "medium", "high", "critical"],
      },
      { key: "enabled", label: "Schedule enabled", type: "check" },
    ],
    columns: ["name", "assetId", "intervalDays", "nextRun", "enabled"],
  },
  "Life tracking": {
    kind: "life_tracking",
    description:
      "Track installed parts against a calendar-based expected service life. This is a planning estimate, not predictive sensor data.",
    fields: [
      name,
      ref("partId", "Part", "parts", true),
      ref("assetId", "Asset", "assets", true),
      {
        key: "installedOn",
        label: "Installed on (YYYY-MM-DD)",
        required: true,
      },
      {
        key: "expectedLifeDays",
        label: "Expected life (days)",
        type: "number",
        min: 1,
        required: true,
      },
      { key: "notes", label: "Installation notes", type: "textarea" },
    ],
    columns: [
      "name",
      "partId",
      "assetId",
      "installedOn",
      "expectedLifeDays",
      "serviceDueOn",
      "remainingDays",
    ],
  },
  Automations: {
    kind: "automations",
    description:
      "Create a fault report when a manual meter reading falls outside its thresholds. Review remains with a Manager.",
    fields: [
      name,
      ref("meterId", "Meter", "meters", true),
      { key: "enabled", label: "Automation enabled", type: "check" },
    ],
    columns: ["name", "meterId", "enabled"],
  },
};
export const OPERATIONS_PAGES = [
  "Overview",
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
  ...Object.keys(MODULES),
];
