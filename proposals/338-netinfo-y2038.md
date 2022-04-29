```
Filename: 338-netinfo-y2038.md
Title: Use an 8-byte timestamp in NETINFO cells
Author: Nick Mathewson
Created: 2022-03-14
Status: Accepted
```

# Introduction

Currently Tor relays use a 4-byte timestamp (in seconds since the Unix
epoch) in their NETINFO cells.  Notoriously, such a timestamp will
overflow on 19 January 2038.

Let's get ahead of the problem and squash this issue now, by expanding
the timestamp to 8 bytes. (8 bytes worth of seconds will be long enough
to outlast the Earth's sun.)

# Proposed change

I propose adding a new link protocol version.  (The next one in
sequence, as of this writing, is version 6.)

I propose that we change the text of tor-spec section 4.5 from:

```
      TIME       (Timestamp)                     [4 bytes]
```

to

```
     TIME       (Timestamp)                     [4 or 8 bytes *]
```

and specify that this field is 4 bytes wide on link protocols 1-5, but 8
bytes wide on link protocols 6 and beyond.

# Rejected alternatives

Our protocol specifies that parties MUST ignore extra data at the end of
cells. Therefore we _could_ add additional data at the end of the
NETINFO cell, and use that to store the high 4 bytes of the timestamp
without having to increase the link protocol version number.  I propose
that we don't do that: it's ugly.

As another alternative, we could declare that parties must interpret the
timestamp such that its high 4 bytes place it as close as possible to
their current time.  I'm rejecting this kludge because it would give
confusing results in the too-common case where clients have their clocks
mis-set to Jan 1, 1970.

# Impacts on our implementations

Arti won't be able to implement this change until it supports connection
padding (as required by link protocol 5), which is currently planned for
the next Arti milestone (1.0.0, scheduled for this fall).

If we think that that's a problem, or if we want to have support for
implementations without connection padding in the future, we should
reconsider this plan so that connection padding support is independent
from 8-byte timestamps.

# Other timestamps in Tor

I've done a cursory search of our protocols to see if we have any other
instances of the Y2038 problem.

There is a 4-byte timestamp in `cert-spec`, but that one is an unsigned
integer counting _hours_ since the Unix epoch, which will keep it from
wrapping around till 478756 C.E. (The rollover date of "10136 CE"
reported in `cert-spec` is wrong, and seems to be based on the
misapprehension that the counter is in *minutes*.)

The v2 onion service protocol has 4-byte timestamps, but it is
thoroughly deprecated and unsupported.

I couldn't find any other 4-byte timestamps, but that is no guarantee:
others should look for them too.
