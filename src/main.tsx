import React, { useState, useEffect, useRef, useId } from "react";
import { createRoot } from "react-dom/client";
import {
  Wrench,
  LayoutDashboard,
  Inbox,
  ClipboardList,
  Settings,
  Plus,
  Search,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  LogOut,
  X,
  ChevronRight,
  Factory,
  ImagePlus,
  Loader2,
  ArrowLeft,
} from "lucide-react";
import "./style.css";
import { Onboarding } from "./components/Onboarding";
import { PhotoInput } from "./components/PhotoInput";
import { validateImages } from "./uploads";
type Config = {
  apiUrl: string;
  region: string;
  clientId: string;
  userPoolId: string;
};
type Item = Record<string, any>;
let config: Config;
let token = sessionStorage.getItem("shiftfix-token") || "";
async function cognito(action: string, body: Item) {
  let r = await fetch(`https://cognito-idp.${config.region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${action}`,
    },
    body: JSON.stringify(body),
  });
  let d = await r.json();
  if (!r.ok) throw Error(d.message || d.__type || "Authentication failed");
  return d;
}
async function api(path: string, body?: Item, key?: string) {
  let r = await fetch(config.apiUrl + path, {
    method: body ? "POST" : "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let d = await r.json();
  if (!r.ok) {
    if (r.status === 401) {
      token = "";
      sessionStorage.removeItem("shiftfix-token");
      window.dispatchEvent(new Event("signed-out"));
    }
    throw Error(d.message || d.error || "Request failed");
  }
  return d;
}
const roleLabels: Item = {
  admin: "Admin",
  manager: "Manager",
  worker: "Worker",
  reporter: "Reporter",
};
const labels: Item = {
  pending_review: "New report",
  needs_details: "Needs details",
  open: "Open",
  in_progress: "In progress",
  awaiting_verification: "Verify repair",
  closed: "Closed",
  rejected: "Rejected",
  merged: "Merged",
};
const fmt = (s: string) =>
  s
    ? new Date(s).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Not scheduled";
function Login({ onLogin }: { onLogin: () => void }) {
  const [mode, setMode] = useState("login"),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [code, setCode] = useState(""),
    [err, setErr] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      if (mode === "signup") {
        await cognito("SignUp", {
          ClientId: config.clientId,
          Username: email,
          Password: password,
          UserAttributes: [
            { Name: "email", Value: email },
            { Name: "name", Value: name },
          ],
        });
        setMode("confirm");
      } else if (mode === "confirm") {
        await cognito("ConfirmSignUp", {
          ClientId: config.clientId,
          Username: email,
          ConfirmationCode: code,
        });
        setMode("login");
        setErr("Email confirmed. Sign in to continue.");
      } else {
        let d = await cognito("InitiateAuth", {
          ClientId: config.clientId,
          AuthFlow: "USER_PASSWORD_AUTH",
          AuthParameters: { USERNAME: email, PASSWORD: password },
        });
        if (!d.AuthenticationResult)
          throw Error(
            "This account needs a password reset. Use a newly registered account.",
          );
        token = d.AuthenticationResult.IdToken;
        sessionStorage.setItem("shiftfix-token", token);
        onLogin();
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <a className="skip-link" href="#sign-in">
        Skip to sign in
      </a>
      <section className="login-story">
        <img
          className="login-factory"
          src="/assets/factory-machines.jpg"
          alt="Illustrative clean factory aisle with CNC machinery"
        />
        <div className="login-photo-shade" />
        <div className="brand">
          <span>
            <Wrench />
          </span>
          ShiftFix
        </div>
        <div>
          <p className="mono">FACTORY MAINTENANCE</p>
          <h1>
            Every fault.
            <br />
            An owner.
            <br />A verified fix.
          </h1>
          <p>
            Keep repairs moving from the factory floor to the next shift.
            Evidence, accountability, and deadlines in one place.
          </p>
          <div className="steps">
            <span>01 Report</span>
            <ChevronRight />
            <span>02 Repair</span>
            <ChevronRight />
            <span>03 Verify</span>
          </div>
        </div>
        <small>
          Built for the people who keep things running.
          <br />
          <a
            href="https://www.pexels.com/photo/industrial-factory-with-modern-cnc-machines-37561815/"
            target="_blank"
            rel="noreferrer"
          >
            Factory photography: YIHAI LASER / Pexels
          </a>
        </small>
      </section>
      <main className="login-form" id="sign-in" tabIndex={-1}>
        <div className="form-wrap">
          <Factory size={32} color="#ed6327" />
          <h2>
            {mode === "signup"
              ? "Create your account"
              : mode === "confirm"
                ? "Check your inbox"
                : "Welcome to ShiftFix"}
          </h2>
          <p>
            {mode === "confirm"
              ? "Enter the verification code sent to your email."
              : "Your next shift starts with a clear handover."}
          </p>
          <form onSubmit={submit} aria-busy={busy}>
            {mode === "signup" && (
              <label>
                Full name
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
            )}
            <label>
              Work email
              <input
                required
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            {mode === "confirm" ? (
              <label>
                Verification code
                <input
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  autoComplete="one-time-code"
                />
              </label>
            ) : (
              <label>
                Password
                <input
                  required
                  type="password"
                  minLength={mode === "signup" ? 12 : 1}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={
                    mode === "signup" ? "new-password" : "current-password"
                  }
                />
              </label>
            )}
            {mode === "confirm" && (
              <button
                type="button"
                className="link"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await cognito("ResendConfirmationCode", {
                      ClientId: config.clientId,
                      Username: email,
                    });
                    setErr(
                      "A new verification code has been sent. Check your inbox and spam folder.",
                    );
                  } catch (e: any) {
                    setErr(e.message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Resend verification code
              </button>
            )}
            {mode === "signup" && (
              <small>
                At least 12 characters, including uppercase, lowercase, a number
                and a symbol.
              </small>
            )}
            {err && (
              <div role="alert" className="notice">
                {err}
              </div>
            )}
            <button className="primary wide" disabled={busy}>
              {busy ? <Loader2 className="spin" /> : null}
              {mode === "signup"
                ? "Create account"
                : mode === "confirm"
                  ? "Verify email"
                  : "Sign in"}
              <ChevronRight size={16} />
            </button>
          </form>
          <button
            className="link"
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setErr("");
            }}
          >
            {mode === "login"
              ? "New here? Create an account"
              : "Back to sign in"}
          </button>
          {mode === "login" && (
            <button
              className="link"
              onClick={() => {
                setMode("confirm");
                setErr("");
              }}
            >
              Already have a verification code?
            </button>
          )}
          <p className="footnote">
            Role-based access · Private photo evidence · Automatic escalation
          </p>
        </div>
      </main>
    </div>
  );
}
function App() {
  let [logged, setLogged] = useState(!!token),
    [me, setMe] = useState<Item | null>(null),
    [items, setItems] = useState<Item[]>([]),
    [machines, setMachines] = useState<Item[]>([]),
    [users, setUsers] = useState<Item[]>([]),
    [selected, setSelected] = useState<Item | null>(null),
    [page, setPage] = useState("Review inbox"),
    [tab, setTab] = useState("All requests"),
    [search, setSearch] = useState(""),
    [priority, setPriority] = useState("all"),
    [err, setErr] = useState(""),
    [busy, setBusy] = useState(false),
    [report, setReport] = useState(false),
    [reason, setReason] = useState(""),
    [assignee, setAssignee] = useState(""),
    [target, setTarget] = useState(""),
    [files, setFiles] = useState<File[]>([]),
    [loading, setLoading] = useState(false),
    [announcement, setAnnouncement] = useState("");
  const supervisor = ["admin", "manager"].includes(me?.role || "");
  const admin = me?.role === "admin";
  const [contrast, setContrast] = useState(
    localStorage.getItem("shiftfix-contrast") === "true",
  );
  const [largeText, setLargeText] = useState(
    localStorage.getItem("shiftfix-large-text") === "true",
  );
  useEffect(() => {
    document.body.dataset.contrast = String(contrast);
    document.body.dataset.largeText = String(largeText);
    localStorage.setItem("shiftfix-contrast", String(contrast));
    localStorage.setItem("shiftfix-large-text", String(largeText));
  }, [contrast, largeText]);
  useEffect(() => {
    if (selected) document.getElementById("detail-heading")?.focus();
  }, [selected?.id]);
  useEffect(() => {
    let f = () => {
      setLogged(false);
      setMe(null);
    };
    window.addEventListener("signed-out", f);
    return () => window.removeEventListener("signed-out", f);
  }, []);
  async function load() {
    setLoading(true);
    try {
      let [m, w, ms] = await Promise.all([
        api("/me"),
        api("/workorders"),
        api("/machines"),
      ]);
      setMe(m);
      setItems(w.items);
      setMachines(ms.items);
      if (["admin", "manager"].includes(m.role)) {
        let u = await api("/users");
        setUsers(u.items);
      } else setPage("Work orders");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (logged) load();
  }, [logged]);
  useEffect(() => {
    document.title = page + " | ShiftFix";
  }, [page]);
  async function detail(id: string) {
    try {
      let d = await api("/workorders/" + id);
      setSelected(d);
      setReason("");
      setFiles([]);
      setAssignee(d.assigneeId || "");
      setTarget("");
    } catch (e: any) {
      setErr(e.message);
    }
  }
  async function upload(fs: File[]) {
    if (!fs.length) return [];
    validateImages(fs);
    let d = await api("/uploads", {
      files: fs.map((f) => ({ name: f.name, type: f.type, size: f.size })),
    });
    for (let i = 0; i < fs.length; i++) {
      let form = new FormData();
      for (let [k, v] of Object.entries(d.items[i].fields))
        form.append(k, String(v));
      form.append("file", fs[i]);
      let r = await fetch(d.items[i].url, { method: "POST", body: form });
      if (!r.ok) throw Error("Photo upload failed. Please retry.");
    }
    return d.items.map(({ key, name, type, size }: Item) => ({
      key,
      name,
      type,
      size,
    }));
  }
  async function act(action: string) {
    if (!selected) return;
    setBusy(true);
    setErr("");
    try {
      let attachments = action === "submit" ? await upload(files) : undefined;
      await api(`/workorders/${selected.id}/actions`, {
        action,
        version: selected.version,
        reason,
        assigneeId: assignee,
        assigneeName: users.find((u) => u.id === assignee)?.name,
        targetId: target,
        ...(attachments ? { attachments } : {}),
      });
      await load();
      await detail(selected.id);
      setAnnouncement("Work order updated successfully.");
    } catch (e: any) {
      setErr(e.message);
      if (e.message.includes("changed")) await detail(selected.id);
    } finally {
      setBusy(false);
    }
  }
  if (!logged) return <Login onLogin={() => setLogged(true)} />;
  if (me?.onboardingComplete === false)
    return (
      <Onboarding
        me={me}
        machines={machines}
        save={(v) => api("/onboarding", v)}
        onDone={load}
        onSignOut={() => {
          token = "";
          sessionStorage.removeItem("shiftfix-token");
          setLogged(false);
          setMe(null);
        }}
      />
    );
  let live = items.filter(
      (w) => !["closed", "rejected", "merged"].includes(w.status),
    ),
    review = live.filter(
      (w) =>
        ["pending_review", "awaiting_verification"].includes(w.status) ||
        w.assignmentStatus === "returned" ||
        w.possibleDuplicate ||
        w.overdue,
    ),
    filtered = (page === "Review inbox" ? review : items)
      .filter(
        (w) =>
          !search ||
          [w.number, w.title, w.machineId, w.assigneeName]
            .join(" ")
            .toLowerCase()
            .includes(search.toLowerCase()),
      )
      .filter((w) => priority === "all" || w.priority === priority)
      .filter(
        (w) =>
          tab === "All requests" ||
          (tab === "New reports" && w.status === "pending_review") ||
          (tab === "Duplicates" && w.possibleDuplicate) ||
          (tab === "Returned" && w.assignmentStatus === "returned") ||
          (tab === "Verification" && w.status === "awaiting_verification"),
      );
  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>
      <aside aria-label="Workspace navigation">
        <div className="brand">
          <span>
            <Wrench />
          </span>
          <div>
            ShiftFix<small>Maintenance operations</small>
          </div>
        </div>
        <nav aria-label="Main navigation">
          {[
            ["Overview", LayoutDashboard],
            ...(supervisor ? [["Review inbox", Inbox]] : []),
            ["Work orders", ClipboardList],
            ["Machines", Settings],
            ["Help & accessibility", AlertCircle],
          ].map(([n, I]: any) => (
            <button
              key={n}
              aria-current={page === n ? "page" : undefined}
              className={page === n ? "active" : ""}
              onClick={() => {
                setPage(n);
                setSelected(null);
                setTab("All requests");
              }}
            >
              <I size={20} />
              {n}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="avatar">
            {(me?.name || "S").slice(0, 2).toUpperCase()}
          </div>
          <div>
            <strong>{me?.name || "Loading…"}</strong>
            <small>{roleLabels[me?.role] || "Connecting"}</small>
          </div>
          <button
            title="Sign out"
            onClick={() => {
              token = "";
              sessionStorage.removeItem("shiftfix-token");
              setLogged(false);
              setMe(null);
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main id="main-content" tabIndex={-1}>
        <header>
          <span>
            Operations <ChevronRight size={16} />
            <b>{page}</b>
          </span>
          <span>
            <Factory size={18} /> Plant 01
          </span>
        </header>
        <div className="content">
          {page === "Overview" && (
            <section className="factory-banner">
              <img
                src="/assets/factory-floor.jpg"
                alt="Illustrative factory floor with modern production machinery"
              />
              <div>
                <span>PLANT 01 · MAINTENANCE WORKSPACE</span>
                <h2>
                  A clear handover.
                  <br />A better next shift.
                </h2>
                <p>
                  One place for your people, your machines, and every repair in
                  between.
                </p>
              </div>
              <small>Illustrative photography · YIHAI LASER / Pexels</small>
            </section>
          )}
          <div className="heading">
            <div>
              <h1>{page}</h1>
              <p>
                {me?.role === "reporter"
                  ? "Report what you notice. Follow every update."
                  : me?.role === "worker"
                    ? "Your assignments, evidence, and shift handover."
                    : "Keep every repair moving. Nothing lost between shifts."}
              </p>
            </div>
            <button className="primary" onClick={() => setReport(true)}>
              <Plus size={18} />
              Report fault
            </button>
          </div>
          {err && (
            <div role="alert" className="notice error">
              {err}
              <button aria-label="Dismiss error" onClick={() => setErr("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className="stats">
            {[
              [ClipboardList, "Needs review", review.length],
              [
                RefreshCw,
                "In progress",
                live.filter((w) => w.status === "in_progress").length,
              ],
              [AlertCircle, "Overdue", live.filter((w) => w.overdue).length],
              [
                CheckCircle2,
                "Closed today",
                items.filter(
                  (w) =>
                    w.status === "closed" &&
                    w.closedAt &&
                    new Date(w.closedAt).toDateString() ===
                      new Date().toDateString(),
                ).length,
              ],
            ].map(([I, l, n]: any) => (
              <div key={l}>
                <I size={26} />
                <div>
                  <span>{l}</span>
                  <strong>{String(n).padStart(2, "0")}</strong>
                </div>
              </div>
            ))}
          </div>
          {page === "Help & accessibility" ? (
            <section className="panel help-panel">
              <h2>Make ShiftFix work for you.</h2>
              <p>
                Keyboard-friendly controls, clear decisions, and a workspace you
                can read comfortably.
              </p>
              <div className="preference">
                <div>
                  <h3>High contrast</h3>
                  <p>
                    Stronger text, borders, and status labels. Status is always
                    written in text, not just color.
                  </p>
                </div>
                <button
                  aria-pressed={contrast}
                  onClick={() => setContrast(!contrast)}
                >
                  {contrast ? "High contrast on" : "Turn on high contrast"}
                </button>
              </div>
              <div className="preference">
                <div>
                  <h3>Larger interface text</h3>
                  <p>
                    Increase text in tables, forms, and repair details. Browser
                    zoom is also supported.
                  </p>
                </div>
                <button
                  aria-pressed={largeText}
                  onClick={() => setLargeText(!largeText)}
                >
                  {largeText ? "Larger text on" : "Use larger text"}
                </button>
              </div>
              <h3>Your role: {roleLabels[me?.role]}</h3>
              <p>
                Admins manage access and operations. Managers review, assign and
                verify. Workers carry out assigned repairs. Reporters submit
                faults and track their own reports.
              </p>
              <h3>Keyboard navigation</h3>
              <p>
                Use Tab and Shift+Tab to move between controls, Enter to
                activate, and Escape to close the fault report. The report form
                keeps focus inside and returns it to the opening control when
                closed.
              </p>
              <h3>Evidence and completed repairs</h3>
              <p>
                Choose up to 5 JPEG, PNG or WebP photos, each no larger than 5
                MB. Oversized files are rejected before upload. A previously
                repaired fault is flagged for manager review; it might be a new
                recurrence and is never automatically discarded.
              </p>
              <h3>Your profile</h3>
              <p>
                {me?.profile?.displayName || me?.name} ·{" "}
                {me?.profile?.department || "Department not set"}
              </p>
            </section>
          ) : page === "Machines" ? (
            <section className="panel machines">
              <h2>Machine registry</h2>
              <p>Prototype registry for Plant 01.</p>
              {machines.map((m) => (
                <div className="machine" key={m.id}>
                  <Factory />
                  <div>
                    <strong>
                      {m.id} · {m.name}
                    </strong>
                    <small>{m.location}</small>
                  </div>
                  <button
                    onClick={() => {
                      setPage("Work orders");
                      setSearch(m.id);
                    }}
                  >
                    View work orders
                    <ChevronRight size={16} />
                  </button>
                </div>
              ))}
            </section>
          ) : (
            <>
              <div className="toolbar">
                <div className="tabs">
                  {[
                    "All requests",
                    "New reports",
                    "Duplicates",
                    "Returned",
                    "Verification",
                  ].map((t) => (
                    <button
                      key={t}
                      aria-pressed={tab === t}
                      className={tab === t ? "chosen" : ""}
                      onClick={() => setTab(t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
                <div className="filters">
                  <label className="search">
                    <Search size={17} />
                    <input
                      aria-label="Search work orders"
                      placeholder="Search WO, machine, or keyword…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                  <select
                    aria-label="Filter priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="all">Priority: All</option>
                    {["low", "medium", "high", "critical"].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                  <button
                    aria-label="Refresh work orders"
                    onClick={() => {
                      load();
                      if (selected) detail(selected.id);
                    }}
                  >
                    <RefreshCw size={17} className={loading ? "spin" : ""} />
                  </button>
                </div>
              </div>
              <div className={"workspace " + (selected ? "has-detail" : "")}>
                <section className="panel list">
                  <table>
                    <caption className="sr-only">
                      Work orders. Open a request to review its evidence and
                      history.
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Request</th>
                        <th scope="col">Priority</th>
                        <th scope="col">Owner</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((w) => (
                        <tr
                          onClick={() => detail(w.id)}
                          className={selected?.id === w.id ? "selected" : ""}
                          key={w.id}
                        >
                          <td>
                            <div className="request">
                              <ClipboardList size={20} />
                              <div>
                                <button
                                  className="request-button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    detail(w.id);
                                  }}
                                  aria-label={`Open ${w.number}: ${w.title}`}
                                >
                                  {w.title}
                                </button>
                                <small>
                                  {w.number} · {w.machineId} · {w.machineName}
                                </small>
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className={"badge " + w.priority}>
                              {w.priority}
                            </span>
                          </td>
                          <td>{w.assigneeName || "Unassigned"}</td>
                          <td>
                            <span
                              className={
                                "badge " + (w.overdue ? "critical" : "status")
                              }
                            >
                              {w.overdue
                                ? "Overdue"
                                : w.assignmentStatus === "returned"
                                  ? "Returned"
                                  : labels[w.status]}
                            </span>
                            {w.possibleDuplicate && (
                              <small className="duplicate">
                                Possible duplicate
                              </small>
                            )}
                            {w.possibleResolved && (
                              <small className="duplicate">
                                Previously repaired · Review
                              </small>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!filtered.length && (
                    <div className="empty">
                      <Inbox size={38} />
                      <h3>
                        {loading
                          ? "Loading work orders…"
                          : "A clear queue starts here."}
                      </h3>
                      <p>
                        {search || tab !== "All requests"
                          ? "No work orders match these filters."
                          : "Report your first machine fault to start tracking repairs."}
                      </p>
                      <button onClick={() => setReport(true)}>
                        <Plus size={16} />
                        Report a fault
                      </button>
                    </div>
                  )}
                  <footer>
                    Showing {filtered.length}{" "}
                    {page === "Review inbox"
                      ? "requests requiring attention"
                      : "work orders"}
                  </footer>
                </section>
                {selected && (
                  <section className="panel detail">
                    <button
                      className="mobile-back"
                      onClick={() => setSelected(null)}
                    >
                      <ArrowLeft size={16} /> Back to work orders
                    </button>
                    <div className="detail-title">
                      <div>
                        <span className="mono muted">{selected.number}</span>
                        <h2 id="detail-heading" tabIndex={-1}>
                          {selected.title}
                        </h2>
                      </div>
                      <button
                        title="Close detail"
                        onClick={() => setSelected(null)}
                      >
                        <X size={18} />
                      </button>
                    </div>
                    {selected.possibleResolved && (
                      <div className="notice">
                        <strong>Similar repair already completed</strong>
                        <p>
                          This may be an already-handled fault or a new
                          recurrence. A Manager must review before closing it.
                        </p>
                        {supervisor &&
                          selected.resolvedCandidates?.map((r: Item) => (
                            <button key={r.id} onClick={() => detail(r.id)}>
                              View {r.number} · {r.title}
                            </button>
                          ))}
                      </div>
                    )}
                    <div className="detail-machine">
                      <Factory size={19} />
                      <b>{selected.machineId}</b>
                      {selected.machineName}
                      <span className={"badge " + selected.priority}>
                        {selected.priority}
                      </span>
                    </div>
                    <h4>Description</h4>
                    <p>{selected.description}</p>
                    {selected.mergedInto && (
                      <p>
                        Merged into{" "}
                        <button onClick={() => detail(selected.mergedInto)}>
                          View surviving work order
                        </button>
                      </p>
                    )}
                    {selected.relatedId && (
                      <button onClick={() => detail(selected.relatedId)}>
                        View related work order
                      </button>
                    )}
                    {selected.linkedReports?.length > 0 && (
                      <div className="notice">
                        Merged reports:{" "}
                        {selected.linkedReports.map((r: Item) => (
                          <button key={r.id} onClick={() => detail(r.id)}>
                            {r.number || r.id}
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="photos">
                      {selected.attachments?.map((a: Item) => (
                        <a
                          key={a.key}
                          href={a.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <img src={a.url} alt={a.name} />
                          <small>
                            {a.stage === "after"
                              ? "Repair evidence"
                              : "Reported evidence"}
                          </small>
                        </a>
                      ))}
                    </div>
                    <dl>
                      <dt>Reported by</dt>
                      <dd>{selected.reporterName}</dd>
                      <dt>Work status</dt>
                      <dd>{labels[selected.status]}</dd>
                      <dt>Assignment</dt>
                      <dd>{selected.assignmentStatus?.replaceAll("_", " ")}</dd>
                      <dt>Assigned to</dt>
                      <dd>{selected.assigneeName || "Unassigned"}</dd>
                      <dt>Due</dt>
                      <dd className={selected.overdue ? "orange" : ""}>
                        {fmt(selected.deadline)}
                      </dd>
                    </dl>
                    {!["closed", "rejected", "merged"].includes(
                      selected.status,
                    ) && (
                      <div className="action-form">
                        {supervisor && (
                          <>
                            <label>
                              Responsible worker
                              <select
                                value={assignee}
                                onChange={(e) => setAssignee(e.target.value)}
                              >
                                <option value="">Select worker</option>
                                {users
                                  .filter((u) => u.role === "worker")
                                  .map((u) => (
                                    <option value={u.id} key={u.id}>
                                      {u.name} · {u.role}
                                    </option>
                                  ))}
                              </select>
                            </label>
                            {selected.possibleDuplicate && (
                              <label>
                                Related work order
                                <select
                                  value={target}
                                  onChange={(e) => setTarget(e.target.value)}
                                >
                                  <option value="">Choose merge target</option>
                                  {items
                                    .filter(
                                      (w) =>
                                        w.id !== selected.id &&
                                        w.machineId === selected.machineId &&
                                        ![
                                          "merged",
                                          "rejected",
                                          "closed",
                                        ].includes(w.status),
                                    )
                                    .map((w) => (
                                      <option key={w.id} value={w.id}>
                                        {w.number} · {w.title}
                                      </option>
                                    ))}
                                </select>
                              </label>
                            )}
                          </>
                        )}
                        <label>
                          Notes / decision reason
                          <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Explain the decision or record repair details…"
                            rows={3}
                          />
                        </label>
                        {selected.assigneeId === me?.id && (
                          <PhotoInput
                            files={files}
                            onChange={setFiles}
                            label="Attach repair evidence"
                          />
                        )}
                        <div className="actions">
                          {supervisor && (
                            <>
                              {["pending_review", "needs_details"].includes(
                                selected.status,
                              ) && (
                                <button
                                  className="primary"
                                  disabled={busy || !assignee}
                                  onClick={() => act("approve")}
                                >
                                  Approve & assign
                                </button>
                              )}
                              {selected.status === "awaiting_verification" && (
                                <>
                                  <button
                                    className="primary"
                                    disabled={busy}
                                    onClick={() => act("verify")}
                                  >
                                    Accept repair
                                  </button>
                                  <button
                                    disabled={busy || !reason.trim()}
                                    onClick={() => act("rework")}
                                  >
                                    Return for rework
                                  </button>
                                </>
                              )}
                              {((selected.status === "open" &&
                                selected.assignmentStatus === "returned") ||
                                (selected.possibleResolved &&
                                  ["pending_review", "needs_details"].includes(
                                    selected.status,
                                  ))) && (
                                <button
                                  className="primary"
                                  disabled={busy || !reason.trim()}
                                  onClick={() => act("resolve_existing")}
                                >
                                  Confirm already resolved
                                </button>
                              )}
                              {![
                                "pending_review",
                                "needs_details",
                                "awaiting_verification",
                              ].includes(selected.status) && (
                                <button
                                  disabled={busy || !assignee}
                                  onClick={() => act("reassign")}
                                >
                                  Reassign
                                </button>
                              )}
                              {["pending_review", "needs_details"].includes(
                                selected.status,
                              ) && (
                                <>
                                  <button
                                    disabled={busy || !reason.trim()}
                                    onClick={() => act("clarify")}
                                  >
                                    Request details
                                  </button>
                                  <button
                                    className="danger"
                                    disabled={busy || !reason.trim()}
                                    onClick={() => act("reject")}
                                  >
                                    Reject report
                                  </button>
                                </>
                              )}
                              {selected.possibleDuplicate && (
                                <>
                                  <button
                                    disabled={
                                      busy ||
                                      !target ||
                                      !reason.trim() ||
                                      ![
                                        "pending_review",
                                        "needs_details",
                                        "open",
                                      ].includes(selected.status)
                                    }
                                    onClick={() => act("merge")}
                                  >
                                    Merge duplicate
                                  </button>
                                  <button
                                    disabled={busy || !reason.trim()}
                                    onClick={() => act("keep_separate")}
                                  >
                                    Keep separate
                                  </button>
                                </>
                              )}
                            </>
                          )}
                          {selected.assigneeId === me?.id && (
                            <>
                              {selected.assignmentStatus ===
                                "awaiting_acceptance" && (
                                <button
                                  className="primary"
                                  disabled={busy}
                                  onClick={() => act("accept")}
                                >
                                  Accept assignment
                                </button>
                              )}
                              {selected.assignmentStatus === "accepted" &&
                                selected.status === "in_progress" && (
                                  <>
                                    <button
                                      className="primary"
                                      disabled={busy || !reason.trim()}
                                      onClick={() => act("submit")}
                                    >
                                      Submit repair
                                    </button>
                                    <button
                                      disabled={busy || !reason.trim()}
                                      onClick={() => act("block")}
                                    >
                                      Mark blocked
                                    </button>
                                  </>
                                )}
                              {["open", "in_progress"].includes(
                                selected.status,
                              ) &&
                                ["awaiting_acceptance", "accepted"].includes(
                                  selected.assignmentStatus,
                                ) && (
                                  <button
                                    disabled={busy || !reason.trim()}
                                    onClick={() => act("return")}
                                  >
                                    Return assignment
                                  </button>
                                )}
                            </>
                          )}
                          {selected.reporterId === me?.id &&
                            selected.status === "needs_details" && (
                              <button
                                className="primary"
                                disabled={busy || !reason.trim()}
                                onClick={() => act("resubmit")}
                              >
                                Resubmit with details
                              </button>
                            )}
                          <button
                            disabled={busy || !reason.trim()}
                            onClick={() => act("add_note")}
                          >
                            {busy ? "Saving…" : "Add note"}
                          </button>
                        </div>
                      </div>
                    )}
                    {["closed", "rejected"].includes(selected.status) && (
                      <button onClick={() => setReport(true)}>
                        Report follow-up fault
                      </button>
                    )}
                    <div className="activity">
                      <h3>Activity</h3>
                      {selected.activity?.map((a: Item) => (
                        <div key={a.id}>
                          <i />
                          <section>
                            <strong>{a.action.replaceAll("_", " ")}</strong>
                            <small>
                              {fmt(a.at)} · {a.actorName}
                            </small>
                            {a.reason && <p>{a.reason}</p>}
                          </section>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            </>
          )}
          {supervisor && page === "Overview" && (
            <section className="panel team">
              <h2>People & access</h2>
              <p>
                {admin
                  ? "Assign Managers to oversee repairs and Workers to carry out maintenance. Reporters can raise faults."
                  : "Manage Worker and Reporter access. Admins manage Manager access."}{" "}
                Roles are enforced by the backend.
              </p>
              {users.map((u) => (
                <div className="team-row" key={u.id}>
                  <div>
                    <strong>{u.name}</strong>
                    <small>{u.email}</small>
                  </div>
                  <span className="badge status">
                    {roleLabels[u.role] || u.role}
                  </span>
                  {u.role !== "admin" && (admin || u.role !== "manager") && (
                    <label className="role-select">
                      <span className="sr-only">Role for {u.name}</span>
                      <select
                        disabled={busy}
                        value={u.role}
                        onChange={async (e) => {
                          const role = e.target.value;
                          setBusy(true);
                          try {
                            await api(`/users/${u.id}/role`, { role });
                            await load();
                          } catch (e: any) {
                            setErr(e.message);
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        {(admin
                          ? ["reporter", "worker", "manager"]
                          : ["reporter", "worker"]
                        ).map((r) => (
                          <option key={r} value={r}>
                            {roleLabels[r]}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              ))}
            </section>
          )}
        </div>
      </main>
      {report && (
        <Report
          relatedId={
            selected && ["closed", "rejected"].includes(selected.status)
              ? selected.id
              : undefined
          }
          machines={machines}
          items={items}
          upload={upload}
          onClose={() => setReport(false)}
          onCreated={async (w: Item) => {
            setReport(false);
            setPage("Work orders");
            await load();
            detail(w.id);
          }}
        />
      )}
    </div>
  );
}
function Report({
  relatedId,
  machines,
  items,
  upload,
  onClose,
  onCreated,
}: any) {
  let [title, setTitle] = useState(""),
    [machineId, setMachine] = useState(
      items.find((w: Item) => w.id === relatedId)?.machineId ||
        machines[0]?.id ||
        "",
    ),
    [description, setDescription] = useState(""),
    [priority, setPriority] = useState("medium"),
    [category, setCategory] = useState("mechanical"),
    [files, setFiles] = useState<File[]>([]),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState("");
  const [key] = useState(crypto.randomUUID());
  const uploaded = useRef<any[] | null>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const modal = document.querySelector<HTMLElement>('[role="dialog"]');
    const shell = document.querySelector<HTMLElement>(".shell");
    const main = shell?.querySelector("main");
    const aside = shell?.querySelector("aside");
    if (main) main.inert = true;
    if (aside) aside.inert = true;
    const get = () =>
      Array.from(
        modal?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
        ) || [],
      ).filter((e) => e.offsetParent !== null);
    get()[0]?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) {
        e.preventDefault();
        onClose();
      }
      if (e.key === "Tab") {
        const f = get(),
          first = f[0],
          last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      if (main) main.inert = false;
      if (aside) aside.inert = false;
      previous?.focus();
    };
  }, [busy]);
  let related = items.filter(
    (w: Item) =>
      w.machineId === machineId &&
      !["closed", "merged", "rejected"].includes(w.status),
  );
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      let attachments = uploaded.current ?? (await upload(files));
      uploaded.current = attachments;
      let w = await api(
        "/workorders",
        {
          title,
          machineId,
          description,
          priority,
          category,
          attachments,
          relatedId,
        },
        key,
      );
      onCreated(w);
    } catch (e: any) {
      setErr(e.message);
      setBusy(false);
    }
  }
  return (
    <div className="overlay">
      <section
        className="modal"
        aria-busy={busy}
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-title"
      >
        <div className="detail-title">
          <div>
            <small className="mono muted">NEW WORK REQUEST</small>
            <h2 id="report-title">Report a machine fault</h2>
          </div>
          <button aria-label="Close report" disabled={busy} onClick={onClose}>
            <X />
          </button>
        </div>
        <p>
          Capture what you see. Your manager will review and assign the
          repair.
        </p>
        <form onSubmit={submit}>
          <fieldset disabled={busy}>
            <label>
              Machine
              <select
                required
                value={machineId}
                onChange={(e) => setMachine(e.target.value)}
              >
                {machines.map((m: Item) => (
                  <option key={m.id} value={m.id}>
                    {m.id} · {m.name}
                  </option>
                ))}
              </select>
            </label>
            {related.length > 0 && (
              <div className="notice">
                {related.length} open issue(s) already exist for this machine:{" "}
                {related.map((w: Item) => w.title).join("; ")}. If this is the
                same fault, add a note to the existing work order instead.
              </div>
            )}
            {items.some(
              (w: Item) =>
                w.machineId === machineId &&
                w.category === category &&
                w.status === "closed",
            ) && (
              <div className="notice" role="status">
                <strong>A similar repair was previously completed.</strong>
                <p>
                  If the fault has returned, describe when it reappeared. A
                  Manager will check the previous repair before deciding whether
                  this is already handled or a new recurrence.
                </p>
              </div>
            )}
            <label>
              Fault title
              <input
                required
                maxLength={150}
                placeholder="e.g. Oil leaking below the main cylinder"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Description
              <textarea
                required
                minLength={10}
                maxLength={4000}
                rows={4}
                placeholder="Where is the fault? When did it start? What did you observe?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <div className="form-grid">
              <label>
                Priority
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                >
                  {["low", "medium", "high", "critical"].map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </label>
              <label>
                Fault category
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {[
                    "mechanical",
                    "electrical",
                    "hydraulic",
                    "instrumentation",
                    "other",
                  ].map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </label>
            </div>
            <PhotoInput
              files={files}
              onChange={(fs) => {
                setFiles(fs);
                uploaded.current = null;
              }}
            />
            {err && (
              <div role="alert" className="notice error">
                {err}
              </div>
            )}
            <div className="modal-footer">
              <button type="button" onClick={onClose}>
                Cancel
              </button>
              <button className="primary" disabled={busy}>
                {busy ? "Uploading & submitting…" : "Submit fault report"}
                <ChevronRight size={16} />
              </button>
            </div>
          </fieldset>
        </form>
      </section>
    </div>
  );
}
fetch("/config.json", { cache: "no-store" })
  .then((r) => r.json())
  .then((c) => {
    config = c;
    createRoot(document.getElementById("root")!).render(<App />);
  })
  .catch(() => {
    document.getElementById("root")!.textContent =
      "ShiftFix could not load its configuration. Please refresh or contact the administrator.";
  });
