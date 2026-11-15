"""Isolate reusable SDK pools between independent Moto backends and mocks."""
import pytest
from backend import clients

@pytest.fixture(autouse=True)
def isolated_sdk_clients():
    clients.clear()
    yield
    clients.clear()
