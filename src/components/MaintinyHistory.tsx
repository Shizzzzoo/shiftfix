import {History,LockKeyhole,Trash2} from 'lucide-react';
import type {MaintinyState,R} from './useMaintiny';
export function MaintinyHistory({state:s,onDelete}:{state:MaintinyState;onDelete:(r:R)=>void}){
 return <div className="maintiny-history" aria-label="Saved conversations"><div className="maintiny-history-heading"><History size={17}/><h2>Saved chats</h2><span>{s.threads.length}</span></div>
  {s.listLoading&&<p role="status" className="maintiny-history-note">Refreshing chats…</p>}
  {!s.listLoading&&!s.threads.length&&<div className="maintiny-history-empty"><p>No saved chats yet.</p><small>Start a conversation here or from the floating Maintiny button. It will appear in this list.</small></div>}
  <ul>{s.threads.map(row=><li key={row.id} className={s.current?.id===row.id?'selected':''}><button className="maintiny-chat-select" disabled={s.busy||s.loading||!row.available} aria-current={s.current?.id===row.id?'true':undefined} onClick={()=>void s.select(row)}><span>{!row.available&&<LockKeyhole size={13}/>} {row.title}</span><small>{new Date(row.updatedAt).toLocaleDateString(undefined,{month:'short',day:'numeric'})} · {row.turnCount} {row.turnCount===1?'exchange':'exchanges'}</small></button><button className="maintiny-delete-chat" title="Delete conversation" aria-label={'Delete conversation: '+row.title} onClick={()=>onDelete(row)}><Trash2 size={15}/></button></li>)}</ul>
  <p className="maintiny-history-note">Private to your account. Delete chats you no longer need. Up to 50 saved conversations.</p>
 </div>;
}
