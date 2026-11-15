import { useRef, useState } from "react";
import { Filter, X, RotateCcw } from "lucide-react";
type Values = Record<string, string>;
type Choice = [string, string];
export type FilterField = {
  key: string;
  label: string;
  choices: Choice[];
  parent?: string;
  parents?: Record<string, string>;
  ancestor?: { key: string; parents: Record<string, string> };
};
const labels: Values = {
  status: "Status",
  from: "From",
  to: "To",
  machineId: "Asset",
  typeId: "Asset type",
  category: "Category",
  teamId: "Team",
  assigneeId: "Assigned to",
  locationId: "Location",
  zoneId: "Zone",
  subzoneId: "Sub-zone",
};
export function DashboardFilters({
  values,
  onChange,
  fields,
}: {
  values: Values;
  onChange: (values: Values) => void;
  fields: FilterField[];
}) {
  const dialog = useRef<HTMLDialogElement>(null),
    trigger = useRef<HTMLButtonElement>(null);
  const [draft, setDraft] = useState<Values>({}),
    [opened, setOpened] = useState(false),
    [error, setError] = useState("");
  const active = Object.entries(values).filter(([, v]) => v);
  function close() {
    dialog.current?.close();
  }
  function open() {
    setDraft({ ...values });
    setError("");
    setOpened(true);
    dialog.current?.showModal();
    dialog.current?.querySelector<HTMLElement>("h2")?.focus();
  }
  function update(key: string, value: string) {
    setDraft((old) => ({
      ...old,
      [key]: value,
      ...(key === "locationId"
        ? { zoneId: "", subzoneId: "" }
        : key === "zoneId"
          ? { subzoneId: "" }
          : {}),
    }));
    setError("");
  }
  function commit(e: React.FormEvent) {
    e.preventDefault();
    if (draft.from && draft.to && draft.from > draft.to) {
      setError("The end date must be on or after the start date.");
      dialog.current?.querySelector<HTMLInputElement>("#filter-to")?.focus();
      return;
    }
    onChange(draft);
    close();
  }
  function select(key: string) {
    const f = fields.find((f) => f.key === key);
    if (!f) return null;
    const options = f.choices.filter(
      ([id]) =>
        (!f.parent ||
          !draft[f.parent] ||
          f.parents?.[id] === draft[f.parent]) &&
        (!f.ancestor ||
          !draft[f.ancestor.key] ||
          f.ancestor.parents[id] === draft[f.ancestor.key]),
    );
    return (
      <div className="drawer-field" key={key}>
        <label htmlFor={"filter-" + key}>{f.label}</label>
        <select
          id={"filter-" + key}
          value={draft[key] || ""}
          onChange={(e) => update(key, e.target.value)}
        >
          <option value="">
            {key === "status"
              ? "All statuses"
              : key === "assigneeId"
                ? "Anyone"
                : "Any " + f.label.toLowerCase()}
          </option>
          {options.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </div>
    );
  }
  function remove(key: string) {
    const next = { ...values };
    delete next[key];
    if (key === "locationId") {
      delete next.zoneId;
      delete next.subzoneId;
    }
    if (key === "zoneId") delete next.subzoneId;
    onChange(next);
  }
  return (
    <>
      <button
        ref={trigger}
        className={"filter-toggle" + (active.length ? " has-filters" : "")}
        aria-haspopup="dialog"
        aria-controls="dashboard-filters"
        aria-expanded={opened}
        onClick={open}
      >
        <Filter size={16} aria-hidden="true" />
        Filters
        {active.length > 0 && (
          <span className="filter-count">{active.length}</span>
        )}
      </button>
      {active.length > 0 && (
        <div
          className="active-filter-list"
          aria-label="Applied dashboard filters"
        >
          {active.map(([key, v]) => (
            <button
              key={key}
              onClick={() => remove(key)}
              aria-label={"Remove " + labels[key] + " filter"}
            >
              <span>
                {labels[key]}:{" "}
                {fields
                  .find((f) => f.key === key)
                  ?.choices.find(([id]) => id === v)?.[1] || v}
              </span>
              <X size={12} aria-hidden="true" />
            </button>
          ))}
          <button className="clear-filters" onClick={() => onChange({})}>
            Clear all
          </button>
        </div>
      )}
      <dialog
        id="dashboard-filters"
        ref={dialog}
        className="filter-drawer"
        aria-labelledby="dashboard-filters-title"
        onClick={(e) => {
          if (e.target === dialog.current) {
            const b = dialog.current.getBoundingClientRect();
            if (
              e.clientX < b.left ||
              e.clientX > b.right ||
              e.clientY < b.top ||
              e.clientY > b.bottom
            )
              close();
          }
        }}
        onKeyDown={(e) => {
          if (e.key !== "Tab") return;
          const controls = Array.from(
            dialog.current?.querySelectorAll<HTMLElement>(
              'button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]',
            ) || [],
          );
          const first = controls[0],
            last = controls[controls.length - 1];
          if (
            e.shiftKey &&
            (document.activeElement === first ||
              document.activeElement?.id === "dashboard-filters-title")
          ) {
            e.preventDefault();
            last?.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first?.focus();
          }
        }}
        onClose={() => {
          setOpened(false);
          setError("");
          trigger.current?.focus();
        }}
      >
        <form onSubmit={commit} noValidate>
          <div className="drawer-header">
            <div>
              <small>WORKSPACE VIEW</small>
              <h2 tabIndex={-1} id="dashboard-filters-title">
                Filter dashboard
              </h2>
              <p>Focus on the work that matters to this shift.</p>
            </div>
            <button type="button" onClick={close} aria-label="Close filters">
              <X size={20} />
            </button>
          </div>
          <div className="drawer-content">
            <fieldset>
              <legend>Work & dates</legend>
              {select("status")}
              <div className="drawer-field-pair">
                <label className="drawer-field" htmlFor="filter-from">
                  <span>From date</span>
                  <input
                    id="filter-from"
                    type="date"
                    value={draft.from || ""}
                    onChange={(e) => update("from", e.target.value)}
                  />
                </label>
                <label className="drawer-field" htmlFor="filter-to">
                  <span>To date</span>
                  <input
                    id="filter-to"
                    type="date"
                    min={draft.from || undefined}
                    aria-invalid={!!error}
                    aria-describedby={error ? "filter-date-error" : undefined}
                    value={draft.to || ""}
                    onChange={(e) => update("to", e.target.value)}
                  />
                </label>
              </div>
              <small className="drawer-hint">
                Dates refer to when a work order was created.
              </small>
            </fieldset>
            <fieldset>
              <legend>Equipment</legend>
              {select("machineId")}
              {select("typeId")}
              {select("category")}
            </fieldset>
            <fieldset>
              <legend>People</legend>
              {select("teamId")}
              {select("assigneeId")}
            </fieldset>
            <fieldset>
              <legend>Factory location</legend>
              {select("locationId")}
              {select("zoneId")}
              {select("subzoneId")}
            </fieldset>
            {error && (
              <p className="notice error" id="filter-date-error" role="alert">
                {error}
              </p>
            )}
          </div>
          <div className="drawer-footer">
            <button
              type="button"
              onClick={() => {
                setDraft({});
                setError("");
              }}
            >
              <RotateCcw size={15} />
              Reset
            </button>
            <button type="button" onClick={close}>
              Cancel
            </button>
            <button type="submit" className="primary">
              Apply filters
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
