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
    # Only the identifier is output. The assistant may use it in CloudFormation.
    print('Stored securely. Secret ARN:',metadata['ARN'])
    print('Only share that ARN, not the key. Key rotation at Google is manual; no stored key is read by this helper.')


if __name__=='__main__':
    try:main()
    except (ClientError,BotoCoreError,KeyboardInterrupt,getpass.GetPassWarning) as exc:
        raise SystemExit('Configuration stopped ('+type(exc).__name__+'). Run with uv run scripts/configure-gemini-secret.py; check AWS sign-in/permissions if it still fails. No secret value was printed.') from None
