import { useMemo, useState } from "react";
import {
  Download,
  Filter,
  ClipboardList,
  Clock,
  CheckCircle2,
  AlertCircle,
  SkipForward,
} from "lucide-react";
import { downloadCsv } from "../csv";
type R = Record<string, any>;
const names: Record<string, string> = {
  pending_review: "Pending request",
  needs_details: "Needs details",
  open: "Open",
  in_progress: "In progress",
  awaiting_verification: "Verify repair",
  closed: "Completed",
  rejected: "Rejected",
  merged: "Merged",
  skipped: "Skipped",
};
export function OperationsDashboard({
  items,
  machines,
  catalog,
  open,
}: {
  items: R[];
  machines: R[];
  catalog: Record<string, R[]>;
  open: (id: string) => void;
}) {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const update = (k: string, v: string) => setFilters({ ...filters, [k]: v });
  const machine = (w: R) => machines.find((m) => m.id === w.machineId) || {};
  const value = (w: R, key: string) => w[key] || machine(w)[key] || "";
  const category = (w: R) => String(value(w, "categoryId") || w.category || "");
  const categoryChoices = Array.from(
    new Map(
      items.map((w) => [
        category(w),
        String(
          w.categoryName ||
            catalog.categories?.find((c) => c.id === category(w))?.name ||
            w.category ||
            category(w),
        ),
      ]),
    ).entries(),
  ).filter(([id]) => id);
  const jobs = useMemo(
    () =>
      items
        .filter((w) => !w.archived)
        .filter((w) =>
          Object.entries(filters).every(
            ([k, v]) =>
              !v ||
              (k === "status"
                ? w.status === v
                : k === "from"
                  ? new Date(w.createdAt) >= new Date(v + "T00:00")
                  : k === "to"
                    ? new Date(w.createdAt) <= new Date(v + "T23:59:59")
                    : k === "machineId"
                      ? w.machineId === v
                      : k === "category"
                        ? category(w) === v
                        : String(value(w, k)) === v),
          ),
        ),
    [items, machines, filters],
  );
  const active = jobs.filter(
      (w) => !["closed", "rejected", "merged", "skipped"].includes(w.status),
    ),
    completed = jobs.filter((w) => w.status === "closed").length,
    overdue = active.filter((w) => w.overdue).length,
    pending = active.filter(
      (w) =>
        !w.overdue &&
        w.status !== "pending_review" &&
        w.status !== "needs_details",
    ).length,
    requests = active.filter(
      (w) =>
        ["pending_review", "needs_details"].includes(w.status) && !w.overdue,
    ).length,
    skipped = jobs.filter((w) => w.status === "skipped").length,
    other = jobs.length - completed - overdue - pending - requests - skipped;
  const series = [
    { label: "Pending work", count: pending, color: "#bd470e" },
    { label: "Completed", count: completed, color: "#24745b" },
    { label: "Overdue", count: overdue, color: "#b32f40" },
    { label: "Requests", count: requests, color: "#58718c" },
    { label: "Skipped", count: skipped, color: "#9b7a39" },
    { label: "Other closed", count: other, color: "#76808c" },
  ];
  let cumulative = 0;
  const gradient = series
    .map((s) => {
      const from = cumulative;
      cumulative += jobs.length ? (s.count / jobs.length) * 100 : 0;
      return `${s.color} ${from}% ${cumulative}%`;
    })
    .join(",");
  const exportJobs = () =>
    downloadCsv("shiftfix-work-orders", jobs, [
      "number",
      "title",
      "machineId",
      "machineName",
      "priority",
      "status",
      "assigneeName",
      "createdAt",
      "deadline",
      "overdue",
    ]);
  const choices = (key: string) =>
    Array.from(
      new Map(
        items.map((w) => [
          String(value(w, key)),
          String(
            w[key.replace("Id", "Name")] ||
              machine(w)[key.replace("Id", "Name")] ||
              value(w, key),
          ),
        ]),
      ).entries(),
    ).filter(([id]) => id);
  function breakdown(key: string) {
    const groups = new Map<
      string,
      { name: string; open: number; closed: number; overdue: number }
    >();
    for (const w of jobs) {
      const id = String(value(w, key) || "unassigned");
      const fallback =
        key === "assigneeId"
          ? "Unassigned"
          : key === "machineId"
            ? w.machineName
            : "Not set";
      const ref = catalog[
        key === "locationId" ? "locations" : key === "teamId" ? "teams" : ""
      ]?.find((x) => x.id === id);
      const name = String(
        ref?.name ||
          w[key.replace("Id", "Name")] ||
          machine(w)[key.replace("Id", "Name")] ||
          fallback ||
          id,
      );
      const g = groups.get(id) || { name, open: 0, closed: 0, overdue: 0 };
      if (w.status === "closed") g.closed++;
      else if (!["rejected", "merged", "skipped"].includes(w.status)) {
        if (w.overdue) g.overdue++;
        else g.open++;
      }
      groups.set(id, g);
    }
    return Array.from(groups.values())
      .sort(
        (a, b) =>
          b.open + b.closed + b.overdue - (a.open + a.closed + a.overdue),
      )
      .slice(0, 10);
  }
  const select = (key: string, label: string, opts: [string, string][]) => (
    <label className="dashboard-filter" key={key}>
      <span>{label}</span>
      <select
        aria-label={label}
        value={filters[key] || ""}
        onChange={(e) => update(key, e.target.value)}
      >
        <option value="">All</option>
        {opts.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <div className="operations-dashboard">
      <div className="dashboard-filterbar">
        <Filter size={17} aria-hidden="true" />
        <strong>Filter dashboard</strong>
        {select("status", "WO status", Object.entries(names))}
        <label className="dashboard-filter">
          <span>From date</span>
          <input
            type="date"
            value={filters.from || ""}
            onChange={(e) => update("from", e.target.value)}
          />
        </label>
        <label className="dashboard-filter">
          <span>To date</span>
          <input
            type="date"
            min={filters.from}
            value={filters.to || ""}
            onChange={(e) => update("to", e.target.value)}
          />
        </label>
        {select(
          "machineId",
          "Asset",
          machines.map((m) => [m.id, (m.code || m.id) + " · " + m.name]),
        )}
        {select("typeId", "Asset type", choices("typeId"))}
        {select("category", "Category", categoryChoices)}
        {select("teamId", "Team", choices("teamId"))}
        {select("assigneeId", "User", choices("assigneeId"))}
        {select(
          "locationId",
          "Location",
          (catalog.locations || []).map((x) => [x.id, x.name]),
        )}
        {select(
          "zoneId",
          "Zone",
          (catalog.zones || []).map((x) => [x.id, x.name]),
        )}
        {select(
          "subzoneId",
          "Sub-zone",
          (catalog.subzones || []).map((x) => [x.id, x.name]),
        )}
        <button onClick={() => setFilters({})}>Reset filters</button>
      </div>
      <div className="metric-cards">
        {[
          [Clock, "Pending work", pending],
          [CheckCircle2, "Completed", completed],
          [SkipForward, "Skipped", skipped],
          [AlertCircle, "Overdue", overdue],
          [ClipboardList, "Pending requests", requests],
        ].map(([I, label, n]: any) => (
          <section className="panel metric" key={label}>
            <I aria-hidden="true" size={22} />
            <strong>{n.toLocaleString()}</strong>
            <span>{label}</span>
          </section>
        ))}
      </div>
      <div className="analytics-grid">
        <section className="panel donut-panel">
          <h2>Work order statistics</h2>
          <div
            className="donut"
            style={{
              background: jobs.length
                ? `conic-gradient(${gradient})`
                : "#e9edf1",
            }}
            role="img"
            aria-label={`${jobs.length} work orders. ${series.map((s) => `${s.label}: ${s.count}`).join(". ")}`}
          >
            <div>
              <strong>
                {jobs.length ? Math.round((completed / jobs.length) * 100) : 0}%
              </strong>
              <small>completed</small>
            </div>
          </div>
          <ul className="chart-legend">
            {series.map((s) => (
              <li key={s.label}>
                <i style={{ background: s.color }} />
                {s.label}
                <strong>{s.count}</strong>
              </li>
            ))}
          </ul>
          <div className="chart-total">
            <strong>{jobs.length.toLocaleString()}</strong>
            <span>Total matching records</span>
          </div>
        </section>
        <Breakdown title="Work orders by user" data={breakdown("assigneeId")} />
        <Breakdown title="Work orders by asset" data={breakdown("machineId")} />
        <Breakdown
          title="Work orders by location"
          data={breakdown("locationId")}
        />
      </div>
      <section className="panel dashboard-orders">
        <div className="section-heading">
          <div>
            <h2>Recent maintenance activity</h2>
            <p>
              Live records within your access, matching the selected filters.
            </p>
          </div>
          <button onClick={exportJobs}>
            <Download size={16} />
            Export CSV
          </button>
        </div>
        {!jobs.length ? (
          <div className="module-empty">
            <ClipboardList size={30} />
            <h3>No matching work yet.</h3>
            <p>
              Report a fault or clear your filters to see maintenance activity.
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  {["Work order", "Asset", "Owner", "Status", "Created"].map(
                    (h) => (
                      <th scope="col" key={h}>
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 12).map((w) => (
                  <tr key={w.id}>
                    <td>
                      <button
                        className="request-button"
                        onClick={() => open(w.id)}
                      >
                        {w.title}
                      </button>
                      <small>{w.number}</small>
                    </td>
                    <td>{w.machineName}</td>
                    <td>{w.assigneeName || "Unassigned"}</td>
                    <td>
                      <span
                        className={
                          "badge " + (w.overdue ? "critical" : "status")
                        }
                      >
                        {w.overdue ? "Overdue" : names[w.status] || w.status}
                      </span>
                    </td>
                    <td>{new Date(w.createdAt).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
function Breakdown({
  title,
  data,
}: {
  title: string;
  data: { name: string; open: number; closed: number; overdue: number }[];
}) {
  const max = Math.max(1, ...data.map((d) => d.open + d.closed + d.overdue));
  return (
    <section className="panel breakdown">
      <div className="section-heading">
        <h2>{title}</h2>
        <button
          aria-label={`Export ${title}`}
          onClick={() =>
            downloadCsv(title.toLowerCase().replaceAll(" ", "-"), data, [
              "name",
              "open",
              "closed",
              "overdue",
            ])
          }
        >
          <Download size={15} />
          Export
        </button>
      </div>
      <p>Compare workload using current, authorized records.</p>
      <div className="bar-legend">
        <span>Open</span>
        <span>Completed</span>
        <span>Overdue</span>
      </div>
      {!data.length ? (
        <div className="module-empty">
          <p>No matching records to chart.</p>
        </div>
      ) : (
        <ul className="bar-chart">
          {data.map((d) => (
            <li key={d.name}>
              <div>
                <strong>{d.name}</strong>
                <span>{d.open + d.closed + d.overdue}</span>
              </div>
              <div
                className="stacked-bar"
                role="img"
                aria-label={`${d.name}: ${d.open} open, ${d.closed} completed, ${d.overdue} overdue`}
              >
                <i style={{ width: (d.open / max) * 100 + "%" }} />
                <i style={{ width: (d.closed / max) * 100 + "%" }} />
                <i style={{ width: (d.overdue / max) * 100 + "%" }} />
              </div>
              <small>
                {d.open} open · {d.closed} completed · {d.overdue} overdue
              </small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
