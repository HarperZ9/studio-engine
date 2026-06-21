"""The contract — the data model the engine emits and the frontend renders.

This is the keystone of the whole package: every API response and the frontend
"experience chamber" are typed against these shapes. Stdlib only (dataclasses + json).
A scene is a witnessed creative act: layered visuals + audio + the reasoning trajectory
that produced them, each carrying a re-checkable receipt.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

SCHEMA_VERSION = "studio-engine/1"

ArtifactKind = Literal["svg", "png", "audio_wav", "audio_params", "data"]
VerdictTag = Literal["verified", "refuted", "unverifiable"]


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


@dataclass
class Artifact:
    """One rendered output. `content` is inline (svg text / base64 / params) or a ref id."""
    kind: ArtifactKind
    content: str            # svg markup, base64 png/wav, or json-encoded params
    width: int = 0
    height: int = 0
    mime: str = ""
    label: str = ""
    sha256: str = ""

    def finalize(self) -> "Artifact":
        if not self.sha256:
            self.sha256 = _sha(self.content)
        if not self.mime:
            self.mime = {
                "svg": "image/svg+xml", "png": "image/png",
                "audio_wav": "audio/wav", "audio_params": "application/json",
                "data": "application/json",
            }.get(self.kind, "application/octet-stream")
        return self


@dataclass
class Verdict:
    """A criterion's judgement on an artifact — the verification half of the loop."""
    criterion: str
    tag: VerdictTag
    score: float            # 0..1, higher = better fit to the criterion
    detail: str = ""


@dataclass
class Step:
    """One iteration of the loop: candidate params, per-axis margins, cohesion, what changed."""
    index: int
    phase: Literal["perceive", "generate", "critique", "refine", "witness"]
    params: dict[str, Any]
    verdicts: list[Verdict] = field(default_factory=list)
    score: float = 0.0                 # cohesion (harmonic mean of the axis margins)
    margins: dict[str, float] = field(default_factory=dict)  # per-axis scores 0..1
    weakest: str = ""                  # the axis the next refine step reflected on
    note: str = ""


@dataclass
class Trajectory:
    """The witnessed path from first attempt to accepted result — the reasoning, replayable."""
    steps: list[Step] = field(default_factory=list)
    accepted_index: int = -1
    converged: bool = False


@dataclass
class Receipt:
    """Proof-before-trust: the scene's provenance + integrity, re-checkable by anyone."""
    scene_id: str
    seed: int
    organ_ids: list[str]
    artifact_shas: list[str]
    final_score: float
    schema_version: str = SCHEMA_VERSION
    author: str = "studio-engine"
    producer: str = "studio-engine"


@dataclass
class SceneLayer:
    """One station/exhibit in the chamber: an artifact + its meaning + placement hint."""
    organ_id: str
    title: str
    artifact: Artifact
    role: str = ""          # e.g. "geometry", "palette", "audio", "critique-overlay"
    z: int = 0              # render order / depth hint for the chamber


@dataclass
class Scene:
    """The full experience the chamber renders: layered visuals + audio + trajectory + receipt."""
    id: str
    title: str
    layers: list[SceneLayer]
    audio: Artifact | None
    trajectory: Trajectory
    receipt: Receipt
    palette: list[str] = field(default_factory=list)   # hex swatches for the chamber theme
    schema_version: str = SCHEMA_VERSION

    def to_json(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass
class OrganInfo:
    """A resource-library entry: a reusable unit the engine composes + the frontend can list."""
    id: str
    name: str
    kind: Literal["generator", "criterion", "sonifier", "compositor"]
    summary: str
    params_schema: dict[str, Any] = field(default_factory=dict)
    lineage: str = ""       # provenance: which shipped organ this matures from


def _clean(obj: Any) -> Any:
    """Drop None audio etc. for compact, frontend-friendly JSON."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2)
