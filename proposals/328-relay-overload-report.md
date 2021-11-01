```
Filename: 328-relay-overload-report.md
Title: Make Relays Report When They Are Overloaded
Author: David Goulet, Mike Perry
Created: November 3rd 2020
Status: Closed
```

# 0. Introduction

Many relays are likely sometimes under heavy load in terms of memory, CPU or
network resources which in turns diminishes their ability to efficiently relay
data through the network.

Having the capability of learning if a relay is overloaded would allow us to
make better informed load balancing decisions. For instance, we can make our
bandwidth scanners more intelligent on how they allocate bandwidth based on
such metrics from relays.

We could furthermore improve our network health monitoring and pinpoint relays
possibly misbehaving or under DDoS attack.

# 1. Metrics to Report

We propose that relays start collecting several metrics (see section 2)
reflecting their loads from different component of tor.

Then, we propose that 1 new line be added to the server descriptor document
(see dir-spec.txt, section 2.1.1) for the general overload case.

And 2 new lines to the extra-info document (see dir-spec.txt, section 2.1.2)
for more specific overload cases.

The following describes a series of metrics to collect but more might come in
the future and thus this is not an exhaustive list.

# 1.1. General Overload

The general overload line indicates that a relay has reached an "overloaded
state" which can be one or many of the following load metrics:

   - Any OOM invocation due to memory pressure
   - Any ntor onionskins are dropped
   - TCP port exhaustion
   - DNS timeout reached (X% of timeouts over Y seconds).
   - CPU utilization of Tor's mainloop CPU core above 90% for 60 sec
     [Never implemented]
   - Control port overload (too many messages queued)
     [Never implemented]

For DNS timeouts, the X and Y are consensus parameters
(overload_dns_timeout_scale_percent and overload_dns_timeout_period_secs)
defined in param-spec.txt.

The format of the overloaded line added in the server descriptor document is
as follows:

```
"overload-general" SP version SP YYYY-MM-DD HH:MM:SS NL
   [At most once.]
```

The timestamp is when at least one metric was detected. It should always be
at the hour and thus, as an example, "2020-01-10 13:00:00" is an expected
timestamp. Because this is a binary state, if the line is present, we consider
that it was hit at the very least once somewhere between the provided
timestamp and the "published" timestamp of the document which is when the
document was generated.

The overload field should remain in place for 72 hours since last triggered.
If the limits are reached again in this period, the timestamp is updated, and
this 72 hour period restarts.

The 'version' field is set to '1' for the initial implementation of this
proposal which includes all the above overload metrics except from the CPU and
control port overload. 

# 1.2. Token bucket size

Relays should report the 'BandwidthBurst' and 'BandwidthRate' limits in their
descriptor, as well as the number of times these limits were reached, for read
and write, in the past 24 hours starting at the provided timestamp rounded down
to the hour.

The format of this overload line added in the extra-info document is as
follows:

```
"overload-ratelimits" SP version SP YYYY-MM-DD SP HH:MM:SS
                      SP rate-limit SP burst-limit
                      SP read-overload-count SP write-overload-count NL
  [At most once.]
```

The "rate-limit" and "burst-limit" are the raw values from the BandwidthRate
and BandwidthBurst found in the torrc configuration file.

The "{read|write}-overload-count" are the counts of how many times the reported
limits of burst/rate were exhausted and thus the maximum between the read and
write count occurrences. To make the counter more meaningful and to avoid
multiple connections saturating the counter when a relay is overloaded, we only
increment it once a minute.

The 'version' field is set to '1' for the initial implementation of this
proposal.

# 1.3. File Descriptor Exhaustion

Not having enough file descriptors in this day of age is really a
misconfiguration or a too old operation system. That way, we can very quickly
notice which relay has a value too small and we can notify them.

The format of this overload line added in the extra-info document is as
follows:

```
"overload-fd-exhausted" SP version YYYY-MM-DD HH:MM:SS NL
  [At most once.]
```

As the overloaded line, the timestamp indicates that the maximum was reached
between the this timestamp and the "published" timestamp of the document.

This overload field should remain in place for 72 hours since last triggered.
If the limits are reached again in this period, the timestamp is updated, and
this 72 hour period restarts.

The 'version' field is set to '1' for the initial implementation of this
proposal which detects fd exhaustion only when a socket open fails.

# 2. Load Metrics

This section proposes a series of metrics that should be collected and
reported to the MetricsPort. The Prometheus format (only one supported for
now) is described for each metrics.

## 2.1 Out-Of-Memory (OOM) Invocation

Tor's OOM manages caches and queues of all sorts. Relays have many of them and
so any invocation of the OOM should be reported.

```
# HELP Total number of bytes the OOM has cleaned up
# TYPE counter
tor_relay_load_oom_bytes_total{<LABEL>} <VALUE>
```

Running counter of how many bytes were cleaned up by the OOM for a tor
component identified by a label (see list below). To make sense, this should
be visualized with the rate() function.

Possible LABELs for which the OOM was triggered:
  - `subsys=cell`: Circuit cell queue
  - `subsys=dns`: DNS resolution cache
  - `subsys=geoip`: GeoIP cache
  - `subsys=hsdir`: Onion service descriptors

## 2.2 Onionskin Queues

Onionskins handling is one of the few items that tor processes in parallel but
they can be dropped for various reasons when under load. For this metrics to
make sense, we also need to gather how many onionskins are we processing and
thus one can provide a total processed versus dropped ratio:

```
# HELP Total number of onionskins
# TYPE counter
tor_relay_load_onionskins_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - `type=<handshake_type>`: Type of handshake of that onionskins.
      * Possible values: `ntor`, `tap`, `fast`
  - `action=processed`: Indicating how many were processed.
  - `action=dropped`: Indicating how many were dropped due to load.

## 2.3 File Descriptor Exhaustion

Relays can reach a "ulimit" (on Linux) cap that is the number of allowed
opened file descriptors. In Tor's use case, this is mostly sockets. File
descriptors should be reported as follow:

```
# HELP Total number of sockets
# TYPE gauge
tor_relay_load_socket_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - <none>: How many available sockets.
  - `state=opened`: How many sockets are opened.

Note: since tor does track that value in order to reserve a block for critical
port such as the Control Port, that value can easily be exported.

## 2.4 TCP Port Exhaustion

TCP protocol is capped at 65535 ports and thus if the relay ever is unable to
open more outbound sockets, that is an overloaded state. It should be
reported:

```
# HELP Total number of times we ran out of TCP ports
# TYPE gauge
tor_relay_load_tcp_exhaustion_total <NUM>
```

## 2.5 Connection Bucket Limit

Rate limited connections track bandwidth using a bucket system. Once the
bucket is filled and tor wants to send more, it pauses until it is refilled a
second later. Once that is hit, it should be reported:

```
# HELP Total number of global connection bucket limit reached
# TYPE counter
tor_relay_load_global_rate_limit_reached_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - `side=read`: Read side of the global rate limit bucket.
  - `side=write`: Write side of the global rate limit bucket.
