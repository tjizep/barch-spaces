from __future__ import annotations

# Moved here from barchex's stress tests with the viewer it exercises.

import json
import math
import os
import random
import shutil
import signal
import statistics
import struct
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError, TimeoutError as RedisTimeoutError

from .conftest import install
from .helpers import connect, free_port, http_call, wait_for_tcp


STRESS = os.environ.get("BARCH_STRESS") == "1"
pytestmark = pytest.mark.skipif(not STRESS, reason="set BARCH_STRESS=1 to run stress tests")


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(pct * len(ordered)) - 1)]


def _report(label: str, elapsed: float, latencies: list[float], operations: int) -> None:
    print(
        f"{label}: operations={operations} elapsed_s={elapsed:.2f} "
        f"ops_per_s={operations / elapsed:.1f} "
        f"p50_ms={statistics.median(latencies) * 1000:.2f} "
        f"p95_ms={_percentile(latencies, 0.95) * 1000:.2f} "
        f"p99_ms={_percentile(latencies, 0.99) * 1000:.2f} "
        f"max_ms={max(latencies) * 1000:.2f}",
        flush=True,
    )


def _post_json(port: int, path: str, payload: dict) -> object:
    body = json.dumps(payload).encode()
    return http_call(port, "POST", path, body, {"Content-Type": "application/json"})


def test_thousands_of_signon_sessions_under_cpu_pressure(spaces_http, server):
    port = spaces_http
    sessions = _positive_env("BARCH_STRESS_SESSIONS", 1000, 5000)
    workers = min(32, _positive_env("BARCH_STRESS_HTTP_WORKERS", 24, 64))
    email = "stress-admin@example.test"
    password = "stress-password-1"
    created = _post_json(
        port,
        "/api/spaces-user/register",
        {"name": "Stress Admin", "email": email, "password": password},
    )
    assert created.status == 200, created.body
    assert created.cookie("sid")

    hog = None
    yes = shutil.which("yes")
    if yes:
        hog = subprocess.Popen([yes], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def signon(_index: int):
        started = time.perf_counter()
        reply = _post_json(
            port,
            "/api/spaces-user/signon",
            {"email": email, "password": password},
        )
        elapsed = time.perf_counter() - started
        assert reply.status == 200, reply.body
        cookie = reply.cookie("sid")
        assert cookie, reply.headers
        return cookie, elapsed

    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(signon, range(sessions)))
    finally:
        if hog is not None:
            hog.terminate()
            try:
                hog.wait(timeout=2)
            except subprocess.TimeoutExpired:
                hog.kill()
                hog.wait()
    elapsed = time.perf_counter() - started

    cookies = [cookie for cookie, _ in results]
    assert len(set(cookies)) == sessions, "sign-on returned duplicate session IDs"
    latencies = [duration for _, duration in results]
    pressure = "on" if hog is not None else "off"
    _report(f"HTTP sign-on cpu_pressure={pressure}", elapsed, latencies, sessions)
    assert _percentile(latencies, 0.99) * 1000 <= float(
        os.environ.get("BARCH_STRESS_HTTP_P99_MS", "10000")
    )

    client = server.client
    client.execute_command("USE", "spaces")
    stored = client.keys("sess:*")
    assert len(stored) == sessions + 1, f"expected {sessions + 1} sessions, got {len(stored)}"
    probe = cookies[0]
    reply = http_call(port, "GET", "/api/admin/me", headers={"Cookie": f"sid={probe}"})
    assert reply.status == 200 and reply.json()["admin"] is True, reply.body
    signed_out = http_call(
        port,
        "POST",
        "/api/spaces-user/signout",
        b"",
        {"Cookie": f"sid={probe}"},
    )
    assert signed_out.status == 200, signed_out.body
    assert client.get(f"sess:{probe}") is None
    assert client.ping() is True
