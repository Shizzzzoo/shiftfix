"""Reuse SDK connection pools, never authorization decisions or user records.

Lambda invokes this Python handler serially per execution environment. Boto3
refreshes the execution role credentials; table resources are not shared across
application threads. Cache keys include the Region and table identity.
"""
import os
from functools import lru_cache
import boto3


def region():
    return os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION','ap-south-1')


@lru_cache(maxsize=8)
def client(service, region_name):
    return boto3.client(service,region_name=region_name)


@lru_cache(maxsize=4)
def table(name, region_name):
    return boto3.resource('dynamodb',region_name=region_name).Table(name)


def clear():
    client.cache_clear()
    table.cache_clear()
