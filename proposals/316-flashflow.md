```
Filename: 316-flashflow.txt
Title: FlashFlow: A Secure Speed Test for Tor (Parent Proposal)
Author: Matthew Traudt, Aaron Johnson, Rob Jansen, Mike Perry
Created: 23 April 2020
Status: Draft
```

# Markdown revision TODO:

- `[ ]` hyperlink sources
- `[ ]` make section numbers work, or don't use them, or ...?
- `[.]` do coords need to communicate? No. Specify better in Measurement
        Scheduling section
    - addressed in Intro

# Introduction

FlashFlow is a new distributed bandwidth measurement system for Tor that
consists of a single authority node ("coordinator") instructing one or
more measurement nodes ("measurers") when and how to measure Tor relays.
A measurement consists of the following steps:

1. The measurement nodes demonstrate to the target relay permission to
   perform measurements.
2. The measurement nodes open many TCP connections to the target relay
   and create a one-hop circuit to the target relay on each one.
3. For 30 seconds the measurement nodes send measurement cells to the
   target relay and verify that the cells echoed back match the ones
   sent. During this time the relay caps the amount of background
   traffic it transfers. Background and measurement traffic are
   handled separately at the relay. Measurement traffic counts towards
   all the standard existing relay statistics.
4. For every second during the measurement, the measurement nodes
   report to the authority node how much traffic was echoed back. The
   target relay also reports the amount of per-second background
   (non-measurement) traffic.
5. The authority node sums the per-second reported throughputs into 30
   sums (one for each second) and calculates the median. This is the
   estimated capacity of the relay.

FlashFlow performs a measurement of every relay according to a schedule
described later in this document. Periodically it produces relay
capacity estimates in the form of a v3bw file, which is suitable for
direct consumption by a Tor directory authority. Alternatively an
existing load balancing system such as Simple Bandwidth Scanner could be
modified to use FlashFlow's v3bw file as input.

It is envisioned that each directory authority that wants to use
FlashFlow will run their own FlashFlow deployment consisting of a
coordinator that they run and one or more measurers that they trust
(e.g. because they run them themselves), similar to how each runs their
own Torflow/sbws. Section 5.2 of this proposal describes long term plans
involving multiple FlashFlow deployments. *FlashFlow coordinators do not need
to communicate with each other*.

FlashFlow is more performant than Torflow: FlashFlow takes 5 hours to
measure the entire existing Tor network from scratch (with 3 Gbit/s
measurer capacity) while Torflow takes 2 days; FlashFlow measures relays
it hasn't seen recently as soon as it learns about them (i.e. every new
consensus) while Torflow can take a day or more; and FlashFlow
accurately measures new high-capacity relays the first time and every
time while Torflow takes days/weeks to assign them their full fair share
of bandwidth (especially for non-exits). FlashFlow is more secure than
Torflow: FlashFlow allows a relay to inflate its measured capacity by up
to 1.33x (configured by a parameter) while Torflow allows weight
inflation by a factor of 89x [0] or even 177x [1].

After an overview in section 2 of the planned deployment stages, section
3, 4, and 5 discuss the short, medium, and long term deployment plans in
more detail.

# Deployment Stages

FlashFlow's deployment shall be broken up into three stages.

In the short term we will implement a working FlashFlow measurement
system. This requires code changes in little-t tor and an external
FlashFlow codebase. The majority of the implementation work will be
done in the short term, and the product is a complete FlashFlow
measurement system. Remaining pieces (e.g. better authentication) are
added later for enhanced security and network performance.

In the medium term we will begin collecting data with a FlashFlow
deployment. The intermediate results and v3bw files produced will be
made available (semi?) publicly for study.

In the long term experiments will be performed to study ways of using FF
v3bw files to improve load balancing. Two examples: (1) using FF v3bw
files instead of sbws's (and eventually phasing out torflow/sbws), and
(2) continuing to run sbws but use FF's results as a better estimate of
relay capacity than observed bandwidth. Authentication and other
FlashFlow features necessary to make it completely ready for full
production deployment will be worked on during this long term phase.

