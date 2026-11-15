import { useCallback, useEffect, useRef, useState } from 'react';
export type R = Record<string, any>;
export type ChatMessage = {id:string;role:'user'|'assistant';text:string;sources?:R[];drafts?:R[];unavailable?:boolean};
export function useMaintiny(api:(path:string,body?:R)=>Promise<any>,active:boolean,onAccessChanged:()=>Promise<void>) {
  const [threads,setThreads]=useState<R[]>([]),[current,setCurrent]=useState<R|null>(null),[messages,setMessages]=useState<ChatMessage[]>([]);
  const [input,setInput]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false),[listLoading,setListLoading]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState<R|null>(null);
  const alive=useRef(true),epoch=useRef(0),listEpoch=useRef(0),initialized=useRef(false),pendingId=useRef(''),retry=useRef<R|null>(null);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;epoch.current++;listEpoch.current++}},[]);
  const refreshList=useCallback(async()=>{
    const stamp=++listEpoch.current;setListLoading(true);
    try {const r=await api('/assistant/conversations');if(alive.current&&stamp===listEpoch.current)setThreads(r.items)}
    catch(e){if(alive.current&&stamp===listEpoch.current)setError((e as Error).message)}
    finally{if(alive.current&&stamp===listEpoch.current)setListLoading(false)}
  },[api]);
  const initialize=useCallback(async()=>{
    setError('');await Promise.all([refreshList(),api('/assistant/status').then(r=>{if(alive.current)setStatus(r)}).catch(e=>{if(alive.current)setError(e.message)})]);
  },[api,refreshList]);
  useEffect(()=>{if(active){if(!initialized.current){initialized.current=true;void initialize()}else void refreshList()}},[active,initialize,refreshList]);
  useEffect(()=>{const focus=()=>{if(active&&!busy)void refreshList()};window.addEventListener('focus',focus);return()=>window.removeEventListener('focus',focus)},[active,busy,refreshList]);
  function newChat(){epoch.current++;retry.current=null;pendingId.current='';setCurrent(null);setMessages([]);setInput('');setError('');setBusy(false);setLoading(false)}
  async function select(row:R){
    if(!row.available)return;const stamp=++epoch.current;retry.current=null;pendingId.current='';setCurrent(row);setMessages([]);setInput('');setError('');setLoading(true);
    try{const r=await api('/assistant/conversations/'+row.id);if(alive.current&&stamp===epoch.current){setCurrent(r.conversation);setMessages(r.messages)}}
    catch(e){if(alive.current&&stamp===epoch.current){setError((e as Error).message);if((e as R).code==='ACCESS_CHANGED')void onAccessChanged();if((e as R).code==='CHAT_DELETED'){setCurrent(null);void refreshList()}}}
    finally{if(alive.current&&stamp===epoch.current)setLoading(false)}
  }
  async function send(text?:string){
    const question=(text??input).trim();if(!question||question.length>1200||busy||loading||!status?.configured)return;
    const stamp=epoch.current,id=current?.id||pendingId.current||crypto.randomUUID();pendingId.current=id;
    const requestId=retry.current?.id===id&&retry.current?.question===question?retry.current.requestId:crypto.randomUUID();
    retry.current={id,question,requestId};setBusy(true);setError('');setInput('');setMessages(old=>[...old,{id:requestId+'-user',role:'user',text:question}]);
    try{
      if(!current){const c=await api('/assistant/conversations',{id});if(!alive.current||stamp!==epoch.current)return;setCurrent(c.conversation);setThreads(old=>[c.conversation,...old.filter(x=>x.id!==id)])}
      const r=await api('/assistant/chat',{conversationId:id,message:question,requestId});if(!alive.current||stamp!==epoch.current)return;
      setCurrent(r.conversation);setMessages(r.messages||[]);setThreads(old=>[r.conversation,...old.filter(x=>x.id!==id)]);retry.current=null;
    }catch(e){if(!alive.current||stamp!==epoch.current)return;setError((e as Error).message);setInput(question);setMessages(old=>old.filter(m=>m.id!==requestId+'-user'));if((e as R).code==='ACCESS_CHANGED')void onAccessChanged();if((e as R).code==='CHAT_DELETED'){epoch.current++;setBusy(false);setLoading(false);setCurrent(null);setMessages([]);pendingId.current='';retry.current=null;void refreshList()}}
    finally{if(alive.current&&stamp===epoch.current)setBusy(false)}
  }
  async function remove(row:R){
    const removingCurrent=current?.id===row.id||pendingId.current===row.id;
    if(removingCurrent){epoch.current++;setBusy(false);setLoading(false)}
    listEpoch.current++;
    try{await api('/assistant/conversations/'+row.id+'/delete',{});if(!alive.current)return;setThreads(old=>old.filter(x=>x.id!==row.id));if(removingCurrent)newChat();setError('');await refreshList()}
    catch(e){if(alive.current)setError((e as Error).message);throw e}
  }
  return {threads,current,messages,input,setInput,busy,loading,listLoading,error,status,newChat,select,send,remove,initialize,refreshList};
}
export type MaintinyState=ReturnType<typeof useMaintiny>;
