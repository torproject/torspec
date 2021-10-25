# Denial-of-service prevention mechanisms in Tor

This document is incomplete; it describes some mechanisms that Tor
uses to avoid different kinds of denial-of-service attacks.

## Handling low-memory conditions

(See also `tor-spec.txt`, section 8.1.)

The Tor protocol requires clients, onion services, relays, and
authorities to store various kind of information in buffers and
caches.  But an attacker can use these buffers and queues to queues
to exhaust the memory of the a targeted Tor process, and force the
operating system to kill that process.

Worse still, the ability to kill targeted Tor instances can be used
to facilitate traffic analysis. (For example, see
[the "Sniper Attack" paper](https://www.freehaven.net/anonbib/#sniper14)
by Jansen, Tschorsch, Johnson, and Scheuermann.

With this in mind, any Tor implementation—especially one that
runs as a relay or onion service—must take steps to prevent
memory-based denial-of-service attacks.

### Detecting low memory

The easiest way to notice you're out of memory would, in theory, be
getting an error when you try to allocate more.  Unfortunately, some
systems (e.g. Linux) won't actually give you an "out of memory"
error when you're low on memory.  Instead, they overcommit and
promise you memory that they can't actually provide… and then later on,
they might kill processes that actually try to use more memory than
they wish they'd given out.

So in practice, the mainline Tor implementation uses a different
strategy.  It uses a self-imposed "MaxMemInQueues" value as an
upper bound for how much memory it's willing to allocate to certain
kinds of queued usages.  This value can either be set by the user,
or derived from a fraction of the total amount of system RAM.

As of Tor 0.4.7.x, the MaxMemInQueues mechanism tracks the following
kinds of allocation:
  * Cells queued on circuits.
  * Per-connection read or write buffers.
  * On-the-fly compression or decompression state.
  * Half-open stream records.
  * Cached onion service descriptors (hsdir only).
  * Cached DNS resolves (relay only).
  * GEOIP-based usage activity statistics.

Note that directory caches aren't counted, since those are stored on
disk and accessed via mmap.

### Responding to low memory

If our allocations exceed MaxMemInQueues, then we take the following
steps to reduce our memory allocation.

*Freeing from caches*: For each of our onion service descriptor
cache, our DNS cache, and our GEOIP statistics cache, we check
whether they account for greater than 20% of our total allocation.
If they do, we free memory from the offending cache until the total
remaining is no more than 10% of our total allocation.

When freeing entries from a cache, we aim to free (approximately)
the oldest entries first.

*Freeing from buffers*: After freeing data from caches, we see
whether allocations are still above 90% of MaxMemInQueues. If they
are, we try to close circuits and connections until we are below 90%
of MaxMemInQueues.

When deciding to what circuits to free, we sort them based on the
age of the oldest data in their queues, and free the ones with the
oldest data.  (For example, a circuit on which a single cell has
been queued for 5 minutes would be freed before a circuit where 100
cells have been queued for 5 seconds.)  "Data queued on a circuit"
includes all data that we could drop if the circuit were destroyed:
not only the cells on the circuit's cell queue, but also any bytes
queued in buffers associated with streams or half-stream records
attached to the circuit.

We free non-tunneled directory connections according to a similar
rule, according to the age of their oldest queued data.

Upon freeing a circuit, a "DESTROY cell" must be sent in both
directions.

### Reporting low memory.

We define a "low threshold" equal to 3/4 of MaxMemInQueues.  Every
time our memory usage is above the low threshold, we record
ourselves as being "under memory pressure".

(This is not currently reported.)


