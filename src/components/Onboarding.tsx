import { useState, useEffect } from "react";
import {
  Factory,
  ArrowRight,
  CheckCircle2,
  Wrench,
  Keyboard,
  Eye,
  MousePointer2,
} from "lucide-react";
import {
  AccessibilityControls,
  type AccessibilityProps,
} from "./AccessibilityControls";
import { TourSections, RoleIntro, onboardingRoles } from "./WorkspaceTour";
import { ProfileSetup } from "./ProfileSetup";
const steps = [
  "Your profile",
  "Your role",
  "Workspace",
  "Operations",
  "Accessibility",
  "Ready",
];
export function Onboarding({
  me,
  machines,
  save,
  onDone,
  onSignOut,
  replay = false,
  accessibility,
}: {
  me: any;
  machines: any[];
  save: (v: any) => Promise<any>;
  onDone: () => Promise<void>;
  onSignOut: () => void;
  replay?: boolean;
  accessibility: AccessibilityProps;
}) {
  const [step, setStep] = useState(replay ? 2 : 0),
    [name, setName] = useState(me.profile?.displayName || me.name || ""),
    [department, setDepartment] = useState(me.profile?.department || ""),
    [chosen, setChosen] = useState<string[]>(me.profile?.machineIds || []),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const role = onboardingRoles[me.role] || onboardingRoles.reporter;
  const first = replay ? 2 : 0;
  useEffect(() => {
    document.getElementById("onboarding-heading")?.focus();
    window.scrollTo(0, 0);
  }, [step]);
  async function finish() {
    setBusy(true);
    setError("");
    try {
      if (!replay)
        await save({
          displayName: name.trim(),
          department,
          machineIds: chosen,
        });
      await onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const titles = [
    "Let’s make this your workspace.",
    `Your role is ${role.title}.`,
    "Find your way around.",
    "Keep the whole shift connected.",
    "Make it comfortable to use.",
    "Ready for your next shift.",
  ];
  const descriptions = [
    "Your email is verified. Tell your team who you are and where you work.",
    "Everyone has a clear responsibility. Your access is assigned by the factory team.",
    "Start with the dashboard, then follow the machine and the work.",
    "Planning, supplies and evidence all support the same maintenance process.",
    "Choose your reading preferences now. You can change them later in Help & accessibility.",
    "Your first action is simple. The workspace guide is always available from the header or Help & accessibility.",
  ];
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
            <Factory size={18} aria-hidden="true" />
            Plant 01 · {replay ? "Workspace guide" : "First-time setup"}
          </span>
          <button onClick={onSignOut} disabled={busy}>
            {replay ? "Close guide" : "Sign out"}
          </button>
        </div>
        <div className="onboarding-content">
          <ol className="stepper" aria-label="Onboarding progress">
            {steps.slice(first).map((label, i) => (
              <li
                aria-current={i + first === step ? "step" : undefined}
                className={i + first <= step ? "reached" : ""}
                key={label}
              >
                <span>
                  {i + first < step ? (
                    <CheckCircle2 size={16} aria-hidden="true" />
                  ) : (
                    i + 1
                  )}
                </span>
                <b>{label}</b>
              </li>
            ))}
          </ol>
          <div aria-live="polite" className="sr-only">
            Step {step - first + 1} of {steps.length - first}: {steps[step]}
          </div>
          <p className="tour-step-caption">
            {steps[step]} · {step - first + 1} / {steps.length - first}
          </p>
          <h2 id="onboarding-heading" tabIndex={-1}>
            {titles[step]}
          </h2>
          <p>{descriptions[step]}</p>
          {step === 0 ? (
            <ProfileSetup
              name={name}
              department={department}
              chosen={chosen}
              machines={machines}
              onName={setName}
              onDepartment={setDepartment}
              onChosen={setChosen}
            />
          ) : step === 1 ? (
            <RoleIntro role={me.role} />
          ) : step === 2 || step === 3 ? (
            <TourSections
              section={step === 2 ? "core" : "operations"}
              role={me.role}
              demoCount={
                me.demoDataset ? Number(me.demoDataset.workOrders) : undefined
              }
            />
          ) : step === 4 ? (
            <>
              <AccessibilityControls {...accessibility} />
              <div className="tour-access-tips">
                <article>
                  <Keyboard size={20} aria-hidden="true" />
                  <div>
                    <h3>Work with the keyboard</h3>
                    <p>
                      Tab and Shift+Tab move through controls. Enter activates
                      buttons. Escape closes the filter panel or report dialog
                      and returns focus to its opening control.
                    </p>
                  </div>
                </article>
                <article>
                  <Eye size={20} aria-hidden="true" />
                  <div>
                    <h3>Clear status, less motion</h3>
                    <p>
                      Status labels include text alongside color. Important
                      errors and updates are announced to screen readers. Motion
                      follows your device’s reduced-motion preference.
                    </p>
                  </div>
                </article>
                <article>
                  <MousePointer2 size={20} aria-hidden="true" />
                  <div>
                    <h3>Search without visual noise</h3>
                    <p>
                      Search fields keep focus within their border. Dashboard
                      filters open only when you need them; Apply saves your
                      choices and Cancel or Escape leaves your view unchanged.
                    </p>
                  </div>
                </article>
              </div>
            </>
          ) : (
            <>
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
                    ? "Pick the machine, describe what you noticed and attach a clear photo. A manager decides what happens next."
                    : me.role === "worker"
                      ? "Accept a job if you are responsible. Return work that belongs to another specialist with a clear reason. Submit the repair for manager verification."
                      : "Review evidence and check for duplicate or previously repaired faults, then assign the right worker. Verify repairs before closing them."}
                </p>
              </div>
              <div className="tour-final-notes">
                <strong>Keep these three things in mind</strong>
                <ul>
                  <li>
                    Your role controls which sections and actions you can use.
                  </li>
                  <li>
                    Choose up to 5 JPEG, PNG or WebP images, each no larger than
                    5 MB. Oversized files are rejected before upload.
                  </li>
                  <li>
                    Demo records are fictional. Deadlines flag overdue work and
                    never hide an unresolved fault.
                  </li>
                </ul>
              </div>
            </>
          )}
          {error && (
            <div className="notice error" role="alert">
              {error}
            </div>
          )}
          <div className="onboarding-actions">
            {step > first && (
              <button disabled={busy} onClick={() => setStep(step - 1)}>
                Back
              </button>
            )}
            <button
              className="primary"
              disabled={
                busy || (step === 0 && (name.trim().length < 2 || !department))
              }
              onClick={() => (step < 5 ? setStep(step + 1) : finish())}
            >
              {busy
                ? "Saving your profile…"
                : step === 5
                  ? replay
                    ? "Back to workspace"
                    : "Open my workspace"
                  : "Continue"}
              <ArrowRight size={17} aria-hidden="true" />
            </button>
          </div>
          <small className="helper">
            {replay
              ? "You can revisit this guide anytime. Your saved profile is unchanged."
              : "Your profile is saved when you choose “Open my workspace”. Reading preferences are saved on this device as you change them."}
          </small>
        </div>
      </section>
    </main>
  );
}
