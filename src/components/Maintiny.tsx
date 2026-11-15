import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {Bot,History,Maximize2,X} from 'lucide-react';
import {useMaintiny,type R} from './useMaintiny';
import {MaintinyChat} from './MaintinyChat';
import {MaintinyHistory} from './MaintinyHistory';
import {AssistantSearch} from './AssistantSearch';
type Props={dedicated:boolean;me:R;api:(p:string,b?:R)=>Promise<any>;onOpenDedicated:()=>void;onSource:(s:R)=>void;onCreated:(id:string)=>void;onReview:(d:R)=>Promise<void>;onRefresh:()=>Promise<void>};
export function Maintiny({dedicated,me,api,onOpenDedicated,onSource,onCreated,onReview,onRefresh}:Props){
 const [open,setOpen]=useState(false),[historyOpen,setHistoryOpen]=useState(false),[target,setTarget]=useState<R|null>(null),[deleting,setDeleting]=useState(false),[deleteError,setDeleteError]=useState('');
 const hintKey='shiftfix-maintiny-hint:'+me.id;
 const [hintVisible,setHintVisible]=useState(()=>{try{return localStorage.getItem(hintKey)!=='seen'}catch{return true}});
 function dismissHint(){setHintVisible(false);try{localStorage.setItem(hintKey,'seen')}catch{/* Chat remains available when browser storage is restricted. */}}
 function openChat(){dismissHint();setOpen(true)}
 const modal=useRef<HTMLDialogElement>(null),confirm=useRef<HTMLDialogElement>(null),launcher=useRef<HTMLButtonElement>(null),cancel=useRef<HTMLButtonElement>(null),deleteOrigin=useRef<HTMLElement|null>(null);
 const state=useMaintiny(api,dedicated||open,onRefresh);
 useEffect(()=>{if(dedicated){setOpen(false);dismissHint()}},[dedicated]);
 useEffect(()=>{const d=modal.current;if(open&&!dedicated&&d){d.showModal();requestAnimationFrame(()=>document.getElementById('maintiny-message')?.focus())}return()=>{if(d?.open)d.close()}},[open,dedicated]);
 useEffect(()=>{const d=confirm.current;if(target&&d){d.showModal();cancel.current?.focus()}return()=>{if(d?.open)d.close()}},[target]);
 function close(){setOpen(false);requestAnimationFrame(()=>launcher.current?.focus())}
 function dedicatedView(){setOpen(false);setHistoryOpen(true);onOpenDedicated()}
 function askDelete(row:R){deleteOrigin.current=document.activeElement as HTMLElement;setDeleteError('');setTarget(row)}
 function dismissDelete(){setTarget(null);requestAnimationFrame(()=>{const el=deleteOrigin.current;el?.isConnected?el.focus():document.getElementById('maintiny-message')?.focus()})}
 async function remove(){if(!target)return;setDeleting(true);setDeleteError('');try{await state.remove(target);dismissDelete()}catch(e){setDeleteError((e as Error).message)}finally{setDeleting(false)}}
 const chat=<MaintinyChat state={state} compact={!dedicated} role={me.role} api={api} onSource={s=>{close();onSource(s)}} onCreated={id=>{close();onCreated(id)}} onReview={async d=>{await onReview(d);setOpen(false)}} onRefresh={onRefresh} onDelete={askDelete} onHistory={dedicated?undefined:dedicatedView}/>;
 return <>
  {dedicated&&<section className="maintiny-workspace" aria-label="Maintiny workspace"><div className="maintiny-page-intro"><p>Your maintenance conversations, kept together. Continue a saved chat or start something new.</p><button className="maintiny-history-toggle" aria-expanded={historyOpen} aria-controls="maintiny-saved-chats" onClick={()=>setHistoryOpen(x=>!x)}><History size={16}/>Saved chats ({state.threads.length})</button></div><div className={'maintiny-layout'+(historyOpen?' show-history':'')}><div id="maintiny-saved-chats"><MaintinyHistory state={state} onDelete={askDelete}/></div>{chat}</div><AssistantSearch role={me.role} api={api} onSource={onSource}/></section>}
  {createPortal(<>
   {!dedicated&&<>{hintVisible&&!open&&<section className="maintiny-hint" aria-label="Meet Maintiny"><button className="maintiny-hint-dismiss" aria-label="Dismiss Maintiny introduction" onClick={()=>{dismissHint();launcher.current?.focus()}}><X size={15}/></button><strong>Need a hand?</strong><p>Ask about work orders, parts or planning.</p><button className="maintiny-hint-start" onClick={openChat}>Chat with Maintiny <span aria-hidden="true">↗</span></button></section>}<button ref={launcher} className="maintiny-launcher" aria-label="Open Maintiny assistant" aria-haspopup="dialog" aria-expanded={open} onClick={openChat}><Bot size={24}/><span>Ask Maintiny</span></button><dialog ref={modal} className="maintiny-widget" aria-labelledby="maintiny-widget-title" onCancel={e=>{e.preventDefault();close()}}><header className="maintiny-widget-heading"><Bot size={23}/><div><h2 id="maintiny-widget-title">Maintiny</h2><small>Your maintenance assistant</small></div><button title="Open Maintiny tab" aria-label="Open Maintiny tab" onClick={dedicatedView}><Maximize2 size={17}/></button><button title="Close Maintiny" aria-label="Close Maintiny" onClick={close}><X size={19}/></button></header>{chat}</dialog></>}
   <dialog ref={confirm} className="maintiny-confirm" role="alertdialog" aria-labelledby="maintiny-delete-title" aria-describedby="maintiny-delete-description" onCancel={e=>{e.preventDefault();if(!deleting)dismissDelete()}}><h2 id="maintiny-delete-title">Delete this conversation?</h2><p id="maintiny-delete-description">The saved messages and drafts will be removed from your chat history. Work orders and saved maintenance rules are kept.</p>{deleteError&&<p role="alert" className="notice error">{deleteError}</p>}<div><button ref={cancel} disabled={deleting} onClick={dismissDelete}>Keep chat</button><button className="danger" disabled={deleting} onClick={()=>void remove()}>{deleting?'Deleting…':'Delete chat'}</button></div></dialog>
  </>,document.body)}
 </>;
}
