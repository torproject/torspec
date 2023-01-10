```
Filename: 342-decouple-hs-interval.md
Title: Decoupling hs_interval and SRV lifetime
Author: Nick Mathewson
Created: 9 January 2023
Status: Draft
```

# Motivation and introduction

Tor uses shared random values (SRVs) in the consensus to determine
positions of relays within a hash ring.  Which shared random value is to
be used for a given time period depends upon the time at which that
shared random value became valid.

But right now, the consensus voting period is closely tied to the shared
random value voting cycle: and clients need to understand both of these
in order to determine when a shared random value became current.

This creates tight coupling between:
   * The voting schedule
   * The SRV liveness schedule
   * The hsdir_interval parameter that determines the length of the
     an HSDIR index

To decouple these values, this proposal describes a forward compatible
change to how Tor reports SRVs in consensuses, and how Tor decides which
hash ring to use when.


## Reporting SRV timestamps

In consensus documents, parties should begin to accept
`shared-rand-*-value` lines with an additional argument, in the format
of an IsoTimeNospace timestamp (like "1985-10-26T00:00:00").  When
present, this timestamp indicates the time at which the given shared
random value first became the "current" SRV.

Additionally, we define a new consensus method that adds these
timestamps to the consensus.

We specify that, in the absence of such a timestamp, parties are to
assume that the `shared-rand-current-value` SRV became "current" at the
first 00:00 UTC on the UTC day of the consensus's valid-after timestamp,
and that the `shard-rand-previous-value` SRV became "current" at 00:00
UTC on the previous UTC day.


## Generalizing HSDir index scheduling.

Under the current HSDir design, there is one SRV for each time period,
and one time period for which each SRV is in use.  Decoupling
`hsdir_interval` from 24 hours will require that we change this notion
slightly.

We therefore propose this set of generalized directory behavior rules,
which should be equivalent to the current rules under current
parameters.

The calculation of time periods remains the same (see `rend-spec-v3.txt`
section `[TIME PERIODS]`).

A single SRV is associated with each time period: specifically, the SRV
that was "current" at the start of the time period.

There is a separate hash ring associated with each time period and its
SRV.

Whenever fetching an onion service descriptor, the client uses the hash
ring for the time period that contains the start of the liveness
interval of the current consensus.  Call this the "Consensus" time period.

Whenever uploading an onion service descriptor, the service uses _two or
three_ hash rings:
  * The "consensus" time period (see above).
  * The immediately preceding time period, if the SRV to calculate that
    hash ring is available in the consensus.
  * The immediately following time period, if the SRV to calculate that
    hash ring is available in the consensus.

(Under the current parameters, where `hsdir_interval = SRV_interval`,
there will never be more than two possible time periods for which the
service can qualify.)

## Migration

We declare that, for at least the lifetime of the C tor client, we will
not make any changes to the voting interval, the SRV interval, or the
`hsdir_interval`.  As such, we do not need to prioritize implementing
these changes in the C client: we can make them in Arti only.

## Issues left unsolved

There are likely other lingering issues that would come up if we try to
change the voting interval.  This proposal does not attempt to solve
them.

This proposal does not attempt to add flexibility to the SRV voting
algorithm itself.

Changing `hsdir_interval` would create a flag day where everybody using
old and new values of `hsdir_interval` would get different hash
rings. We do not try to solve that here.

## Acknowledgments

Thanks to David Goulet for explaining all of this stuff to me!