# FlashFlow measurement system: Short term

The core measurement mechanics will be implemented in little-t tor, but
a separate codebase for the FlashFlow side of the measurement system
will also be created. This section is divided into three parts: first a
discussion of changes/additions that logically reside entirely within
tor (essentially: relay-side modifications), second a discussion of the
separate FlashFlow code that also requires some amount of tor changes
(essentially: measurer-side and coordinator-side modifications), and
third a security discussion.

## Little-T Tor Components

The primary additions/changes that entirely reside within tor on the
relay side:

- New torrc options/consensus parameters.
- New cell commands.
- Pre-measurement handshaking (with a simplified authentication
  scheme).
- Measurement mode, during which the relay will echo traffic with
  measurers, set a cap on the amount of background traffic it
  transfers, and report the amount of transferred background traffic.

### Parameters

FlashFlow will require some consensus parameters/torrc options. Each has
some default value if nothing is specified; the consensus parameter
overrides this default value; the torrc option overrides both.

FFMeasurementsAllowed: A global toggle on whether or not to allow
measurements. Even if all other settings would allow a measurement, if
this is turned off, then no measurement is allowed. Possible values: 0,
1. Default: 0 (disallowed).

FFAllowedCoordinators: The list of coordinator TLS certificate
fingerprints that are allowed to start measurements. Relays check their
torrc when they receive a connection from a FlashFlow coordinator to see
if it's on the list. If they have no list, they check the consensus
parameter. If nether exist, then no FlashFlow deployment is allowed to
measure this relay. Default: empty list.

FFMeasurementPeriod: A relay should expect on average, to be measured by
each FlashFlow deployment once each measurement period. A relay will not
allow itself to be measured more than twice by a FlashFlow deployment in
any time window of this length. Relays should not change this option
unless they really know what they're doing. Changing it at the relay
will not change how often FlashFlow will attempt to measure the relay.
Possible values are in the range [1 hour, 1 month] inclusive. Default: 1
day.

FFBackgroundTrafficPercent: The maximum amount of regular
non-measurement traffic a relay should handle while being measured, as a
percent of total traffic (measurement + non-measurement). This
parameter is a trade off between having to limit background traffic and
limiting how much a relay can inflate its result by handling no
background traffic but reporting that it has done so. Possible values
are in the range [0, 99] inclusive. Default: 25 (a maximum inflation
factor of 1.33).

FFMaxMeasurementDuration: The maximum amount of time, in seconds, that
is allowed to pass from the moment the relay is notified that a
measurement will begin soon and the end of the measurement. If this
amount of time passes, the relay shall close all measurement connections
and exit its measurement mode. Note this duration includes handshake
time, thus it necessarily is larger than the expected actual measurement
duration. Possible values are in the range [10, 120] inclusive.
Default: 45.

### New Cell Types

FlashFlow will introduce a new cell command MEASURE.

The payload of each MEASURE cell consists of:

```
Measure command [1 byte]
Length          [2 bytes]
Data            [Length-3 bytes]
```

The measure commands are:

```
0 -- MSM_PARAMS    [forward]
1 -- MSM_PARAMS_OK [backward]
2 -- MSM_ECHO      [forward and backward]
3 -- MSM_BG        [backward]
4 -- MSM_ERR       [forward and backward]
```

Forward cells are sent from the measurer/coordinator to the relay.
Backward cells are sent from the relay to the measurer/coordinator.

MSM_PARAMS and MSM_PARAMS_OK are used during the pre-measurement stage
to tell the target what to expect and for the relay to positively
acknowledge the message. MSM_ECHO cells are the measurement traffic;
the measurer generates them, sends them to the target, and the target
echos them back. The target send a MSM_BG cell once per second to report
the amount of background traffic it is handling. MSM_ERR cells are used
to signal to the other party that there has been some sort of problem
and that the measurement should be aborted. These measure commands are
described in more detail in the next section.

