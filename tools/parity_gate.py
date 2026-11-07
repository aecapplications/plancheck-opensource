#!/usr/bin/env python3
"""Run the CRC parity gate end to end (see tests/parity-baseline/README.md).

Starts the webapp in FAKE-extractor mode on a free port, uploads
tests/parity-baseline/sample.pdf as ``baseline-sample.pdf`` with CRC selected,
waits for the job, then byte-compares the six artifacts against the baseline.

    python tools/parity_gate.py                 # check this repo
    python tools/parity_gate.py --root DIR      # check another checkout
    python tools/parity_gate.py --update        # rewrite baseline + CHECKSUMS

--update is for intentional, reviewed output changes only (and for the public
export, whose stripped rule packs legitimately change the artifacts).
Uses only the standard library plus the webapp's own dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ARTIFACTS = ["facts.json", "expanded.json", "violations.json", "chains.json",
             "report.md", "result.json"]
UPLOAD_NAME = "baseline-sample.pdf"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post_pdf(url: str, pdf: Path) -> str:
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{UPLOAD_NAME}"\r\n'.encode(),
        b"Content-Type: application/pdf\r\n\r\n", pdf.read_bytes(), b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="books"\r\n\r\ncrc\r\n',
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)["job_id"]


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def run_job(root: Path, python: str, timeout: float) -> Path:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "EXTRACTOR_FAKE": "1"}
    server = subprocess.Popen(
        [python, "-m", "uvicorn", "webapp.app:app", "--port", str(port)],
        cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.time() + 30
        while True:
            try:
                get_json(f"{base}/api/books")
                break
            except OSError:
                if server.poll() is not None or time.time() > deadline:
                    raise SystemExit("server failed to start:\n" +
                                     server.stderr.read().decode()[-2000:])
                time.sleep(0.3)
        job_id = post_pdf(f"{base}/api/jobs",
                          root / "tests" / "parity-baseline" / "sample.pdf")
        deadline = time.time() + timeout
        while True:
            st = get_json(f"{base}/api/jobs/{job_id}")
            if st["state"] == "done":
                break
            if st["state"] == "error" or time.time() > deadline:
                raise SystemExit(f"job {job_id} did not finish: "
                                 f"{json.dumps(st)[:1000]}")
            time.sleep(0.5)
        return root / "webapp" / "jobs" / job_id
    finally:
        server.terminate()
        server.wait(10)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter with the webapp requirements installed")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--keep-job", action="store_true")
    ap.add_argument("--timeout", type=float, default=300)
    args = ap.parse_args()

    root = args.root.resolve()
    baseline = root / "tests" / "parity-baseline"
    job_dir = run_job(root, args.python, args.timeout)
    out = job_dir / "books" / "crc"
    try:
        if args.update:
            lines = []
            for name in ARTIFACTS:
                shutil.copyfile(out / name, baseline / name)
                lines.append(f"{sha(baseline / name)}  {name}\n")
            (baseline / "CHECKSUMS.txt").write_text("".join(lines))
            print(f"baseline updated from job {job_dir.name}")
            return 0
        expected = {}
        for line in (baseline / "CHECKSUMS.txt").read_text().splitlines():
            digest, name = line.split(maxsplit=1)
            expected[name.strip()] = digest
        failed = 0
        for name in ARTIFACTS:
            ok = sha(out / name) == expected.get(name)
            failed += not ok
            print(f"{name}: {'OK' if ok else 'FAILED'}")
        print("PARITY OK" if not failed else f"PARITY FAILED ({failed}/6)")
        return 1 if failed else 0
    finally:
        if not args.keep_job:
            shutil.rmtree(job_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
