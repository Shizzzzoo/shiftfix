"""Post-confirmation assigns the verified owner email, never client-supplied roles."""
import os
import boto3


def post_confirmation(event,context):
    if event.get('triggerSource')!='PostConfirmation_ConfirmSignUp': return event
    attrs=event['request']['userAttributes']
    if attrs.get('email_verified')!='true': return event
    role='supervisor' if attrs.get('email','').lower()==os.environ['SUPERVISOR_EMAIL'].lower() else 'operator'
    boto3.client('cognito-idp').admin_add_user_to_group(UserPoolId=event['userPoolId'],Username=event['userName'],GroupName=role)
    return event
