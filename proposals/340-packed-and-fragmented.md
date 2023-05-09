```
Filename: 340-packed-and-fragmented.md
Title: Packed and fragmented relay messages
Author: Nick Mathewson
Created: 31 May 2022
Status: Open
```

# Introduction

Tor sends long-distance messages on circuits via _relay cells_.  The
current relay cell format allows one _relay message_ (e.g., "BEGIN" or
"DATA" or "END") per relay cell. We want to relax this 1:1 requirement,
between messages and cells, for two reasons:

 * To support relay messages that are longer than the current 498-byte
   limit.  Applications would include wider handshake messages for
   postquantum crypto, UDP messages, and SNIP transfer in walking
   onions.

 * To transmit small messages more efficiently.  Several message types
   (notably `SENDME`, `XON`, `XOFF`, and several types from
   [proposal 329](./329-traffic-splitting.txt)) are much smaller than
   the relay cell size, and could be sent comparatively often.

In this proposal, we describe a way to decouple relay cells from relay
messages.  Relay messages can now be packed into multiple cells or split
across multiple cells.

This proposal combines ideas from
[proposal 319](./319-wide-everything.md) (fragmentation) and
[proposal 325](./325-packed-relay-cells.md) (packed cells).  It requires
[ntor v3](./332-ntor-v3-with-extra-data.md) and prepares for
[next-generation relay cryptography](./308-counter-galois-onion).

Additionally, this proposal has been revised to incorporate another
protocol change, and move StreamId from the relay cell header into a new,
optional header.

## A preliminary change: Relay encryption, version 1.5

We are fairly sure that, whatever we do for our next batch of relay
cryptography, we will want to increase the size of the data used to
authenticate relay cells to 128 bits.  (Currently it uses a 4-byte tag
plus 2 bytes of zeros.)

To avoid proliferating formats, I'm going to suggest that we make the
other changes in this proposal changes concurrently with a change in our
relay cryptography, so that we do not have too many incompatible cell
formats going on at the same time.

The new format for a decrypted relay _cell_ will be:

   recognized [2 bytes]
   digest     [14 bytes]
   body       [509 - 16 = 493 bytes]

The `recognized` and `digest` fields are computed as before; the only
difference is that they occur _before_ the rest of the cell, and that `digest`
is truncated to 14 bytes instead of 4.

If we are lucky, we won't have to build this encryption at all, and we
can just move to some version of GCM-UIV or other RPRP that reserves 16
bytes for an authentication tag or similar cryptographic object.

The `body` MUST contain exactly 493 bytes as cells have a fixed size.

## New relay message packing

We define this new format for a relay message which has to fit within one
relay cell. However, the body can be split accross many relay cells:

```
  Message Header
    command         u8
    length          u16
  Message Routing Header (optional)
    stream_id       u16
  Message Body
    data            u8[length]
```

One big change from the current tor protocol is something that has become
optional: we have moved `stream_id` into a separate inner header that only
appears sometimes named the Message Routing Header. The command value tells us
if the header is to be expected or not.

The following message types take required stream IDs: `BEGIN`, `DATA`, `END`,
`CONNECTED`, `RESOLVE`, `RESOLVED`, and `BEGIN_DIR`, `XON`, `XOFF`.

The following message types from proposal 339 (UDP) take required stream IDs:
`CONNECT_UDP`, `CONNECTED_UDP` and `DATAGRAM`.

No other message types take stream IDs. The `stream_id` field, when present,
MUST NOT be zero.

Messages can be split across relay cells; multiple messages can occur in
a single relay cell.  We enforce the following rules:

  * Headers may not be split across cells.
  * If a 0 byte follows a message body, there are no more messages.
  * A relay cell may not be "empty": it must have at least some part of
    some message.

Unless specified elsewhere, **all** message types may be packed, and
**all** message types may be fragmented.

Every command has an associated maximum length for its messages.  If not
specified elsewhere, the maximum length for every message is 498 bytes (for
legacy reasons).

Receivers MUST validate that the cell `header` and the `message header` are
well-formed and have valid lengths while handling the cell in which the header
is encoded. If any of them is invalid, the circuit MUST be destroyed.

An unrecognized `command` is considered invalid and thus MUST result in the
circuit being immediately destroyed.

## Negotiation

This message format requires a new `Relay` subprotocol version to
indicate support.  If a client wants to indicate support for this
format, it sends the following extension as part of its `ntor3`
handshake:

   RELAY_PROTOCOL
     version    u8

The `version` field is the `Relay` subprotocol version that the client
wants to use. The relay must send back the same extension in its ntor3
handshake to acknowledge support.

## Migration

We add a consensus parameter, "streamed-relay-messages", with default
value 0, minimum value 0, and maximum value 1.

If this value is 0, then clients will not (by default) negotiate this
relay protocol.  If it is 1, then clients will negotiate it when relays
support it.

For testing, clients can override this setting.  Once enough relays
support this proposal, we'll change the consensus parameter to 1.
Later, we'll change the default to 1 as well.

## Packing decisions

We specify the following greedy algorithm for making decisions about
fragmentation and packing.  Other algorithms are possible, but this one
is fairly simple, and using it will help avoid distinguishability
issues:

Whenever a client or relay is about to send a cell that would leave
at least 32 bytes unused in a relay cell, it checks to see whether there
is any pending data to be sent in the same circuit (in a data cell).  If
there is, then it adds a DATA message to the end of the current cell,
with as much data as possible.  Otherwise, the client sends the cell
with no packed data.

