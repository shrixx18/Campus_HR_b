#!/usr/bin/env python3
"""Seed sample users after stack is up."""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "http://localhost:8080")


def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    users = [
        ("coordinator@campus.edu", "coordinator"),
        ("rahul@campus.edu", "student"),
        ("priya@campus.edu", "student"),
    ]
    for email, role in users:
        try:
            api("POST", "/api/v1/auth/register", {"email": email, "password": "password123", "role": role})
            print("Registered", email, role)
        except urllib.error.HTTPError:
            print("Exists", email)

    print("Seed script finished")


if __name__ == "__main__":
    main()
