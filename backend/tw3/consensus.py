"""Multi-rater consensus for per-bone TW3 staging (training-data quality gate).

The literature is unanimous that stage-classifier accuracy is capped by *label*
quality: a single rater agrees with a second expert only ~0.58-0.76 of the time on
the hard bones, so single-rater labels carry 25-40% noise. Majority vote across
three raters drops that below ~8%. Before crops are exported for training, the
several independent stagings of one film should be reduced to a consensus label,
and bones where raters disagree should be routed to adjudication — not silently
averaged.

This module is PURE (no DB, no I/O): it takes the raters' stagings as plain dicts
so it can be unit-tested and reused by the exporter, an API endpoint, or a review
UI. It does not invent a stage: a bone with no clear majority is returned with
``needs_adjudication=True`` and no consensus stage, exactly as the protocol requires.

Deliberately NOT included here (build when a labelling team actually exists):
rater identity in the schema, an adjudication queue/UI, and full Fleiss' kappa.
``observed_agreement`` below is Po (proportion of full-agreement bones), a simple,
honest agreement measure — not kappa (which needs category marginals).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from .constants import bones_for_system


@dataclass(frozen=True)
class BoneConsensus:
    """Consensus for one bone across the raters who staged it."""
    bone_code: str
    consensus_stage: Optional[str]   # None when no clear majority
    agreement: float                 # top-vote count / n_votes (0..1); 0 if unstaged
    n_votes: int                     # raters who staged this bone
    n_raters: int                    # total raters considered
    has_majority: bool               # top count > half of n_votes (strict)
    unanimous: bool
    needs_adjudication: bool         # no majority, a tie, or too few votes
    votes: dict                      # stage -> count (for display / audit)


def bone_consensus(bone: str, stagings: Sequence[Mapping[str, str]],
                   *, min_votes: int = 2) -> BoneConsensus:
    """Majority vote for one bone across ``stagings`` (one mapping per rater).

    A bone is decided only when a single stage has strictly more than half the
    votes AND at least ``min_votes`` raters staged it; otherwise it is flagged for
    adjudication with no consensus stage (never a guess).
    """
    n_raters = len(stagings)
    votes = Counter(s[bone] for s in stagings if s.get(bone))
    n_votes = sum(votes.values())
    if n_votes == 0:
        return BoneConsensus(bone, None, 0.0, 0, n_raters, False, False, True, {})

    top_stage, top_count = votes.most_common(1)[0]
    tied = [st for st, c in votes.items() if c == top_count]
    agreement = top_count / n_votes
    has_majority = top_count * 2 > n_votes and len(tied) == 1
    unanimous = len(votes) == 1 and n_votes >= 1
    enough = n_votes >= min_votes
    decided = has_majority and enough
    return BoneConsensus(
        bone_code=bone,
        consensus_stage=top_stage if decided else None,
        agreement=round(agreement, 3),
        n_votes=n_votes,
        n_raters=n_raters,
        has_majority=has_majority,
        unanimous=unanimous,
        needs_adjudication=not decided,
        votes=dict(votes),
    )


@dataclass(frozen=True)
class ConsensusResult:
    per_bone: dict            # bone_code -> BoneConsensus
    consensus_stages: dict    # bone_code -> stage, only decided bones
    adjudication_bones: tuple # bones needing a senior read
    observed_agreement: float # Po: fraction of staged bones with full agreement
    mean_agreement: float     # mean per-bone agreement over staged bones
    n_raters: int
    n_bones_staged: int


def consensus(stagings: Sequence[Mapping[str, str]], bones: Iterable[str],
              *, min_votes: int = 2) -> ConsensusResult:
    """Reduce several raters' stagings of ONE film to per-bone consensus + metrics.

    ``stagings``: list of {bone_code: stage}, one per rater (independent reads).
    ``bones``: the bone codes to consider (e.g. RUS_BONES, or RUS+carpal).
    """
    per_bone: dict = {}
    decided: dict = {}
    adjudication: list = []
    agreements: list = []
    unanimous_count = 0
    staged = 0
    for b in bones:
        bc = bone_consensus(b, stagings, min_votes=min_votes)
        per_bone[b] = bc
        if bc.n_votes > 0:
            staged += 1
            agreements.append(bc.agreement)
            if bc.unanimous:
                unanimous_count += 1
        if bc.consensus_stage is not None:
            decided[b] = bc.consensus_stage
        if bc.needs_adjudication and bc.n_votes > 0:
            adjudication.append(b)
    po = (unanimous_count / staged) if staged else 0.0
    mean_agr = (sum(agreements) / len(agreements)) if agreements else 0.0
    return ConsensusResult(
        per_bone=per_bone,
        consensus_stages=decided,
        adjudication_bones=tuple(adjudication),
        observed_agreement=round(po, 3),
        mean_agreement=round(mean_agr, 3),
        n_raters=len(stagings),
        n_bones_staged=staged,
    )


def build_film_consensus(films: Iterable[Mapping], *, min_readers: int = 2) -> dict:
    """Group independent reads of the SAME film and compute consensus per group.

    ``films``: iterable of ``{"radiograph_id", "stage_system", "stages": {bone: stage}}``
    — one entry per (rater's) assessment. Only films with ≥ ``min_readers`` distinct
    reads in the same stage system yield a consensus group (a single read cannot form
    a majority). Pure/DB-free so the exporter and tests share it.
    """
    groups: dict = defaultdict(list)
    for f in films:
        rid = f.get("radiograph_id")
        if rid is None:
            continue  # annotation-only rows can't be "the same film" across raters
        groups[(rid, f.get("stage_system"))].append(dict(f.get("stages") or {}))

    out: list = []
    for (rid, system), stagings in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        if len(stagings) < min_readers:
            continue
        res = consensus(stagings, bones_for_system(system))
        out.append({
            "radiograph_id": rid,
            "stage_system": system,
            "n_readers": len(stagings),
            "consensus_stages": res.consensus_stages,
            "adjudication_bones": list(res.adjudication_bones),
            "n_bones_staged": res.n_bones_staged,
            "observed_agreement": res.observed_agreement,
            "mean_agreement": res.mean_agreement,
        })
    return {
        "n_multireader_films": len(out),
        "films_needing_adjudication": sum(1 for g in out if g["adjudication_bones"]),
        "groups": out,
    }


def _selftest() -> None:
    from backend.tw3 import RUS_BONES
    # 3 raters, mostly agreeing; radius unanimous, ulna 2-1 majority, mc1 3-way tie.
    r1 = {"radius": "F", "ulna": "E", "mc1": "D"}
    r2 = {"radius": "F", "ulna": "E", "mc1": "E"}
    r3 = {"radius": "F", "ulna": "F", "mc1": "F"}
    res = consensus([r1, r2, r3], RUS_BONES)
    assert res.per_bone["radius"].unanimous and res.consensus_stages["radius"] == "F"
    assert res.consensus_stages["ulna"] == "E"          # 2 of 3 = majority
    assert "mc1" in res.adjudication_bones               # 1-1-1 tie → adjudicate
    assert res.per_bone["mc1"].consensus_stage is None
    assert res.n_bones_staged == 3
    # single rater → every staged bone needs adjudication (min_votes=2)
    solo = consensus([{"radius": "F"}], RUS_BONES)
    assert solo.adjudication_bones == ("radius",) and not solo.consensus_stages
    print("consensus selftest OK:",
          {"decided": res.consensus_stages, "adjudicate": res.adjudication_bones,
           "Po": res.observed_agreement, "mean_agr": res.mean_agreement})


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("usage: python -m backend.tw3.consensus --selftest")
