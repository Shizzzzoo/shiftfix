import { useEffect, useRef, useState } from "react";
import {
  ShieldCheck,
  UserRound,
  Save,
  RotateCcw,
  Users,
  CheckCircle2,
} from "lucide-react";
import { ProfileSetup } from "./ProfileSetup";
import { onboardingRoles } from "./WorkspaceTour";
type R = Record<string, any>;
const fields = (me: R) => ({
  displayName: me.profile?.displayName || me.name || "",
  department: me.profile?.department || "",
  machineIds: (me.profile?.machineIds || []) as string[],
  jobTitle: me.profile?.jobTitle || "",
  phone: me.profile?.phone || "",
  shift: me.profile?.shift || "unspecified",
  bio: me.profile?.bio || "",
  version: me.profile?.version || 0,
});
export function Profile({
  me,
  machines,
  api,
  onSaved,
  onAccess,
}: {
  me: R;
  machines: R[];
  api: (path: string, body?: R) => Promise<any>;
  onSaved: (next: R) => void;
  onAccess: () => void;
}) {
  const [draft, setDraft] = useState(() => fields(me));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState("");
  const mounted = useRef(true);
  useEffect(
    () => () => {
      mounted.current = false;
    },
    [],
  );
  const role = onboardingRoles[me.role] || onboardingRoles.reporter;
  const dirty = JSON.stringify(draft) !== JSON.stringify(fields(me));
  useEffect(() => {
    if (!dirty) return;
    const leave = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", leave);
    return () => window.removeEventListener("beforeunload", leave);
  }, [dirty]);
  const update = (key: keyof typeof draft, value: string) => {
    setDraft((old) => ({ ...old, [key]: value }));
    setSuccess("");
  };
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const next = await api("/profile", draft);
      if (!mounted.current) return;
      onSaved(next);
      setDraft(fields(next));
      setSuccess("Your profile has been saved.");
    } catch (e) {
      if (mounted.current) setError((e as Error).message);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <div className="profile-layout">
      <section className="panel profile-editor">
        <div className="profile-summary">
          <div className="profile-avatar" aria-hidden="true">
            {draft.displayName
              .trim()
              .split(/\s+/)
              .slice(0, 2)
              .map((s: string) => s[0])
              .join("")
              .toUpperCase() || <UserRound />}
          </div>
          <div>
            <h2>Your profile</h2>
            <p>Your details help the team recognize you and plan the shift.</p>
          </div>
        </div>
        {error && (
          <div className="notice error" role="alert">
            {error}
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  const next = await api("/me");
                  if (!mounted.current) return;
                  onSaved(next);
                  setDraft(fields(next));
                  setError("");
                } catch (e) {
                  if (mounted.current) setError((e as Error).message);
                } finally {
                  if (mounted.current) setBusy(false);
                }
              }}
            >
              Reload saved profile
            </button>
          </div>
        )}
        {success && (
          <p className="notice success" role="status">
            <CheckCircle2 size={16} aria-hidden="true" />
            {success}
          </p>
        )}
        <form onSubmit={save} aria-label="Edit your profile">
          <fieldset disabled={busy} className="profile-fields">
            <ProfileSetup
              name={draft.displayName}
              department={draft.department}
              chosen={draft.machineIds}
              machines={machines}
              onName={(v) => update("displayName", v)}
              onDepartment={(v) => update("department", v)}
              onChosen={(v) => {
                setDraft((old) => ({ ...old, machineIds: v }));
                setSuccess("");
              }}
            />
            <div className="profile-field-pair">
              <label>
                Job title <span className="optional">Optional</span>
                <input
                  value={draft.jobTitle}
                  maxLength={100}
                  autoComplete="organization-title"
                  onChange={(e) => update("jobTitle", e.target.value)}
                />
              </label>
              <div className="profile-shift-field">
                <label htmlFor="profile-shift">Preferred shift</label>
                <select
                  id="profile-shift"
                  value={draft.shift}
                  onChange={(e) => update("shift", e.target.value)}
                >
                  {[
                    "unspecified",
                    "day",
                    "evening",
                    "night",
                    "rotating",
                    "flexible",
                  ].map((s) => (
                    <option key={s} value={s}>
                      {s === "unspecified"
                        ? "Not specified"
                        : s[0].toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <label>
              Contact phone{" "}
              <span className="optional">
                Optional · visible only on your profile
              </span>
              <input
                type="tel"
                value={draft.phone}
                maxLength={40}
                autoComplete="tel"
                onChange={(e) => update("phone", e.target.value)}
              />
            </label>
            <label>
              About you{" "}
              <span className="optional">
                Optional · skills or handover context, up to 600 characters
              </span>
              <textarea
                rows={3}
                value={draft.bio}
                maxLength={600}
                onChange={(e) => update("bio", e.target.value)}
              />
            </label>
            <small className="profile-privacy">
              Department, job title and preferred shift appear in the management
              roster. Phone and About you stay on your own profile. A preferred
              shift does not change deadlines or permissions.
            </small>
          </fieldset>
          <div className="profile-actions">
            <span role="status">
              {dirty ? "Unsaved changes" : "Profile is up to date"}
            </span>
            <button
              type="button"
              disabled={busy || !dirty}
              onClick={() => {
                setDraft(fields(me));
                setError("");
                setSuccess("");
              }}
            >
              <RotateCcw size={15} aria-hidden="true" />
              Discard changes
            </button>
            <button
              className="primary"
              disabled={
                busy ||
                !dirty ||
                draft.displayName.trim().length < 2 ||
                !draft.department
              }
            >
              <Save size={16} aria-hidden="true" />
              {busy ? "Saving…" : "Save profile"}
            </button>
          </div>
        </form>
      </section>
      <section
        className="panel profile-access"
        aria-labelledby="profile-access-heading"
      >
        <ShieldCheck size={24} aria-hidden="true" />
        <h2 id="profile-access-heading">Account & access</h2>
        <dl>
          <div>
            <dt>Verified email</dt>
            <dd>{me.email}</dd>
          </div>
          <div>
            <dt>Access role</dt>
            <dd>
              <span className="badge status">{role.title}</span>
            </dd>
          </div>
          <div>
            <dt>Workspace</dt>
            <dd>Plant 01</dd>
          </div>
        </dl>
        <p>{role.description}</p>
        <h3>Your access at a glance</h3>
        <ul>
          <li>Report faults and follow your own requests.</li>
          {me.role !== "reporter" && (
            <li>View equipment, inventory, inspections and readings.</li>
          )}
          {["admin", "manager"].includes(me.role) ? (
            <>
              <li>Review requests, assign workers and verify repairs.</li>
              <li>
                {me.role === "admin"
                  ? "Manage Manager, Worker and Reporter access."
                  : "Manage Worker and Reporter access. Admins manage Managers."}
              </li>
            </>
          ) : me.role === "worker" ? (
            <li>Accept and update your own assigned repairs.</li>
          ) : (
            <li>Your reports are reviewed by a Manager before assignment.</li>
          )}
        </ul>
        <div className="profile-access-note">
          <strong>Access is assigned by the team</strong>
          <p>
            Editing your profile or machine preferences does not change your
            role. Contact an Admin or Manager when your responsibilities change.
          </p>
        </div>
        {["admin", "manager"].includes(me.role) && (
          <button onClick={onAccess}>
            <Users size={16} aria-hidden="true" />
            Manage people & access
          </button>
        )}
      </section>
    </div>
  );
}
