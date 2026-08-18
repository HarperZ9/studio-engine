"""External oracle: judge a witnessed World with a coherence-membrane criterion the engine did
NOT author.

studio-engine self-grades cohesion (its own tag/floor) -- the ungrounded-self-critic trap its own
docs warn about. This routes the converged World's cohesion through cm's
structural_fitness_criterion (an INDEPENDENT criterion + an independent tolerance) -> a real cm
Certificate (oracle structural-fitness-v1, verified/refuted/unverifiable). The verdict authority is
cm's, not the engine's tag.

coherence_membrane is an OPTIONAL organ, not a hard dependency: it is a sibling in the
unified-organism architecture, not a PyPI package, so importing it at module load would break a
fresh ``pip install studio-engine`` that does not also have the spine on the path. It is imported
lazily inside ``world_certificate``; when it is absent the engine still produces a World and the
external verdict is an honest ``unverifiable`` record rather than a fabricated pass. Install the
spine to get the real external certificate."""
from __future__ import annotations

from dataclasses import dataclass

# cm's independent bar: a structurally-sound creative World's cohesion deviates from perfect (1.0)
# by no more than this tolerance (i.e. cohesion >= 0.6). cm sets this -- NOT the engine's own floor.
_TOLERANCE = 0.4


@dataclass(frozen=True)
class OracleUnavailable:
    """Honest null for the external verdict when the coherence-membrane organ is not installed.

    Carries the same ``to_dict()`` shape a Certificate is consumed by, so the engine keeps
    producing a World; the verdict is ``unverifiable`` (cm's own vocabulary), not a self-graded
    pass, because the independent oracle could not be reached."""

    cohesion: float

    def to_dict(self) -> dict:
        return {
            "oracle": "structural-fitness-v1",
            "verdict": "unverifiable",
            "reason": "coherence_membrane is not installed; external certification unavailable",
            "cohesion": round(float(self.cohesion), 4),
        }


def world_certificate(cohesion: float):
    """An external structural-fitness Certificate for a World's converged cohesion (0..1).

    Returns a real coherence-membrane ``Certificate`` when the spine is installed, otherwise an
    ``OracleUnavailable`` honest null. Both expose ``to_dict()``, so the caller is unchanged."""
    try:
        from coherence_membrane.structural_fitness import structural_fitness_criterion
    except ImportError:
        return OracleUnavailable(cohesion)
    crit = structural_fitness_criterion(deviation=lambda c: 1.0 - float(c), tolerance=_TOLERANCE)
    return crit.judge(cohesion)
