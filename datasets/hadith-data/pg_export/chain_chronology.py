"""Chain chronology guard: impossible teacher-student years and repeated-narrator seams. See AGENTS.md §Chain chronology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

# A teacher may die at most this many years after his student (AGENTS.md §Chain chronology for the measurement).
DEATH_GAP_YEARS = 60
# A student born at most this many years after his teacher died may be reporting across a gap (irsal): the pair is
# impossible as hearing, but neither identity is shown to be wrong by it.
IRSAL_YEARS = 20


@dataclass(frozen=True)
class Lifespan:
    """Lexicon Hijri years; None when unrecorded (a recorded 0 is not a year and is passed as None)."""

    birth: int | None = None
    death: int | None = None


def transmission_chronology(student: Lifespan, teacher: Lifespan, attested: bool = False,
                            adjacent: bool = True) -> str | None:
    """Why `student` cannot have heard `teacher` on these years, else None. Same rule as narrator_transmissions."""
    if attested:  # the lexicon's own teacher list names the pair: a date is wrong, not the identity
        return None
    if adjacent and student.birth is not None and teacher.death is not None and student.birth > teacher.death:
        return "student_born_after_teacher_died"
    if teacher.birth is not None and student.death is not None and teacher.birth > student.death:
        return "teacher_born_after_student_died"
    if teacher.death is not None and student.death is not None and teacher.death > student.death + DEATH_GAP_YEARS:
        return "teacher_died_long_after_student"
    return None


def irsal_possible(rule: str, student: Lifespan, teacher: Lifespan) -> bool:
    """A short birth-after-death gap reads as a broken chain (irsal), not a wrong identity."""
    return rule == "student_born_after_teacher_died" and student.birth - teacher.death <= IRSAL_YEARS


def seam_blocked_pairs(narrator_ids: Sequence[str | None]) -> set[int]:
    """Positions p whose pair (p, p+1) lies between two occurrences of one narrator (a flattened tahwil seam)."""
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    for position, narrator_id in enumerate(narrator_ids):
        if narrator_id:
            first.setdefault(narrator_id, position)
            last[narrator_id] = position
    blocked: set[int] = set()
    for narrator_id, start in first.items():
        blocked.update(range(start, last[narrator_id]))
    return blocked


def _segments(length: int, blocked: set[int]) -> list[int]:
    """Segment number per position: positions joined by an unblocked pair share a route."""
    segment, out = 0, []
    for position in range(length):
        if position > 0 and position - 1 in blocked:
            segment += 1
        out.append(segment)
    return out


def withheld_reason(rule: str, own: Lifespan, other: Lifespan, as_student: bool) -> str:
    """Reader-facing reason for the mention whose identity is withheld."""
    if rule == "teacher_died_long_after_student":
        if as_student:
            return (f"chronology: the person named here died in {own.death} AH, {other.death - own.death} years before "
                    f"the next transmitter (d. {other.death} AH), from whom he is said to narrate")
        return (f"chronology: the person named here died in {own.death} AH, {own.death - other.death} years after the "
                f"transmitter said to narrate from him (d. {other.death} AH)")
    if rule == "teacher_born_after_student_died":
        if as_student:
            return (f"chronology: the person named here died in {own.death} AH, before the next transmitter was born "
                    f"({other.birth} AH)")
        return (f"chronology: the person named here was born in {own.birth} AH, after the transmitter said to narrate "
                f"from him had died ({other.death} AH)")
    if as_student:
        return (f"chronology: the person named here was born in {own.birth} AH, {own.birth - other.death} years after "
                f"the next transmitter died ({other.death} AH)")
    return (f"chronology: the person named here died in {own.death} AH, {other.birth - own.death} years before the "
            f"transmitter said to narrate from him was born ({other.birth} AH)")


@dataclass(frozen=True)
class Contest:
    """Outcome for one chain: positions whose standing identity is withheld, with the reader-facing reason."""

    withheld: dict[int, str]
    decided: int        # impossible pairs settled against one mention
    undecided: int      # impossible pairs where both identities are withheld
    irsal: int          # impossible pairs left standing as a possible broken chain
    seam_pairs: int     # identified pairs between two occurrences of one narrator (never a transmission)
    repeated_left: int  # impossible pairs touching a repeated narrator, left to the view


def contest_chain(narrator_ids: Sequence[str | None], lifespans: Mapping[str, Lifespan],
                  attested: set[tuple[str, str]] | frozenset = frozenset()) -> Contest:
    """Withholds standing identities that make an adjacent pair impossible (position p narrates from p+1).

    Evidence, in order: the mention that conflicts with at least two dated members of its route while its partner
    conflicts with it alone; else the one of the two whose other neighbour the lexicon's teacher lists do not tie to it;
    else both are withheld. Pairs across a repeated-narrator seam are never contested.
    """
    blocked = seam_blocked_pairs(narrator_ids)
    segment = _segments(len(narrator_ids), blocked)
    span = {p: lifespans[n] for p, n in enumerate(narrator_ids) if n and n in lifespans}
    dated = [p for p, life in span.items() if life.birth is not None or life.death is not None]
    # A repeated narrator keeps his identity: withholding one occurrence would move the seam the view computes.
    repeated = {n for n in narrator_ids if n and narrator_ids.count(n) > 1}

    def conflict(later: int, earlier: int) -> str | None:
        """Rule for the member at `later` (nearer the collector) against `earlier` on the same route."""
        return transmission_chronology(span[later], span[earlier],
                                       (narrator_ids[later], narrator_ids[earlier]) in attested,
                                       adjacent=earlier == later + 1)

    def conflicts(position: int) -> set[int]:
        found = set()
        for other in dated:
            if other != position and segment[other] == segment[position]:
                later, earlier = sorted((position, other))
                if conflict(later, earlier):
                    found.add(other)
        return found

    def anchored(position: int, partner: int) -> bool:
        """The lexicon's teacher lists tie this identity to its other neighbour (not the partner)."""
        for student, teacher in ((position - 1, position), (position, position + 1)):
            if partner in (student, teacher) or student < 0 or teacher >= len(narrator_ids):
                continue
            if student in blocked or not narrator_ids[student] or not narrator_ids[teacher]:
                continue
            if (narrator_ids[student], narrator_ids[teacher]) in attested:
                return True
        return False

    withheld: dict[int, str] = {}
    decided = undecided = irsal = repeated_left = 0
    for student in range(len(narrator_ids) - 1):
        teacher = student + 1
        if student in blocked or student not in span or teacher not in span:
            continue
        rule = conflict(student, teacher)
        if rule is None:
            continue
        if irsal_possible(rule, span[student], span[teacher]):
            irsal += 1
            continue
        student_conflicts, teacher_conflicts = conflicts(student), conflicts(teacher)
        if len(student_conflicts) >= 2 and teacher_conflicts == {student}:
            losers = [student]
        elif len(teacher_conflicts) >= 2 and student_conflicts == {teacher}:
            losers = [teacher]
        elif anchored(teacher, student) and not anchored(student, teacher):
            losers = [student]
        elif anchored(student, teacher) and not anchored(teacher, student):
            losers = [teacher]
        else:
            losers = [student, teacher]
        undecidable = len(losers) == 2
        losers = [loser for loser in losers if narrator_ids[loser] not in repeated]
        if not losers:
            repeated_left += 1
            continue
        if undecidable:
            undecided += 1
        else:
            decided += 1
        for loser in losers:
            as_student = loser == student
            own, other = (span[student], span[teacher]) if as_student else (span[teacher], span[student])
            reason = withheld_reason(rule, own, other, as_student)
            if undecidable:
                reason += "; the chain cannot tell which of the two names is wrong"
            withheld.setdefault(loser, reason)
    seam_pairs = sum(1 for p in blocked if narrator_ids[p] and narrator_ids[p + 1])
    return Contest(withheld, decided, undecided, irsal, seam_pairs, repeated_left)
