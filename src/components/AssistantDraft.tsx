import { useState } from "react";
import { ClipboardList, CheckCircle2, ArrowRight, X } from "lucide-react";
type R = Record<string, any>;
export function AssistantDraft({
  draft,
  api,
  onCreated,
  onReview,
  onRefresh,
}: {
  draft: R;
  api: (path: string, body?: R) => Promise<any>;
  onCreated: (id: string) => void;
  onReview: (draft: R) => Promise<void>;
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [created, setCreated] = useState<R | null>(null),
    [dismissed, setDismissed] = useState(false);
  if (dismissed)
    return (
      <p className="assistant-draft-dismissed">
        Draft dismissed. Nothing was created.
      </p>
    );
  async function review() {
    setBusy(true);
    setError("");
    try {
      await onReview(draft);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const expired = Date.now() / 1000 >= draft.expiresAt;
  const work = draft.kind === "work_order";
  async function confirm() {
    setBusy(true);
    setError("");
    try {
      const r = await api("/assistant/confirm", { draftId: draft.id });
      setCreated(r.workOrder);
      void onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="assistant-draft"
      aria-label={work ? "Work order draft" : "Planning draft"}
    >
      <div className="assistant-draft-title">
        <ClipboardList size={18} aria-hidden="true" />
        <strong>
          {work
            ? "Review work-order draft"
            : draft.kind === "plans"
              ? "Review recurring plan draft"
              : "Review automation draft"}
        </strong>
      </div>
      <dl>
        {Object.entries(draft.payload)
          .filter(([k]) => !["enabled"].includes(k))
          .map(([key, value]) => (
            <div key={key}>
              <dt>
                {(
                  {
                    machineId: "Machine",
                    title: "Title",
                    description: "Description",
                    priority: "Priority",
                    category: "Category",
                    name: "Name",
                    meterId: "Meter",
                    assetId: "Asset",
                    intervalDays: "Repeat every (days)",
                    nextRun: "First run (UTC)",
                  } as R
                )[key] || key}
              </dt>
              <dd>
                {key === "machineId" && draft.context?.machineName
                  ? `${draft.context.machineCode} · ${draft.context.machineName}`
                  : key === "assetId" && draft.context?.assetName
                    ? draft.context.assetName
                    : key === "meterId" && draft.context?.meterName
                      ? draft.context.meterName
                      : String(value)}
              </dd>
            </div>
          ))}
      </dl>
      <p>
        {work
          ? "Creates a new request for manager review. Assignment and repair approval follow the existing workflow."
          : "Starts paused. Review the populated editor and choose Save before this rule exists."}
      </p>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {created ? (
        <div className="assistant-created" role="status">
          <CheckCircle2 size={17} aria-hidden="true" />
          <strong>{created.number} created</strong>
          <button onClick={() => onCreated(created.id)}>
            Open work order <ArrowRight size={15} />
          </button>
          {(created.possibleDuplicate || created.possibleResolved) && (
            <p>
              A similar report or repair was detected. A manager will review it.
            </p>
          )}
        </div>
      ) : (
        <div className="assistant-draft-actions">
          <button disabled={busy} onClick={() => setDismissed(true)}>
            <X size={14} aria-hidden="true" />
            Dismiss
          </button>
          <button
            className="primary"
            disabled={busy || expired}
            onClick={() => (work ? confirm() : review())}
          >
            {expired
              ? "Draft expired"
              : busy
                ? "Creating…"
                : work
                  ? "Confirm create"
                  : "Review in editor"}
          </button>
        </div>
      )}
    </section>
  );
}
