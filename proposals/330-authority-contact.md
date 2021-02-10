```
Filename: 330-authority-contact.md
Title: Modernizing authority contact entries
Author: Nick Mathewson
Created: 10 Feb 2021
Status: Open
```

This proposal suggests changes to interfaces used to describe a
directory authority, to better support load balancing and
denial-of-service resistance.

(In an appendix, it also suggests an improvement to the description of
authority identity keys, to avoid a deprecated cryptographic algorithm.)

# Background

There are, broadly, three good reasons to make a directory request to a Tor
directory authority:

   - As a relay, to publish a new descriptor.
   - As another authority, to perform part of the voting and consensus
     protocol.
   - As a relay, to fetch a consensus or a set of (micro)descriptors.

There are some more reasons that are OK-ish:
   - as a bandwidth authority or similar related tool running under the
     auspices of an authority.
   - as a metrics tool, to fetch directory information.
   - As a liveness checking tool, to make sure the authorities are running.

There are also a number of bad reasons to make a directory request to a
Tor directory authority.

   - As a client, to download directory information.  (_Clients should
     instead use a directory guard, or a fallback directory if
     they don't know any directory information at all._)
   - As a tor-related application, to download directory information.
     (_Such applications should instead run a tor client, which can
     maintain an up-to-date directory much more efficiently._)


Currently, Tor provides two mechanisms for downloading and uploading directory
information: the DirPort, and the BeginDir command.  A DirPort is an
HTTP port on which directory information is served.  The BeginDir
command is a relay command that is used to send an HTTP stream directly
over a Tor circuit.

Historically, we used DirPort for all directory requests.  Later, when
we needed encrypted or anonymous directory requests, we moved to a
"Begin-over-tor" approach, and then to BeginDir.  We still use the
DirPort directly, however, when relays are connecting to authorities to
publish descriptors or download fresh directories.  We also use it for
voting.

This proposal suggests that instead of having only a single DirPort,
authorities should be able to expose a separate contact point for each
supported interaction above.  By separating these contact points, we can
impose separate access controls and rate limits on each, to improve the
robustness of the consensus voting process.

Eventually, separate contact points will allow us do even more: we'll be
able to have separate implementations for the upload and download
components of the authorities, and keep the voting component mostly
offline.

# Adding contact points to authorities

Currently, for each directory authority, we ship an authority entry.
For example, the entry describing tor26 is:

    "tor26 orport=443 "
      "v3ident=14C131DFC5C6F93646BE72FA1401C02A8DF2E8B4 "
      "ipv6=[2001:858:2:2:aabb:0:563b:1526]:443 "
      "86.59.21.38:80 847B 1F85 0344 D787 6491 A548 92F9 0493 4E4E B85D",

We extend these lines with optional contact point elements as follows:

   - `upload=http://IP:port/`  A location to publish router descriptors.
   - `download=http://IP:port/`  A location to use for caches when fetching
     router descriptors.
   - `vote=http://IP:port/` A location to use for authorities when voting.

Each of these contact point elements can appear more than once.  If it does,
then it describes multiple valid contact points for a given purpose;
implementations MAY use any of the contact point elements that they recognize
for a given authority.

Implementations SHOULD ignore url schemas that they do not recognize, and
SHOULD ignore hostnames addresses that appear in the place of the IP elements
above. (This will make it easier for us to extend these lists in the future.)

If there is no contact point element for a given type, then implementations
should fall back to using the main IPv4 addr:port, and/or the IPv6 addr:port
if available.

As an extra rule: If more than one authority lists the same upload
point, then uploading a descriptor to that upload point counts as having
uploaded it to all of those authorities.  (This rule will allow multiple
authorities to share an upload point in the future, if they decide to do
so.  We do not need a corresponding rules for voting or downloading,
since every authority participates in voting directly, and since there
is no notion of "downloading from each authority.")

# Authority-side configuration

We add a few flags to DirPort configuration, indicating what kind of requests
are acceptable.

   - `no-voting`
   - `no-download`
   - `no-upload`

These flags remove a given set of possible operations from a given
DirPort.  So for example, an authority might say:
    
     DirPort 9030 no-download no-upload
     DirPort 9040 no-voting no-upload
     DirPort 9050 no-voting no-download

We can also allow "upload-only" as an alias for "no-voting no-download", and so on.

Note that authorities would need to keep a legacy dirport around until
all relays have upgraded.

# Bridge authorities

This proposal does not yet apply to bridge authorities, since neither
clients nor bridges connect to bridge authorities over HTTP.  A later
proposal may add a schema that can be used to describe contacting to a
bridge authority via BEGINDIR.

# Example uses

## Example setup: Simple access control and balancing.

Right now the essential functionality of authorities is sometimes
blocked by getting too much load from directory downloads by
non-relays.  To address this we can proceed as follows.  We can have
each relay authority open four separate dirports: One for publishing,
one for voting, one for downloading, and one legacy port.
These can be rate-limited separately, and requests sent to the wrong port
can be rejected.  We could additionally prioritize voting, then uploads,
then downloads.  This could be done either within Tor, or with other IP
shaping tools.

## Example setup: Full authority refactoring

In the future, this system lets us get fancier with our authorities and
how they are factored.  For example, as in proposal 257, an authority could
run upload services, voting, and download services all at
separate locations.

The authorities themselves would be the only ones that needed to use
their voting protocol.  The upload services (run on the behalf of
authorities or groups of authorities) could receive descriptors and do
initial testing on them before passing them on to the authorities.  The
authorities could then vote with one another, and push the resulting
consensus and descriptors to the download services.  This would make the
download services primarily responsible for serving directory
information, and have them take all the load.


# Appendix: Cryptographic extensions to authority configuration

The 'v3ident' element, and the relay identity fingerprint in authority
configuration, are currently both given as SHA1 digests of RSA keys.  SHA1 is
currently deprecated: even though we're only relying on second-preimage
resistance, we should migrate away.

With that in mind, we're adding two more fields to the authority entries:

   - `ed25519-id=BASE64` The ed25519 identity of a the authority when it
      acts as a relay.
   - `v3ident-sha3-256=HEX` The SHA3-256 digest of the authority's v3 signing
      key.

(We use base64 here for the ed25519 key since that's what we use
elsewhere.)

