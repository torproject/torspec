```
Filename: 339-udp-over-tor.md
Title: UDP traffic over Tor
Author: Nick Mathewson
Created: 11 May 2020
Status: Accepted
```

# Introduction

Tor currently only supports delivering two kinds of traffic to the
internet: TCP data streams, and a certain limited subset of DNS
requests. This proposal describes a plan to extend the Tor protocol so
that exit relays can also relay UDP traffic to the network?.

Why would we want to do this?  There are important protocols that use
UDP, and in order to support users that rely on these protocols, we'll
need to support them over Tor.

This proposal is a minimal version of UDP-over-Tor.  Notably, it _does
not_ add an unreliable out-of-order transport to Tor's semantics.
Instead, UDP messages are just tunneled over Tor's existing reliable
in-order circuits.  (Adding a datagram transport to Tor is attractive
for some reasons, but it presents a number of problems; see
[this whitepaper](https://research.torproject.org/techreports/side-channel-analysis-2018-11-27.pdf)
for more information.)

In some parts of this proposal I'll assume that we have accepted and
implemented some version of
[proposal 319](https://gitlab.torproject.org/tpo/core/torspec/-/blob/main/proposals/319-wide-everything.md)
(relay fragment cells) so that we can transmit relay messages larger
than 498 bytes.

# Overview

UDP is a datagram protocol; it allows messages of up to 65536 bytes,
though in practice most protocols will use smaller messages in order to
avoid having to deal with fragmentation.

UDP messages can be dropped or re-ordered.  There is no authentication
or encryption baked into UDP, though it can be added by higher-level
protocols like DTLS or QUIC.

When an application opens a UDP socket, the OS assigns it a 16-bit port
on some IP address of a local interface.  The application may send
datagrams from that address:port combination, and will receive datagrams
sent to that address:port.

With most (all?) IP stacks, a UDP socket can either be _connected_ to a
remote address:port (in which case all messages will be sent to that
address:port, and only messages from that address will be passed to the
application), or _unconnected_ (in which case outgoing messages can be
sent to any address:port, and incoming messages from any address:port
will be accepted).

In this version of the protocol, we support only _connected_ UDP
sockets, though we provide extension points for someday adding
_unconnected_ socket support.


# Tor protocol specification


## Overview

We reserve three new relay commands: `CONNECT_UDP`, `CONNECTED_UDP` and
`DATAGRAM`.

The `CONNECT_UDP` command is sent by a client to an exit relay to tell it
to open a new UDP stream "connected" to a targeted address and UDP port.
The same restrictions apply as for CONNECT cells: the target must be
permitted by the relay's exit policy, the target must not be private,
localhost, or ANY, the circuit must appear to be multi-hop, there must
not be a stream with the same ID on the same circuit, and so on.

On success, the relay replies with a `CONNECTED_UDP` cell telling the client
the IP address it is connected to, and which IP address and port (on the
relay) it has bound to.  On failure, the relay replies immediately with
an `END` cell.

(Note that we do not allow the client to choose an arbitrary port to
bind to.  It doesn't work when two clients want the same port, and makes
it too easy to probe which ports are in use.)

When the UDP stream is open, the client can send and receive `DATAGRAM`
messages from the exit relay.  Each such message corresponds to a single
UDP datagram.  If a datagram is larger than 498 bytes, it is
transmitted as a fragmented message.

When a client no longer wishes to use a UDP stream, but it wants to keep
the circuit open, it sends an END cell over the circuit.  Upon receiving
this message, the exit closes the stream, and stops sending any more
cells on it.

Exits MAY send an END cell on a UDP stream; when a client receives it,
it must treat the UDP stream as closed.  Exits MAY send END cells in
response to resource exhaustion, time-out signals, or (TODO what else?).

(TODO: Should there be an END ACK?  We've wanted one in DATA streams for
a while, to know when we can treat a stream as definitively gone-away.)

Optimistic traffic is permitted as with TCP streams: a client MAY send
`DATAGRAM` messages immediately after its `CONNECT_UDP` message, without
waiting for a `CONNECTED_UDP`.  These are dropped if the `CONNECT_UDP` fails.

Clients and exits MAY drop incoming datagrams if their stream
or circuit buffers are too full.  (Once a DATAGRAM message has been sent
on a circuit, however, it cannot be dropped until it reaches its
intended recipient.)

Circuits carrying UDP traffic obey the same SENDME congestion control
protocol as other circuits.  Rather than using XON/XOFF to control
transmission, excess packets may simply be dropped. UDP and TCP traffic
can be mixed on the same circuit, but not on the same stream.

## Discussion on "too full"

(To be determined!  We need an algorithm here before we implement, though
our choice of algorithm doesn't need to be the same on all exits or for
all clients, IIUC.)

Discussion from the pad:

```
  - "Too full" should be a pair of watermark consensus parameter in
     implementation, imo. At the low watermark, random early dropping
     MAY be performed, a-la RED, etc. At the high watermark, all packets
     SHOULD be dropped. - mike
  - +1. I left "too full" as deliberately underspecified here, since I figured
    you would have a better idea than me about what it should really be.
    Maybe we should say "for one suggested algorithm, see section X below" and
    describe the algorithm you propose above in a bit more detail? -nickm
    - I have not dug deeply into drop strategies, but I believe that BLUE
      is what is in use now: https://en.wikipedia.org/wiki/Blue_(queue_management_algorithm)
    - Additionally, an important implementation detail is that it is likely
      best to actually continue to read even if our buffer is full, so we can
      perform the drop ourselves and ensure the kernel/socket buffers don't
      also bloat on us. Though this may have tradeoffs with the eventloop
      bottleneck on C-Tor. Because of that bottleneck, it might be best to
      stop reading. arti likely will have different optimal properties here. -mike
```



## Message formats

Here we describe the format for the bodies of the new relay messages,
along with extensions to some older relay message types.  We note in
passing how we could extend these messages to support unconnected UDP
sockets in the future.


### CONNECT_UDP

```
/* Tells an exit to connect a UDP port for connecting to a new target
   address.  The stream ID is chosen by the client, and is part of
   the relay header.
*/

struct connect_udp_body {
   /* As in BEGIN cells. */
   u32 flags;
   /* Tag for union below. */
   u8 addr_type IN [T_HOSTNAME, T_IPV4, T_IPV6];
   /* Length of the following union */
   u8 addr_len;
   /* The address to connect to. */
   union address[addr_type] with length addr_len {
      T_IPV4: u32 ipv4;
      T_IPV6: u8 ipv6[16];
      T_HOSTNAME: nulterm name
   };
   u16 port;
   // The rest is ignored.

   // TODO: Is "the rest is ignored" still a good idea? Look at Rochet's
   // research.
}
/* Address types */
const T_HOSTNAME = 0x01;
const T_IPV4     = 0x04;
const T_IPV6     = 0x06;

/* As in BEGIN cells: these control how hostnames are interpreted.
   Clients MUST NOT send unrecognized flags; relays MUST ignore them.
   See tor-spec for semantics.
 */
const FLAG_IPV6_OKAY      = 0x01;
const FLAG_IPV4_NOT_OKAY  = 0x02;
const FLAG_IPV6_PREFERRED = 0x04;
```

### CONNECTED_UDP

A CONNECTED_UDP cell sent in response to a CONNECT_UDP cell has the following
format.

```
struct udp_connected_body {
   /* 5 bytes to distinguish from other CONNECTED_UDP cells.  This is not
    * strictly necessary, since we can distinguish by context, but
    * it's nice to have a way to tell them apart at the parsing stage.
    */
   u32 zero IN [0];
   u8 ff IN [0xFF];
   /* The address that the relay has bound locally.  This might not
    * be an address that is advertised in the relay's descriptor. */
   struct address our_address;
   /* The address that the stream is connected to. */
   struct address their_address;
   // The rest is ignored.  There is no resolved-address TTL.

   // TODO: Is "the rest is ignored" still a good idea? Look at Rochet's
   // research.
}

/* Note that this is a subset of the allowable address parts of a CONNECT_UDP 
   message */
struct address {
   u8 tag IN [T_IPV4, T_IPV6];
   u8 len;
   union addr[tag] with length len {
      T_IPV4: u32 ipv4;
      T_IPV6: u8 ipv6[16];
   };
   u16 port;
}
```

### DATAGRAM

```
struct datagram_body {
   /* The datagram body is the entire body of the message.
      This length is in the relay message header.
    */
   u8 body[..];
}
```

### END

We explicitly allow all END reasons from the existing Tor protocol.

We may wish to add more as we gain experience with this protocol.

### Extensions for unconnected sockets

Because of security concerns I don't suggest that we support unconnected
sockets in the first version of this protocol.  But _if we did_, here's how
I'd suggest we do it.

1. We would add a new "`FLAG_UNCONNECTED`" flag for `CONNECT_UDP` messages.

2. We would designate the ANY addresses 0.0.0.0:0 and [::]:0 as permitted in
   `CONNECT_UDP` messages, and as indicating unconnected sockets.  These would
   be only permitted along with the `FLAG_UNCONNECTED` flag, and not
   permitted otherwise.

3. We would designate the ANY addresses above as permitted for the
   `their_address` field in the `CONNECTED_UDP` message, in the case when
   `FLAG_UNCONNECTED` was used.

4. We would define a new `DATAGRAM` message format for unconnected streams,
   where the first 6 or 18 bytes were reserved for an IPv4 or IPv6
   address:port respectively.

## Specifying exit policies and compatibility

We add the following fields to relay descriptors and microdescriptors:

```
// In relay descriptors
ipv4-udp-policy accept PortList
ipv6-udp-policy accept PostList

// In microdescriptors
p4u accept PortList
p6u accept PortList
```

(We need to include the policies in relay descriptors so that the
authorities can include them in the microdescriptors when voting.)

As in the `p` and `p6` fields, the PortList fields are comma-separated
lists of port ranges.  Only "accept" policies are parsed or generated in
this case; the alternative is not appreciably shorter.  When no policy
is listed, the default is "reject 1-65535".

This proposal would also add a new subprotocol, "Datagram".  Only relays
that implement this proposal would advertise "Datagram=1".  Doing so
would not necessarily mean that they permitted datagram streams, if
their exit policies did not say so.


# MTU notes and issues

Internet time.  I might have this wrong.

The "maximum safe IPv4 UDP payload" is "well known" to be only 508 bytes
long: that's defined by the 576-byte minimum-maximum IP datagram size in
[RFC 791 p.12](https://datatracker.ietf.org/doc/html/rfc791), minus 60 bytes
for a very big IPv4 header, minus 8 bytes for the UDP header.

Unfortunately, our RELAY body size is only 498 bytes. It would be lovely if
we could easily move to larger relay cells, or tell applications not to send
datagrams whose bodies are larger than 498 bytes, but there is probably a
pretty large body of tools out there that assume that they will never have to
restrict their datagram size to fit into a transport this small.

(That means that if we implement this proposal _without_ fragmentation,
we'll probably be breaking a bunch of stuff, and creating a great deal
of overhead.)


# Integration issues

I do not know how applications should tell Tor that they want to use this
feature.  Any ideas?  We should probably integrate with their MTU discovery
systems too if we can.  (TODO: write about some alternatives)


# Resource management issues

TODO: Talk about sharing server-side relay sockets, and whether it's safe to
do so, and how to avoid information leakage when doing so.

TODO: Talk about limiting UDP sockets per circuit, and whether that's a good
idea?


# Security issues

- Are there any major DoS or amplification attack vectors that this
  enables? I *think* no, because we don't allow spoofing the IP
  header. But maybe some wacky protocol out there lets you specify a
  reply address in the payload even if the source IP is different. -mike

- Are there port-reuse issues with source port on exits, such that
  destinations could become confused over the start and end of a UDP
  stream, if a source port is reused "too fast"? This also likely varies
  by protocol. We should prameterize time-before-reuse on source port,
  in case we notice issues with some broken/braindead UDP protocol
  later. -mike

# Future work

Extend this for onion services, possibly based on Matt's prototypes.
