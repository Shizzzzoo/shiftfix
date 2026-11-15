import { useState } from "react";
import { Search } from "lucide-react";
export function ProfileSetup({
  name,
  department,
  chosen,
  machines,
  onName,
  onDepartment,
  onChosen,
}: {
  name: string;
  department: string;
  chosen: string[];
  machines: any[];
  onName: (name: string) => void;
  onDepartment: (value: string) => void;
  onChosen: (value: string[]) => void;
}) {
  const [search, setSearch] = useState("");
  const filtered = machines.filter(
    (m) =>
      !search ||
      [m.code, m.id, m.name].some((v) =>
        String(v || "")
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
  );
  return (
    <>
      <label>
        Display name
        <input
          value={name}
          minLength={2}
          maxLength={100}
          autoComplete="name"
          onChange={(e) => onName(e.target.value)}
        />
      </label>
      <label htmlFor="onboarding-department">Department</label>
      <select
        id="onboarding-department"
        value={department}
        required
        onChange={(e) => onDepartment(e.target.value)}
      >
        <option value="">Choose your department</option>
        {[
          "production",
          "maintenance",
          "engineering",
          "quality",
          "operations",
          "other",
        ].map((d) => (
          <option key={d} value={d}>
            {d[0].toUpperCase() + d.slice(1)}
          </option>
        ))}
      </select>
      <fieldset className="machine-checks">
        <legend>
          Machines you work around <span>(optional · choose up to 4)</span>
        </legend>
        <label className="search machine-picker-search">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            aria-label="Find onboarding machines"
            placeholder="Find a machine…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <p className="machine-selection-count" role="status">
          {chosen.length} of 4 selected
        </p>
        <div
          className="machine-picker-list"
          tabIndex={0}
          aria-label="Available machines"
        >
          {filtered.map((m) => (
            <label key={m.id}>
              <input
                type="checkbox"
                checked={chosen.includes(m.id)}
                disabled={!chosen.includes(m.id) && chosen.length >= 4}
                onChange={(e) =>
                  onChosen(
                    e.target.checked
                      ? [...chosen, m.id]
                      : chosen.filter((x) => x !== m.id),
                  )
                }
              />
              <span>
                <b>{m.code || m.id}</b> {m.name}
                <small>
                  {m.locationName ||
                    m.location ||
                    "Registered factory equipment"}
                </small>
              </span>
            </label>
          ))}
          {chosen
            .filter((id) => !machines.some((m) => m.id === id))
            .map((id) => (
              <label key={id}>
                <input
                  type="checkbox"
                  checked
                  onChange={() => onChosen(chosen.filter((x) => x !== id))}
                />
                <span>
                  <b>{id}</b>
                  <small>
                    No longer available · uncheck to remove this preference
                  </small>
                </span>
              </label>
            ))}
          {!filtered.length && <p>No machines match this search.</p>}
        </div>
      </fieldset>
    </>
  );
}
