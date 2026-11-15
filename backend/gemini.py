"""Gemini REST adapter. Keeps provider-native signed parts inside one request only."""
import copy
import json
import os
import re
import socket
import uuid
from urllib import request, error

MAX_RESPONSE=262144

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None  # Never forward the API-key header to another endpoint.


def configuration():
    model=os.environ.get('GEMINI_MODEL_ID','gemini-3.5-flash-lite')
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]{1,100}',model):
        raise ValueError('Invalid configured Gemini model ID')
    return model


def contents(messages):
    out=[];calls={}
    for message in messages:
        if message['role']=='assistant' and '_geminiContent' in message:
            out.append(copy.deepcopy(message['_geminiContent']))
            for block in message['content']:
                if 'toolUse' in block:
                    t=block['toolUse'];calls[t['toolUseId']]=t['name']
            continue
        parts=[]
        for block in message['content']:
            if 'text' in block:parts.append({'text':block['text']})
            elif 'toolResult' in block:
                t=block['toolResult'];response=t['content'][0]['json']
                if t['toolUseId'] not in calls:raise ValueError('Unmatched internal function response')
                item={'name':calls[t['toolUseId']],'response':response}
                # Gemini 3+ returns call IDs. Echo them when present.
                if not t['toolUseId'].startswith('local-'):item['id']=t['toolUseId']
                parts.append({'functionResponse':item})
            else:raise ValueError('Unsupported internal conversation block')
        out.append({'role':'model' if message['role']=='assistant' else 'user','parts':parts})
    return out


def body(messages,system,tools):
    return {'systemInstruction':{'parts':[{'text':system}]},'contents':contents(messages),
        'tools':[{'functionDeclarations':[{'name':t['toolSpec']['name'],'description':t['toolSpec']['description'],'parametersJsonSchema':t['toolSpec']['inputSchema']['json']} for t in tools['tools']]}],
        'toolConfig':{'functionCallingConfig':{'mode':'AUTO'}},
        'generationConfig':{'temperature':0,'maxOutputTokens':1024,'candidateCount':1,'thinkingConfig':{'thinkingLevel':'MINIMAL'}}}


def normalized(data):
    from .assistant import AssistantError
    candidates=data.get('candidates',[])
    if not candidates:
        raise AssistantError('The assistant could not answer this request. Rephrase it or use direct search.',422,'AI_CONTENT_BLOCKED')
    candidate=candidates[0];native=candidate.get('content',{});blocks=[]
    finish=candidate.get('finishReason','')
    if finish not in ['STOP','MAX_TOKENS']:
        raise AssistantError('The assistant could not complete this request. Rephrase it or use direct search.',422,'AI_CONTENT_BLOCKED')
    for part in native.get('parts',[]):
        if part.get('thought'):continue
        if 'functionCall' in part:
            f=part['functionCall']
            if not isinstance(f.get('name'),str) or not isinstance(f.get('args',{}),dict):
                raise AssistantError('The assistant returned an invalid tool request. Please retry.',503,'AI_INVALID_RESPONSE')
            blocks.append({'toolUse':{'toolUseId':f.get('id') or 'local-'+str(uuid.uuid4()),'name':f['name'],'input':f.get('args',{})}})
        elif isinstance(part.get('text'),str):blocks.append({'text':part['text'][:6000]})
    if not blocks:raise AssistantError('The assistant returned an empty response. Please retry.',503,'AI_INVALID_RESPONSE')
    # An incomplete function call must never be executed.
    if finish=='MAX_TOKENS' and any('toolUse' in b for b in blocks):
        raise AssistantError('The assistant reached its output limit. Ask a narrower question.',503,'AI_OUTPUT_LIMIT')
    usage=data.get('usageMetadata',{})
    return {'output':{'message':{'role':'assistant','content':blocks,'_geminiContent':native}},
        'stopReason':'tool_use' if any('toolUse' in b for b in blocks) else 'end_turn',
        'usage':{'inputTokens':int(usage.get('promptTokenCount',0)),'outputTokens':int(usage.get('candidatesTokenCount',0))+int(usage.get('thoughtsTokenCount',0))}}


def converse(messages,system,tools):
    from .assistant import AssistantError
    key=os.environ.get('GEMINI_API_KEY','').strip()
    if not key:raise AssistantError('The assistant is awaiting secure credential configuration. Direct search is available.',503,'AI_NOT_CONFIGURED')
    try:model=configuration()
    except ValueError as exc:raise AssistantError('The assistant model configuration needs administrator review.',503,'AI_NOT_CONFIGURED') from exc
    req=request.Request('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',
        data=json.dumps(body(messages,system,tools)).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
    try:
        with request.build_opener(NoRedirect()).open(req,timeout=6) as response:
            raw=response.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:raise AssistantError('The assistant response exceeded its size limit. Ask a narrower question.',503,'AI_INVALID_RESPONSE')
        return normalized(json.loads(raw))
    except error.HTTPError as exc:
        # Provider error bodies may include request contents or key information.
        # Never log, return, or stringify them.
        print(json.dumps({'assistantError':'GeminiHTTP','status':exc.code}))
        if exc.code==429:raise AssistantError('The assistant request allowance is busy or exhausted. Try later; direct search is available.',429,'AI_BUSY') from None
        if exc.code in [401,403]:raise AssistantError('The assistant credential or project access needs administrator review. Direct search is available.',503,'AI_ACCESS_DENIED') from None
        if exc.code==404:raise AssistantError('The configured assistant model is unavailable for this project. Direct search is available.',503,'AI_MODEL_UNAVAILABLE') from None
        raise AssistantError('The assistant service could not complete this request. Direct search is available.',503,'AI_UNAVAILABLE') from None
    except (error.URLError,TimeoutError,socket.timeout):
        raise AssistantError('The assistant connection timed out. Direct search is available.',503,'AI_TIMEOUT') from None
    except (ValueError,KeyError,TypeError):
        raise AssistantError('The assistant returned an invalid response. Try again or use direct search.',503,'AI_INVALID_RESPONSE') from None
