"""Bridge to the native zero-dependency renderer (the `raw-native` C++ CLI).

The two-way render loop's afferent half: given render params (camera / view /
size), invoke the native CLI as a subprocess, then read back the machine-readable
channel certificate + compact channel summaries it emits (`channels.json`). The
model perceives those superhuman channels and steers the next re-render.

Honest by construction:
  - the binary is located via the RAW_NATIVE_CLI env var or an explicit path;
  - if the binary is absent (or fails), we return an HONEST result that says so
    (`available=False` / `ok=False` + a reason) and NEVER a fabricated render.

Stdlib only: subprocess, json, os, tempfile, pathlib, shutil, dataclasses.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Env var the operator points at the compiled CLI (e.g. raw-native's
# build/Release/raw_native_cli.exe). Absent -> the renderer is honestly "not built".
ENV_BINARY = "RAW_NATIVE_CLI"
CHANNELS_FILE = "channels.json"
_DEFAULT_TIMEOUT = 60.0


@dataclass
class RenderParams:
    """The view a model chooses for a (re-)render. Mirrors the CLI's flags."""
    width: int = 256
    height: int = 256
    eye: tuple[float, float, float] = (4.0, 4.0, 6.0)
    target: tuple[float, float, float] = (0.0, 1.0, 0.0)
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)
    fovy: float = 0.9
    # Optional previous camera for motion vectors (the two-way loop feeds the
    # last view here). Absent -> the CLI renders a static frame (zero motion).
    prev_eye: tuple[float, float, float] | None = None
    prev_target: tuple[float, float, float] | None = None
    prev_up: tuple[float, float, float] | None = None

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "RenderParams":
        d = d or {}
        p = RenderParams()
        if "width" in d:
            p.width = int(d["width"])
        if "height" in d:
            p.height = int(d["height"])
        for k in ("eye", "target", "up", "prev_eye", "prev_target", "prev_up"):
            if d.get(k) is not None:
                setattr(p, k, _vec3(d[k]))
        if "fovy" in d:
            p.fovy = float(d["fovy"])
        return p

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "width": self.width, "height": self.height,
            "eye": list(self.eye), "target": list(self.target), "up": list(self.up),
            "fovy": self.fovy,
        }
        for k in ("prev_eye", "prev_target", "prev_up"):
            v = getattr(self, k)
            if v is not None:
                d[k] = list(v)
        return d


@dataclass
class NativeRenderResult:
    """The witnessed result of a native render attempt, or an honest absence.

    `available` is False when no binary is configured/found; `ok` is False when
    the binary ran but failed (nonzero exit, missing/invalid channels.json). In
    either failure mode `certificate`/`channels` are None, never faked.
    """
    available: bool
    ok: bool
    reason: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    certificate: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    camera: dict[str, Any] | None = None
    binary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available, "ok": self.ok, "reason": self.reason,
            "params": self.params, "certificate": self.certificate,
            "channels": self.channels, "camera": self.camera, "binary": self.binary,
        }


def _vec3(v: Any) -> tuple[float, float, float]:
    a = [float(x) for x in v]
    if len(a) != 3:
        raise ValueError(f"expected a 3-vector, got {v!r}")
    return (a[0], a[1], a[2])


def locate_binary(explicit: str | None = None) -> str | None:
    """Resolve the native CLI path: explicit arg, then RAW_NATIVE_CLI, then PATH.
    Returns None when nothing usable is found (honest absence)."""
    cand = explicit or os.environ.get(ENV_BINARY)
    if cand:
        p = Path(cand)
        return str(p) if p.is_file() else None
    return shutil.which("raw_native_cli")


def _csv(v: tuple[float, float, float]) -> str:
    return ",".join(repr(float(x)) for x in v)


def build_argv(binary: str, params: RenderParams, out_dir: str) -> list[str]:
    """Map RenderParams onto the CLI's flag interface."""
    argv = [binary, "--out", out_dir,
            "--width", str(params.width), "--height", str(params.height),
            "--eye", _csv(params.eye), "--target", _csv(params.target),
            "--up", _csv(params.up), "--fovy", repr(float(params.fovy))]
    if params.prev_eye is not None:
        argv += ["--prev-eye", _csv(params.prev_eye)]
    if params.prev_target is not None:
        argv += ["--prev-target", _csv(params.prev_target)]
    if params.prev_up is not None:
        argv += ["--prev-up", _csv(params.prev_up)]
    return argv


def native_render(params: RenderParams | dict | None = None, *, binary: str | None = None,
                  timeout: float = _DEFAULT_TIMEOUT,
                  runner=subprocess.run) -> NativeRenderResult:
    """Invoke the native renderer for `params` and read back its channels.

    `runner` is injectable (defaults to subprocess.run) so tests can mock the
    binary without a compiled CLI. On any failure we return an honest result;
    we never synthesize channels.
    """
    p = params if isinstance(params, RenderParams) else RenderParams.from_dict(params)
    pd = p.to_dict()

    bin_path = locate_binary(binary)
    if not bin_path:
        return NativeRenderResult(
            available=False, ok=False,
            reason=f"native renderer not built: set {ENV_BINARY} to the raw-native CLI",
            params=pd)

    out_dir = tempfile.mkdtemp(prefix="raw_native_")
    try:
        argv = build_argv(bin_path, p, out_dir)
        try:
            proc = runner(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return NativeRenderResult(True, False, f"native render timed out after {timeout}s",
                                      params=pd, binary=bin_path)
        except OSError as e:
            return NativeRenderResult(True, False, f"native render could not launch: {e}",
                                      params=pd, binary=bin_path)
        if proc.returncode != 0:
            tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
            return NativeRenderResult(True, False,
                                      f"native render exited {proc.returncode}: {tail[0]}",
                                      params=pd, binary=bin_path)

        chan_path = Path(out_dir) / CHANNELS_FILE
        if not chan_path.is_file():
            return NativeRenderResult(True, False, f"native render emitted no {CHANNELS_FILE}",
                                      params=pd, binary=bin_path)
        try:
            doc = json.loads(chan_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return NativeRenderResult(True, False, f"invalid {CHANNELS_FILE}: {e}",
                                      params=pd, binary=bin_path)

        return NativeRenderResult(
            available=True, ok=True, reason="ok", params=pd,
            certificate=doc.get("certificate"), channels=doc.get("channels"),
            camera=doc.get("camera"), binary=bin_path)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
