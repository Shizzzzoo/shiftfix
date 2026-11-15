import { useState } from "react";
import { Search, ArrowUpRight } from "lucide-react";
type R = Record<string, any>;
export function AssistantSearch({
  role,
  api,
  onSource,
}: {
  role: string;
  api: (path: string, body?: R) => Promise<any>;
  onSource: (source: R) => void;
}) {
  const [scope, setScope] = useState("work_orders"),
    [query, setQuery] = useState(""),
    [result, setResult] = useState<R | null>(null),
    [sources, setSources] = useState<R[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const manages = ["admin", "manager"].includes(role);
  const choices = [
    ["work_orders", "Work orders"],
    ["assets", "Assets"],
    ["locations", "Locations"],
    ...(role !== "reporter"
      ? [
          ["parts", "Parts"],
          ["meters", "Meters"],
        ]
      : []),
    ...(manages
      ? [
          ["people", "People"],
          ["plans", "Recurring plans"],
          ["automations", "Automations"],
        ]
      : []),
  ];
  async function search(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    setSources([]);
    try {
      const tool =
        scope === "work_orders"
          ? "search_work_orders"
          : scope === "people"
            ? "search_people"
            : "search_catalog";
      const r = await api("/assistant/search", {
        tool,
        input: {
          query,
          limit: 10,
          ...(tool === "search_catalog" ? { kind: scope } : {}),
        },
      });
      setResult(r.result);
      setSources(r.sources || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="panel assistant-search"
      aria-labelledby="assistant-search-title"
    >
      <div className="assistant-search-heading">
        <Search size={20} aria-hidden="true" />
        <div>
          <h2 id="assistant-search-title">Search workspace directly</h2>
          <p>
            Live, permission-scoped results. This search works without an AI
            model.
          </p>
        </div>
      </div>
      <form onSubmit={search}>
        <label htmlFor="assistant-search-scope" className="sr-only">
          Search section
        </label>
        <select
          id="assistant-search-scope"
          value={scope}
          onChange={(e) => {
            setScope(e.target.value);
            setResult(null);
            setSources([]);
          }}
        >
          {choices.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <label className="search">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            aria-label="Search workspace records"
            value={query}
            maxLength={200}
            placeholder="Machine, work-order number or keyword…"
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button disabled={busy} type="submit">
          {busy ? "Searching…" : "Search records"}
        </button>
      </form>
      {error && (
        <p role="alert" className="notice error">
          {error}
        </p>
      )}
      {result && (
        <div className="assistant-search-results">
          <p role="status">
            {result.totalMatches} matching records
            {result.items?.length < result.totalMatches
              ? ` · showing ${result.items.length}`
              : ""}
          </p>
          {result.items?.length ? (
            result.items.map((item: R) => (
              <article key={item.id}>
                <strong>
                  {item.number ? item.number + " · " : ""}
                  {item.title || item.name}
                </strong>
                <p>
                  {[
                    item.machineName,
                    item.role,
                    item.department,
                    item.status,
                    item.priority,
                    item.sku,
                    item.quantity !== undefined
                      ? `${item.quantity} ${item.unit || "units"} in stock`
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                {sources.some((s) => s.id === item.id) && (
                  <button
                    onClick={() =>
                      onSource(sources.find((s) => s.id === item.id)!)
                    }
                  >
                    Open record <ArrowUpRight size={14} />
                  </button>
                )}
              </article>
            ))
          ) : (
            <p>No records match within your current access.</p>
          )}
          {sources
            .filter((s) => s.kind === "page")
            .map((s) => (
              <button key={s.page} onClick={() => onSource(s)}>
                Open {s.label} <ArrowUpRight size={14} />
              </button>
            ))}
        </div>
      )}
    </section>
  );
}
