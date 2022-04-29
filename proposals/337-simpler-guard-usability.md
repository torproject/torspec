```
Filename: 337-simpler-guard-usability.md
Title: A simpler way to decide, "Is this guard usable?"
Author: Nick Mathewson
Created: 2021-10-22
Status: Accepted
```

# Introduction

The current `guard-spec` describes a mechanism for how to behave when
our primary guards are unreachable, and we don't know which other guards
are reachable.  This proposal describes a simpler method, currently
implemented in [Arti](https://gitlab.torproject.org/tpo/core/arti/).

(Note that this method might not actually give different results: its
only advantage is that it is much simpler to implement.)

## The task at hand

For illustration, we'll assume that our primary guards are P1, P2, and
P3, and our subsequent guards (in preference order) are G1, G2, G3, and
so on.  The status of each guard is Reachable (we think we can connect
to it), Unreachable (we think it's down), or Unknown (we haven't tried
it recently).

The question becomes, "What should we do when P1, P2, and P3 are
Unreachable, and G1, G2, ... are all Unknown"?

In this circumstance, we _could_ say that we only build circuits to G1,
wait for them to succeed or fail, and only try G2 if we see that the
circuits to G1 have failed completely.  But that delays in the case that
G1 is down.

Instead, the first time we get a circuit request, we try to build one
circuit to G1.  On the next circuit request, if the circuit to G1 isn't
done yet, we launch a circuit to G2 instead.  The next request (if the
G1 and G2 circuits are still pending) goes to G3, and so on.  But
(here's the critical part!) we don't actually _use_ the circuit to G2
unless the circuit to G1 fails, and we don't actually _use_ the circuit
to G3 unless the circuits to G1 and G2 both fail.

This approach causes Tor clients to check the status of multiple
possible guards in parallel, while not actually _using_ any guard until
we're sure that all the guards we'd rather use are down.

## The current algorithm and its drawbacks

For the current algorithm, see `guard-spec` section 4.9: circuits are
exploratory if they are not using a primary guard.  If such an
exploratory circuit is `waiting_for_better_guard`, then we advance it
(or not) depending on the status of all other _circuits_ using guards that
we'd rather be using.

In other words, the current algorithm is described in terms of actions
to take with given circuits.

For Arti (and for other modular Tor implementations), however, this
algorithm is a bit of a pain: it introduces dependencies between the
guard code and the circuit handling code, requiring each one to mess
with the other.

# Proposal

I suggest that we describe an alternative algorithm for handing circuits
to non-primary guards, to be used in preference to the current
algorithm.  Unlike the existing approach, it isolates the guard logic a
bit better from the circuit logic.

## Handling exploratory circuits

When all primary guards are Unreachable, we need to try non-primary
guards.  We select the first such guard (in preference order) that is
neither Unreachable nor Pending.  Whenever we give out such a guard, if
the guard's status is Unknown, then we call that guard "Pending" until
the attempt to use it succeeds or fails.  We remember when the guard
became Pending.

> Aside: None of the above is a change from our existing specification.

After completing a circuit, the implementation must check whether
its guard is usable.  A guard is usable according to these rules:

Primary guards are always usable.

Non-primary guards are usable for a given circuit if every guard earlier
in the preference list is either unsuitable for that circuit
(e.g. because of family restrictions), or marked as Unreachable, or has
been pending for at least `{NONPRIMARY_GUARD_CONNECT_TIMEOUT}`.

Non-primary guards are unusable for a given circuit if some guard earlier
in the preference list is suitable for the circuit _and_ Reachable.

Non-primary guards are unusable if they have not become usable after
`{NONPRIMARY_GUARD_IDLE_TIMEOUT}` seconds.

If a circuit's guard is neither usable nor unusable immediately, the
circuit is not discarded; instead, it is kept (but not used) until it
becomes usable or unusable.

> I am not 100% sure whether this description produces the same behavior
> as the current guard-spec, but it is simpler to describe, and has
> proven to be simpler to implement.

## Implications for program design.

(This entire section is implementation detail to explain why this is a
simplification from the previous algorithm. It is for explanatory
purposes only and is not part of the spec.)

With this algorithm, we cut down the interaction between the guard code
and the circuit code considerably, but we do not remove it entirely.
Instead, there remains (in Arti terms) a pair of communication channels
between the circuit manager and the guard manager:

 * Whenever a guard is given to the circuit manager, the circuit manager
   receives the write end of a single-use channel to
   report whether the guard has succeeded or failed.

 * Whenever a non-primary guard is given to the circuit manager, the
   circuit receives the read end of a single-use channel that will tell
   it whether the guard is usable or unusable.  This channel doesn't
   report anything until the guard has one status or the other.

With this design, the circuit manager never needs to look at the list of
guards, and the guard manager never needs to look at the list of
circuits.

## Subtleties concerning "guard success"

Note that the above definitions of a Reachable guard depend on reporting
when the _guard_ is successful or failed. This is not necessarily the
same as reporting whether the _circuit_ is successful or failed.  For
example, a circuit that fails after the first hop does not necessarily
indicate that there's anything wrong with the guard.  Similarly, we can
reasonably conclude that the guard is working (at least somewhat) as
long as we have an open channel to it.

