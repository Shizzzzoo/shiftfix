import { useState, useEffect } from "react";
import {
  Factory,
  ArrowRight,
  CheckCircle2,
  Wrench,
  ShieldCheck,
  ClipboardList,
  Users,
} from "lucide-react";
const roles: Record<string, { title: string; description: string; Icon: any }> =
  {
    admin: {
      title: "Admin",
      description:
        "Manage team access, oversee maintenance, and verify repairs across the factory.",
      Icon: ShieldCheck,
    },
    manager: {
      title: "Manager",
      description:
        "Review incoming reports, assign workers, resolve duplicates, and verify repairs.",
      Icon: Users,
    },
    worker: {
      title: "Worker",
      description:
        "Accept your assignments, record repairs, and return work that needs a different specialist.",
      Icon: Wrench,
    },
    reporter: {
      title: "Reporter",
      description:
        "Report a fault with photos, answer follow-up questions, and track your own requests.",
      Icon: ClipboardList,
    },
  };
export function Onboarding({
  me,
  machines,
  save,
  onDone,
  onSignOut,
}: {
  me: any;
  machines: any[];
  save: (v: any) => Promise<any>;
  onDone: () => Promise<void>;
  onSignOut: () => void;
}) {
  const [step, setStep] = useState(0),
    [name, setName] = useState(me.name || ""),
    [department, setDepartment] = useState(""),
    [chosen, setChosen] = useState<string[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const role = roles[me.role] || roles.reporter;
  useEffect(() => {
    document.getElementById("onboarding-heading")?.focus();
  }, [step]);
  async function finish() {
    setBusy(true);
    setError("");
    try {
      await save({ displayName: name.trim(), department, machineIds: chosen });
      await onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="onboarding" id="main-content">
      <section className="onboarding-story">
        <img src="/assets/factory-machines.jpg" alt="" />
        <div className="onboarding-shade" />
        <div className="onboarding-story-content">
          <div className="brand">
            <span>
              <Wrench aria-hidden="true" />
            </span>
            ShiftFix
          </div>
          <div>
            <p>WELCOME TO YOUR WORKSPACE</p>
            <h1>
              Better handovers.
              <br />
              Safer shifts.
            </h1>
            <span>
              A clear process, from the first fault report to the final verified
              repair.
            </span>
          </div>
          <small>Factory photography · YIHAI LASER / Pexels</small>
        </div>
      </section>
      <section className="onboarding-form">
        <div className="onboarding-top">
          <span>
            <Factory size={18} aria-hidden="true" /> Plant 01 · First-time setup
          </span>
          <button onClick={onSignOut}>Sign out</button>
        </div>
        <div className="onboarding-content">
          <ol className="stepper" aria-label="Onboarding progress">
            {["Your profile", "Your role", "Ready to work"].map((label, i) => (
              <li
                aria-current={i === step ? "step" : undefined}
                className={i <= step ? "reached" : ""}
                key={label}
              >
                <span>
                  {i < step ? (
                    <CheckCircle2 size={17} aria-hidden="true" />
                  ) : (
                    i + 1
                  )}
                </span>
                {label}
              </li>
            ))}
          </ol>
          <div aria-live="polite" className="sr-only">
            Step {step + 1} of 3:{" "}
            {["Your profile", "Your role", "Ready to work"][step]}
          </div>
          {step === 0 ? (
            <>
              <h2 id="onboarding-heading" tabIndex={-1}>
                Let’s make this your workspace.
              </h2>
              <p>
                Your email is verified. Tell your team who you are and where you
                work.
              </p>
              <label>
                Display name
                <input
                  autoFocus
                  value={name}
                  minLength={2}
                  maxLength={100}
                  autoComplete="name"
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label htmlFor="onboarding-department">Department</label>
              <select
                id="onboarding-department"
                value={department}
                required
                onChange={(e) => setDepartment(e.target.value)}
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
                  Machines you work around <span>(optional)</span>
                </legend>
                {machines.map((m) => (
                  <label key={m.id}>
                    <input
                      type="checkbox"
                      checked={chosen.includes(m.id)}
                      onChange={(e) =>
                        setChosen(
                          e.target.checked
                            ? [...chosen, m.id]
                            : chosen.filter((x) => x !== m.id),
                        )
                      }
                    />
                    <span>
                      <b>{m.id}</b> {m.name}
                      <small>{m.location}</small>
                    </span>
                  </label>
                ))}
              </fieldset>
            </>
          ) : step === 1 ? (
            <>
              <h2 id="onboarding-heading" tabIndex={-1}>
                Your role is {role.title}.
              </h2>
              <p>
                Everyone has a clear responsibility. Your role is assigned by
                the factory team.
              </p>
              <div className="role-intro">
                <role.Icon size={28} aria-hidden="true" />
                <strong>{role.title}</strong>
                <p>{role.description}</p>
              </div>
              <div className="hierarchy">
                {Object.entries(roles).map(([key, r], i) => (
                  <div className={key === me.role ? "your-role" : ""} key={key}>
                    <r.Icon size={20} aria-hidden="true" />
                    <div>
                      <strong>
                        {r.title}
                        {key === me.role ? " · You" : ""}
                      </strong>
                      <small>
                        {
                          [
                            "Manages access and operations",
                            "Reviews, assigns and verifies",
                            "Carries out assigned maintenance",
                            "Reports faults and follows progress",
                          ][i]
                        }
                      </small>
                    </div>
                  </div>
                ))}
              </div>
              <p className="helper">
                Need different access? Ask an Admin or Manager. You cannot grant
                yourself a role.
              </p>
            </>
          ) : (
            <>
              <h2 id="onboarding-heading" tabIndex={-1}>
                Ready for your next shift.
              </h2>
              <p>
                Your first action is simple. You can always find the workflow
                guide in Help & accessibility.
              </p>
              <div className="role-intro">
                <CheckCircle2 size={30} aria-hidden="true" />
                <h3>
                  {me.role === "reporter"
                    ? "Start with a fault report"
                    : me.role === "worker"
                      ? "Check your assigned work"
                      : "Review the maintenance inbox"}
                </h3>
                <p>
                  {me.role === "reporter"
                    ? "Pick the machine, describe what you noticed, and attach a clear photo. A manager decides what happens next."
                    : me.role === "worker"
                      ? "Accept the job if you are responsible. If it belongs to someone else or is already repaired, return it with a reason."
                      : "Review evidence, check for duplicate or already completed repairs, then assign the right worker."}
                </p>
              </div>
              <p className="helper">
                Photos are checked before upload. Deadlines flag overdue work;
                they never hide unresolved faults.
              </p>
            </>
          )}
          {error && (
            <div className="notice error" role="alert">
              {error}
            </div>
          )}
          <div className="onboarding-actions">
            {step > 0 && (
              <button disabled={busy} onClick={() => setStep(step - 1)}>
                Back
              </button>
            )}
            <button
              className="primary"
              disabled={
                busy || (step === 0 && (name.trim().length < 2 || !department))
              }
              onClick={() => (step < 2 ? setStep(step + 1) : finish())}
            >
              {busy
                ? "Saving your profile…"
                : step === 2
                  ? "Open my workspace"
                  : "Continue"}
              <ArrowRight size={17} aria-hidden="true" />
            </button>
          </div>
          <small className="helper">
            Setup is saved only when you choose “Open my workspace”.
          </small>
        </div>
      </section>
    </main>
  );
}