The only cell that sometimes undergoes cell encryption is MSM_ECHO; no
other cell ever gets cell encrypted. (All cells are transmitted on a
regular TLS-wrapped OR connection; that encryption still exists.)

The relay "decrypts" MSM_ECHO cells before sending them back to the
measurer; this mirrors the way relays decrypt/encrypt RELAY_DATA cells
in order to induce realistic cryptographic CPU load. The measurer
usually skips encrypting MSM_ECHO cells to reduce its own CPU load;
however, to verify the relay is actually correctly decrypting all cells,
the measurer will choose random outgoing cells, encrypt them, remember
the ciphertext, and verify the corresponding incoming cell matches.

### Pre-Measurement Handshaking/Starting a Measurement

The coordinator connects to the target relay and sends it a MSM_PARAMS
cell. If the target is unwilling to be measured at this time or if the
coordinator didn't use a TLS certificate that the target trusts, it
responds with an error cell and closes the connection. Otherwise it
checks that the parameters of the measurement are acceptable (e.g. the
version is acceptable, the duration isn't too long, etc.). If the
target is happy, it sends a MSM_PARAMS_OK, otherwise it sends a MSM_ERR
and closes the connection.

Upon learning the IP addresses of the measurers from the coordinator in
the MSM_PARAMS cell, the target whitelists their IPs in its DoS
detection subsystem until the measurement ends (successfully or
otherwise), at which point the whitelist is cleared.

Upon receiving a MSM_PARAMS_OK from the target, the coordinator will
instruct the measurers to open their TCP connections with the target. If
the coordinator or any measurer receives a MSM_ERR, it reports the error
to the coordinator and considers the measurement a failure. It is also a
failure if any measurer is unable to open at least half of its TCP
connections with the target.

The payload of MSM_PARAMS cells [XXX more may need to be added]:

```
- version       [1 byte]
- msm_duration  [1 byte]
- num_measurers [1 byte]
- measurer_info [num_measurers times]
  - ipv4_addr   [4 bytes]
  - num_conns   [2 bytes]
```

version dictates how this MSM_PARAMS cell shall be parsed. msm_duration
is the duration, in seconds, that the actual measurement will last.
num_measurers is how many measurer_info structs follow. For each
measurer, the ipv4_addr it will use when connecting to the target is
provided, as is num_conns, the number of TCP connections that measurer
will open with the target. Future versions of FlashFlow and MSM_PARAMS
will use TLS certificates instead of IP addresses.

MSM_PARAMS_OK has no payload: it's just padding bytes to make the cell
514 bytes long.

The payload of MSM_ECHO cells:

```
- arbitrary bytes [max to fill up 514 byte cell]
```

The payload of MSM_BG cells:

```
- second        [1 byte]
- sent_bg_bytes [4 bytes]
- recv_bg_bytes [4 bytes]
```

second is the number of seconds since the measurement began. MSM_BG
cells are sent once per second from the relay to the FlashFlow
coordinator. The first cell will have this set to 1, and each
subsequent cell will increment it by one. sent_bg_bytes is the number of
background traffic bytes sent in the last second (since the last MSM_BG
cell). recv_bg_bytes is the same but for received bytes.

The payload of MSM_ERR cells:

```
- err_code [1 byte]
- err_str  [possibly zero-len null-terminated string]
```

The error code is one of:

```
[... XXX TODO ...]
255 -- OTHER
```

The error string is optional in all cases. It isn't present if the first
byte of err_str is null, otherwise it is present. It ends at the first
null byte or the end of the cell, whichever comes first.

### Measurement Mode

The relay considers the measurement to have started the moment it
receives the first MSM_ECHO cell from any measurer. At this point, the
relay

- Starts a repeating 1s timer on which it will report the amount of
  background traffic to the coordinator over the coordinator's
  connection.
- Enters "measurement mode" and limits the amount of background
  traffic it handles according to the torrc option/consensus
  parameter.

The relay decrypts and echos back all MSM_ECHO cells it receives on
measurement connections until it has reported its amount of background
traffic the same number of times as there are seconds in the measurement
(e.g. 30 per-second reports for a 30 second measurement). After sending
the last MSM_BG cell, the relay drops all buffered MSM_ECHO cells,
closes all measurement connections, and exits measurement mode.

During the measurement the relay targets a ratio of background traffic
to measurement traffic as specified by a consensus parameter/torrc
option. For a given ratio r, if the relay has handled x cells of
measurement traffic recently, Tor then limits itself to y = xr/(1-r)
cells of non-measurement traffic this scheduling round. The target will
enforce that a minimum of 10 Mbit/s of measurement traffic is recorded
since the last background traffic scheduling round to ensure it always
allows some minimum amount of background traffic.

## FlashFlow Components

The FF coordinator and measurer code will reside in a FlashFlow
repository separate from little-t tor.

There are three notable parameters for which a FF deployment must choose
values. They are:

- The number of sockets, s, the measurers should open, in aggregate,
  with the target relay. We suggest s=160 based on the FF paper.
- The bandwidth multiplier, m. Given an existing capacity estimate for
  a relay, z, the coordinator will instruct the measurers to, in
  aggregate, send m*z Mbit/s to the target relay. We recommend m=2.25.
- The measurement duration, d. Based on the FF paper, we recommend
  d=30 seconds.

The rest of this section first discusses notable functions of the
FlashFlow coordinator, then goes on to discuss FF measurer code that
will require supporting tor code.

### FlashFlow Coordinator

The coordinator is responsible for scheduling measurements, aggregating
results, and producing v3bw files. It needs continuous access to new
consensus files, which it can obtain by running an accompanying Tor
process in client mode.

The coordinator has the following functions, which will be described in
this section:

- result aggregation.
- schedule measurements.
- v3bw file generation.

#### Aggregating Results

Every second during a measurement, the measurers send the amount of
verified measurement traffic they have received back from the relay.
Additionally, the relay sends a MSM_BG cell each second to the
coordinator with amount of non-measurement background traffic it is
sending and receiving.

For each second's reports, the coordinator sums the measurer's reports.
The coordinator takes the minimum of the relay's reported sent and
received background traffic. If, when compared to the measurer's reports
for this second, the relay's claimed background traffic is more than
what's allowed by the background/measurement traffic ratio, then the
coordinator further clamps the relay's report down. The coordinator adds
this final adjusted amount of background traffic to the sum of the
measurer's reports.

Once the coordinator has done the above for each second in the
measurement (e.g. 30 times for a 30 second measurement), the coordinator
takes the median of the 30 per-second throughputs and records it as the
estimated capacity of the target relay.

#### Measurement Schedule

The short term implementation of measurement scheduling will be simpler
than the long term one due to (1) there only being one FlashFlow
deployment, and (2) there being very few relays that support being
measured by FlashFlow. In fact the FF coordinator will maintain a list
of the relays that have updated to support being measured and have opted
in to being measured, and it will only measure them.

The coordinator divides time into a series of 24 hour periods, commonly
referred to as days. Each period has measurement slots that are longer
than a measurement lasts (30s), say 60s, to account for pre- and
post-measurement work. Thus with 60s slots there's 1,440 slots in a
day.

At the start of each day the coordinator considers the list of relays
that have opted in to being measured. From this list of relays, it
repeatedly takes the relay with the largest existing capacity estimate.
It selects a random slot. If the slot has existing relays assigned to
it, the coordinator makes sure there is enough additional measurer
capacity to handle this relay. If so, it assigns this relay to this
slot. If not, it keeps picking new random slots until one has sufficient
additional measurer capacity.

Relays without existing capacity estimates are assumed to have the 75th
percentile capacity of the current network.

If a relay is not online when it's scheduled to be measured, it doesn't
get measured that day.

##### Example

Assume the FF deployment has 1 Gbit/s of measurer capacity. Assume the
chosen multiplier m=2. Assume there are only 5 slots in a measurement
period.

Consider a set of relays with the following existing capacity estimates
and that have opted in to being measured by FlashFlow.

- 500 Mbit/s
- 300 Mbit/s
- 250 Mbit/s
- 200 Mbit/s
- 100 Mbit/s
-  50 Mbit/s

The coordinator takes the largest relay, 500 Mbit/s, and picks a random
slot for it. It picks slot 3. The coordinator takes the next largest,
300, and randomly picks slot 2. The slots are now:

```
   0   |   1   |   2   |   3   |   4
-------|-------|-------|-------|-------
       |       |  300  |  500  |
       |       |       |       |
```

The coordinator takes the next largest, 250, and randomly picks slot 2.
Slot 2 already has 600 Mbit/s of measurer capacity reserved (300*m);
given just 1000 Mbit/s of total measurer capacity, there is just 400
Mbit/s of spare capacity while this relay requires 500 Mbit/s. There is
not enough room in slot 2 for this relay. The coordinator picks a new
random slot, 0.

```
   0   |   1   |   2   |   3   |   4
-------|-------|-------|-------|-------
  250  |       |  300  |  500  |
       |       |       |       |
```

The next largest is 200 and the coordinator randomly picks slot 2 again
(wow!). As there is just enough spare capacity, the coordinator assigns
this relay to slot 2.

```
   0   |   1   |   2   |   3   |   4
-------|-------|-------|-------|-------
  250  |       |  300  |  500  |
       |       |  200  |       |
```

The coordinator randomly picks slot 4 for the last remaining relays, in
that order.

```
   0   |   1   |   2   |   3   |   4
-------|-------|-------|-------|-------
  250  |       |  300  |  500  |  100
       |       |  200  |       |   50
```

#### Generating V3BW files

Every hour the FF coordinator produces a v3bw file in which it stores
the latest capacity estimate for every relay it has measured in the last
week. The coordinator will create this file on the host's local file
system. Previously-generated v3bw files will not be deleted by the
coordinator. A symbolic link at a static path will always point to the
latest v3bw file.

```
$ ls -l
v3bw -> v3bw.2020-03-01-05-00-00
v3bw.2020-03-01-00-00-00
v3bw.2020-03-01-01-00-00
v3bw.2020-03-01-02-00-00
v3bw.2020-03-01-03-00-00
v3bw.2020-03-01-04-00-00
v3bw.2020-03-01-05-00-00
```

### FlashFlow Measurer

The measurers take commands from the coordinator, connect to target
relays with many sockets, send them traffic, and verify the received
traffic is the same as what was sent. Measurers need access to a lot of
internal tor functionality. One strategy is to house as much logic as
possible inside an compile-time-optional control port module that calls
into other parts of tor. Alternatively FlashFlow could link against tor
and call internal tor functions directly.

[XXX for now I'll assume that an optional little-t tor control port
module housing a lot of this code is the best idea.]

Notable new things that internal tor code will need to do on the
measurer (client) side:

1. Open many TLS+TCP connections to the same relay on purpose.
2. Verify echo cells.

#### Open many connections

FlashFlow prototypes needed to "hack in" a flag in the
open-a-connection-with-this-relay function call chain that indicated
whether or not we wanted to force a new connection to be created. Most
of Tor doesn't care if it reuses an existing connection, but FF does
want to create many different connections. The cleanest way to
accomplish this will be investigated.

On the relay side, these measurer connections do not count towards DoS
detection algorithms.

#### Verify echo cells

A parameter will exist to tell the measurers with what frequency they
shall verify that cells echoed back to them match what was sent. This
parameter does not need to exist outside of the FF deployment (e.g. it
doesn't need to be a consensus parameter).

The parameter instructs the measurers to check 1 out of every N cells.

The measurer keeps a count of how many measurement cells it has sent. It
also logically splits its output stream of cells into buckets of size N.
At the start of each bucket (when num_sent % N == 0), the measurer
chooses a random index in the bucket. Upon sending the cell at that
index (num_sent % N == chosen_index), the measurer records the cell.

The measurer also counts cells that it receives. When it receives a cell
at an index that was recorded, it verifies that the received cell
matches the recorded sent cell. If they match, no special action is
taken. If they don't match, the measurer indicates failure to the
coordinator and target relay and closes all connections, ending the
measurement.

##### Example

Consider bucket_size is 1000. For the moment ignore cell encryption.

We start at idx=0 and pick an idx in [0, 1000) to record, say 640. At
idx=640 we record the cell. At idx=1000 we choose a new idx in [1000,
2000) to record, say 1236. At idx=1236 we record the cell. At idx=2000
we choose a new idx in [2000, 3000). Etc.

There's 2000+ cells in flight and the measurer has recorded two items:

```
- (640, contents_of_cellA)
- (1236, contents_of_cellB)
```

Consider the receive side now. It counts the cells it receives. At
receive idx=640, it checks the received cell matches the saved cell from
before. At receive idx=1236, it again checks the received cell matches.
Etc.

##### Motivation

A malicious relay may want to skip decryption of measurement cells to
save CPU cycles and obtain a higher capacity estimate. More generally,
it could generate fake measurement cells locally, ignore the measurement
traffic it is receiving, and flood the measurer with more traffic that
it (the measurer) is even sending.

The security of echo cell verification is discussed in section 3.3.1.

## Security

In this section we discuss the security of various aspects of FlashFlow
and the tor changes it requires.

### Echo Cell Verification: Bucket Size

A smaller bucket size means more cells are checked and FF is more likely
to detect a malicious target. It also means more bookkeeping overhead
(CPU/RAM).

An adversary that knows bucket_size and cheats on one item out of every
bucket_size items will have a 1/bucket_size chance of getting caught in
the first bucket. This is the worst case adversary. While cheating on
just a single item per bucket yields very little advantage, cheating on
more items per bucket increases the likelihood the adversary gets
caught. Thus only the worst case is considered here.

In general, the odds the adversary can successfully cheat in a single
bucket are

```
(bucket_size-1)/bucket_size
```

Thus the odds the adversary can cheat in X consecutive buckets are

```
[(bucket_size-1)/bucket_size]^X
```

In our case, X will be highly varied: Slow relays won't see very many
buckets, but fast relays will. The damage to the network a very slow
relay can do by faking being only slightly faster is limited.
Nonetheless, for now we motivate the selection of bucket_size with a
slow relay:

- Assume a very slow relay of 1 Mbit/s capacity that will cheat 1 cell
  in each bucket. Assume a 30 second measurement.
- The relay will handle 1*30 = 30 Mbit of traffic during the
  measurement, or 3.75 MB, or 3.75 million bytes.
- Cells are 514 bytes. Approximately (e.g. ignoring TLS) 7300 cells
  will be sent/recv over the course of the measurement.
- A bucket_size of 50 results in about 146 buckets over the course of
  the 30s measurement.
- Therefore, the odds of the adversary cheating successfully as
  (49/50)^(146), or about 5.2%.

This sounds high, but a relay capable of double the bandwidth (2 Mbit/s)
will have (49/50)^(2*146) or 0.2% odds of success, which is quite low.

Wanting a <1% chance that a 10 Mbit/s relay can successfully cheat
results in a bucket size of approximately 125:

- 10*30 = 300 Mbit of traffic during 30s measurement. 37.5 million
  bytes.
- 37,500,000 bytes / 514 bytes/cell = ~73,000 cells
- bucket_size of 125 cells means 73,000 / 125 = 584 buckets
- (124/125)^(584) = 0.918% chance of successfully cheating

Slower relays can cheat more easily but the amount of extra weight they
can obtain is insignificant in absolute terms. Faster relays are
essentially unable to cheat.

### Weight Inflation

Target relays are an active part of the measurement process; they know
they are getting measured. While a relay cannot fake the measurement
traffic, it can trivially stop transferring client background traffic
for the duration of the measurement yet claim it carried some. More
generally, there is no verification of the claimed amount of background
traffic during the measurement. The relay can claim whatever it wants,
but it will not be trusted above the ratio the FlashFlow deployment is
configured to know. This places an easy to understand, firm, and (if set
as we suggest) low cap on how much a relay can inflate its measured
capacity.

Consider a background/measurement ratio of 1/4, or 25%. Assume the relay
in question has a hard limit on capacity (e.g. from its NIC) of 100
Mbit/s. The relay is supposed to use up to 25% of its capacity for
background traffic and the remaining 75%+ capacity for measurement
traffic. Instead the relay ceases carrying background traffic, uses all
100 Mbit/s of capacity to handle measurement traffic, and reports ~33
Mbit/s of background traffic (33/133 = ~25%). FlashFlow would trust this
and consider the relay capable of 133 Mbit/s. (If the relay were to
report more than ~33 Mbit/s, FlashFlow limits it to just ~33 Mbit/s.)
With r=25%, FlashFlow only allows 1.33x weight inflation.

Prior work shows that Torflow allows weight inflation by a factor of 89x
[0] or even 177x [1].

The ratio chosen is a trade-off between impact on background traffic and
security: r=50% allows a relay to double its weight but won't impact
client traffic for relays with steady state throughput below 50%, while
r=10% allows a very low inflation factor but will cause throttling of
client traffic at far more relays. We suggest r=25% (and thus
1/(1-0.25)=1.33x inflation) for a reasonable trade-off between
performance and security.

It may be possible to catch relays performing this attack, especially if
they literally drop all background traffic during the measurement: have
the measurer (or some party on its behalf) create a regular stream
through the relay and measure the throughput on the stream
before/during/after the measurement. This can be explored longer term.

### Incomplete Authentication

The short term FlashFlow implementation has the relay set two torrc
options if they would like to allow themselves to be measured: a flag
allowing measurement, and the list of coordinator TLS certificate that
are allowed to start a measurement.

The relay drops MSM_PARAMS cells from coordinators it does not trust,
and immediately closes the connection after that. A FF coordinator
cannot convince a relay to enter measurement mode unless the relay
trusts its TLS certificate.

A trusted coordinator specifies in the MSM_PARAMS cell the IP addresses
of the measurers the relay shall expect to connect to it shortly. The
target adds the measurer IP addresses to a whitelist in the DoS
connection limit system, exempting them from any configured connection
limit. If a measurer is behind a NAT, an adversary behind the same NAT
can DoS the relay's available sockets until the end of the measurement.
The adversary could also pretend to be the measurer. Such an adversary
could induce measurement failures and inaccuracies. (Note: the whitelist
is cleared after the measurement is over.)

# FlashFlow measurement system: Medium term

The medium term deployment stage begins after FlashFlow has been
implemented and relays are starting to update to a version of Tor that
supports it.

We plan to host a FlashFlow deployment consisting of a FF coordinator
and a single FF measurer on a single 1 Gbit/s machine. Data produced by
this deployment will be made available (semi?) publicly, including both
v3bw files and intermediate results.

Any development changes needed during this time would go through
separate proposals.

# FlashFlow measurement system: Long term

In the long term, finishing-touch development work will be done,
including adding better authentication and measurement scheduling, and
experiments will be run to determine the best way to integrate FlashFlow
into the Tor ecosystem.

Any development changes needed during this time would go through
separate proposals.

## Authentication to Target Relay

Short term deployment already had FlashFlow coordinators using TLS
certificates when connecting to relays, but in the long term, directory
authorities will vote on the consensus parameter for which coordinators
should be allowed to perform measurements. The voting is done in the
same way they currently vote on recommended tor versions.

FlashFlow measurers will be updated to use TLS certificates when
connecting to relays too. FlashFlow coordinators will update the
contents of MSM_PARAMS cells to contain measurer TLS certificates
instead of IP addresses, and relays will update to expect this change.

## Measurement Scheduling

Short term deployment only has one FF deployment running. Long term this
may no longer be the case because, for example, more than one directory
authority decides to adopt it and they each want to run their own
deployment. FF deployments will need to coordinate between themselves
to not measure the same relay at the same time, and to handle new relays
as they join during the middle of a measurement period (during the day).

The following is quoted from Section 4.3 of the FlashFlow paper.

    To measure all relays in the network, the BWAuths periodically
    determine the measurement schedule. The schedule determines when and
    by whom a relay should be measured. We assume that the BWAuths have
    sufficiently synchronized clocks to facilitate coordinating their
    schedules. A measurement schedule is created for each measurement
    period, the length p of which determines how often a relay is
    measured. We use a measurement period of p = 24 hours.

    To help avoid active denial-of-service attacks on targeted relays,
    the measurement schedule is randomized and known only to the
    BWAuths. Before the next measurement period starts, the BWAuths
    collectively generate a random seed (e.g. using Tor’s
    secure-randomness protocol). Each BWAuth can then locally determine
    the shared schedule using pseudorandom bits extracted from that
    seed. The algorithm to create the schedule considers each
    measurement period to be divided into a sequence of t-second
    measurement slots. For each old relay, slots for each BWAuth to
    measure it are selected uniformly at random without replacement
    from all slots in the period that have sufficient unallocated
    measurement capacity to accommodate the measurement. When a new
    relay appears, it is measured separately by each BWAuth in the first
    slots with sufficient unallocated capacity. Note that this design
    ensures that old relays will continue to be measured, with new
    relays given secondary priority in the order they arrive.

## Experiments

   [XXX todo]

## Other Changes/Investigations/Ideas

- How can FlashFlow data be used in a way that doesn't lead to poor load
  balancing given the following items that lead to non-uniform client
  behavior:
    - Guards that high-traffic HSs choose (for 3 months at a time)
    - Guard vs middle flag allocation issues
    - New Guard nodes (Guardfraction)
    - Exit policies other than default/all
    - Directory activity
    - Total onion service activity
    - Super long-lived circuits
- Add a cell that the target relay sends to the coordinator indicating
  its CPU and memory usage, whether it has a shortage of sockets, how
  much bandwidth load it has been experiencing lately, etc. Use this
  information to lower a relays weight, never increase.
- If FlashFlow and sbws work together (as opposed to FlashFlow replacing
  sbws), consider logic for how much sbws can increase/decrease FF
  results
- Coordination of multiple FlashFlow deployments: scheduling of
  measurements, seeding schedule with shared random value.
- Other background/measurement traffic ratios. Dynamic? (known slow
  relay => more allowed bg traffic?)
- Catching relays inflating their measured capacity by dropping
  background traffic.
- What to do about co-located relays. Can they be detected reliably?
  Should we just add a torrc option a la MyFamily for co-located relays?
- What is the explanation for dennis.jackson's scary graphs in this [2]
  ticket?  Was it because of the speed test? Why? Will FlashFlow produce
  the same behavior?

# Citations

[0] F. Thill. Hidden Service Tracking Detection and Bandwidth Cheating
    in Tor Anonymity Network. Master’s thesis, Univ. Luxembourg, 2014.
[1] A. Johnson, R. Jansen, N. Hopper, A. Segal, and P. Syverson.
    PeerFlow: Secure Load Balancing in Tor. Proceedings on Privacy
    Enhancing Technologies (PoPETs), 2017(2), April 2017.
[2] Mike Perry: Graph onionperf and consensus information from Rob's
    experiments https://trac.torproject.org/projects/tor/ticket/33076

