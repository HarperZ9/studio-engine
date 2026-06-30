"""External oracle: judge a witnessed World with a coherence-membrane criterion the engine did
NOT author.

studio-engine self-grades cohesion (its own tag/floor) -- the ungrounded-self-critic trap its own
docs warn about. This routes the converged World's cohesion through cm's
structural_fitness_criterion (an INDEPENDENT criterion + an independent tolerance) -> a real cm
Certificate (oracle structural-fitness-v1, verified/refuted/unverifiable). The verdict authority is
cm's, not the engine's tag. Depends on the spine (coherence_membrane) -- an internal dependency,
per the unified-organism architecture (organs may depend on one another; zero THIRD-PARTY deps)."""
from __future__ import annotations

from coherence_membrane.certificate import Certificate
from coherence_membrane.structural_fitness import structural_fitness_criterion

# cm's independent bar: a structurally-sound creative World's cohesion deviates from perfect (1.0)
# by no more than this tolerance (i.e. cohesion >= 0.6). cm sets this -- NOT the engine's own floor.
_TOLERANCE = 0.4


def world_certificate(cohesion: float) -> Certificate:
    """An external structural-fitness Certificate for a World's converged cohesion (0..1)."""
    crit = structural_fitness_criterion(deviation=lambda c: 1.0 - float(c), tolerance=_TOLERANCE)
    return crit.judge(cohesion)
