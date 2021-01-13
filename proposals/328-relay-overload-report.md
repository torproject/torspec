```
Filename: 328-relay-overload-report.md
Title: Make Relays Report When They Are Overloaded
Author: David Goulet, Mike Perry
Created: November 3rd 2020
Status: Draft
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

Then, we propose that 3 new lines be added to the extra-info document (see
dir-spec.txt, section 2.1.2) if only the overload case arrise.

This following describes a series of metrics to collect but more might come in
the future and thus this is not an exhaustive list.

# 1.1. General Overload

The general overload line indicates that a relay has reached an "overloaded
state" which can be one or many of the following load metrics:

   - Any OOMkiller invocation due to memory pressure
   - Any onionskins are dropped
   - CPU utilization of Tor's mainloop CPU core above 90% for 60 sec
   - TCP port exhaustion

The format of the overloaded line added in the extra-info document is as
follow:

```
"overload-reached" YYYY-MM-DD HH:MM:SS NL
   [At most once.]
```

The timestamp is when a at least one metrics was detected. It should always be
at the hour and thus, as an example, "2020-01-10 13:00:00" is an expected
timestamp. Because this is a binary state, if the line is present, we consider
that it was hit at the very least once somewhere between the provided
timestamp and the "published" timestamp of the document which is when the
document was generated.

The overload field should remain in place for 72 hours since last triggered.
If the limits are reached again in this period, the timestamp is updated, and
this 72 hour period restarts.

# 1.2. Token bucket size

Relays should report the 'BandwidthBurst' and 'BandwidthRate' limits in their
descriptor, as well as the number of times these limits were reached, for read
and write, in the past 24 hours starting at the provided timestamp rounded
down to the hour.

```
"overload-ratelimits" SP YYYY-MM-DD SP HH:MM:SS
                      SP rate-limit SP burst-limit
                      SP read-rate-count SP read-burst-count
                      SP write-rate-count SP write-burst-count NL
  [At most once.]
```

The "rate-limit" and "burst-limit" are the raw values from the BandwidthRate
and BandwidthBurst found in the torrc configuration file.

The "{read|write}-rate-count" and "{read|write}-burst-count" are the counts of
how many times the reported limits were exhausted and thus the maximum between
the read and write count occurances.

# 1.3. File Descriptor Exhaustion

Not having enough file descriptors in this day of age is really a
misconfiguration or a too old operation system. That way, we can very quickly
notice which relay has a value too small and we can notify them.

This should be published in this format:

```
"overload-fd-exhausted" YYYY-MM-DD HH:MM:SS NL
  [At most once.]
```

As the overloaded line, the timestamp indicates that the maximum was reached
between the this timestamp and the "published" timestamp of the document.

This overload field should remain in place for 72 hours since last triggered.
If the limits are reached again in this period, the timestamp is updated, and
this 72 hour period restarts.

# 2. Load Metrics

This section proposes a series of metrics that should be collected and
reported to the MetricsPort. The Prometheus format (only one supported for
now) is described for each metrics but each of them are prefixed with the
following in order to have a proper namespace for "load" events:

`tor_load_`

## 2.1 Out-Of-Memory (OOM) Invocation

Tor's OOM manages caches and queues of all sorts. Relays have many of them and
so any invocation of the OOM should be reported.

```
# HELP Total number of bytes the OOM has cleaned up
# TYPE counter
tor_load_oom_bytes_total{<LABEL>} <VALUE>
```

Running counter of how many bytes were cleaned up by the OOM for a tor
component identified by a label (see list below). To make sense, this should
be visualized with the rate() function.

Possible LABELs for which the OOM was triggered:
  - `cell`: Circuit cell queue
  - `dns`: DNS resolution cache
  - `geoip`: GeoIP cache
  - `hsdir`: Onion service descriptors

## 2.2 Onionskin Queues

Onionskins handling is one of the few items that tor processes in parallel but
they can be dropped for various reasons when under load. For this metrics to
make sense, we also need to gather how many onionskins are we processing and
thus one can provide a total processed versus dropped ratio:

```
# HELP Total number of onionskins
# TYPE counter
tor_load_onionskin_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - `processed`: Indicating how many were processed.
  - `dropped`: Indicating how many were dropped due to load.

## 2.3 File Descriptor Exhaustion

Relays can reach a "ulimit" (on Linux) cap that is the number of allowed
opened file descriptors. In Tor's use case, this is mostly sockets. File
descriptors should be reported as follow:

```
# HELP Total number of file descriptors
# TYPE gauge
tor_load_fd_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - `remaining`: How many file descriptors remains that is can be opened.

Note: since tor does track that value in order to reserve a block for critical
port such as the Control Port, that value can easily be exported.

## 2.4 TCP Port Exhaustion

TCP protocol is capped at 65535 ports and thus if the relay ever is unable to
open more outbound sockets, that is an overloaded state. It should be
reported:

```
# HELP Total number of opened outbound connections.
# TYPE gauge
tor_load_socket_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - `outbound`: Sockets used for outbound connections.

## 2.5 Connection Bucket Limit

Rate limited connections track bandwidth using a bucket system. Once the
bucket is filled and tor wants to send more, it pauses until it is refilled a
second later. Once that is hit, it should be reported:

```
# HELP Total number of global connection bucket limit reached
# TYPE counter
tor_load_global_rate_limit_reached_total{<LABEL>} <NUM>
```

Possible LABELs are:
  - `read`: Read side of the global rate limit bucket.
  - `write`: Write side of the global rate limit bucket.