## Onion services

Negotiating this for onion services will happen in a separate proposal;
it is not a current priority, since there is nothing sent over
rendezvous circuits that we currently need to fragment or pack.

## Miscellany

### Handling `RELAY_EARLY`

The `RELAY_EARLY` status for a command is determined based on the relay
cell in which the command's _header_ appeared.

### Handling `SENDME`s

SENDME messages may not be fragmented; the body and the command must
appear in the same cell.  (This is necessary so authenticated sendmes
can have a reasonable implementation.)

### An exception for `DATA`.

Data messages may not be fragmented.  (There is never a reason to do
this.)

### Extending message-length maxima

For now, the maximum length for every message body is 493 bytes, except as
follows:

   - `DATAGRAM` messages (see proposal 339) have a maximum body length
     of 1967 bytes.  (This works out to four relay cells, and
     accommodates most reasonable MTU choices)

Any increase in maximum length for any other message type requires a new
Relay subprotocol version.  (For example, if we later want to allow
EXTEND2 messages to be 2000 bytes long, we need to add a new proposal
saying so, and reserving a new subprotocol version.)

# Appendix: Example cells

Here is an example of the simplest case: one message, sent in one relay cell:

```
  Cell 1:
    header:
       circid         ..                [4 bytes]
       command        RELAY             [1 byte]
    relay cell header:
       recognized     0                 [2 bytes]
       digest         (...)             [14 bytes]
    message header:
       command        BEGIN             [1 byte]
       length         23                [2 bytes]
    message routing header:
       stream_id      42                [2 bytes]
    message body:
      "www.torproject.org:443\0"        [23 bytes]
    end-of-messages marker:
      0                                 [1 byte]
    padding up to end of cell:
      random                            [464 bytes]
```

Total of 514 bytes which is the absolute maximum cell size.

Here's an example with fragmentation only: a large EXTEND2 message split
across two relay cells.

```
  Cell 1:
    header:
       circid         ..               [4 bytes]
       command        RELAY_EARLY      [1 byte]
    relay cell header:
       recognized     0                [2 bytes]
       digest         (...)            [14 bytes]
    message header:
       command        EXTEND           [1 byte]
       length         800              [2 bytes]
    message body:
       (extend body, part 1)           [490 bytes]

  Cell 2:
    header:
       circid         ..               [4 bytes]
       command        RELAY            [1 byte]
    relay cell header:
      recognized     0                 [2 bytes]
      digest         (...)             [14 bytes]
    message body, continued:
      (extend body, part 2)            [310 bytes] (310+490=800)
    end-of-messages marker:
      0                                [1 byte]
    padding up to end of cell:
      random                           [182 bytes]

```

Each cells are 514 bytes for a message body totalling 800 bytes.

Here is an example with packing only: A `BEGIN_DIR` message and a data message
in the same cell.

```
  Cell 1:
    header:
       circid         ..                [4 bytes]
       command        RELAY             [1 byte]
    relay cell header:
       recognized     0                 [2 bytes]
       digest         (...)             [14 bytes]

    # First relay message
    message header:
       command        BEGIN_DIR         [1 byte]
       length         0                 [2 bytes]
    message routing header:
       stream_id      32                [2 bytes]

    # Second relay message
    message header:
       command        DATA              [1 byte]
       length         25                [2 bytes]
    message routing header:
       stream_id      32                [2 bytes]
    message body:
       "HTTP/1.0 GET /tor/foo\r\n\r\n"  [25 bytes]

    end-of-messages marker:
      0                                 [1 byte]
    padding up to end of cell:
      random                            [457 bytes]

```

Here is an example with packing and fragmentation: a large DATAGRAM cell, a
SENDME cell, and an XON cell.

(Note that this sequence of cells would not actually be generated by the
algorithm described in "Packing decisions" above; this is only an example of
what parties need to accept.)

```
  Cell 1:
    header:
       circid         ..               [4 bytes]
       command        RELAY            [1 byte]
    relay cell header:
       recognized     0                [2 bytes]
       digest         (...)            [14 bytes]

    # First message
    message header:
       command        DATAGRAM         [1 byte]
       length         1200             [2 bytes]
    message routing header:
       stream_id      99               [2 bytes]
    message body:
       (datagram body, part 1)         [488 bytes]

  Cell 2:
    header:
       circid         ..               [4 bytes]
       command        RELAY            [1 byte]
    relay cell header:
      recognized     0                 [2 bytes]
      digest         (...)             [14 bytes]
    message body, continued:
      (datagram body, part 2)          [493 bytes]

  Cell 3:
    header:
       circid         ..               [4 bytes]
       command        RELAY            [1 byte]
    relay cell header:
      recognized     0                 [2 bytes]
      digest         (...)             [14 bytes]
    message body, continued:
      (datagram body, part 3)          [219 bytes] (488+493+219=1200)

    # Second message
    message header:
       command        SENDME           [1 byte]
       length         23               [2 bytes]
    message body:
       version        1                [1 byte]
       datalen        20               [2 bytes]
       data           (digest to ack)  [20 bytes]

    # Third message
    message header:
       command        XON              [1 byte]
       length         1                [2 bytes]
    message routing header:
       stream_id      50               [2 bytes]
    message body:
       version        1                [1 byte]

    end-of-messages marker:
      0                                [1 byte]
    padding up to end of cell:
      random                           [241 bytes]
```
