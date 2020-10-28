```
Filename: 318-limit-protovers.md
Title: Limit protover values to 0-63.
Author: Nick Mathewson
Created: 11 May 2020
Status: Closed
Implemented-In: 0.4.5.1-alpha
```

# Limit protover values to 0-63.

I propose that we no longer accept protover values higher than 63,
so that they can all fit nicely into 64-bit fields.

(This proposal is part of the Walking Onions spec project.)

## Motivation

Doing this will simplify our implementations and our protocols.
Right now, an efficient protover implementation needs to use ranges
to represent possible protocol versions, and needs workarounds to
prevent an attacker from constructing a protover line that would
consume too much memory.  With Walking Onions, we need lists of
protocol versions to be represented in an extremely compact format,
which also would benefit from a limited set of possible versions.

I believe that we will lose nothing by making this
change. Currently, after nearly two decades of Tor development
and 3.5 years of experiences with protovers in production, we have
no protocol version high than 5.

Even if we did someday need to implement higher protocol
versions, we could simply add a new subprotocol name instead.  For
example, instead of "HSIntro=64", we could say "HSIntro2=1".

## Migration

Immediately, authorities should begin rejecting relays with protocol
versions above 63.  (There are no such relays in the consensus right
now.)

Once this change is deployed to a majority of authorities, we can
remove support in other Tor environments for protocol versions
above 63.


