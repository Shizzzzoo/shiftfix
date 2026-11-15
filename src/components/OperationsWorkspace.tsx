import { useState, useEffect, useRef } from "react";
import {
  Plus,
  Search,
  Download,
  Archive,
  RotateCcw,
  ClipboardList,
  RefreshCw,
  Factory,
  Clock,
  Settings,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { MODULES, type Field } from "../operations-schema";
import { downloadCsv, parseCsv } from "../csv";
import { OperationsDashboard } from "./OperationsDashboard";
type R = Record<string, any>;
type Props = {
  page: string;
  me: R;
  initialCatalog?: Record<string, R[]>;
  items: R[];
  machines: R[];
  users: R[];
  api: (path: string, body?: R, key?: string) => Promise<any>;
  open: (id: string) => void;
  refresh: () => Promise<void>;
};
const human = (s: string) =>
  s.replaceAll("_", " ").replace(/([a-z])([A-Z])/g, "$1 $2");
const localDate = (iso: string) => {
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? ""
    : new Date(d.getTime() - d.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
};
export function OperationsWorkspace({
  page,
  initialCatalog,
  me,
  items,
  machines,
  users,
  api,
  open,
  refresh,
}: Props) {
  const [catalog, setCatalog] = useState<Record<string, R[]>>(
      initialCatalog || {},
    ),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(!initialCatalog),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [search, setSearch] = useState(""),
    [editor, setEditor] = useState<R | null>(null),
    [showArchived, setShowArchived] = useState(false),
    [action, setAction] = useState<R | null>(null),
    [values, setValues] = useState<R>({}),
    [history, setHistory] = useState<R[]>([]),
    [workflow, setWorkflow] = useState<R | null>(null),
    [templateId, setTemplateId] = useState(""),
    [answers, setAnswers] = useState<R[]>([]),
    [preview, setPreview] = useState<R[]>([]),
    [selected, setSelected] = useState<string[]>([]);
  const formRef = useRef<HTMLDivElement>(null);
  const readId = useRef(0);
  const manages = ["admin", "manager"].includes(me.role);
  const module = MODULES[page];
  const kind = module?.kind;
  async function load() {
    const request = ++readId.current;
    setLoading(true);
    try {
      const d = await api("/catalog");
      if (request !== readId.current) return;
      setCatalog(d.catalog || {});
      if (page === "Workflows") setWorkflow(await api("/settings/workflow"));
    } catch (e) {
      if (request === readId.current) {
        setError((e as Error).message);
        setCatalog({});
      }
    } finally {
      if (request === readId.current) setLoading(false);
    }
  }
  useEffect(() => {
    setEditor(null);
    setAction(null);
    setValues({});
    setSearch("");
    setShowArchived(false);
    setMessage("");
    setError("");
    setPreview([]);
    setSelected([]);
    void load();
    return () => {
      readId.current++;
    };
  }, [page]);
  useEffect(() => {
    if (editor || action)
      formRef.current?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
        block: "start",
      });
  }, [editor, action]);
  const options = (ref?: string) =>
    ref === "assets"
      ? machines
      : ref === "users"
        ? users
        : catalog[ref || ""] || [];
  const display = (field: string, v: any) => {
    if (v === undefined || v === null || v === "") return "—";
    if (typeof v === "boolean") return v ? "Enabled" : "Paused";
    if (Array.isArray(v))
      return field === "questions"
        ? `${v.length} checklist items`
        : v
            .map((x) =>
              typeof x === "string"
                ? users.find((u) => u.id === x)?.name || x
                : x.answer || x.name || JSON.stringify(x),
            )
            .join(", ");
    if (field.endsWith("Id")) {
      const f = module?.fields.find((f) => f.key === field);
      const pool = f ? options(f.ref) : [];
      return (
        pool.find((x) => x.id === v)?.name ||
        machines.find((x) => x.id === v)?.name ||
        v
      );
    }
    return String(v);
  };
  const showMessage = (s: string) => {
    setMessage(s);
    setError("");
  };
  async function mutate(path: string, data: R, key?: string) {
    setBusy(true);
    setError("");
    try {
      const out = await api(path, data, key);
      await Promise.all([load(), refresh()]);
      setEditor(null);
      setAction(null);
      setValues({});
      showMessage(
        out.workOrderId
          ? "Reading saved. A threshold breach created a fault request for manager review."
          : "Changes saved.",
      );
      return out;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  function edit(row?: R) {
    const initial: R = {};
    for (const f of module.fields) {
      let v = row?.[f.key];
      if (f.type === "questions") v = Array.isArray(v) ? v.join("\n") : "";
      else if (f.type === "datetime-local") v = v ? localDate(v) : "";
      else if (f.type === "check") v = v ?? true;
      else if (f.type === "multi") v = v || [];
      else
        v =
          v ??
          (f.type === "select"
            ? f.options?.[0]
            : f.type === "number"
              ? ""
              : "");
      initial[f.key] = v;
    }
    setEditor(row || {});
    setValues(initial);
    setAction(null);
    setError("");
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    const data: R = {};
    try {
      for (const f of module.fields) {
        if (kind === "parts" && editor?.id && f.key === "quantity") continue;
        const v = values[f.key];
        if (f.type === "number") {
          if (v === "" && ["minValue", "maxValue", "unitCost"].includes(f.key))
            data[f.key] = "";
          else if (v !== "" && v !== undefined) {
            const n = Number(v);
            if (!Number.isFinite(n)) throw Error(`${f.label} must be a number`);
            data[f.key] = n;
          }
        } else if (f.type === "datetime-local") {
          if (v) data[f.key] = new Date(v).toISOString();
        } else if (f.type === "questions")
          data[f.key] = String(v || "")
            .split("\n")
            .map((x) => x.trim())
            .filter(Boolean);
        else if (f.type === "multi" || f.type === "check") data[f.key] = v;
        else if (v !== undefined) data[f.key] = String(v).trim();
      }
      if (editor?.id) data.version = editor.version;
      await mutate(
        "/catalog/" + kind + (editor?.id ? "/" + editor.id : ""),
        data,
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const fieldControl = (f: Field) => {
    const attrs = {
      id: "catalog-" + f.key,
      required: f.required,
      readOnly: kind === "assets" && !!editor?.id && f.key === "code",
      value: values[f.key] ?? "",
      onChange: (e: any) => setValues({ ...values, [f.key]: e.target.value }),
    };
    if (f.type === "check")
      return (
        <label className="check-field">
          <input
            type="checkbox"
            checked={!!values[f.key]}
            onChange={(e) =>
              setValues({ ...values, [f.key]: e.target.checked })
            }
          />
          {f.label}
        </label>
      );
    if (f.type === "multi")
      return (
        <fieldset className="catalog-multi">
          <legend>{f.label}</legend>
          {options(f.ref).map((o) => (
            <label key={o.id}>
              <input
                type="checkbox"
                checked={(values[f.key] || []).includes(o.id)}
                onChange={(e) =>
                  setValues({
                    ...values,
                    [f.key]: e.target.checked
                      ? [...(values[f.key] || []), o.id]
                      : (values[f.key] || []).filter((x: string) => x !== o.id),
                  })
                }
              />
              {o.name}
            </label>
          ))}
        </fieldset>
      );
    return (
      <div className="catalog-field">
        <label htmlFor={attrs.id}>
          {f.label}
          {f.required ? " *" : ""}
        </label>
        {f.type === "textarea" || f.type === "questions" ? (
          <textarea
            {...attrs}
            rows={f.type === "questions" ? 5 : 3}
            maxLength={4000}
          />
        ) : f.type === "ref" || f.type === "select" ? (
          <select {...attrs}>
            <option value="">Select…</option>
            {(f.type === "ref"
              ? options(f.ref)
                  .filter((o) => !o.archived)
                  .map((o) => ({
                    value: o.id,
                    label: (o.code ? o.code + " · " : "") + o.name,
                  }))
              : f.options?.map((o) => ({ value: o, label: human(o) }))
            )?.map((o) => (
              <option value={o.value} key={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            {...attrs}
            type={
              f.type === "number"
                ? "number"
                : f.type === "datetime-local"
                  ? "datetime-local"
                  : f.key === "email"
                    ? "email"
                    : "text"
            }
            min={f.min}
            step={f.step || "1"}
            maxLength={f.key === "name" ? 150 : 1000}
          />
        )}
        {f.hint && <small>{f.hint}</small>}
      </div>
    );
  };
  async function actionSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!action) return;
    let path = `/catalog/${action.kind}/${action.row.id}`;
    let data: R = {};
    if (action.type === "archive") {
      path += "/archive";
      data = { version: action.row.version, archived: !action.row.archived };
    } else if (action.type === "adjust") {
      path += "/adjust";
      data = {
        version: action.row.version,
        delta: Number(values.delta),
        reason: values.reason,
      };
    } else if (action.type === "receive") {
      path += "/receive";
      data = { version: action.row.version };
    } else if (action.type === "reading") {
      path += "/readings";
      data = { value: Number(values.value), note: values.note || "" };
    }
    await mutate(path, data, action.key);
  }
  async function inspectHistory(row: R, type: string) {
    setAction({ type, row, kind, key: crypto.randomUUID() });
    setValues({});
    setHistory([]);
    if (type === "history" || type === "reading")
      try {
        const r = await api(
          `/catalog/${kind}/${row.id}/${kind === "parts" ? "history" : "readings"}`,
        );
        setHistory(r.items || []);
      } catch (e) {
        setError((e as Error).message);
      }
  }
  const rowActions = (row: R) => {
    return (
      <div className="row-actions">
        {manages &&
          !row.archived &&
          !(kind === "purchases" && row.status === "received") && (
            <button onClick={() => edit(row)}>Edit</button>
          )}
        {kind === "parts" && !row.archived && (
          <>
            <button onClick={() => inspectHistory(row, "history")}>
              History
            </button>
            {manages && (
              <button onClick={() => inspectHistory(row, "adjust")}>
                Adjust stock
              </button>
            )}
          </>
        )}
        {kind === "meters" && !row.archived && me.role !== "reporter" && (
          <button onClick={() => inspectHistory(row, "reading")}>
            Record reading
          </button>
        )}
        {kind === "purchases" &&
          row.status !== "received" &&
          !row.archived &&
          manages && (
            <button onClick={() => inspectHistory(row, "receive")}>
              Receive
            </button>
          )}
        {manages && (
          <button
            aria-label={`${row.archived ? "Restore" : "Archive"} ${row.name}`}
            onClick={() => {
              setAction({ type: "archive", kind, row });
              setEditor(null);
            }}
          >
            {row.archived ? <RotateCcw size={15} /> : <Archive size={15} />}
          </button>
        )}
      </div>
    );
  };
  let rows = (catalog[kind] || [])
    .map((r) =>
      kind === "life_tracking"
        ? {
            ...r,
            serviceDueOn: new Date(
              new Date(r.installedOn + "T00:00:00Z").getTime() +
                Number(r.expectedLifeDays) * 86400000,
            )
              .toISOString()
              .slice(0, 10),
            remainingDays: Math.ceil(
              (new Date(r.installedOn + "T00:00:00Z").getTime() +
                Number(r.expectedLifeDays) * 86400000 -
                Date.now()) /
                86400000,
            ),
          }
        : r,
    )
    .filter((r) => !!r.archived === showArchived)
    .filter(
      (r) =>
        !search ||
        Object.values(r).some(
          (v) =>
            typeof v === "string" &&
            v.toLowerCase().includes(search.toLowerCase()),
        ),
    );
  const terminal = ["closed", "rejected", "merged", "skipped"];
  const archiveCandidates = items.filter(
    (w) => terminal.includes(w.status) && !w.archived,
  );
  const template = (catalog.inspection_templates || []).find(
    (t) => t.id === templateId,
  );
  return (
    <div className="operations-workspace" aria-busy={busy || loading}>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button
            onClick={() => setError("")}
            aria-label="Dismiss module error"
          >
            ×
          </button>
        </div>
      )}
      {message && (
        <div className="notice success" role="status">
          {message}
        </div>
      )}
      {loading && (
        <p role="status" className="workspace-loading">
          {Object.keys(catalog).length
            ? "Refreshing workspace records…"
            : "Loading workspace records…"}
        </p>
      )}
      {page === "Overview" ? (
        <OperationsDashboard
          items={items}
          machines={machines}
          catalog={catalog}
          open={open}
        />
      ) : module ? (
        <>
          <div className="module-heading">
            <p>{module.description}</p>
            <div>
              <button onClick={() => downloadCsv(kind, rows, module.columns)}>
                <Download size={16} />
                Export CSV
              </button>
              {manages && (
                <button className="primary" onClick={() => edit()}>
                  <Plus size={16} />
                  Add {page === "Recurrence" ? "plan" : "record"}
                </button>
              )}
            </div>
          </div>
          {kind === "assets" &&
            machines.some(
              (m) => !catalog.assets?.some((a) => a.id === m.id),
            ) && (
              <details className="panel starter-assets">
                <summary>
                  Starter machines available for reporting & monitoring
                </summary>
                <p>
                  These built-in examples remain available to existing work
                  orders. Add your own equipment below to manage its type,
                  ownership and location.
                </p>
                <ul>
                  {machines
                    .filter((m) => !catalog.assets?.some((a) => a.id === m.id))
                    .map((m) => (
                      <li key={m.id}>
                        <strong>{m.id}</strong> · {m.name} · {m.location}
                      </li>
                    ))}
                </ul>
              </details>
            )}
          <div className="module-tools">
            <label className="search">
              <Search size={17} aria-hidden="true" />
              <input
                type="search"
                aria-label={`Search ${page}`}
                placeholder={`Search ${page.toLowerCase()}…`}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <label className="check-field">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
              />
              Show archived
            </label>
            <button onClick={load} aria-label="Refresh module">
              <RefreshCw size={16} />
            </button>
          </div>
          <section className="panel table-scroll">
            <table className="data-table">
              <caption className="sr-only">{page} records</caption>
              <thead>
                <tr>
                  {module.columns.map((c) => (
                    <th key={c} scope="col">
                      {module.fields.find((f) => f.key === c)?.label ||
                        human(c)}
                    </th>
                  ))}
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    {module.columns.map((c) => (
                      <td key={c}>
                        {c === "quantity" &&
                        Number(row.quantity) <= Number(row.minQuantity) ? (
                          <span className="badge critical">
                            {row.quantity} · Low stock
                          </span>
                        ) : (
                          display(c, row[c])
                        )}
                      </td>
                    ))}
                    <td>{rowActions(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && (
              <div className="module-empty">
                <ClipboardList size={32} />
                <h3>
                  {showArchived ? "No archived records." : "No records yet."}
                </h3>
                <p>
                  {manages
                    ? "Add the first record to start using this module."
                    : "Your manager can add records for this workspace."}
                </p>
              </div>
            )}
            <footer className="module-footer">
              {rows.length} {showArchived ? "archived" : "active"} records ·
              saved in AWS
            </footer>
          </section>
          {editor && (
            <div className="panel catalog-editor" ref={formRef}>
              <div className="section-heading">
                <h2>
                  {editor.id ? "Edit" : "Add"} {page.toLowerCase()}
                </h2>
                <button onClick={() => setEditor(null)}>Close editor</button>
              </div>
              <form onSubmit={save}>
                <fieldset disabled={busy}>
                  <div className="catalog-form-grid">
                    {module.fields
                      .filter(
                        (f) =>
                          !(
                            kind === "parts" &&
                            editor.id &&
                            f.key === "quantity"
                          ),
                      )
                      .map((f) => (
                        <div
                          key={f.key}
                          className={
                            ["textarea", "questions", "multi"].includes(
                              f.type || "",
                            )
                              ? "full-width"
                              : ""
                          }
                        >
                          {fieldControl(f)}
                        </div>
                      ))}
                  </div>
                  <p className="helper">
                    Required fields are marked *. Changes are version checked to
                    avoid overwriting another person's update.
                  </p>
                  <div className="form-actions">
                    <button type="button" onClick={() => setEditor(null)}>
                      Cancel
                    </button>
                    <button className="primary" disabled={busy}>
                      {busy ? "Saving…" : "Save record"}
                    </button>
                  </div>
                </fieldset>
              </form>
            </div>
          )}
        </>
      ) : page === "Upcoming" ? (
        <section className="panel module-panel">
          <h2>Upcoming maintenance</h2>
          <p>
            Enabled plans generate requests for manager review when due. The
            scheduler checks hourly. Paused plans are shown for planning only.
          </p>
          {(catalog.plans || [])
            .filter((x) => !x.archived)
            .sort((a, b) => a.nextRun.localeCompare(b.nextRun))
            .map((p) => (
              <div className="upcoming-row" key={p.id}>
                <Clock aria-hidden="true" />
                <div>
                  <strong>{p.name}</strong>
                  <small>
                    {machines.find((m) => m.id === p.assetId)?.name} · every{" "}
                    {p.intervalDays} days · {p.enabled ? "Enabled" : "Paused"}
                  </small>
                </div>
                <time dateTime={p.nextRun}>
                  {new Date(p.nextRun).toLocaleString()}
                </time>
              </div>
            ))}
          {!(catalog.plans || []).some((p) => !p.archived) && (
            <div className="module-empty">
              <Clock size={30} />
              <h3>No scheduled maintenance.</h3>
              <p>
                Create a plan in Recurrence to start preventive maintenance.
              </p>
            </div>
          )}
        </section>
      ) : page === "Asset monitoring" ? (
        <section className="panel module-panel">
          <h2>Asset condition board</h2>
          <p>
            Based on reported faults and manually recorded readings. No live
            sensor connection is implied.
          </p>
          <div className="monitor-grid">
            {machines.map((m) => {
              const faults = items.filter(
                (w) =>
                  w.machineId === m.id &&
                  !terminal.includes(w.status) &&
                  !w.archived,
              );
              const meters = (catalog.meters || []).filter(
                (x) => x.assetId === m.id && !x.archived,
              );
              return (
                <article key={m.id}>
                  <Factory aria-hidden="true" />
                  <h3>{m.name}</h3>
                  <small>
                    {m.code || m.id} ·{" "}
                    {m.locationName ||
                      m.location ||
                      catalog.locations?.find((l) => l.id === m.locationId)
                        ?.name ||
                      "Location not set"}
                  </small>
                  <span
                    className={"badge " + (faults.length ? "high" : "status")}
                  >
                    {faults.length} open fault{faults.length === 1 ? "" : "s"}
                  </span>
                  {meters.length ? (
                    meters.map((x) => (
                      <p key={x.id}>
                        {x.name}:{" "}
                        <strong>{x.latestReading ?? "No reading"}</strong>{" "}
                        {x.unit}
                        <small>
                          Limits: {x.minValue ?? "—"} to {x.maxValue ?? "—"}
                        </small>
                      </p>
                    ))
                  ) : (
                    <p>No meters configured.</p>
                  )}
                  {faults.map((w) => (
                    <button key={w.id} onClick={() => open(w.id)}>
                      {w.title}
                      <ArrowRight size={14} />
                    </button>
                  ))}
                </article>
              );
            })}
          </div>
        </section>
      ) : page === "Requests" ? (
        <section className="panel module-panel">
          <h2>Fault report requests</h2>
          <p>New reports and clarification requests awaiting a decision.</p>
          {items
            .filter(
              (w) =>
                ["pending_review", "needs_details"].includes(w.status) &&
                !w.archived,
            )
            .map((w) => (
              <div className="upcoming-row" key={w.id}>
                <ClipboardList />
                <div>
                  <strong>{w.title}</strong>
                  <small>
                    {w.number} · {w.machineName} · {w.reporterName}
                  </small>
                </div>
                <button onClick={() => open(w.id)}>Review request</button>
              </div>
            ))}
          {!items.some(
            (w) =>
              ["pending_review", "needs_details"].includes(w.status) &&
              !w.archived,
          ) && <div className="module-empty">No requests need review.</div>}
        </section>
      ) : page === "Workflows" ? (
        <section className="panel module-panel">
          <h2>Maintenance workflow & deadlines</h2>
          <div className="workflow-steps">
            {[
              "Report fault",
              "Manager review",
              "Worker accepts",
              "Repair evidence",
              "Manager verifies",
            ].map((s, i) => (
              <div key={s}>
                <span>{i + 1}</span>
                <strong>{s}</strong>
              </div>
            ))}
          </div>
          <p>
            Rejected assignments return to a manager. Duplicate and
            already-repaired reports require review. Missed deadlines escalate
            the existing job; they do not close it.
          </p>
          {workflow && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const saved = await mutate("/settings/workflow", workflow);
                if (saved)
                  showMessage(
                    "Deadline policy saved. Applies to future transitions; existing timers retain their original deadlines.",
                  );
              }}
            >
              <fieldset disabled={!manages || busy}>
                <div className="catalog-form-grid">
                  {[
                    ["ackMinutes", "Acknowledgment deadline (minutes)"],
                    ["repairMinutes", "Repair deadline (minutes)"],
                    ["verifyMinutes", "Verification deadline (minutes)"],
                  ].map(([key, label]) => (
                    <label key={key}>
                      {label}
                      <input
                        type="number"
                        min={1}
                        max={525600}
                        required
                        value={workflow[key]}
                        onChange={(e) =>
                          setWorkflow({
                            ...workflow,
                            [key]: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  ))}
                </div>
                <p className="helper">
                  Policies apply when a new assignment, acceptance or repair
                  submission schedules a deadline. Existing timers are
                  preserved.
                </p>
                {manages && (
                  <button className="primary" disabled={busy}>
                    Save deadline policy
                  </button>
                )}
              </fieldset>
            </form>
          )}
        </section>
      ) : page === "Inspection responses" ? (
        <section className="panel module-panel">
          <h2>Inspection rounds</h2>
          <p>
            Complete a checklist and preserve a dated response for the
            maintenance team.
          </p>
          {me.role !== "reporter" && (
            <>
              <label>
                Inspection template
                <select
                  aria-label="Inspection template"
                  value={templateId}
                  onChange={(e) => {
                    const id = e.target.value;
                    setTemplateId(id);
                    const t = (catalog.inspection_templates || []).find(
                      (t) => t.id === id,
                    );
                    setValues((v) => ({
                      ...v,
                      inspectionAsset: t?.assetId || "",
                    }));
                    setAnswers(
                      (t?.questions || []).map((question: string) => ({
                        question,
                        answer: "",
                        note: "",
                      })),
                    );
                  }}
                >
                  <option value="">Choose a checklist</option>
                  {(catalog.inspection_templates || [])
                    .filter((t) => !t.archived)
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                </select>
              </label>
              {template && (
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const data = {
                      templateId,
                      assetId: values.inspectionAsset || template.assetId,
                      answers,
                      notes: values.notes || "",
                    };
                    const out = await mutate(
                      "/catalog/inspection_responses",
                      data,
                    );
                    if (out) {
                      setTemplateId("");
                      setAnswers([]);
                    }
                  }}
                >
                  <fieldset disabled={busy}>
                    <label>
                      Asset
                      <select
                        required
                        aria-label="Inspected asset"
                        disabled={!!template.assetId}
                        value={values.inspectionAsset || template.assetId || ""}
                        onChange={(e) =>
                          setValues({
                            ...values,
                            inspectionAsset: e.target.value,
                          })
                        }
                      >
                        <option value="">Select asset</option>
                        {machines.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    {answers.map((a, i) => (
                      <fieldset className="inspection-answer" key={a.question}>
                        <legend>
                          {i + 1}. {a.question}
                        </legend>
                        <div>
                          {["pass", "fail", "na"].map((v) => (
                            <label key={v}>
                              <input
                                type="radio"
                                required
                                name={"answer-" + i}
                                value={v}
                                checked={a.answer === v}
                                onChange={() =>
                                  setAnswers(
                                    answers.map((old, j) =>
                                      j === i ? { ...old, answer: v } : old,
                                    ),
                                  )
                                }
                              />
                              {v === "na" ? "Not applicable" : human(v)}
                            </label>
                          ))}
                        </div>
                        <label>
                          Observation
                          <input
                            maxLength={500}
                            value={a.note}
                            onChange={(e) =>
                              setAnswers(
                                answers.map((old, j) =>
                                  j === i
                                    ? { ...old, note: e.target.value }
                                    : old,
                                ),
                              )
                            }
                          />
                        </label>
                      </fieldset>
                    ))}
                    <button className="primary" disabled={busy}>
                      Submit inspection
                    </button>
                  </fieldset>
                </form>
              )}
            </>
          )}
          <h3 className="history-heading">Recorded responses</h3>
          {(catalog.inspection_responses || [])
            .filter((r) => !r.archived)
            .map((r) => (
              <details className="inspection-history" key={r.id}>
                <summary>
                  {r.name || "Inspection response"} ·{" "}
                  {new Date(r.createdAt).toLocaleString()}
                </summary>
                {r.answers?.map((a: R, i: number) => (
                  <p key={i}>
                    {a.question}: <strong>{a.answer}</strong>
                    {a.note ? " · " + a.note : ""}
                  </p>
                ))}
              </details>
            ))}
          {!(catalog.inspection_responses || []).length && (
            <p>No inspection responses recorded.</p>
          )}
        </section>
      ) : page === "Users" ? (
        <section className="panel module-panel">
          <h2>People & access</h2>
          <p>
            Admins manage Managers, Workers and Reporters. Managers can manage
            Worker/Reporter access only. Team membership never grants
            permissions.
          </p>
          {users.map((u) => (
            <div className="team-row" key={u.id}>
              <div>
                <strong>{u.name}</strong>
                <small>{u.email}</small>
                {(u.department || u.jobTitle || u.shift) && (
                  <small>
                    {[
                      u.jobTitle,
                      human(u.department || ""),
                      u.shift ? human(u.shift) + " shift" : "",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </small>
                )}
                {!u.demo && (
                  <small>
                    {u.emailVerified
                      ? "Verified email"
                      : "Email verification pending"}
                    {u.enabled === false ? " · Account disabled" : ""}
                  </small>
                )}
              </div>
              <span className="badge status">{u.role}</span>
              {u.demo && (
                <small className="demo-person-note">
                  Demo person · no login or access permissions
                </small>
              )}
              {!u.demo &&
                u.role !== "admin" &&
                (me.role === "admin" || u.role !== "manager") && (
                  <label className="role-select">
                    <span className="sr-only">Role for {u.name}</span>
                    <select
                      disabled={busy}
                      value={u.role}
                      onChange={async (e) => {
                        await mutate(`/users/${u.id}/role`, {
                          role: e.target.value,
                        });
                      }}
                    >
                      {(me.role === "admin"
                        ? ["manager", "worker", "reporter"]
                        : ["worker", "reporter"]
                      ).map((r) => (
                        <option key={r} value={r}>
                          {human(r)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
            </div>
          ))}
        </section>
      ) : page === "Archive" ? (
        <section className="panel module-panel">
          <h2>Archived work orders</h2>
          <p>
            Archived records and evidence remain recoverable. Unresolved work
            cannot be archived.
          </p>
          {items
            .filter((w) => w.archived)
            .map((w) => (
              <div className="upcoming-row" key={w.id}>
                <Archive />
                <div>
                  <strong>{w.title}</strong>
                  <small>
                    {w.number} · {w.status}
                  </small>
                </div>
                <button onClick={() => open(w.id)}>View history</button>
                <button
                  disabled={busy}
                  onClick={() =>
                    mutate(`/workorders/${w.id}/actions`, {
                      action: "restore",
                      version: w.version,
                      reason: "Restored from archive",
                    })
                  }
                >
                  Restore
                </button>
              </div>
            ))}
          {!items.some((w) => w.archived) && (
            <div className="module-empty">No archived work orders.</div>
          )}
        </section>
      ) : page === "Billing & usage" ? (
        <section className="panel module-panel">
          <h2>Workspace usage</h2>
          <p>
            Application record counts, not invoices or measured AWS spending.
            This app does not collect subscription payments.
          </p>
          <dl>
            <dt>Work orders</dt>
            <dd>{items.length}</dd>
            <dt>Assets</dt>
            <dd>{machines.length}</dd>
            <dt>Stored catalog records</dt>
            <dd>
              {Object.values(catalog).reduce((n, rows) => n + rows.length, 0)}
            </dd>
            <dt>Region</dt>
            <dd>Mumbai · ap-south-1</dd>
          </dl>
          <p>
            AWS bills are determined by actual cloud usage. AWS credits are not
            a hard spending cap.
          </p>
          {me.role === "admin" && (
            <a
              className="button-link"
              href="https://console.aws.amazon.com/billing/home"
              target="_blank"
              rel="noreferrer"
            >
              Open AWS Billing console
            </a>
          )}
        </section>
      ) : page === "Bulk archive" ? (
        <section className="panel module-panel">
          <h2>Preview & bulk archive</h2>
          <p>
            Select finished records, review the selection, then archive. This
            replaces destructive spreadsheet deletion and preserves evidence.
          </p>
          {archiveCandidates.map((w) => (
            <label className="bulk-choice" key={w.id}>
              <input
                type="checkbox"
                checked={selected.includes(w.id)}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, w.id]
                      : selected.filter((id) => id !== w.id),
                  )
                }
              />
              <span>
                <strong>
                  {w.number} · {w.title}
                </strong>
                <small>
                  {w.status} · {w.machineName}
                </small>
              </span>
            </label>
          ))}
          {!archiveCandidates.length && (
            <p>No finished work orders available to archive.</p>
          )}
          <div className="notice">
            {selected.length} finished work order(s) selected. Open and
            in-progress work is excluded.
          </div>
          <button
            className="primary"
            disabled={busy || !selected.length}
            onClick={async () => {
              setBusy(true);
              let completed = 0;
              try {
                for (const id of selected) {
                  const w = items.find((w) => w.id === id)!;
                  await api(`/workorders/${id}/actions`, {
                    action: "archive",
                    version: w.version,
                    reason: "Bulk archive of finished work",
                  });
                  completed++;
                }
                await refresh();
                setSelected([]);
                showMessage(
                  `Archived ${completed} records. Restore them from Archive.`,
                );
              } catch (e) {
                setError(
                  `Archived ${completed} records before stopping: ${(e as Error).message}`,
                );
                await refresh();
              } finally {
                setBusy(false);
              }
            }}
          >
            Confirm archive of {selected.length} records
          </button>
        </section>
      ) : page === "Download centre" ? (
        <section className="panel module-panel">
          <h2>Download centre</h2>
          <p>
            Spreadsheet-friendly CSV exports use only data available to your
            role. Formula-like values are escaped for safer spreadsheet opening.
          </p>
          <div className="download-grid">
            <button
              onClick={() =>
                downloadCsv("work-orders", items, [
                  "number",
                  "title",
                  "machineId",
                  "machineName",
                  "status",
                  "priority",
                  "assigneeName",
                  "createdAt",
                  "deadline",
                  "archived",
                ])
              }
            >
              <Download />
              Work orders CSV
            </button>
            <button
              onClick={() =>
                downloadCsv("assets", machines, [
                  "code",
                  "id",
                  "name",
                  "location",
                  "serial",
                ])
              }
            >
              <Download />
              Asset registry CSV
            </button>
            {Object.entries(MODULES)
              .filter(([, m]) => catalog[m.kind]?.length)
              .map(([name, m]) => (
                <button
                  key={name}
                  onClick={() =>
                    downloadCsv(m.kind, catalog[m.kind], m.columns)
                  }
                >
                  <Download />
                  {name} CSV
                </button>
              ))}
          </div>
          {manages && (
            <div className="csv-import">
              <h3>Import assets from CSV</h3>
              <p>
                Maximum 1 MB and 100 rows. Required columns: code, name.
                Existing asset codes cannot be silently overwritten.
              </p>
              <button
                onClick={() =>
                  downloadCsv(
                    "asset-import-template",
                    [{ code: "PRESS-01", name: "Hydraulic press", serial: "" }],
                    ["code", "name", "serial"],
                  )
                }
              >
                Download import template
              </button>
              <label>
                Choose CSV
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={async (e) => {
                    try {
                      const f = e.target.files?.[0];
                      if (!f) return;
                      if (f.size > 1024 * 1024)
                        throw Error("CSV must be smaller than 1 MB.");
                      const rows = parseCsv(await f.text());
                      if (rows.some((r) => !r.code || !r.name))
                        throw Error("Every row needs a code and name.");
                      if (
                        rows.some((r) =>
                          Object.keys(r).some(
                            (k) => !["code", "name", "serial"].includes(k),
                          ),
                        )
                      )
                        throw Error("Use only code, name and serial columns.");
                      if (
                        new Set(rows.map((r) => r.code.toLowerCase())).size !==
                        rows.length
                      )
                        throw Error("Duplicate codes in this CSV.");
                      setPreview(rows);
                      setError("");
                    } catch (err) {
                      setPreview([]);
                      setError((err as Error).message);
                    }
                  }}
                />
              </label>
              {preview.length > 0 && (
                <>
                  <div className="notice">
                    Preview: {preview.length} assets. No records have been
                    imported yet.
                  </div>
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Code</th>
                          <th>Name</th>
                          <th>Serial</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.map((r, i) => (
                          <tr key={i}>
                            <td>{r.code}</td>
                            <td>{r.name}</td>
                            <td>{r.serial}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      let n = 0;
                      try {
                        for (const row of preview) {
                          await api("/catalog/assets", row);
                          n++;
                          await new Promise((r) => setTimeout(r, 250));
                        }
                        await load();
                        await refresh();
                        setPreview([]);
                        showMessage(`Imported ${n} assets.`);
                      } catch (e) {
                        setPreview(preview.slice(n));
                        setError(
                          `Imported ${n} rows; stopped at the next row: ${(e as Error).message}`,
                        );
                        await load();
                        await refresh();
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Confirm import
                  </button>
                </>
              )}
            </div>
          )}
        </section>
      ) : null}
      {action && (
        <section className="panel catalog-editor" ref={formRef}>
          <div className="section-heading">
            <h2>
              {action.type === "adjust"
                ? "Adjust stock"
                : action.type === "receive"
                  ? "Receive purchase"
                  : action.type === "reading"
                    ? "Record meter reading"
                    : action.type === "history"
                      ? "Stock movement history"
                      : action.row.archived
                        ? "Restore record"
                        : "Archive record"}{" "}
              · {action.row.name}
            </h2>
            <button onClick={() => setAction(null)}>Close</button>
          </div>
          {action.type !== "history" && (
            <form onSubmit={actionSubmit}>
              <fieldset disabled={busy}>
                {action.type === "adjust" ? (
                  <>
                    <label>
                      Quantity change (negative to issue stock)
                      <input
                        type="number"
                        step="1"
                        required
                        value={values.delta ?? ""}
                        onChange={(e) =>
                          setValues({ ...values, delta: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Reason
                      <textarea
                        required
                        maxLength={1000}
                        value={values.reason || ""}
                        onChange={(e) =>
                          setValues({ ...values, reason: e.target.value })
                        }
                      />
                    </label>
                  </>
                ) : action.type === "reading" ? (
                  <>
                    <label>
                      Reading ({action.row.unit})
                      <input
                        type="number"
                        required
                        step="any"
                        value={values.value ?? ""}
                        onChange={(e) =>
                          setValues({ ...values, value: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Observation
                      <input
                        value={values.note || ""}
                        maxLength={500}
                        onChange={(e) =>
                          setValues({ ...values, note: e.target.value })
                        }
                      />
                    </label>
                  </>
                ) : (
                  <p>
                    {action.type === "receive"
                      ? `Receive ${action.row.quantity} units into stock? This can happen only once. No payment or external order will be made.`
                      : action.row.archived
                        ? "Restore this record to active use?"
                        : "Archive this record? Related data and history remain stored. Referenced records may be protected from archiving."}
                  </p>
                )}
                <button className="primary" disabled={busy}>
                  Confirm{" "}
                  {action.type === "receive"
                    ? "receipt"
                    : action.type === "adjust"
                      ? "stock change"
                      : action.type === "reading"
                        ? "reading"
                        : action.row.archived
                          ? "restore"
                          : "archive"}
                </button>
              </fieldset>
            </form>
          )}
          {(action.type === "history" || action.type === "reading") && (
            <>
              <h3 className="history-heading">Recorded history</h3>
              {history.length ? (
                history.map((h, i) => (
                  <div className="history-entry" key={h.id || i}>
                    <strong>
                      {h.delta !== undefined
                        ? (h.delta > 0 ? "+" : "") + h.delta
                        : h.value}{" "}
                      {action.row.unit || ""}
                    </strong>
                    <span>{h.reason || h.note || h.actorName || ""}</span>
                    <time>
                      {new Date(h.createdAt || h.at).toLocaleString()}
                    </time>
                  </div>
                ))
              ) : (
                <p>No recorded history.</p>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
