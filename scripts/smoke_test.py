#!/usr/bin/env python3
"""Smoke test for CampusHire backend via API gateway."""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8080"


def call(method: str, path: str, data=None, token=None, expect_auth_fail=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read().decode()
            return resp.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        if expect_auth_fail and e.code in (401, 403):
            return e.code, {}
        raise


def main():
    status, health = call("GET", "/health")
    assert status == 200, health
    print("OK gateway health")

    email = "smoke_student@campus.edu"
    try:
        call("POST", "/api/v1/auth/register", {"email": email, "password": "password123", "role": "student"})
    except urllib.error.HTTPError:
        pass

    _, tokens = call("POST", "/api/v1/auth/login", {"email": email, "password": "password123"})
    token = tokens["access_token"]
    print("OK login")

    _, opps = call("GET", "/api/v1/opportunities", token=token)
    print(f"OK list opportunities ({len(opps)} items)")

    print("Smoke tests passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Smoke tests failed:", exc)
        sys.exit(1)
