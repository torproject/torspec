```
Filename: 341-better-oos.md
Title: A better algorithm for out-of-sockets eviction
Author: Nick Mathewson
Created: 25 July 2022
Status: Open
```

# Introduction

Our existing algorithm for handling an out-of-sockets condition needs
improvement.  It only handles sockets used for OR connections, and
prioritizes those with more circuits.  Because of these weaknesses, the
algorithm is trivial to circumvent, and it's disabled by default with
`DisableOOSCheck`.

Here we propose a new algorithm for choosing which connections to close
when we're out of sockets.  In summary, the new algorithm works by
deciding which kinds of connections we have "too many" of, and then by
closing excess connections of each kind.  The algorithm for selecting
connections of each kind is different.



# Intuitions behind the algorithm below

We want to keep a healthy mix of connections running; favoring one kind
of connection over another gives the attacker a fine way to starve the
disfavored connections by making a bunch of the favored kind.

The correct mix of connections depends on the type of service we are
providing.  Everywhere _except_ authorities, for example, inbound
directory connections are perfectly fine to close, since nothing in our
protocol actually generates them.

In general, we would prefer to close DirPort connections, then Exit
connections, then OR connections.

The priority with which to close connections is different depending on
the connection type.  "Age of connection" or "number of circuits" may be
a fine metric for how truly used an OR connection is, but for a DirPort
connection, high age is suspicious.

# The algorithm

Define a "candidate" connection as one that has a socket, and is either
an exit stream, an _inbound_ directory stream, or an OR connection.

(Note that OR connections can be from clients, relays, or bridges. Note
that ordinary relays should not get directory streams that use sockets,
since clients always use `BEGIN_DIR` to create tunneled directory
streams.)

In all of the following, treat subtraction as saturating at zero.  In
other words, when you see "A - B" below, read it as "MAX(A-B, 0)".

## Phase 1: Deciding how many connections to close

When we find that we are low on sockets, we pick a number of sockets
that we want to close according to our existing algorithm.  (That is, we
try to close 1/4 of our maximum sockets if we have reached our upper
limit, or 1/10 of our maximum sockets if we have encountered a failure
from socket(2).)  Call this `N_CLOSE`.

Then we decide which sockets to target based on this algorithm.

1. Consider the total number of sockets used for exit streams
   (`N_EXIT`), the total number used for _inbound_ directory streams
   (`N_DIR`), and the total number used for OR connections (`N_OR`).
   (In these calculations, we exclude connections that are already
   marked to be closed.)  Call the total `N_CONN = N_DIR + N_OR +
   N_EXIT`.  Define `N_RETAIN = N_CONN - N_CLOSE`.

2. Compute how many connections of each type are "in excess". First,
   calculate our target proportions:

    * If we are an authority, let `T_DIR` = 1.  Otherwise set `T_DIR = 0.1`.
    * If we are an exit or we are running an onion service, let `T_EXIT =
      2`. Otherwise let `T_EXIT = 0.1`.
    * Let `T_OR` = 1.

   > TODO: Should those numbers be consensus parameters?

   These numbers define the relative proportions of connections that
   we would be willing to retain retain in our final mix.  Compute a
   number of _excess_ connections of each type by calculating.

   ```
   T_TOTAL = T_OR + T_DIR + T_EXIT.
   EXCESS_DIR   = N_DIR  - N_RETAIN * (T_DIR  / T_TOTAL)
   EXCESS_EXIT  = N_EXIT - N_RETAIN * (T_EXIT / T_TOTAL)
   EXCESS_OR    = N_OR   - N_RETAIN * (T_OR   / T_TOTAL)
   ```

3. Finally, divide N_CLOSE among the different types of excess
   connections, assigning first to excess directory connections, then
   excess exit connections, and finally to excess OR connections.

   ```
   CLOSE_DIR = MIN(EXCESS_DIR, N_CLOSE)
   N_CLOSE := N_CLOSE - CLOSE_DIR
   CLOSE_EXIT = MIN(EXCESS_EXIT, N_CLOSE)
   N_CLOSE := N_CLOSE - CLOSE_EXIT
   CLOSE_OR = MIN(EXCESS_OR, N_CLOSE)
   ```

We will try to close `CLOSE_DIR` directory connections, `CLOSE_EXIT`
exit connections, and `CLOSE_OR` OR connections.

## Phase 2: Closing directory connections

We want to close a certain number of directory connections.  To select
our targets, we sort first by the number of directory connections from
a similar address (see "similar address" below) and then by their age,
preferring to close the oldest ones first.

> This approach defeats "many requests from the same address" and "Open
> a connection and hold it open, and do so from many addresses".  It
> doesn't do such a great job with defeating "open and close frequently
> and do so on many addresses."

> Note that fallback directories do not typically use sockets for
> handling directory connections: theirs are usually created with
> BEGIN_DIR.

## Phase 3: Closing exit connections.

We want to close a certain number of exit connections.  To do this, we
pick an exit connection at random, then close its circuit _along with
all the other exit connections on the same circuit_.  Then we repeat
until we have closed at least our target number of exit connections.

> This approach probabilistically favors closing circuits with a large
> number of sockets open, regardless of how long those sockets have been
> open.  This defeats the easiest way of opening a large number of exit
> streams ("open them all on one circuit") without making the
> counter-approach ("open each exit stream on its own circuit") much
> more attractive.

## Phase 3: Closing OR connections.

We want to close a certain number of OR connections, to clients, bridges, or
relays.

To do this, we first close OR connections with zero circuits.  Then we
close all OR connections but the most recent 2 from each "similar
address".  Then we close OR connections at random from among those _not_
to a recognized relay in the latest directory.  Finally, we close OR
connections at random.

> We used to unconditionally prefer to close connections with fewer
> circuits.  That's trivial for an adversary to circumvent, though: they
> can just open a bunch of circuits on their bogus OR connections, and
> force us to preferentially close circuits from real clients, bridges,
> and relays.

> Note that some connections that seem like client connections ("not
> from relays in the latest directory") are actually those created by
> bridges.

## What is "A similar address"?

We define two connections as having a similar address if they are in the
same IPv4 /30, or if they are in the same IPv6 /90.


# Acknowledgments

This proposal was inspired by a set of
[OOS improvements](https://gitlab.torproject.org/tpo/core/tor/-/issues/32794)
from `starlight`.
