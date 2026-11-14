"""Public static UI only. Application data remains on the JWT-protected API."""
import base64,mimetypes
from pathlib import Path
ROOT=Path(__file__).with_name('staticfiles')
def handler(event,context):
 path=event.get('rawPath','/').lstrip('/') or 'index.html'
 if '..' in path or not (path=='index.html' or path=='config.json' or path.startswith('assets/')):
  return {'statusCode':404,'body':'Not found'}
 file=ROOT/path
 if not file.is_file():return {'statusCode':404,'body':'Not found'}
 return {'statusCode':200,'headers':{'Content-Type':mimetypes.guess_type(path)[0] or 'application/octet-stream','Cache-Control':'no-store' if path in {'index.html','config.json'} else 'public,max-age=31536000,immutable','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' https://*.amazonaws.com data:; connect-src 'self' https://*.amazonaws.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"},'body':base64.b64encode(file.read_bytes()).decode(),'isBase64Encoded':True}
