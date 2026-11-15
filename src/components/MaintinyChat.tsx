import {useEffect,useRef} from 'react';
import {ArrowUpRight,Bot,History,Plus,Send,Trash2} from 'lucide-react';
import {AssistantDraft} from './AssistantDraft';
import type {MaintinyState,R} from './useMaintiny';
type Props={state:MaintinyState;compact?:boolean;role:string;api:(p:string,b?:R)=>Promise<any>;onSource:(s:R)=>void;onCreated:(id:string)=>void;onReview:(d:R)=>Promise<void>;onRefresh:()=>Promise<void>;onDelete:(r:R)=>void;onHistory?:()=>void};
export function MaintinyChat({state:s,compact=false,role,api,onSource,onCreated,onReview,onRefresh,onDelete,onHistory}:Props){
  const log=useRef<HTMLDivElement>(null),field=useRef<HTMLTextAreaElement>(null);
  useEffect(()=>{if(log.current)log.current.scrollTop=log.current.scrollHeight},[s.messages,s.busy,s.loading]);
  const Heading=compact?'h3':'h2';
  const prompts=role==='reporter'?['Find hydraulic press assets','Help me draft a demo fault report']:['Show demo work awaiting verification','Which demo parts need replenishment?','Find demo work assigned to Meera'];
  return <div className="maintiny-chat">
    <header className="maintiny-chat-heading"><div><Heading>{s.current?.title||'New conversation'}</Heading><small>{s.busy?'Preparing your reply…':s.current?'Saved privately to your account':'Start a chat. Replies are saved automatically.'}</small></div>
      <div className="maintiny-tools">
        {onHistory&&<button title="Saved chats" aria-label="Open saved chats" onClick={onHistory}><History size={17}/></button>}
        {s.current&&<button title="Delete chat" aria-label="Delete current conversation" onClick={()=>onDelete(s.current!)}><Trash2 size={16}/></button>}
        <button disabled={s.busy||s.loading} onClick={()=>{s.newChat();requestAnimationFrame(()=>field.current?.focus())}} aria-label="New conversation"><Plus size={16}/>{!compact&&<span>New chat</span>}</button>
      </div>
    </header>
    {s.status?.dataScope==='demo'&&<p className="maintiny-scope">Demo records only. Keep personal and confidential information out of chat.</p>}
    <div ref={log} className="maintiny-log assistant-transcript" role="log" aria-label="Maintiny conversation" aria-live="polite" aria-relevant="additions text" aria-busy={s.busy||s.loading} tabIndex={0}>
      {s.loading?<p className="maintiny-loading" role="status">Loading saved conversation…</p>:!s.messages.length&&!s.busy&&<div className="maintiny-welcome"><span className="maintiny-bot-mark"><Bot size={28}/></span><h3>What needs attention this shift?</h3><p>Find a repair, check parts or prepare a request. You review every proposed action.</p><div className="maintiny-starters">{prompts.map(p=><button key={p} disabled={!s.status?.configured} onClick={()=>void s.send(p)}>{p}<ArrowUpRight size={14}/></button>)}</div></div>}
      {s.messages.map(m=><article key={m.id} className={'assistant-message '+m.role+(m.unavailable?' maintiny-unavailable':'')}><strong>{m.role==='user'?'You':'Maintiny'}</strong><p>{m.text}</p>
        {!!m.sources?.length&&<div className="assistant-sources" aria-label="Source records">{m.sources.map(source=><button key={source.id||source.page} onClick={()=>onSource(source)}>{source.label}<ArrowUpRight size={13}/></button>)}</div>}
        {m.drafts?.map(d=>d.expired?<p className="maintiny-expired" key={d.id}>This draft has expired. Ask Maintiny to prepare a new one.</p>:<AssistantDraft key={d.id} draft={d} api={api} onCreated={onCreated} onReview={onReview} onRefresh={onRefresh}/>)}
      </article>)}
      {s.busy&&<p className="assistant-thinking" role="status">Checking permitted records and preparing your answer…</p>}
    </div>
    {s.error&&<div className="maintiny-error notice error" role="alert"><p>{s.error}</p><button disabled={s.busy||s.loading} onClick={()=>s.current?void s.select(s.current):void s.initialize()}>Reload</button></div>}
    <form className="assistant-composer maintiny-composer" onSubmit={e=>{e.preventDefault();void s.send()}}>
      <label htmlFor="maintiny-message">Message Maintiny</label><div><textarea id="maintiny-message" ref={field} rows={2} maxLength={1200} value={s.input} disabled={s.busy||s.loading||s.current?.full} placeholder="Ask about work, equipment or planning…" onChange={e=>s.setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();void s.send()}}}/><button className="primary" type="submit" aria-label="Send message" disabled={s.busy||s.loading||!s.input.trim()||!s.status?.configured||s.current?.full}><Send size={17}/><span className="maintiny-send-label">Send</span></button></div>
      <small>{s.current?.full?'This chat is full. Start a new conversation.':`Enter to send · Shift+Enter for a new line · ${s.input.length}/1200`}</small>
    </form>
  </div>;
}
