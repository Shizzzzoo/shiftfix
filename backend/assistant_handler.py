"""Dedicated bounded-concurrency Lambda for assistant paths only."""
from . import api

def handler(event,context):
    if not event.get('rawPath','').startswith('/assistant/'):
        return {'statusCode':404,'headers':{'Content-Type':'application/json'},'body':'{"message":"Endpoint not found"}'}
    return api.handler(event,context)
