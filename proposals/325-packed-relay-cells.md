```
Filename: 325-packed-relay-cells.md
Title: Packed relay cells: saving space on small commands
Author: Nick Mathewson
Created: 10 July 2020
Status: Draft
```

# Introduction

In proposal 319 I suggested a way to fragment long commands across
multiple RELAY cells.  In this proposal, I suggest a new format for
RELAY cells that can be used to pack multiple relay commands into a
single cell.

Why would we want to do this?  As we move towards improved
congestion-control and flow-control algorithms, we might not want to
use an entire 498-byte relay payload just to send a one-byte
flow-control message.

We already have some cases where we'd benefit from this feature.
For example, when we send SENDME messages, END cells, or BEGIN_DIR
cells, most of the cell body is wasted with padding.

As a side benefit, packing cells in this way may make the job of the
traffic analyst a little more tricky, as cell contents become less
predictable.

# The basic design

Let's use the term "Relay Message" to mean the kind of thing that a
relay cell used to hold.  Thus, this proposal is about packing
multiple "Relay Messages" in to a cell.

I'll use "Packed relay cell" to mean a relay cell in this new
format, that supports multiple messages.

I'll use "client" to mean the initiator of a circuit, and "relay" to
refer to the parties through who a circuit is created.  Note that
each "relay" (as used here) may be the "client" on circuits of its own.

When a relay supports relay message packing, it advertises the fact
using a new Relay protocol version.  Clients must opt-in to using
this protocol version (see XXX below) before they can send any
packed relay cells, and before the relay will send them any packed
relay cells.

When packed cells are in use, multiple cell messages can be
concatenated in a single relay cell.

Only some relay commands are supported for relay cell packing,
listed here:
      - SENDME
      - DROP
      - DATA
      - BEGIN
      - BEGIN_DIR
      - END
      - CONNECTED
      - PADDING_NEGOTIATE
      - PADDING_NEGOTIATED

If any relay message with a relay command _not_ listed above appears
in a packed relay cell with another relay message, then the
receiving party MUST tear down the circuit.

(Note that relay cell fragments (proposal 319) are not supported for
packing.)

The command byte "0" is now used to explicitly indicate "end of
cell".  If the byte "0" appears after a relay message, the rest of
the cell MUST be ignored.

When generating RELAY cells, implementations SHOULD (as they do
today) fill in the unused bytes with four 0-valued bytes, followed by
a sequence of random bytes up to the end of the cell.  If there are
fewer than 4 unused bytes at the end of the cell, those unused bytes
should all be filled with 0-valued bytes.

# Negotiation and migration

After receiving a packed relay cell, the relay knows that the client
supports this proposal: Relays SHOULD send packed relay
cells on any circuit on which they have received a packed relay
cell.  Relays MUST NOT send packed relay cells otherwise.

Clients, in turn, MAY send packed relay cells to any relay whose
"Relay" subprotocol version indicates that it supports this
protocol.  To avoid fingerprinting, this client behavior should
controlled with a tristate (1/0/auto) torrc configuration value,
with the default set to use a consensus parameter.

The parameter is:

    "relay-cell-packing"

    Boolean: if 1, clients should send packed relay cells.
    (Min: 0, Max 1, Default: 0)

To handle migration, first the parameter should be set to 0 and the
configuration setting should be "auto".  To test the feature, individual
clients can set the tristate to "1".

Once enough clients have support for the parameter, the parameter
can be set to 1.


# A new relay message format

(This section is optional and should be considered separately; we
may decide it is too complex.)

Currently, every relay message uses 5 bytes of header to hold a
relay command, a length field, and a stream ID.  This is wasteful:
the stream ID is often redundant, and the top 7 bits of the length
field are always zero.

I propose a new relay message format, described here (with `ux`
denoting an x-bit bitfield).  This format is 2 bytes or 4 bytes,
depending on its first bit.

    struct relay_header {
       u1 stream_id_included; // Is the stream_id included?
       u6 relay_command; // as before
       u9 relay_data_len; // as before
       u8 optional_stream_id[]; // 0 bytes or two bytes.
    }

Alternatively, you can view the first three fields as a 16-bit
value, computed as:

    (stream_id_included<<15) | (relay_command << 9) | (relay_data_len).

If the optional_stream_id field is not present, then the default
value for the stream_id is computed as follows.  We use stream_id 0
for any command that doesn't take a stream ID.  For commands that
_do_ take a steam_id, we use whichever nonzero stream_id appeared
most recently in the same cell.

This format limits the space of possible relay commands.  That's
probably okay: after 20 years of Tor development, we have defined 25
relay command values.  But in case 2^6==64 commands will not be
enough, we reserve command values 48 through 63 for future formats
that need more command bits.

