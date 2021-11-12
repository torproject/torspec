```
Filename: 333-vanguards-lite.md
Title: Vanguards lite
Author: George Kadianakis, Mike Perry
Created: 2021-05-20
Status: Finished
Implemented-In: 0.4.7.1-alpha
```

# 0. Introduction & Motivation

  This proposal specifies a simplified version of Proposal 292 "Mesh-based
  vanguards" for the purposes of implementing it directly into the C Tor
  codebase.

  For more details on guard discovery attacks and how vanguards defend against
  it, we refer to Proposal 292 [PROP292_REF].

# 1. Overview

  We propose an identical system to the Mesh-based Vanguards from proposal 292,
  but with the following differences:

  - No third layer of guards is used.
  - The Layer2 lifetime uses the max(x,x) distribution with a minimum of one
    day and maximum of 12 days. This makes the average lifetime approximately a
    week.
  - We let NUM_LAYER2_GUARDS=4. We also introduce a consensus parameter
    `guard-hs-l2-number` that controls the number of layer2 guards (with a
    maximum of 19 layer2 guards).
  - We don't write guards on disk. This means that the guard topology resets
    when tor restarts.

  By avoiding a third-layer of guards we avoid most of the linkability issues
  of Proposal 292. This means that we don't add an extra hop on top of most of
  our onion service paths, which increases performance. However, we do add an
  extra middle hop at the end of service-side introduction circuits to avoid
  linkability of L2s by the intro points.

  This is how onion service circuits look like with this proposal:

	 Client rend:   C -> G -> L2 -> Rend
	 Client intro:  C -> G -> L2 -> M -> Intro
	 Client hsdir:  C -> G -> L2 -> M -> HSDir
	 Service rend:  C -> G -> L2 -> M -> Rend
	 Service intro: C -> G -> L2 -> M -> Intro
	 Service hsdir: C -> G -> L2 -> M -> HSDir

# 3. Rotation Period Analysis

  From the table in Section 3.1 of Proposal 292, with NUM_LAYER2_GUARDS=4 it
  can be seen that this means that the Sybil attack on Layer2 will complete
  with 50% chance in 18*7 days (126 days) for the 1% adversary, 4*7 days (one
  month) for the 5% adversary, and 2*7 days (two weeks) for the 10% adversary.

# 4. Tradeoffs from Proposal 292

  This proposal has several advantages over Proposal 292:

  By avoiding a third-layer of guards we reduce the linkability issues of
  Proposal 292, which means that we don't have to add an extra hop on top of
  our paths. This simplifies engineering and makes paths shorter by default:
  this means less latency and quicker page load times.

  This proposal also comes with disadvantages:

  The lack of third-layer guards makes it easier to launch guard discovery
  attacks against clients and onion services. Long-lived services are not well
  protected, and this proposal might provide those services with a false sense
  of security. Such services should still use the vanguards addon [VANGUARDS_REF].

# 4. References

  [PROP292_REF]: https://gitlab.torproject.org/tpo/core/torspec/-/blob/main/proposals/292-mesh-vanguards.txt
  [VANGUARDS_REF]: https://github.com/mikeperry-tor/vanguards
