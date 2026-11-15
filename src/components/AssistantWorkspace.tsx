import { useEffect, useRef, useState } from "react";
import {
  MessageSquare,
  Send,
  ArrowUpRight,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { AssistantDraft } from "./AssistantDraft";
import { AssistantSearch } from "./AssistantSearch";
type R = Record<string, any>;
type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: R[];
  drafts?: R[];
  model?: string;
};
export function AssistantWorkspace({
  visible,
  me,
  api,
  onSource,
  onCreated,
  onReview,
  onRefresh,
}: {
  visible: boolean;
  me: R;
  api: (path: string, body?: R) => Promise<any>;
  onSource: (source: R) => void;
  onCreated: (id: string) => void;
  onReview: (draft: R) => Promise<void>;
  onRefresh: () => Promise<void>;
}) {
  const [messages, setMessages] = useState<Message[]>([]),
    [input, setInput] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [verification, setVerification] = useState(false),
    [status, setStatus] = useState<R | null>(null);
  const mounted = useRef(true),
    transcript = useRef<HTMLDivElement>(null),
    field = useRef<HTMLTextAreaElement>(null);
  useEffect(
    () => () => {
      mounted.current = false;
    },
    [],
  );
  useEffect(() => {
    if (visible && !status)
      void api("/assistant/status")
        .then((s) => {
          if (mounted.current) setStatus(s);
        })
        .catch((e: Error) => {
          if (mounted.current) setError(e.message);
        });
  }, [visible]);
  useEffect(() => {
    if (visible && messages.length)
      transcript.current?.scrollTo({
        top: transcript.current.scrollHeight,
        behavior: "instant",
      });
  }, [messages, busy, visible]);
  const prompts = [
    "Show my overdue work orders",
    ...(me.role !== "reporter" ? ["Which parts need replenishment?"] : []),
    "Find hydraulic press assets",
    ...(me.role === "admin" || me.role === "manager"
      ? ["Show requests awaiting verification"]
      : []),
  ];
  async function send(e?: React.FormEvent, text?: string) {
    e?.preventDefault();
    const question = (text ?? input).trim();
    if (!question || busy || question.length > 1200) return;
    const id = crypto.randomUUID();
    const recent = messages
      .slice(-6)
      .map((m) => ({ role: m.role, text: m.text.slice(0, 1500) }));
    setMessages((old) => [...old, { id, role: "user", text: question }]);
    setInput("");
    setError("");
    setBusy(true);
    try {
      const r = await api("/assistant/chat", {
        message: question,
        history: recent,
        requestId: id,
      });
      if (!mounted.current) return;
      setVerification(false);
      setMessages((old) => [
        ...old,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: r.reply,
          sources: r.sources || [],
          drafts: r.drafts || [],
          model: r.model,
        },
      ]);
    } catch (e) {
      if (!mounted.current) return;
      const ex = e as Error & { code?: string };
      setError(ex.message);
      if (
        ["MODEL_VERIFICATION_PENDING", "AI_ACCOUNT_RESTRICTED"].includes(
          ex.code || "",
        )
      )
        setVerification(true);
      if (ex.code === "ACCESS_CHANGED") void onRefresh();
      setMessages((old) => old.filter((m) => m.id !== id));
      setInput(question);
    } finally {
      if (mounted.current) {
        setBusy(false);
        field.current?.focus();
      }
    }
  }
  return (
    <section
      hidden={!visible}
      className="assistant-workspace"
      aria-label="Ask ShiftFix workspace"
    >
      <div className="assistant-intro">
        <div>
          <span className="assistant-eyebrow">
            <MessageSquare size={16} aria-hidden="true" />
            ASK SHIFTFIX
          </span>
          <h2>Your maintenance workspace, in plain language.</h2>
          <p>
            Find work, explain its history and prepare requests. Your {me.role}{" "}
            access applies to every answer and action.
          </p>
        </div>
        <div className="assistant-access-label">
          <ShieldCheck size={16} aria-hidden="true" />
          Server-checked access
        </div>
      </div>
      <div className="panel assistant-conversation">
        <div className="assistant-conversation-header">
          <div>
            <strong>Maintenance assistant</strong>
            <small>
              Maintenance assistant · conversation stays in this
              tab
            </small>
          </div>
          <button
            disabled={busy || !messages.length}
            onClick={() => {
              setMessages([]);
              setError("");
              field.current?.focus();
            }}
          >
            <RotateCcw size={15} aria-hidden="true" />
            New conversation
          </button>
        </div>
        {status?.dataScope === "demo" && (
          <div className="notice" role="note">
            This assistant uses fictional demo records. Do not enter personal or
            confidential information. Direct search below covers your normal workspace.
          </div>
        )}
        {verification && (
          <div className="notice assistant-verification" role="status">
            <strong>Assistant access pending</strong>
            <p>
              The model service is currently unavailable. You can
              use direct workspace search below and retry your message later.
            </p>
          </div>
        )}
        <div
          className="assistant-transcript"
          ref={transcript}
          role="log"
          aria-label="Conversation"
          aria-live="polite"
          aria-relevant="additions text"
          tabIndex={0}
        >
          {!messages.length && !busy && (
            <div className="assistant-empty">
              <MessageSquare size={28} aria-hidden="true" />
              <h3>Start with a real maintenance question</h3>
              <p>
                Answers use live tools and link to records you can open.
                Work-order drafts require your confirmation; planning drafts
                open in the normal editor.
              </p>
              <div className="assistant-prompts">
                {prompts.map((p) => (
                  <button key={p} onClick={() => send(undefined, p)}>
                    {p}
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <article className={"assistant-message " + m.role} key={m.id}>
              <strong>{m.role === "user" ? "You" : "Ask ShiftFix"}</strong>
              <p>{m.text}</p>
              {!!m.sources?.length && (
                <div className="assistant-sources" aria-label="Source records">
                  {m.sources.map((s) => (
                    <button key={s.id || s.page} onClick={() => onSource(s)}>
                      {s.label}
                      <ArrowUpRight size={13} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              )}
              {m.drafts?.map((d) => (
                <AssistantDraft
                  key={d.id}
                  draft={d}
                  api={api}
                  onCreated={onCreated}
                  onReview={onReview}
                  onRefresh={onRefresh}
                />
              ))}
            </article>
          ))}
          {busy && (
            <p className="assistant-thinking" role="status">
              Checking permitted records and preparing your answer…
            </p>
          )}
        </div>
        {error && (
          <p className="notice error assistant-error" role="alert">
            {error}
          </p>
        )}
        <form className="assistant-composer" onSubmit={send}>
          <label htmlFor="assistant-message">
            Ask about work, equipment or planning
          </label>
          <div>
            <textarea
              id="assistant-message"
              ref={field}
              rows={2}
              maxLength={1200}
              value={input}
              disabled={busy}
              placeholder="e.g. Find the hydraulic press, then help me draft a report for an oil leak…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button
              className="primary"
              disabled={busy || !input.trim() || !status?.configured}
              type="submit"
            >
              <Send size={17} aria-hidden="true" />
              <span>{busy ? "Working…" : "Ask"}</span>
            </button>
          </div>
          <small>
            Enter to send · Shift+Enter for a new line · {input.length}/1200 · 6
            requests/minute. Review AI suggestions against factory procedures.
          </small>
        </form>
      </div>
      <AssistantSearch role={me.role} api={api} onSource={onSource} />
    </section>
  );
}
