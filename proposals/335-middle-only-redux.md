```
Filename: 335-middle-only-redux.md
Title: An authority-only design for MiddleOnly
Author: Nick Mathewson
Created: 2021-10-08
Status: Closed
Implemented-In: 0.4.7.2-alpha
```

# Introduction

This proposal describes an alternative design for a `MiddleOnly`
flag.  Instead of making changes at the client level, it adds a
little increased complexity at the directory authority's voting
process.  In return for that complexity, this design will work
without additional changes required from Tor clients.

For additional motivation and discussion see proposal 334 by Neel
Chauhan, and the related discussions on tor-dev.

# Protocol changes

## Generating votes

When voting for a relay with the `MiddleOnly` flag, an authority
should vote _for_ all flags indicating that a relay is unusable for a
particular purpose, and _against_ all flags indicating that the relay
is usable for a particular position.

Specifically, these flags SHOULD be set in a vote whenever
`MiddleOnly` is present, and only when the authority is configured
to vote on the `BadExit` flag.

  * `BadExit`

And these flags SHOULD be cleared in a vote whenever `MiddleOnly` is
present.

  * `Exit`
  * `Guard`
  * `HSDir`
  * `V2Dir`

## Computing a consensus

This proposal will introduce a new consensus method (probably 32).
Whenever computing a consensus using that consensus method or later,
authorities post-process the set of flags that appear in the
consensus after flag voting takes place, by applying the same rule
as above.

That is, with this consensus method, the authorities first compute
the presence or absence of each flag on each relay as usual.  Then,
if the `MiddleOnly` flag is present, the authorities set `BadExit`,
and clear `Exit`, `Guard`, `HSDir`, and `V2Dir`.

# Configuring authorities

We'll need a means for configuring which relays will receive this
flag.  For now, we'll just reuse the same mechanism as
`AuthDirReject` and `AuthDirBadExit`: a set of torrc configuration
lines listing relays by address.  We'll call this
`AuthDirMiddleOnly`.

We'll also add an `AuthDirListsMiddleOnly` option to turn on or off
voting on this option at all.

# Notes on safety and migration

Under this design, the MiddleOnly option becomes useful immediately,
since authorities that use it will stop voting for certain
additional options for MiddleOnly relays without waiting for the
other authorities.

We don't need to worry about a single authority setting MiddleOnly
unilaterally for all relays, since the MiddleOnly flag will have no
special effect until most authorities have upgraded to the new
consensus method.
