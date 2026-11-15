# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3>=1.41.0", "botocore[crt]>=1.41.0"]
# ///
"""Run in your terminal, never via an assistant tool. Hidden prompt writes a fresh
key straight to Secrets Manager; never reads a stored secret or prints its value.
Usage: uv run scripts/configure-gemini-secret.py
"""
import argparse
import getpass
import json
import sys
import warnings
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from urllib import request as urlrequest, error as urlerror


class NoRedirect(urlrequest.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def validate_google_key(key):
    # This checks authentication only. No factory data or inference is sent.
    req=urlrequest.Request('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1',headers={'x-goog-api-key':key})
    try:
        with urlrequest.build_opener(NoRedirect()).open(req,timeout=10):pass
    except urlerror.HTTPError as exc:
        reason=''
        try:
            raw=exc.read(65537)
            data=json.loads(raw) if len(raw)<=65536 else {}
            allowed={'API_KEY_INVALID','API_KEY_EXPIRED','API_KEY_SERVICE_BLOCKED','SERVICE_DISABLED','ACCESS_TOKEN_TYPE_UNSUPPORTED','API_KEY_NOT_AUTHORIZED'}
            reason=next((d['reason'] for d in data.get('error',{}).get('details',[]) if isinstance(d,dict) and d.get('reason') in allowed and key not in d['reason']),'')
        except (ValueError,TypeError,AttributeError,OSError):pass
        raise SystemExit('Google rejected the connection check (HTTP '+str(exc.code)+('/'+reason if reason else '')+'). Nothing new was stored. Check that this key is enabled in Google AI Studio.') from None
    except (urlerror.URLError,TimeoutError):
        raise SystemExit('Could not reach Google for the key check. Nothing new was stored; try again when the connection is available.') from None
    print('Google accepted the connection check. Model access will be tested during deployment.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',default='shiftfix')
    parser.add_argument('--region',default='ap-south-1')
    parser.add_argument('--name',default='shiftfix/gemini')
    parser.add_argument('--check',action='store_true',help='Check SDK dependencies and AWS sign-in without prompting for or writing a key.')
    args=parser.parse_args()
    # Resolve the local aws-login credential provider before asking for a secret.
    session=boto3.Session(profile_name=args.profile,region_name=args.region)
    sm=session.client('secretsmanager')
    session.client('sts').get_caller_identity()
    print('AWS SDK dependencies and sign-in verified.')
    if args.check:return
    if not sys.stdin.isatty():raise SystemExit('Run this directly in an interactive terminal; do not pipe a key or pass it as an argument.')
    warnings.simplefilter('error',getpass.GetPassWarning)
    first=getpass.getpass('Fresh Gemini API key (hidden): ').strip()
    second=getpass.getpass('Repeat fresh key (hidden): ').strip()
    if not first or first!=second or any(c.isspace() for c in first):raise SystemExit('Keys must be nonempty, match, and contain no whitespace. Nothing stored.')
    validate_google_key(first)
    value=json.dumps({'api_key':first})
    try:
        metadata=sm.describe_secret(SecretId=args.name)
    except ClientError as exc:
        if exc.response['Error']['Code']!='ResourceNotFoundException':raise
        kms=session.client('kms')
        tags=[{'TagKey':'Project','TagValue':'ShiftFix'},{'TagKey':'Purpose','TagValue':'ExternalAssistantCredential'}]
        key=kms.create_key(Description='ShiftFix Gemini API credential encryption',Tags=tags)['KeyMetadata']['KeyId']
        kms.enable_key_rotation(KeyId=key)
        metadata=sm.create_secret(Name=args.name,Description='ShiftFix temporary Gemini API provider credential',KmsKeyId=key,SecretString=value,Tags=[{'Key':'Project','Value':'ShiftFix'}])
    else:
        sm.put_secret_value(SecretId=metadata['ARN'],SecretString=value)
    print('Key stored successfully. You are finished - return to the chat and say stored.')
    print('No ARN or key needs to be copied. The deployment can locate the saved key automatically.')


if __name__=='__main__':
    try:main()
    except (ClientError,BotoCoreError,KeyboardInterrupt,getpass.GetPassWarning) as exc:
        raise SystemExit('Configuration stopped ('+type(exc).__name__+'). Run with uv run scripts/configure-gemini-secret.py; check AWS sign-in/permissions if it still fails. No secret value was printed.') from None
