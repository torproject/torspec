```
Filename: 323-walking-onions-full.md
Title: Specification for Walking Onions
Author: Nick Mathewson
Created: 3 June 2020
Status: Open
```


<!-- Section 1 --> <a id='S1'></a>

# Introduction: A Specification for Walking Onions

In Proposal 300, I introduced Walking Onions, a design for scaling
Tor and simplifying clients, by removing the requirement that every
client know about every relay on the network.

This proposal will elaborate on the original Walking Onions idea,
and should provide enough detail to allow multiple compatible
implementations. In this introduction, I'll start by summarizing the
key ideas of Walking Onions, and then outline how the rest of this
proposal will be structured.

<!-- Section 1.1 --> <a id='S1.1'></a>

## Remind me about Walking Onions again?

With Tor's current design, every client downloads and refreshes a
set of directory documents that describe the directory authorities'
views about every single relay on the Tor network.  This requirement
makes directory bandwidth usage grow quadratically, since the
directory size grows linearly with the number of relays, and it is
downloaded a number of times that grows linearly with the number of
clients.  Additionally, low-bandwidth clients and bootstrapping
clients spend a disproportionate amount of their bandwidth loading
directory information.

With these drawbacks, why does Tor still require clients to
download a directory?  It does so in order to prevent attacks that
would be possible if clients let somebody else choose their
paths through the network, or if each client chose its paths from a
different subset of relays.

Walking Onions is a design that resists these attacks without
requiring clients ever to have a complete view of the network.

You can think of the Walking Onions design like this: Imagine that with
the current Tor design, the client covers a wall with little pieces
of paper, each representing a relay, and then throws a dart at the wall
to pick a relay.  Low-bandwidth relays get small pieces of paper;
high-bandwidth relays get large pieces of paper.  With the Walking
Onions design, however, the client throws its dart at a _blank
wall_, notes the position of the dart, and asks for the relay whose
paper _would be_ at that position on a "standard wall".  These
"standard walls" are mapped out by directory authorities in advance,
and are authenticated in such a way that the client can receive a
proof of a relay's position on the wall without actually having to
know the whole wall.

Because the client itself picks the position on the wall, and
because the authorities must vote together to build a set of
"standard walls", nobody else controls the client's path through the
network, and all clients can choose their paths in the same way.
But since clients only probe one position on the wall at a time,
they don't need to download a complete directory.

(Note that there has to be more than one wall at a time: the client
throws darts at one wall to pick guards, another wall to pick
middle relays, and so on.)

In Walking Onions, we call a collection of standard walls an
"ENDIVE" (Efficient Network Directory with Individually Verifiable
Entries).  We call each of the individual walls a "routing index",
and we call each of the little pieces of paper describing a relay and
its position within the routing index a "SNIP" (Separable Network
Index Proof).

For more details about the key ideas behind Walking Onions, see
proposal 300.  For more detailed analysis and discussion, see
"Walking Onions: Scaling Anonymity Networks while Protecting Users"
by Komlo, Mathewson, and Goldberg.

<!-- Section 1.2 --> <a id='S1.2'></a>

## The rest of this document

This proposal is unusually long, since Walking Onions touches on many
aspects of Tor's functionality.  It requires changes to voting,
directory formats, directory operations, circuit building, path
selection, client operations, and more.  These changes are described in the
sections listed below.

Here in section 1, we briefly reintroduce Walking Onions, and talk
about the rest of this proposal.

Section 2 will describe the formats for ENDIVEs, SNIPs, and related
documents.

Section 3 will describe new behavior for directory authorities as
they vote on and produce ENDIVEs.

Section 4 describes how relays fetch and reconstruct ENDIVEs from
the directory authorities.

Section 5 has the necessary changes to Tor's circuit extension
protocol so that clients can extend to relays by index position.

Section 6 describes new behaviors for clients as they use Walking
Onions, to retain existing Tor functionality for circuit construction.

Section 7 explains how to implement onion services using Walking
Onions.

Section 8 describes small alterations in client and relay behavior
to strengthen clients against some kinds of attacks based on relays
picking among multiple ENDIVEs, while still making the voting
system robust against transient authority failures.

Section 9 closes with a discussion of how to migrate from the
existing Tor design to the new system proposed here.

<!-- Section 1.2.1 --> <a id='S1.2.1'></a>

### Appendices

Additionally, this proposal has several appendices:

Appendix A defines commonly used terms.

Appendix B provides definitions for CDDL grammar productions that
are used elsewhere in the documents.

Appendix C lists the new elements in the protocol that will require
assigned values.

Appendix D lists new network parameters that authorities must vote
on.

Appendix E gives a sorting algorithm for a subset of the CBOR object
representation.

Appendix F gives an example set of possible "voting rules" that
authorities could use to produce an ENDIVE.

Appendix G lists the different routing indices that will be required
in a Walking Onions deployment.

Appendix H discusses partitioning TCP ports into a small number of
subsets, so that relays' exit policies can be represented only as
the group of ports that they support.

Appendix Z closes with acknowledgments.

<!-- Section 1.2.2 --> <a id='S1.2.2'></a>

### Related proposals

The following proposals are not part of the Walking Onions proposal,
but they were written at the same time, and are either helpful or
necessary for its implementation.

318-limit-protovers.md restricts the allowed version numbers for
each subprotocol to the range 0..63.

319-wide-everything.md gives a general mechanism for splitting relay
commands across more than one cell.

320-tap-out-again.md attempts to remove the need for TAP keys in
the HSv2 protocol.

321-happy-families.md lets families be represented with a single
identifier, rather than a long list of keys

322-dirport-linkspec.md allows a directory port to be represented
with a link specifier.

<!-- Section 2 --> <a id='S2'></a>

# Document Formats: ENDIVEs and SNIPs

Here we specify a pair of related document formats that we will
use for specifying SNIPs and ENDIVEs.

Recall from proposal 300 that a SNIP is a set of information about
a single relay, plus proof from the directory authorities that the
given relay occupies a given range in a certain routing index.
For example, we can imagine that a SNIP might say:

* Relay X has the following IP, port, and onion key.
* In the routing index Y, it occupies index positions 0x20002
  through 0x23000.
* This SNIP is valid on 2020-12-09 00:00:00, for one hour.
* Here is a signature of all the above text, using a threshold
  signature algorithm.

You can think of a SNIP as a signed combination of a routerstatus and
a microdescriptor... together with a little bit of the randomized
routing table from Tor's current path selection code, all wrapped
in a signature.

Every relay keeps a set of SNIPs, and serves them to clients when
the client is extending by a routing index position.

An ENDIVE is a complete set of SNIPs.  Relays download ENDIVEs, or
diffs between ENDIVEs, once every voting period.  We'll accept some
complexity in order to make these diffs small, even though some of the
information in them (particularly SNIP signatures and index
ranges) will tend to change with every period.

<!-- Section 2.1 --> <a id='S2.1'></a>

## Preliminaries and scope

<!-- Section 2.1.1 --> <a id='S2.1.1'></a>

### Goals for our formats

We want SNIPs to be small, since they need to be sent on the wire
one at a time, and won't get much benefit from compression.  (To
avoid a side-channel, we want CREATED cells to all be the same
size, which means we need to pad up to the largest size possible
for a SNIP.)

We want to place as few requirements on clients as possible, and we
want to preserve forward compatibility.

We want ENDIVEs to be compressible, and small. We want successive
ENDIVEs to be textually similar, so that we can use diffs to
transmit only the parts that change.

We should preserve our policy of requiring only loose time
synchronization between clients and relays, and allow even looser
synchronization when possible.  Where possible, we'll make the
permitted skew explicit in the protocol: for example, rather than
saying "you can accept a document 10 minutes before it is valid", we
will just make the validity interval start 10 minutes earlier.

<!-- Section 2.1.2 --> <a id='S2.1.2'></a>

### Notes on Metaformat

In the format descriptions below, we will describe a set of
documents in the CBOR metaformat, as specified in RFC 7049.  If
you're not familiar with CBOR, you can think of it as a simple
binary version of JSON, optimized first for simplicity of
implementation and second for space.

I've chosen CBOR because it's schema-free (you can parse it
without knowing what it is), terse, dumpable as text, extensible,
standardized, and very easy to parse and encode.

We will choose to represent many size-critical types as maps whose
keys are short integers: this is slightly shorter in its encoding
than string-based dictionaries.  In some cases, we make types even
shorter by using arrays rather than maps, but only when we are
confident we will not have to make changes to the number of elements
in the future.

We'll use CDDL (defined in RFC 8610) to describe the data in a way
that can be validated -- and hopefully, in a way that will make it
comprehensible. (The state of CDDL tooling is a bit lacking at the
moment, so my CDDL validation will likely be imperfect.)

We make the following restrictions to CBOR documents that Tor
implementations will _generate_:

   * No floating-point values are permitted.

   * No tags are allowed unless otherwise specified.

   * All items must follow the rules of RFC 7049 section 3.9 for
     canonical encoding, unless otherwise specified.

Implementations SHOULD accept and parse documents that are not
generated according to these rules, for future extensibility.
However, implementations SHOULD reject documents that are not
"well-formed" and "valid" by the definitions of RFC 7049.

<!-- Section 2.1.3 --> <a id='S2.1.3'></a>

### Design overview: signing documents

We try to use a single document-signing approach here, using a hash
function parameterized to accommodate lifespan information and an
optional nonce.

All the signed CBOR data used in this format is represented as a
binary string, so that CBOR-processing tools are less likely to
re-encode or transform it.   We denote this below with the CDDL syntax
`bstr .cbor Object`, which means "a binary string that must hold a valid
encoding of a CBOR object whose type is `Object`".

<!-- Section 2.1.4 --> <a id='S2.1.4'></a>

### Design overview: SNIP Authentication

I'm going to specify a flexible authentication format for SNIPs that
can handle threshold signatures, multisignatures, and Merkle trees.
This will give us flexibility in our choice of authentication
mechanism over time.

  * If we use Merkle trees, we can make ENDIVE diffs much much smaller,
    and save a bunch of authority CPU -- at the expense of requiring
    slightly larger SNIPs.

  * If Merkle tree root signatures are in SNIPs, SNIPs get a
    bit larger, but they can be used by clients that do not have the
    latest signed Merkle tree root.

  * If we use threshold signatures, we need to depend on
    not-yet-quite-standardized algorithms.  If we use multisignatures,
    then either SNIPs get bigger, or we need to put the signed Merkle
    tree roots into a consensus document.

Of course, flexibility in signature formats is risky, since the more
code paths there are, the more opportunities there are for nasty bugs.
With this in mind, I'm structuring our authentication so that there
should (to the extent possible) be only a single validation path for
different uses.

With this in mind, our format is structured so that "not using a
Merkle tree" is considered, from the client's point of view, the same as
"using a Merkle of depth 1".

The authentication on a single snip is structured, in the abstract, as:
   - ITEM: The item to be authenticated.
   - PATH: A string of N bits, representing a path through a Merkle tree from
     its root, where 0 indicates a left branch and 1 indicates a right
     branch.  (Note that in a left-leaning tree, the 0th leaf will have
     path 000..0, the 1st leaf will have path 000..1, and so on.)
   - BRANCH: A list of N digests, representing the digests for the
     branches in the Merkle tree that we are _not_ taking.
   - SIG: A generalized signature (either a threshold signature or a
     multisignature) of a top-level digest.
   - NONCE: an optional nonce for use with the hash functions.

Note that PATH here is a bitstring, not an integer! "0001" and "01" are
different paths, and "" is a valid path, indicating the root of the tree.

We assume two hash functions here: `H_leaf()` to be used with leaf
items, and `H_node()` to be used with intermediate nodes.  These functions
are parameterized with a path through the tree, with
the lifespan of the object to be signed, and with a nonce.

To validate the authentication on a SNIP, the client proceeds as follows:

    Algorithm: Validating SNIP authentication

    Let N = the length of PATH, in bits.

    Let H = H_leaf(PATH, LIFESPAN, NONCE, ITEM).

    While N > 0:
       Remove the last bit of PATH; call it P.
       Remove the last digest of BRANCH; call it B.

       If P is zero:
           Let H = H_node(PATH, LIFESPAN, NONCE, H, B)
       else:
           Let H = H_node(PATH, LIFESPAN, NONCE, B, H)

       Let N = N - 1

    Check wither SIG is a correct (multi)signature over H with the
    correct key(s).

Parameterization on this structure is up to the authorities.  If N is
zero, then we are not using a Merkle tree.  The generalize signature
SIG can either be given as part of the SNIP, or as part of a consensus
document.  I expect that in practice, we will converge on a single set of
parameters here quickly (I'm favoring BLS signatures and a Merkle
tree), but using this format will give clients the flexibility to handle
other variations in the future.

For our definition of `H_leaf()` and `H_node()`, see "Digests and
parameters" below.

<!-- Section 2.1.5 --> <a id='S2.1.5'></a>

### Design overview: timestamps and validity.

For future-proofing, SNIPs and ENDIVEs have separate time ranges
indicating when they are valid.  Unlike with current designs, these
validity ranges should take clock skew into account, and should not
require clients or relays to deliberately add extra tolerance to their
processing.  (For example, instead of saying that a document is "fresh"
for three hours and then telling clients to accept documents for 24
hours before they are valid and 24 hours after they are expired, we will
simply make the documents valid for 51 hours.)

We give each lifespan as a (PUBLISHED, PRE, POST) triple, such that
objects are valid from (PUBLISHED - PRE) through (PUBLISHED + POST).
(The "PUBLISHED" time is provided so that we can more reliably tell
which of two objects is more recent.)

Later (see section 08), we'll explain measures to ensure that
hostile relays do not take advantage of multiple overlapping SNIP
lifetimes to attack clients.

<!-- Section 2.1.6 --> <a id='S2.1.6'></a>

### Design overview: how the formats work together

Authorities, as part of their current voting process, will produce an
ENDIVE.

Relays will download this ENDIVE (either directly or as a diff),
validate it, and extract SNIPs from it.  Extracting these SNIPs may be
trivial (if they are signed individually), or more complex (if they are
signed via a Merkle tree, and the Merkle tree needs to be
reconstructed).  This complexity is acceptable only to the extent that
it reduces compressed diff size.

Once the SNIPs are reconstructed, relays will hold them and serve them
to clients.

<!-- Section 2.1.7 --> <a id='S2.1.7'></a>

### What isn't in this section

This section doesn't tell you what the different routing indices
are or mean.  For now, we can imagine there being one routing index for
guards, one for middles, and one for exits, and one for each hidden
service directory ring. (See section 06 for more on regular indices,
and section 07 for more on onion services.)

This section doesn't give an algorithm for computing ENDIVEs from
votes, and doesn't give an algorithm for extracting SNIPs from an ENDIVE.
Those come later. (See sections 03 and 04 respectively.)

<!-- Section 2.2 --> <a id='S2.2'></a>

## SNIPs

Each SNIP has three pieces: the part of the SNIP that describes the
router, the part of that describes the SNIP's place within an ENDIVE, and
the part that authenticates the whole SNIP.

Why two _separate_ authenticated pieces?  Because one (the router
description) is taken verbatim from the ENDIVE, and the other
(the location within the ENDIVE) is computed from the ENDIVE by the
relays. Separating them like this helps ensure that the part
generated by the relay and the part generated by the authorities
can't interfere with each other.

    ; A SNIP, as it is sent from the relay to the client.  Note that
    ; this is represented as a three-element array.
    SNIP = [
        ; First comes the signature.  This is computed over
        ; the concatenation of the two bstr objects below.
        auth: SNIPSignature,

        ; Next comes the location of the SNIP within the ENDIVE.
        index: bstr .cbor SNIPLocation,

        ; Finally comes the information about the router.
        router: bstr .cbor SNIPRouterData,
    ]

(Computing the signature over a concatenation of objects is safe, since
the objects' content is self-describing CBOR, and isn't vulnerable to
framing issues.)

<!-- Section 2.2.1 --> <a id='S2.2.1'></a>

### SNIPRouterData: information about a single router.

Here we talk about the type that tells a client about a single
router.  For cases where we are just storing information about a
router (for example, when using it as a guard), we can remember
this part, and discard the other pieces.

The only required parts here are those that identify the router
and tell the client how to build a circuit through it.  The others
are all optional.  In practice, I expect they will be encoded in most
cases, but clients MUST behave properly if they are absent.

More than one SNIPRouterData may exist in the same ENDIVE for a
single router.  For example, there might be a longer version to
represent a router to be used as a guard, and another to represent
the same router when used as a hidden service directory.  (This is
not possible in the voting mechanism that I'm working on, but relays
and clients MUST NOT treat this as an error.)

This representation is based on the routerstats and
microdescriptor entries of today, but tries to omit a number of
obsolete fields, including RSA identity fingerprint, TAP key,
published time, etc.

    ; A SNIPRouterData is a map from integer keys to values for
    ; those keys.
    SNIPRouterData = {
        ; identity key.
        ? 0 => Ed25519PublicKey,

        ; ntor onion key.
        ? 1 => Curve25519PublicKey,

        ; list of link specifiers other than the identity key.
        ; If a client wants to extend to the same router later on,
        ; they SHOULD include all of these link specifiers verbatim,
        ; whether they recognize them or not.
        ? 2 => [ LinkSpecifier ],

        ; The software that this relay says it is running.
        ? 3 => SoftwareDescription,

        ; protovers.
        ? 4 => ProtoVersions,

        ; Family.  See below for notes on dual encoding.
        ? 5 => [ * FamilyId ],

        ; Country Code
        ? 6 => Country,

        ; Exit policies describing supported port _classes_.  Absent exit
        ; policies are treated as "deny all".
        ? 7 => ExitPolicy,

        ; NOTE: Properly speaking, there should be a CDDL 'cut'
        ; here, to indicate that the rules below should only match
        ; if one if the previous rules hasn't matched.
        ; Unfortunately, my CDDL tool doesn't seem to support cuts.

        ; For future tor extensions.
        * int => any,

        ; For unofficial and experimental extensions.
        * tstr => any,
    }

    ; For future-proofing, we are allowing multiple ways to encode
    ; families.  One is as a list of other relays that are in your
    ; family.  One is as a list of authority-generated family
    ; identifiers. And one is as a master key for a family (as in
    ; Tor proposal 242).
    ;
    ; A client should consider two routers to be in the same
    ; family if they have at least one FamilyId in common.
    ; Authorities will canonicalize these lists.
    FamilyId = bstr

    ; A country.  These should ordinarily be 2-character strings,
    ; but I don't want to enforce that.
    Country = tstr;

    ; SoftwareDescription replaces our old "version".
    SoftwareDescription = [
      software: tstr,
      version: tstr,
      extra: tstr
    ]

    ; Protocol versions: after a bit of experimentation, I think
    ; the most reasonable representation to use is a map from protocol
    ; ID to a bitmask of the supported versions.
    ProtoVersions = { ProtoId => ProtoBitmask }

    ; Integer protocols are reserved for future version of Tor. tstr ids
    ; are reserved for experimental and non-tor extensions.
    ProtoId = ProtoIdEnum / int / tstr

    ProtoIdEnum = &(
      Link     : 0,
      LinkAuth : 1,
      Relay    : 2,
      DirCache : 3,
      HSDir    : 4,
      HSIntro  : 5,
      HSRend   : 6,
      Desc     : 7,
      MicroDesc: 8,
      Cons     : 9,
      Padding  : 10,
      FlowCtrl : 11,
    )
    ; This type is limited to 64 bits, and that's fine.  If we ever
    ; need a protocol version higher than 63, we should allocate a
    ; new protoid.
    ProtoBitmask = uint

    ; An exit policy may exist in up to two variants.  When port classes
    ; have not changed in a while, only one policy is needed.  If port
    ; classes have changed recently, however, then SNIPs need to include
    ; each relay's position according to both the older and the newer policy
    ; until older network parameter documents become invalid.
    ExitPolicy = SinglePolicy / [ SinglePolicy, SinglePolicy ]

    ; Each single exit policy is a tagged bit array, whose bits
    ; correspond to the members of the list of port classes in the
    ; network parameter document with a corresponding tag.
    SinglePolicy = [
         ; Identifies which group of port classes we're talking about
         tag: unsigned,
         ; Bit-array of which port classes this relay supports.
         policy: bstr
    ]

<!-- Section 2.2.2 --> <a id='S2.2.2'></a>

### SNIPLocation: Locating a SNIP within a routing index.

The SNIPLocation type can encode where a SNIP is located with
respect to one or more routing indices.  Note that a SNIPLocation
does not need to be exhaustive: If a given IndexId is not listed for
a given relay in one SNIP, it might exist in another SNIP. Clients
should not infer that the absence of an IndexId in one SNIPLocation
for a relay means that no SNIPLocation with that IndexId exists for
the relay.

    ; SNIPLocation: we're using a map here because it's natural
    ; to look up indices in maps.
    SNIPLocation = {
        ; The keys of this mapping represent the routing indices in
        ; which a SNIP appears.  The values represent the index ranges
        ; that it occupies in those indices.
        * IndexId => IndexRange / ExtensionIndex,
    }

    ; We'll define the different index ranges as we go on with
    ; these specifications.
    ;
    ; IndexId values over 65535 are reserved for extensions and
    ; experimentation.
    IndexId = uint32

    ; An index range extends from a minimum to a maximum value.
    ; These ranges are _inclusive_ on both sides.  If 'hi' is less
    ; than 'lo', then this index "wraps around" the end of the ring.
    ; A "nil" value indicates an empty range, which would not
    ; ordinarily be included.
    IndexRange = [ lo: IndexPos,
                   hi: IndexPos ] / nil

    ; An ExtensionIndex is reserved for future use; current clients
    ; will not understand it and current ENDIVEs will not contain it.
    ExtensionIndex = any

    ; For most routing indices, the ranges are encoded as 4-byte integers.
    ; But for hsdir rings, they are binary strings.  (Clients and
    ; relays SHOULD NOT require this.)
    IndexPos = uint / bstr

A bit more on IndexRanges: Every IndexRange actually describes a set of
_prefixes_ for possible index positions.  For example, the IndexRange
`[ h'AB12', h'AB24' ]` includes all the binary strings that start with (hex)
`AB12`, `AB13`, and so on, up through all strings that start with `AB24`.
Alternatively, you can think of a `bstr`-based IndexRange *(lo, hi)* as
covering *lo*`00000...` through *hi*`ff...`.

IndexRanges based on the uint type work the same, except that they always
specify the first 32 bits of a prefix.

<!-- Section 2.2.3 --> <a id='S2.2.3'></a>

### SNIPSignature: How to prove a SNIP is in the ENDIVE.

Here we describe the types for implementing SNIP signatures, to be
validated as described in "Design overview: Authentication" above.

    ; Most elements in a SNIPSignature are positional and fixed
    SNIPSignature = [
        ; The actual signature or signatures.  If this is a single signature,
        ; it's probably a threshold signature.  Otherwise, it's probably
        ; a list containing one signature from each directory authority.
        SingleSig / MultiSig,

        ; algorithm to use for the path through the merkle tree.
        d_alg: DigestAlgorithm,
        ; Path through merkle tree, possibly empty.
        merkle_path: MerklePath,

        ; Lifespan information.  This is included as part of the input
        ; to the hash algorithm for the signature.
        LifespanInfo,

        ; optional nonce for hash algorithm.
        ? nonce: bstr,

        ; extensions for later use. These are not signed.
        ? extensions: { * any => any },
    ]

    ; We use this group to indicate when an object originated, and when
    ; it should be accepted.
    ;
    ; When we are using it as an input to a hash algorithm for computing
    ; signatures, we encode it as an 8-byte number for "published",
    ; followed by two 4-byte numbers for pre-valid and post-valid.
    LifespanInfo = (
        ; Official publication time in seconds since the epoch.  These
        ; MUST be monotonically increasing over time for a given set of
        ; authorities on all SNIPs or ENDIVEs that they generate: a
        ; document with a greater `published` time is always more recent
        ; than one with an earlier `published` time.
        ;
        ; Seeing a publication time "in the future" on a correctly
        ; authenticated document is a reliable sign that your
        ; clock is set too far in the past.
        published: uint,

        ; Value to subtract from "published" in order to find the first second
        ; at which this object should be accepted.
        pre-valid: uint32,

        ; Value to add to "published" in order to find the last
        ; second at which this object should be accepted.  The
        ; lifetime of an object is therefore equal to "(post-valid +
        ; pre-valid)".
        post-valid: uint32,
    )

    ; A Lifespan is just the fields of LifespanInfo, encoded as a list.
    Lifespan = [ LifespanInfo ]

    ; One signature on a SNIP or ENDIVE.  If the signature is a threshold
    ; signature, or a reference to a signature in another
    ; document, there will probably be just one of these per SNIP.  But if
    ; we're sticking a full multisignature in the document, this
    ; is just one of the signatures on it.
    SingleSig = [
       s_alg: SigningAlgorithm,
       ; One of signature and sig_reference must be present.
       ?signature: bstr,
       ; sig_reference is an identifier for a signature that appears
       ; elsewhere, and can be fetched on request.  It should only be
       ; used with signature types too large to attach to SNIPs on their
       ; own.
       ?sig_reference: bstr,
       ; A prefix of the key or the key's digest, depending on the
       ; algorithm.
       ?keyid: bstr,
    ]

    MultiSig = [ + SingleSig ]

    ; A Merkle path is represented as a sequence of bits to
    ; indicate whether we're going left or right, and a list of
    ; hashes for the parts of the tree that we aren't including.
    ;
    ; (It's safe to use a uint for the number of bits, since it will
    ; never overflow 64 bits -- that would mean a Merkle tree with
    ; too many leaves to actually calculate on.)
    MerklePath = [ uint, *bstr ]

<!-- Section 2.3 --> <a id='S2.3'></a>

## ENDIVEs: sending a bunch of SNIPs efficiently.

ENDIVEs are delivered by the authorities in a compressed format, optimized
for diffs.

Note that if we are using Merkle trees for SNIP authentication, ENDIVEs do
not include the trees at all, since those can be inferred from the leaves of
the tree.  Similarly, the ENDIVEs do not include raw routing indices, but
instead include a set of bandwidths that can be combined into the routing
indices -- these bandwidths change less frequently, and therefore are more
diff-friendly.

Note also that this format has more "wasted bytes" than SNIPs
do. Unlike SNIPs, ENDIVEs are large enough to benefit from
compression with with gzip, lzma2, or so on.

This section does not fully specify how to construct SNIPs from an ENDIVE;
for the full algorithm, see section 04.

    ; ENDIVEs are also sent as CBOR.
    ENDIVE = [
        ; Signature for the ENDIVE, using a simpler format than for 
        ; a SNIP.  Since ENDIVEs are more like a consensus, we don't need
        ; to use threshold signatures or Merkle paths here.
        sig: ENDIVESignature,

        ; Contents, as a binary string.
        body: encoded-cbor .cbor ENDIVEContent,
    ]

    ; The set of signatures across an ENDIVE.
    ;
    ; This type doubles as the "detached signature" document used when
    ; collecting signatures for a consensus.
    ENDIVESignature = {
        ; The actual signatures on the endive. A multisignature is the
        ; likeliest format here.
        endive_sig: [ + SingleSig ],

        ; Lifespan information.  As with SNIPs, this is included as part
        ; of the input to the hash algorithm for the signature.
        ; Note that the lifespan of an ENDIVE is likely to be a subset
        ; of the lifespan of its SNIPs.
        endive_lifespan: Lifespan,

        ; Signatures across SNIPs, at some level of the Merkle tree.  Note
        ; that these signatures are not themselves signed -- having them
        ; signed would take another step in the voting algorithm.
        snip_sigs: DetachedSNIPSignatures,

        ; Signatures across the ParamDoc pieces.  Note that as with the
        ; DetachedSNIPSignatures, these signatures are not themselves signed.
        param_doc: ParamDocSignature,

        ; extensions for later use. These are not signed.
        * tstr => any,
    }

    ; A list of single signatures or a list of multisignatures. This
    ; list must have 2^signature-depth elements.
    DetachedSNIPSignatures =
          [ *SingleSig ] / [ *MultiSig ]

    ENDIVEContent = {

        ; Describes how to interpret the signatures over the SNIPs in this
        ; ENDIVE. See section 04 for the full algorithm.
        sig_params: {
            ; When should we say that the signatures are valid?
            lifespan: Lifespan,
            ; Nonce to be used with the signing algorithm for the signatures.
            ? signature-nonce: bstr,

            ; At what depth of a Merkle tree do the signatures apply?
            ; (If this value is 0, then only the root of the tree is signed.
            ; If this value is >= ceil(log2(n_leaves)), then every leaf is
            ; signed.).
            signature-depth: uint,

            ; What digest algorithm is used for calculating the signatures?
            signature-digest-alg: DigestAlgorithm,

            ; reserved for future extensions.
            * tstr => any,
        },

        ; Documents for clients/relays to learn about current network
        ; parameters.
        client-param-doc: encoded-cbor .cbor ClientParamDoc,
        relay-param-doc: encoded-cbor .cbor RelayParamDoc,

        ; Definitions for index group.  Each "index group" is all
        ; applied to the same SNIPs.  (If there is one index group,
        ; then every relay is in at most one SNIP, and likely has several
        ; indices.  If there are multiple index groups, then relays
        ; can appear in more than one SNIP.)
        indexgroups: [ *IndexGroup ],

        ; Information on particular relays.
        ;
        ; (The total number of SNIPs identified by an ENDIVE is at most
        ; len(indexgroups) * len(relays).)
        relays: [ * ENDIVERouterData ],

        ; for future exensions
        * tstr => any,
    }

    ; An "index group" lists a bunch of routing indices that apply to the same
    ; SNIPs.  There may be multiple index groups when a relay needs to appear
    ; in different SNIPs with routing indices for some reason.
    IndexGroup = {
        ; A list of all the indices that are built for this index group.
        ; An IndexId may appear in at most one group per ENDIVE.
        indices: [ + IndexId ],
        ; A list of keys to delete from SNIPs to build this index group.
        omit_from_snips: [ *(int/tstr) ],
        ; A list of keys to forward from SNIPs to the next relay in an EXTEND
        ; cell.  This can help the next relay know which keys to use in its
        ; handshake.
        forward_with_extend: [ *(int/tstr) ],

        ; A number of "gaps" to place in the Merkle tree after the SNIPs
        ; in this group.  This can be used together with signature-depth
        ; to give different index-groups independent signatures.
        ? n_padding_entries: uint,

        ; A detailed description of how to build the index.
        + IndexId => IndexSpec,

        ; For experimental and extension use.
        * tstr => any,
    }

    ; Enumeration to identify how to generate an index.
    Indextype_Raw = 0
    Indextype_Weighted = 1
    Indextype_RSAId = 2
    Indextype_Ed25519Id = 3
    Indextype_RawNumeric = 4

    ; An indexspec may be given as a raw set of index ranges.  This is a
    ; fallback for cases where we simply can't construct an index any other
    ; way.
    IndexSpec_Raw = {
        type: Indextype_Raw,
        ; This index is constructed by taking relays by their position in the
        ; list from the list of ENDIVERouterData, and placing them at a given
        ; location in the routing index.  Each index range extends up to
        ; right before the next index position.
        index_ranges: [ * [ uint, IndexPos ] ],
    }

    ; An indexspec given as a list of numeric spans on the index.
    IndexSpec_RawNumeric = {
        type: Indextype_RawNumeric,
        first_index_pos: uint,
        ; This index is constructed by taking relays by index from the list
        ; of ENDIVERouterData, and giving them a certain amount of "weight"
        ; in the index.
        index_ranges: [ * [ idx: uint, span: uint ] ],
    }

    ; This index is computed from the weighted bandwidths of all the SNIPs.
    ;
    ; Note that when a single bandwidth changes, it can change _all_ of
    ; the indices in a bandwidth-weighted index, even if no other
    ; bandwidth changes.  That's why we only pack the bandwidths
    ; here, and scale them as part of the reconstruction algorithm.
    IndexSpec_Weighted = {
        type: Indextype_Weighted,
        ; This index is constructed by assigning a weight to each relay,
        ; and then normalizing those weights. See algorithm below in section
        ; 04.
        ; Limiting bandwidth weights to uint32 makes reconstruction algorithms
        ; much easier.
        index_weights: [ * uint32 ],
    }

    ; This index is computed from the RSA identity key digests of all of the
    ; SNIPs. It is used in the HSv2 directory ring.
    IndexSpec_RSAId = {
        type: Indextype_RSAId,
        ; How many bytes of RSA identity data go into each indexpos entry?
        n_bytes: uint,
        ; Bitmap of which routers should be included.
        members: bstr,
    }

    ; This index is computed from the Ed25519 identity keys of all of the
    ; SNIPs.  It is used in the HSv3 directory ring.
    IndexSpec_Ed25519Id = {
        type: Indextype_Ed25519Id,
        ; How many bytes of digest go into each indexpos entry?
        n_bytes: uint,
        ; What digest do we use for building this ring?
        d_alg: DigestAlgorithm,
        ; What bytes do we give to the hash before the ed25519?
        prefix: bstr,
        ; What bytes do we give to the hash after the ed25519?
        suffix: bstr,
        ; Bitmap of which routers should be included.
        members: bstr,
    }

    IndexSpec = IndexSpec_Raw /
                IndexSpec_RawNumeric /
                IndexSpec_Weighted /
                IndexSpec_RSAId /
                IndexSpec_Ed25519Id

    ; Information about a single router in an ENDIVE.
    ENDIVERouterData = {
        ; The authority-generated SNIPRouterData for this router.
        1 => encoded-cbor .cbor SNIPRouterData,
        ; The RSA identity, or a prefix of it, to use for HSv2 indices.
        ? 2 => RSAIdentityFingerprint,

        * int => any,
        * tstr => any,
    }

    ; encoded-cbor is defined in the CDDL postlude as a bstr that is
    ; tagged as holding verbatim CBOR:
    ;
    ;    encoded-cbor = #6.24(bstr)
    ;
    ; Using a tag like this helps tools that validate the string as
    ; valid CBOR; using a bstr helps indicate that the signed data
    ; should not be interpreted until after the signature is checked.
    ; It also helps diff tools know that they should look inside these
    ; objects.

<!-- Section 2.4 --> <a id='S2.4'></a>

## Network parameter documents

Network parameter documents ("ParamDocs" for short) take the place of the
current consensus and certificates as a small document that clients and
relays need to download periodically and keep up-to-date.  They are generated
as part of the voting process, and contain fields like network parameters,
recommended versions, authority certificates, and so on.

    ; A "parameter document" is like a tiny consensus that relays and clients
    ; can use to get network parameters.
    ParamDoc = [
       sig: ParamDocSignature,
       ; Client-relevant portion of the parameter document. Everybody fetches
       ; this.
       cbody: encoded-cbor .cbor ClientParamDoc,
       ; Relay-relevant portion of the parameter document. Only relays need to
       ; fetch this; the document can be validated without it.
       ? sbody: encoded-cbor .cbor RelayParamDoc,
    ]
    ParamDocSignature = [
       ; Multisignature or threshold signature of the concatenation
       ; of the two digests below.
       SingleSig / MultiSig,

       ; Lifespan information.  As with SNIPs, this is included as part
       ; of the input to the hash algorithm for the signature.
       ; Note that the lifespan of a parameter document is likely to be
       ; very long.
       LifespanInfo,

       ; how are c_digest and s_digest computed?
       d_alg: DigestAlgorithm,
       ; Digest over the cbody field
       c_digest: bstr,
       ; Digest over the sbody field
       s_digest: bstr,
    ]

    ClientParamDoc = {
       params: NetParams,
       ; List of certificates for all the voters.  These
       ; authenticate the keys used to sign SNIPs and ENDIVEs and votes,
       ; using the authorities' longest-term identity keys.
       voters: [ + bstr .cbor VoterCert ],

       ; A division of exit ports into "classes" of ports.
       port-classes: PortClasses,

       ; As in client-versions from dir-spec.txt
       ? recommend-versions: [ * tstr ],
       ; As in recommended-client-protocols in dir-spec.txt
       ? recommend-protos: ProtoVersions,
       ; As in required-client-protocols in dir-spec.txt
       ? require-protos: ProtoVersions,

       ; For future extensions.
       * tstr => any,
    }

    RelayParamDoc = {
       params: NetParams,

       ; As in server-versions from dir-spec.txt
       ? recommend-versions: [ * tstr ],
       ; As in recommended-relay-protocols in dir-spec.txt
       ? recommend-protos: ProtoVersions,
       ; As in required-relay-protocols in dir-spec.txt
       ? require-versions: ProtoVersions,

       * tstr => any,
    }

    ; A NetParams encodes information about the Tor network that
    ; clients and relays need in order to participate in it.  The
    ; current list of parameters is described in the "params" field
    ; as specified in dir-spec.txt.
    ;
    ; Note that there are separate client and relay NetParams now.
    ; Relays are expected to first check for a defintion in the
    ; RelayParamDoc, and then in the ClientParamDoc.
    NetParams = { *tstr => int }

    PortClasses = {
        ; identifies which port class grouping this is. Used to migrate
        ; from one group of port classes to another.
        tag: uint,
        ; list of the port classes.
        classes: { * IndexId => PortList },
    }
    PortList = [ *PortOrRange ]
     ; Either a single port or a low-high pair
    PortOrRange = Port / [ Port, Port ]
    Port = 1...65535

<!-- Section 2.5 --> <a id='S2.5'></a>

## Certificates

Voting certificates are used to bind authorities' long-term
identities to shorter-term signing keys.  These have a similar
purpose to the authority certs made for the existing voting
algorithm, but support more key types.

    ; A 'voter certificate' is a statement by an authority binding keys to
    ; each other.
    VoterCert = [

       ; One or more signatures over `content` using the provided lifetime.
       ; Each signature should be treated independently.
       [ + SingleSig ],
       ; A lifetime value, used (as usual ) as an input to the
       ; signature algorithm.
       LifespanInfo,
       ; The keys and other data to be certified.
       content: encoded-cbor .cbor CertContent,
    ]

    ; The contents of the certificate that get signed.
    CertContent = {
       ; What kind of a certificate is this?
       type: CertType,
       ; A list of keys that are being certified in this document
       keys: [ + CertifiedKey ],
       ; A list of other keys that you might need to know about, which
       ; are NOT certififed in this document.
       ? extra: [ + CertifiedKey ],
       * tstr => any,
    }

    CertifiedKey = {
       ; What is the intended usage of this key?
       usage: KeyUsage,
       ; What cryptographic algorithm is this key used for?
       alg: PKAlgorithm,
       ; The actual key being certified.
       data: bstr,
       ; A human readable string.
       ? remarks: tstr,
       * tstr => any,
    }

<!-- Section 2.6 --> <a id='S2.6'></a>

## ENDIVE diffs

Here is a binary format to be used with ENDIVEs, ParamDocs, and any
other similar binary formats.  Authorities and directory caches need to
be able to generate it; clients and non-cache relays only need to be
able to parse and apply it.

    ; Binary diff specification.
    BinaryDiff = {
        ; This is version 1.
        v: 1,
        ; Optionally, a diff can say what different digests
        ; of the document should be before and after it is applied.
        ; If there is more than one entry, parties MAY check one or
        ; all of them.
        ? digest: { * DigestAlgorithm =>
                         [ pre: Digest,
                           post: Digest ]},

        ; Optionally, a diff can give some information to identify
        ; which document it applies to, and what document you get
        ; from applying it.  These might be a tuple of a document type
        ; and a publication type.
        ? ident: [ pre: any, post: any ],

        ; list of commands to apply in order to the original document in
        ; order to get the transformed document
        cmds: [ *DiffCommand ],

        ; for future extension.
        * tstr => any,
    }

    ; There are currently only two diff commands.
    ; One is to copy some bytes from the original.
    CopyDiffCommand = [
        OrigBytesCmdId,
        ; Range of bytes to copy from the original document.
        ; Ranges include their starting byte.  The "offset" is relative to
        ; the end of the _last_ range that was copied.
        offset: int,
        length: uint,
    ]

    ; The other diff comment is to insert some bytes from the diff.
    InsertDiffCommand = [
        InsertBytesCmdId,
        data: bstr,
    ]

    DiffCommand = CopyDiffCommand / InsertDiffCommand

    OrigBytesCmdId = 0
    InsertBytesCmdId = 1

Applying a binary diff is simple:

    Algorithm: applying a binary diff.

    (Given an input bytestring INP and a diff D, produces an output OUT.)

    Initialize OUT to an empty bytestring.

    Set OFFSET to 0.

    For each command C in D.commands, in order:

        If C begins with OrigBytesCmdId:
            Increase "OFFSET" by C.offset
            If OFFSET..OFFSET+C.length is not a valid range in
               INP, abort.
            Append INP[OFFSET .. OFFSET+C.length] to OUT.
            Increase "OFFSET" by C.length

        else: # C begins with InsertBytesCmdId:
            Append C.data to OUT.

Generating a binary diff can be trickier, and is not specified here.
There are several generic algorithms out there for making binary diffs
between arbitrary byte sequences. Since these are complex, I recommend a
chunk-based CBOR-aware algorithm, using each CBOR item in a similar way
to the way in which our current line-oriented code uses lines.  When
encountering a bstr tagged with "encoded-cbor", the diff algorithm
should look inside it to find more cbor chunks. (See
example-code/cbor_diff.py for an example of doing this with Python's
difflib.)

The diff format above should work equally well no matter what
diff algorithm is used, so we have room to move to other algorithms
in the future if needed.

To indicate support for the above diff format in directory requests,
implementations should use an `X-Support-Diff-Formats` header.  The
above format is designated "cbor-bindiff"; our existing format is
called "ed".

<!-- Section 2.7 --> <a id='S2.7'></a>

## Digests and parameters

Here we give definitions for `H_leaf()` and `H_node()`, based on an
underlying digest function H() with a preferred input block size of B.
(B should be chosen as the natural input size of the hash function, to
aid in precomputation.)

We also define `H_sign()`, to be used outside of SNIP authentication
where we aren't using a Merkle tree at all.

PATH must be no more than 64 bits long.  NONCE must be no more than B-33
bytes long.

     H_sign(LIFESPAN, NONCE, ITEM) =
        H( PREFIX(OTHER_C, LIFESPAN, NONCE) || ITEM)

     H_leaf(PATH, LIFESPAN, NONCE, ITEM) =
        H( PREFIX(LEAF_C, LIFESPAN, NONCE) ||
           U64(PATH) ||
           U64(bits(path)) ||
           ITEM )

     H_node(PATH, LIFESPAN, NONCE, ITEM) =
        H( PREFIX(NODE_C, LIFESPAN, NONCE) ||
           U64(PATH) ||
           U64(bits(PATH)) ||
           ITEM )

     PREFIX(leafcode, lifespan, nonce) =
          U64(leafcode) ||
          U64(lifespan.published) ||
          U32(lifespan.pre-valid) ||
          U32(lifespan.post-valid) ||
          U8(len(nonce)) ||
          nonce ||
          Z(B - 33 - len(nonce))

     LEAF_C = 0x8BFF0F687F4DC6A1 ^ NETCONST
     NODE_C = 0xA6F7933D3E6B60DB ^ NETCONST
     OTHER_C = 0x7365706172617465 ^ NETCONST

     # For the live Tor network only.
     NETCONST = 0x0746f72202020202
     # For testing networks, by default.
     NETCONST = 0x74657374696e6720

     U64(n) -- N encoded as a big-endian 64-bit number.
     Z(n) -- N bytes with value zero.
     len(b) -- the number of bytes in a byte-string b.
     bits(b) -- the number of bits in a bit-string b.


<!-- Section 3 --> <a id='S3'></a>

# Directory authority operations

For Walking Onions to work, authorities must begin to generate
ENDIVEs as a new kind of "consensus document".  Since this format is
incompatible with the previous consensus document formats, and is
CBOR-based, a text-based voting protocol is no longer appropriate
for generating it.

We cannot immediately abandon the text-based consensus and
microdescriptor formats, but instead will need to keep
generating them for legacy relays and clients.  Ideally, process
that produces the ENDIVE should also produce a legacy consensus,
to limit the amount of divergence in their contents.

Further, it would be good for the purposes of this proposal if we
can "inherit" as much as possible of our existing voting mechanism
for legacy purposes.

This section of the proposal will try to solve these goals by defining a
new binary-based voting format, a new set of voting rules for it, and a
series of migration steps.

<!-- Section 3.1 --> <a id='S3.1'></a>

## Overview

Except as described below, we retain from Tor's existing voting
mechanism all notions of how votes are transferred and processed.
Other changes are likely desirable, but they are out of scope for
this proposal.

Notably, we are not changing how the voting schedule works.  Nor are
we changing the property that all authorities must agree on the list
of authorities; the property that a consensus is computed as a
deterministic function of a set of votes; or the property that if
authorities believe in different sets of votes, they will not reach
the same consensus.

The principal changes in the voting that are relevant for legacy
consensus computation are:

  * The uploading process for votes now supports negotiation, so
    that the receiving authority can tell the uploading authority
    what kind of formats, diffs, and compression it supports.

  * We specify a CBOR-based binary format for votes, with a simple
    embedding method for the legacy text format.  This embedding is
    meant for transitional use only; once all authorities support
    the binary format, the transitional format and its support
    structures can be abandoned.

  * To reduce complexity, the new vote format also includes
    _verbatim_ microdescriptors, whereas previously microdescriptors
    would have been referenced by hash.  (The use of diffs and
    compression should make the bandwidth impact of this addition
    negligible.)

For computing ENDIVEs, the principal changes in voting are:

  * The consensus outputs for most voteable objects are specified in a
    way that does not require the authorities to understand their
    semantics when computing a consensus.  This should make it
    easier to change fields without requiring new consensus methods.

<!-- Section 3.2 --> <a id='S3.2'></a>

## Negotiating vote uploads

Authorities supporting Walking Onions are required to support a new
resource "/tor/auth-vote-opts".  This resource is a text document
containing a list of HTTP-style headers. Recognized headers are
described below; unrecognized headers MUST be ignored.

The *Accept-Encoding* header follows the same format as the HTTP
header of the same name; it indicates a list of Content-Encodings
that the authority will accept for uploads.  All authorities SHOULD
support the gzip and identity encodings.  The identity encoding is
mandatory.  (Default: "identity")

The *Accept-Vote-Diffs-From* header is a list of digests of previous
votes held by this authority; any new uploaded votes that are given
as diffs from one of these old votes SHOULD be accepted.  The format
is a space-separated list of "digestname:Hexdigest".  (Default: "".)

The *Accept-Vote-Formats* header is a space-separated list of the
vote formats that this router accepts. The recognized vote formats
are "legacy-3" (Tor's current vote format) and "endive-1" (the vote
format described here). Unrecognized vote formats MUST be ignored.
(Default: "legacy-3".)

If requesting "/tor/auth-vote-opts" gives an error, or if one or
more headers are missing, the default values SHOULD be used.  These
documents (or their absence) MAY be cached for up to 2 voting
periods.)

Authorities supporting Walking Onions SHOULD also support the
"Connection: keep-alive" and "Keep-Alive" HTTP headers, to avoid
needless reconnections in response to these requests.
Implementors SHOULD be aware of potential denial-of-service
attacks based on open HTTP connections, and mitigate them as
appropriate.

> Note: I thought about using OPTIONS here, but OPTIONS isn't quite
> right for this, since Accept-Vote-Diffs-From does not fit with its
> semantics.

> Note: It might be desirable to support this negotiation for legacy
> votes as well, even before walking onions is implemented.  Doing so
> would allow us to reduce authority bandwidth a little, and possibly
> include microdescriptors in votes for more convenient processing.

<!-- Section 3.3 --> <a id='S3.3'></a>

## A generalized algorithm for voting

Unlike with previous versions of our voting specification, here I'm
going to try to describe pieces the voting algorithm in terms of
simpler voting operations.  Each voting operation will be named and
possibly parameterized, and data will frequently self-describe what
voting operation is to be used on it.

Voting operations may operate over different CBOR types, and are
themselves specified as CBOR objects.

A voting operation takes place over a given "voteable field".  Each
authority that specifies a value for a voteable field MUST specify
which voting operation to use for that field.  Specifying a voteable
field without a voting operation MUST be taken as specifying the
voting operation "None" -- that is, voting against a consensus.

On the other hand, an authority MAY specify a voting operation for
a field without casting any vote for it.  This means that the
authority has an opinion on how to reach a consensus about the
field, without having any preferred value for the field itself.

<!-- Section 3.3.1 --> <a id='S3.3.1'></a>

### Constants used with voting operations

Many voting operations may be parameterized by an unsigned integer.
In some cases the integers are constant, but in others, they depend
on the number of authorities, the number of votes cast, or the
number of votes cast for a particular field.

When we encode these values, we encode them as short strings
rather than as integers.

> I had thought of using negative integers here to encode these
> special constants, but that seems too error-prone.

The following constants are defined:

`N_AUTH` -- the total number of authorities, including those whose
votes are absent.

`N_PRESENT` -- the total number of authorities whose votes are
present for this vote.

`N_FIELD` -- the total number of authorities whose votes for a given
field are present.

Necessarily, `N_FIELD` <= `N_PRESENT` <= `N_AUTH` -- you can't vote
on a field unless you've cast a vote, and you can't cast a vote
unless you're an authority.

In the definitions below, `//` denotes the truncating integer division
operation, as implemented with `/` in C.

`QUORUM_AUTH` -- The lowest integer that is greater than half of
`N_AUTH`.  Equivalent to `N_AUTH // 2 + 1`.

`QUORUM_PRESENT` -- The lowest integer that is greater than half of
`N_PRESENT`.  Equivalent to `N_PRESENT // 2 + 1`.

`QUORUM_FIELD` -- The lowest integer that is greater than half of
`N_FIELD`.  Equivalent to `N_FIELD // 2 + 1`.

We define `SUPERQUORUM_`..., variants of these fields as well, based
on the lowest integer that is greater than 2/3 majority of the
underlying field.  `SUPERQUORUM_x` is thus equivalent to
`(N_x * 2) // 3 + 1`.

    ; We need to encode these arguments; we do so as short strings.
    IntOpArgument = uint / "auth" / "present" / "field" /
         "qauth" / "qpresent" / "qfield" /
         "sqauth" / "sqpresent" / "sqfield"

No IntOpArgument may be greater than AUTH.  If an IntOpArgument is
given as an integer, and that integer is greater than AUTH, then it
is treated as if it were AUTH.

> This rule lets us say things like "at least 3 authorities must
> vote on x...if there are 3 authorities."

<!-- Section 3.3.2 --> <a id='S3.3.2'></a>

### Producing consensus on a field

Each voting operation will either produce a CBOR output, or produce
no consensus.  Unless otherwise stated, all CBOR outputs are to be
given in canonical form.

Below we specify a number of operations, and the parameters that
they take.  We begin with operations that apply to "simple" values
(integers and binary strings), then show how to compose them to
larger values.

All of the descriptions below show how to apply a _single_ voting
operation to a set of votes.  We will later describe how to behave when
the authorities do not agree on which voting operation to use, in our
discussion of the StructJoinOp operation.

Note that while some voting operations take other operations as
parameters, we are _not_ supporting full recursion here: there is a
strict hierarchy of operations, and more complex operations can only
have simpler operations in their parameters.

All voting operations follow this metaformat:

    ; All a generic voting operation has to do is say what kind it is.
    GenericVotingOp = {
        op: tstr,
        * tstr => any,
    }

Note that some voting operations require a sort or comparison
operation over CBOR values.  This operation is defined later in
appendix E; it works only on homogeneous inputs.

<!-- Section 3.3.3 --> <a id='S3.3.3'></a>

### Generic voting operations

<!-- Section 3.3.3.1 --> <a id='S3.3.3.1'></a>

#### None

This voting operation takes no parameters, and always produces "no
consensus".  It is encoded as:

    ; "Don't produce a consensus".
    NoneOp = { op: "None" }

When encountering an unrecognized or nonconforming voting operation,
_or one which is not recognized by the consensus-method in use_, the
authorities proceed as if the operation had been "None".

<!-- Section 3.3.4 --> <a id='S3.3.4'></a>

### Voting operations for simple values

We define a "simple value" according to these cddl rules:

    ; Simple values are primitive types, and tuples of primitive types.
    SimpleVal = BasicVal / SimpleTupleVal
    BasicVal = bool / int / bstr / tstr
    SimpleTupleVal = [ *BasicVal ]

We also need the ability to encode the types for these values:

    ; Encoding a simple type.
    SimpleType = BasicType / SimpleTupleType
    BasicType = "bool" /  "uint" / "sint" / "bstr" / "tstr"
    SimpleTupleType = [ "tuple", *BasicType ]

In other words, a SimpleVal is either an non-compound base value, or is
a tuple of such values.

    ; We encode these operations as:
    SimpleOp = MedianOp / ModeOp / ThresholdOp /
        BitThresholdOp / CborSimpleOp / NoneOp

We define each of these operations in the sections below.

<!-- Section 3.3.4.1 --> <a id='S3.3.4.1'></a>

#### Median

_Parameters_: `MIN_VOTES` (an integer), `BREAK_EVEN_LOW` (a boolean),
`TYPE` (a SimpleType)

    ; Encoding:
    MedianOp = { op: "Median",
                 ? min_vote: IntOpArgument,  ; Default is 1.
                 ? even_low: bool,           ; Default is true.
                 type: SimpleType  }

Discard all votes that are not of the specified `TYPE`. If there are
fewer than `MIN_VOTES` votes remaining, return "no consensus".

Put the votes in ascending sorted order. If the number of votes N
is odd, take the center vote (the one at position (N+1)/2).  If N is
even, take the lower of the two center votes (the one at position
N/2) if `BREAK_EVEN_LOW` is true. Otherwise, take the higher of the
two center votes (the one at position N/2 + 1).

For example, the Median(…, even_low: True, type: "uint") of the votes
["String", 2, 111, 6] is 6. The Median(…, even_low: True, type: "uint")
of the votes ["String", 77, 9, 22, "String", 3] is 9.

<!-- Section 3.3.4.2 --> <a id='S3.3.4.2'></a>

#### Mode

_Parameters_: `MIN_COUNT` (an integer), `BREAK_TIES_LOW` (a boolean),
`TYPE` (a SimpleType)

    ; Encoding:
    ModeOp = { op: "Mode",
               ? min_count: IntOpArgument,   ; Default 1.
               ? tie_low: bool,              ; Default true.
               type: SimpleType
    }

Discard all votes that are not of the specified `TYPE`.  Of the
remaining votes, look for the value that has received the most
votes.  If no value has received at least `MIN_COUNT` votes, then
return "no consensus".

If there is a single value that has received the most votes, return
it. Break ties in favor of lower values if `BREAK_TIES_LOW` is true,
and in favor of higher values if `BREAK_TIES_LOW` is false.
(Perform comparisons in canonical cbor order.)

<!-- Section 3.3.4.3 --> <a id='S3.3.4.3'></a>

#### Threshold

_Parameters_: `MIN_COUNT` (an integer), `BREAK_MULTI_LOW` (a boolean),
`TYPE` (a SimpleType)

    ; Encoding
    ThresholdOp = { op: "Threshold",
                    min_count: IntOpArgument,  ; No default.
                    ? multi_low: bool,          ; Default true.
                    type: SimpleType
    }

Discard all votes that are not of the specified `TYPE`.  Sort in
canonical cbor order.  If `BREAK_MULTI_LOW` is false, reverse the
order of the list.

Return the first element that received at least `MIN_COUNT` votes.
If no value has received at least `MIN_COUNT` votes, then return
"no consensus".

<!-- Section 3.3.4.4 --> <a id='S3.3.4.4'></a>

#### BitThreshold

Parameters: `MIN_COUNT` (an integer >= 1)

    ; Encoding
    BitThresholdOp = { op: "BitThreshold",
                       min_count: IntOpArgument, ; No default.
    }

These are usually not needed, but are quite useful for
building some ProtoVer operations.

Discard all votes that are not of type uint or bstr; construe bstr
inputs as having type "biguint".

The output is a uint or biguint in which the b'th bit is set iff the
b'th bit is set in at least `MIN_COUNT` of the votes.

<!-- Section 3.3.5 --> <a id='S3.3.5'></a>

### Voting operations for lists

These operations work on lists of SimpleVal:

    ; List type definitions
    ListVal = [ * SimpleVal ]

    ListType = [ "list",
                 [ *SimpleType ] / nil ]

They are encoded as:

    ; Only one list operation exists right now.
    ListOp = SetJoinOp

<!-- Section 3.3.5.1 --> <a id='S3.3.5.1'></a>

#### SetJoin

Parameters: `MIN_COUNT` (an integer >= 1).
Optional parameters: `TYPE` (a SimpleType.)

    ; Encoding:
    SetJoinOp = {
       op: "SetJoin",
       min_count: IntOpArgument,
       ? type: SimpleType
    }

Discard all votes that are not lists.  From each vote,
discard all members that are not of type 'TYPE'.

For the consensus, construct a new list containing exactly those
elements that appears in at least `MIN_COUNT` votes.

(Note that the input votes may contain duplicate elements.  These
must be treated as if there were no duplicates: the vote
[1, 1, 1, 1] is the same as the vote [1]. Implementations may want
to preprocess votes by discarding all but one instance of each
member.)

<!-- Section 3.3.6 --> <a id='S3.3.6'></a>

### Voting operations for maps

Map voting operations work over maps from key types to other non-map
types.

    ; Map type definitions.
    MapVal = { * SimpleVal => ItemVal }
    ItemVal = ListVal / SimpleVal

    MapType = [ "map", [ *SimpleType ] / nil, [ *ItemType ] / nil ]
    ItemType = ListType / SimpleType

They are encoded as:

    ; MapOp encodings
    MapOp = MapJoinOp / StructJoinOp

<!-- Section 3.3.6.1 --> <a id='S3.3.6.1'></a>

#### MapJoin

The MapJoin operation combines homogeneous maps (that is, maps from
a single key type to a single value type.)

Parameters:
   `KEY_MIN_COUNT` (an integer >= 1)
   `KEY_TYPE` (a SimpleType type)
   `ITEM_OP` (A non-MapJoin voting operation)

Encoding:

    ; MapJoin operation encoding
    MapJoinOp = {
       op: "MapJoin"
       ? key_min_count: IntOpArgument, ; Default 1.
       key_type: SimpleType,
       item_op: ListOp / SimpleOp
    }

First, discard all votes that are not maps.  Then consider the set
of keys from each vote as if they were a list, and apply
`SetJoin[KEY_MIN_COUNT,KEY_TYPE]` to those lists.  The resulting list
is a set of keys to consider including in the output map.

> We have a separate `key_min_count` field, even if `item_op` has
> its own `min_count` field, because some min_count values (like
> `qfield`) depend on the overall number of votes for the field.
> Having `key_min_count` lets us specify rules like "the FOO of all
> votes on this field, if there are at least 2 such votes."

For each key in the output list, run the sub-voting operation
`ItemOperation` on the values it received in the votes.  Discard all
keys for which the outcome was "no consensus".

The final vote result is a map from the remaining keys to the values
produced by the voting operation.

<!-- Section 3.3.6.2 --> <a id='S3.3.6.2'></a>

#### StructJoin

A StructJoinOp operation describes a way to vote on maps that encode a
structure-like object.

Parameters:
    `KEY_RULES` (a map from int or string to StructItemOp)
    `UNKNOWN_RULE` (An operation to apply to unrecognized keys.)

    ; Encoding
    StructItemOp = ListOp / SimpleOp / MapJoinOp / DerivedItemOp /
        CborDerivedItemOp

    VoteableStructKey = int / tstr

    StructJoinOp = {
        op: "StructJoin",
        key_rules: {
            * VoteableStructKey => StructItemOp,
        }
        ? unknown_rule: StructItemOp
    }

To apply a StructJoinOp to a set of votes, first discard every vote that is
not a map.  Then consider the set of keys from all the votes as a single
list, with duplicates removed.  Also remove all entries that are not integers
or strings from the list of keys.

For each key, then look for that key in the `KEY_RULES` map.  If there is an
entry, then apply the StructItemOp for that entry to the values for that key
in every vote.  Otherwise, apply the `UNKNOWN_RULE` operation to the values
for that key in every vote.  Otherwise, there is no consensus for the values
of this key.  If there _is_ a consensus for the values, then the key should
map to that consensus in the result.

This operation always reaches a consensus, even if it is an empty map.

<!-- Section 3.3.6.3 --> <a id='S3.3.6.3'></a>

#### CborData

A CborData operation wraps another operation, and tells the authorities
that after the operation is completed, its result should be decoded as a
CBOR bytestring and interpolated directly into the document.

Parameters: `ITEM_OP` (Any SingleOp that can take a bstr input.)

     ; Encoding
     CborSimpleOp = {
         op: "CborSimple",
         item-op: MedianOp / ModeOp / ThresholdOp / NoneOp
     }
     CborDerivedItemOp = {
         op: "CborDerived",
         item-op: DerivedItemOp,
     }

To apply either of these operations to a set of votes, first apply
`ITEM_OP` to those votes.  After that's done, check whether the
consensus from that operation is a bstr that encodes a single item of
"well-formed" "valid" cbor.  If it is not, this operation gives no
consensus.  Otherwise, the consensus value for this operation is the
decoding of that bstr value.

<!-- Section 3.3.6.4 --> <a id='S3.3.6.4'></a>

#### DerivedFromField

This operation can only occur within a StructJoinOp operation (or a
semantically similar SectionRules). It indicates that one field
should have been derived from another.  It can be used, for example,
to say that a relay's version is "derived from" a relay's descriptor
digest.

Unlike other operations, this one depends on the entire consensus (as
computed so far), and on the entirety of the set of votes.

> This operation might be a mistake, but we need it to continue lots of
> our current behavior.

Parameters:
    `FIELDS` (one or more other locations in the vote)
    `RULE` (the rule used to combine values)

Encoding
    ; This item is "derived from" some other field.
    DerivedItemOp = {
        op: "DerivedFrom",
        fields: [ +SourceField ],
        rule: SimpleOp
    }

    ; A field in the vote.
    SourceField = [ FieldSource, VoteableStructKey ]

    ; A location in the vote.  Each location here can only
    ; be referenced from later locations, or from itself.
    FieldSource = "M" ; Meta.
               / "CP" ; ClientParam.
               / "SP" ; ServerParam.
               / "RM" ; Relay-meta
               / "RS" ; Relay-SNIP
               / "RL" ; Relay-legacy

To compute a consensus with this operation, first locate each field described
in the SourceField entry in each VoteDocument (if present), and in the
consensus computed so far.  If there is no such field in the
consensus or if it has not been computed yet, then
this operation produces "no consensus".  Otherwise, discard the VoteDocuments
that do not have the same value for the field as the consensus, and their
corresponding votes for this field.  Do this for every listed field.

At this point, we have a set of votes for this field's value that all come
from VoteDocuments that describe the same value for the source field(s).  Apply
the `RULE` operation to those votes in order to give the result for this
voting operation.

The DerivedFromField members in a SectionRules or a StructJoinOp
should be computed _after_ the other members, so that they can refer
to those members themselves.

<!-- Section 3.3.7 --> <a id='S3.3.7'></a>

### Voting on document sections

Voting on a section of the document is similar to the StructJoin
operation, with some exceptions.  When we vote on a section of the
document, we do *not* apply a single voting rule immediately.
Instead, we first "_merge_" a set of SectionRules together, and then
apply the merged rule to the votes.  This is the only place where we
merge rules like this.

A SectionRules is _not_ a voting operation, so its format is not
tagged with an "op":

    ; Format for section rules.
    SectionRules = {
      * VoteableStructKey => SectionItemOp,
      ? nil => SectionItemOp
    }
    SectionItemOp = StructJoinOp / StructItemOp

To merge a set of SectionRules together, proceed as follows. For each
key, consider whether at least QUORUM_AUTH authorities have voted the
same StructItemOp for that key.  If so, that StructItemOp is the
resulting operation for this key.  Otherwise, there is no entry for this key.

Do the same for the "nil" StructItemOp; use the result as the
`UNKNOWN_RULE`.

Note that this merging operation is *not* recursive.

<!-- Section 3.4 --> <a id='S3.4'></a>

## A CBOR-based metaformat for votes.

A vote is a signed document containing a number of sections; each
section corresponds roughly to a section of another document, a
description of how the vote is to be conducted, or both.

    ; VoteDocument is a top-level signed vote.
    VoteDocument = [
        ; Each signature may be produced by a different key, if they
        ; are all held by the same authority.
        sig: [ + SingleSig ],
        lifetime: Lifespan,
        digest-alg: DigestAlgorithm,
        body: bstr .cbor VoteContent
    ]

    VoteContent = {
        ; List of supported consensus methods.
        consensus-methods: [ + uint ],

        ; Text-based legacy vote to be used if the negotiated
        ; consensus method is too old.  It should itself be signed.
        ; It's encoded as a series of text chunks, to help with
        ; cbor-based binary diffs.
        ? legacy-vote: [ * tstr ],

        ; How should the votes within the individual sections be
        ; computed?
        voting-rules: VotingRules,

        ; Information that the authority wants to share about this
        ; vote, which is not itself voted upon.
        notes: NoteSection,

        ; Meta-information that the authorities vote on, which does
        ; not actually appear in the ENDIVE or consensus directory.
        meta: MetaSection .within VoteableSection,

        ; Fields that appear in the client network parameter document.
        client-params: ParamSection .within VoteableSection,
        ; Fields that appear in the server network parameter document.
        server-params: ParamSection .within VoteableSection,

        ; Information about each relay.
        relays: RelaySection,

        ; Information about indices.
        indices: IndexSection,

        * tstr => any
    }

    ; Self-description of a voter.
    VoterSection = {
        ; human-memorable name
        name: tstr,

        ; List of link specifiers to use when uploading to this
        ; authority. (See proposal for dirport link specifier)
        ? ul: [ *LinkSpecifier ],

        ; List of link specifiers to use when downloading from this authority.
        ? dl: [ *LinkSpecifier ],

        ; contact information for this authority.
        ? contact: tstr,

        ; legacy certificate in format given by dir-spec.txt.
        ? legacy-cert: tstr,

        ; for extensions
        * tstr => any,
    }

    ; An indexsection says how we think routing indices should be built.
    IndexSection = {
        * IndexId => bstr .cbor [ IndexGroupId, GenericIndexRule ],
    }
    IndexGroupId = uint
    ; A mechanism for building a single routing index.  Actual values need to
    ; be within RecognizedIndexRule or the authority can't complete the
    ; consensus.
    GenericIndexRule = {
        type: tstr,
        * tstr => any
    }
    RecognizedIndexRule = EdIndex / RSAIndex / BWIndex / WeightedIndex
    ; The values in an RSAIndex are derived from digests of Ed25519 keys.
    EdIndex = {
        type: "ed-id",
        alg: DigestAlgorithm,
        prefix: bstr,
        suffix: bstr
    }
    ; The values in an RSAIndex are derived from RSA keys.
    RSAIndex = {
        type: "rsa-id"
    }
    ; A BWIndex is built by taking some uint-valued field referred to by
    ; SourceField from all the relays that have all of required_flags set.
    BWIndex = {
        type: "bw",
        bwfield: SourceField,
        require_flags: FlagSet,
    }
    ; A flag can be prefixed with "!" to indicate negation.  A flag
    ; with a name like P@X indicates support for port class 'X' in its
    ; exit policy.
    ;
    ; FUTURE WORK: perhaps we should add more structure here and it
    ; should be a matching pattern?
    FlagSet = [ *tstr ]
    ; A WeightedIndex applies a set of weights to a BWIndex based on which
    ; flags the various routers have.  Relays that match a set of flags have
    ; their weights multiplied by the corresponding WeightVal.
    WeightedIndex = {
        type: "weighted",
        source: BwIndex,
        weight: { * FlagSet => WeightVal }
    }
    ; A WeightVal is either an integer to multiply bandwidths by, or a
    ; string from the Wgg, Weg, Wbm, ... set as documented in dir-spec.txt,
    ; or a reference to an earlier field.
    WeightVal = uint / tstr / SourceField
    VoteableValue =  MapVal / ListVal / SimpleVal

    ; A "VoteableSection" is something that we apply part of the
    ; voting rules to.  When we apply voting rules to these sections,
    ; we do so without regards to their semantics.  When we are done,
    ; we use these consensus values to make the final consensus.
    VoteableSection = {
       VoteableStructKey => VoteableValue,
    }

    ; A NoteSection is used to convey information about the voter and
    ; its vote that is not actually voted on.
    NoteSection = {
       ; Information about the voter itself
       voter: VoterSection,
       ; Information that the voter used when assigning flags.
       ? flag-thresholds: { tstr => any },
       ; Headers from the bandwidth file to be reported as part of
       ; the vote.
       ? bw-file-headers: {tstr => any },
       ? shared-rand-commit: SRCommit,
       * VoteableStructKey => VoteableValue,
    }

    ; Shared random commitment; fields are as for the current
    ; shared-random-commit fields.
    SRCommit = {
       ver: uint,
       alg: DigestAlgorithm,
       ident: bstr,
       commit: bstr,
       ? reveal: bstr
    }

    ; the meta-section is voted on, but does not appear in the ENDIVE.
    MetaSection = {
       ; Seconds to allocate for voting and distributing signatures
       ; Analagous to the "voting-delay" field in the legacy algorithm.
       voting-delay: [ vote_seconds: uint, dist_seconds: uint ],
       ; Proposed time till next vote.
       voting-interval: uint,
       ; proposed lifetime for the SNIPs and ENDIVEs
       snip-lifetime: Lifespan,
       ; proposed lifetime for client params document
       c-param-lifetime: Lifespan,
       ; proposed lifetime for server params document
       s-param-lifetime: Lifespan,
       ; signature depth for ENDIVE
       signature-depth: uint,
       ; digest algorithm to use with ENDIVE.
       signature-digest-alg: DigestAlgorithm,
       ; Current and previous shared-random values
       ? cur-shared-rand: [ reveals: uint, rand: bstr ],
       ? prev-shared-rand: [ reveals: uint, rand: bstr ],
       ; extensions.
       * VoteableStructKey => VoteableValue,
    };

    ; A ParamSection will be made into a ParamDoc after voting;
    ; the fields are analogous.
    ParamSection = {
       ? certs: [ 1*2 bstr .cbor VoterCert ],
       ? recommend-versions: [ * tstr ],
       ? require-protos: ProtoVersions,
       ? recommend-protos: ProtoVersions,
       ? params: NetParams,
       * VoteableStructKey => VoteableValue,
    }
    RelaySection = {
       ; Mapping from relay identity key (or digest) to relay information.
       * bstr => RelayInfo,
    }

    ; A RelayInfo is a vote about a single relay.
    RelayInfo = {
       meta: RelayMetaInfo .within VoteableSection,
       snip: RelaySNIPInfo .within VoteableSection,
       legacy: RelayLegacyInfo .within VoteableSection,
    }

    ; Information about a relay that doesn't go into a SNIP.
    RelayMetaInfo = {
        ; Tuple of published-time and descriptor digest.
        ? desc: [ uint , bstr ],
        ; What flags are assigned to this relay?  We use a
        ; string->value encoding here so that only the authorities
        ; who have an opinion on the status of a flag for a relay need
        ; to vote yes or no on it.
        ? flags: { *tstr=>bool },
        ; The relay's self-declared bandwidth.
        ? bw: uint,
        ; The relay's measured bandwidth.
        ? mbw: uint,
        ; The fingerprint of the relay's RSA identity key.
        ? rsa-id: RSAIdentityFingerprint
    }
    ; SNIP information can just be voted on directly; the formats
    ; are the same.
    RelaySNIPInfo = SNIPRouterData

    ; Legacy information is used to build legacy consensuses, but
    ; not actually required by walking onions clients.
    RelayLegacyInfo = {
       ; Mapping from consensus version to microdescriptor digests
       ; and microdescriptors.
       ? mds: [ *Microdesc ],
    }

    ; Microdescriptor votes now include the digest AND the
    ; microdescriptor-- see note.
    Microdesc = [
       low: uint,
       high: uint,
       digest: bstr .size 32,
       ; This is encoded in this way so that cbor-based diff tools
       ; can see inside it.  Because of compression and diffs,
       ; including microdesc text verbatim should be comparatively cheap.
       content: encoded-cbor .cbor [ *tstr ],
    ]

    ; ==========

    ; The VotingRules field explains how to vote on the members of
    ; each section
    VotingRules = {
        meta: SectionRules,
        params: SectionRules,
        relay: RelayRules,
        indices: SectionRules,
    }

    ; The RelayRules object explains the rules that apply to each
    ; part of a RelayInfo.  A key will appear in the consensus if it
    ; has been listed by at least key_min_count authorities.
    RelayRules = {
        key_min_count: IntOpArgument,
        meta: SectionRules,
        snip: SectionRules,
        legacy: SectionRules,
    }

<!-- Section 3.5 --> <a id='S3.5'></a>

## Computing a consensus.

To compute a consensus, the authorities first verify that all the votes are
timely and correctly signed by real authorities.  This includes
validating all invariants stated here, and all internal documents.

If they have two votes from an authority, authorities SHOULD issue a
warning, and they should take the one that is published more
recently.

> TODO: Teor suggests that maybe we shouldn't warn about two votes
> from an authority for the same period, and we could instead have a
> more resilient process here, where authorities can update their
> votes at various times over the voting period, up to some point.
>
> I'm not sure whether this helps reliability more or less than it risks it,
> but it worth investigating.

Next, the authorities determine the consensus method as they do today,
using the field "consensus-method".  This can also be expressed as
the voting operation `Threshold[SUPERQUORUM_PRESENT, false, uint]`.

If there is no consensus for the consensus-method, then voting stops
without having produced a consensus.

Note that in contrast with its behavior in the current voting algorithm, the
consensus method does not determine the way to vote on every
individual field: that aspect of voting is controlled by the
voting-rules.  Instead, the consensus-method changes other aspects
of this voting, such as:

    * Adding, removing, or changing the semantics of voting
      operations.
    * Changing the set of documents to which voting operations apply.
    * Otherwise changing the rules that are set out in this
      document.

Once a consensus-method is decided, the next step is to compute the
consensus for other sections in this order: `meta`, `client-params`,
`server-params`, and `indices`.  The consensus for each is calculated
according to the operations given in the corresponding section of
VotingRules.

Next the authorities compute a consensus on the `relays` section,
which is done slightly differently, according to the rules of
RelayRules element of VotingRules.

Finally, the authorities transform the resulting sections into an
ENDIVE and a legacy consensus, as in "Computing an ENDIVE" and
"Computing a legacy consensus" below.

To vote on a single VotingSection, find the corresponding
SectionRules objects in the VotingRules of this votes, and apply it
as described above in "Voting on document sections".

<!-- Section 3.6 --> <a id='S3.6'></a>

## If an older consensus method is negotiated (Transitional)

The `legacy-vote` field in the vote document contains an older (v3,
text-style) consensus vote, and is used when an older consensus
method is negotiated.  The legacy-vote is encoded by splitting it
into pieces, to help with CBOR diff calculation.  Authorities MAY split at
line boundaries, space boundaries, or anywhere that will help with
diffs.   To reconstruct the legacy vote, concatenate the members of
`legacy-vote` in order.  The resulting string MUST validate
according to the rules of the legacy voting algorithm.

If a legacy vote is present, then authorities SHOULD include the
same view of the network in the legacy vote as they included in their
real vote.

If a legacy vote is present, then authorities MUST
give the same list of consensus-methods and the same voting
schedule in both votes.  Authorities MUST reject noncompliant votes.

<!-- Section 3.7 --> <a id='S3.7'></a>

## Computing an ENDIVE.

If a consensus-method is negotiated that is high enough to support
ENDIVEs, then the authorities proceed as follows to transform the consensus
sectoins above into an ENDIVE.

The ParamSections from the consensus are used verbatim as the bodies of the
`client-params` and `relay-params` fields.

The fields that appear in each RelaySNIPInfo determine what goes
into the SNIPRouterData for each relay. To build the relay section,
first decide which relays appear according to the `key_min_count`
field in the RelayRules.  Then collate relays across all the votes
by their keys, and see which ones are listed.  For each key that
appears in at least `key_min_count` votes, apply the RelayRules to
each section of the RelayInfos for that key.

The sig_params section is derived from fields in the meta section.
Fields with identical names are simply copied; Lifespan values are
copied to the corresponding documents (snip-lifetime as the lifespan
for SNIPs and ENDIVEs, and c and s-param-lifetime as the lifespan
for ParamDocs).

To compute the signature nonce, use the signature digest algorithm
to compute the digest of each input vote body, sort those digests
lexicographically, and concatenate and hash those digests again.

Routing indices are built according to named IndexRules, and grouped
according to fields in the meta section.  See "Constructing Indices" below.

> (At this point extra fields may be copied from the Meta section of
> each RelayInfo into the ENDIVERouterData depending on the meta
> document; we do not, however, currently specify any case where this
> is done.)

<!-- Section 3.7.1 --> <a id='S3.7.1'></a>

### Constructing indices

After having built the list of relays, the authorities construct and
encode the indices that appear in the ENDIVEs.  The voted-upon
GenericIndexRule values in the IndexSection of the consensus say how
to build the indices in the ENDIVE, as follows.

An `EdIndex` is built using the IndexType_Ed25519Id value, with the
provided prefix and suffix values.  Authorities don't need to expand
this index in the ENDIVE, since the relays can compute it
deterministically.

An `RSAIndex` is built using the IndexType_RSAId type.  Authorities
don't need to expand this index in the ENDIVE, since the relays can
compute it deterministically.

A `BwIndex` is built using the IndexType_Weighted type. Each relay has a
weight equal to some specified bandwidth field in its consensus
RelayInfo.  If a relay is missing any of the `required_flags` in
its meta section, or if it does not have the specified bandwidth
field, that relay's weight becomes 0.

A `WeightedIndex` is built by computing a BwIndex, and then
transforming each relay in the list according to the flags that it
has set.  Relays that match any set of flags in the WeightedIndex
rule get their bandwidths multiplied by _all_ WeightVals that
apply.  Some WeightVals are computed according to special rules,
such as "Wgg", "Weg", and so on.  These are taken from the current
dir-spec.txt.

For both BwIndex and WeightedIndex values, authorities MUST scale
the computed outputs so that no value is greater than UINT32_MAX;
they MUST do by shifting all values right by lowest number of bits
that achieves this.

> We could specify a more precise algorithm, but this is simpler.

Indices with the same IndexGroupId are placed in the same index
group; index groups are ordered numerically.

<!-- Section 3.8 --> <a id='S3.8'></a>

## Computing a legacy consensus.

When using a consensus method that supports Walking Onions, the
legacy consensus is computed from the same data as the ENDIVE.
Because the legacy consensus format will be frozen once Walking
Onions is finalized, we specify this transformation directly, rather
than in a more extensible way.

The published time and descriptor digest are used directly.
Microdescriptor negotiation proceeds as before.  Bandwidths,
measured bandwidths, descriptor digests, published times, flags, and
rsa-id values are taken from the RelayMetaInfo section.  Addresses,
protovers, versions, and so on are taken from the RelaySNIPInfo. Header
fields are all taken from the corresponding header fields in the
MetaSection or the ClientParamsSection. All parameters are copied
into the net-params field.

<!-- Section 3.9 --> <a id='S3.9'></a>

## Managing indices over time.

> The present voting mechanism does not do a great job of handling
> the authorities

The semantic meaning of most IndexId values, as understood by
clients should remain unchanging; if a client uses index 6 for
middle nodes, 6 should _always_ mean "middle nodes".

If an IndexId is going to change its meaning over time, it should
_not_ be hardcoded by clients; it should instead be listed in the
NetParams document, as the exit indices are in the `port-classes`
field. (See also section 6 and appendix AH.)  If such a field needs
to change, it also needs a migration method that allows clients with
older and newer parameters documents to exist at the same time.

<!-- Section 4 --> <a id='S4'></a>

# Relay operations: Receiving and expanding ENDIVEs

Previously, we introduced a format for ENDIVEs to be transmitted
from authorities to relays.  To save on bandwidth, the relays
download diffs rather than entire ENDIVEs.  The ENDIVE format makes
several choices in order to make these diffs small: the Merkle tree
is omitted, and routing indices are not included directly.

To address those issues, this document describes the steps that a
relay needs to perform, upon receiving an ENDIVE document, to derive
all the SNIPs for that ENDIVE.

Here are the steps to be followed.  We'll describe them in order,
though in practice they could be pipelined somewhat.  We'll expand
further on each step later on.

  1. Compute routing indices positions.

  2. Compute truncated SNIPRouterData variations.

  3. Build signed SNIP data.

  4. Compute Merkle tree.

  5. Build authenticated SNIPs.

Below we'll specify specific algorithms for these steps.  Note that
relays do not need to follow the steps of these algorithms exactly,
but they MUST produce the same outputs as if they had followed them.

<!-- Section 4.1 --> <a id='S4.1'></a>

## Computing index positions.

For every IndexId in every Index Group, the relay will compute the
full routing index.  Every routing index is a mapping from
index position ranges (represented as 2-tuples) to relays, where the
relays are represented as ENDIVERouterData members of the ENDIVE.  The
routing index must map every possible value of the index to exactly one
relay.

An IndexSpec field describes how the index is to be constructed.  There
are four types of IndexSpec: Raw, Raw Spans, Weighted, RSAId, and
Ed25519Id.  We'll describe how to build the indices for each.

Every index may either have an integer key, or a binary-string
key. We define the "successor" of an integer index as the succeeding
integer.  We define the "successor" of a binary string as the next
binary string of the same length in lexicographical (memcmp) order.  We
define "predecessor" as the inverse of "successor".  Both these
operations "wrap around" the index.

The algorithms here describe a set of invariants that are
"verified".  Relays SHOULD check each of these invariants;
authorities MUST NOT generate any ENDIVEs that violate them.  If a
relay encounters an ENDIVE that cannot be verified, then the ENDIVE
cannot be expanded.

> NOTE: conceivably should there be some way to define an index as a
> subset of another index, with elements weighted in different ways?  In
> other words, "Index a is index b, except multiply these relays by 0 and
> these relays by 1.2".  We can keep this idea sitting around in case there
> turns out to be a use for it.

<!-- Section 4.1.1 --> <a id='S4.1.1'></a>

### Raw indices

When the IndexType is Indextype_Raw, then its members are listed
directly in the IndexSpec.

    Algorithm: Expanding a "Raw" indexspec.

    Let result_idx = {} (an empty mapping).

    Let previous_pos = indexspec.first_index

    For each element [i, pos2] of indexspec.index_ranges:

        Verify that i is a valid index into the list of ENDIVERouterData.

        Set pos1 = the successor of previous_pos.

        Verify that pos1 and pos2 have the same type.

        Append the mapping (pos1, pos2) => i to result_idx

        Set previous_pos to pos2.

    Verify that previous_pos = the predecessor of indexspec.first_index.

    Return result_idx.

<!-- Section 4.1.2 --> <a id='S4.1.2'></a>

### Raw numeric indices

If the IndexType is Indextype_RawNumeric, it is described by a set of
spans on a 32-bit index range.

    Algorithm: Expanding a RawNumeric index.

    Let prev_pos = 0

    For each element [i, span] of indexspec.index_ranges:

        Verify that i is a valid index into the list of ENDIVERouterData.

        Verify that prev_pos <= UINT32_MAX - span.

        Let pos2 = prev_pos + span.

        Append the mapping (pos1, pos2) => i to result_idx.

        Let prev_pos = successor(pos2)

    Verify that prev_pos = UINT32_MAX.

    Return result_idx.

<!-- Section 4.1.3 --> <a id='S4.1.3'></a>

### Weighted indices

If the IndexSpec type is Indextype_Weighted, then the index is
described by assigning a probability weight to each of a number of relays.
From these, we compute a series of 32-bit index positions.

This algorithm uses 64-bit math, and 64-by-32-bit integer division.

It requires that the sum of weights is no more than UINT32_MAX.

    Algorithm: Expanding a "Weighted" indexspec.

    Let total_weight = SUM(indexspec.index_weights)

    Verify total_weight <= UINT32_MAX.

    Let total_so_far = 0.

    Let result_idx = {} (an empty mapping).

    Define POS(b) = FLOOR( (b << 32) / total_weight).

    For 0 <= i < LEN(indexspec.indexweights):

       Let w = indexspec.indexweights[i].

       Let lo = POS(total_so_far).

       Let total_so_far = total_so_far + w.

       Let hi = POS(total_so_far) - 1.

       Append (lo, hi) => i to result_idx.

    Verify that total_so_far = total_weight.

    Verify that the last value of "hi" was UINT32_MAX.

    Return result_idx.

This algorithm is a bit finicky in its use of division, but it
results in a mapping onto 32 bit integers that completely covers the
space of available indices.

<!-- Section 4.1.4 --> <a id='S4.1.4'></a>

### RSAId indices

If the IndexSpec type is Indextype_RSAId then the index is a set of
binary strings describing the routers' legacy RSA identities, for
use in the HSv2 hash ring.

These identities are truncated to a fixed length.  Though the SNIP
format allows _variable_-length binary prefixes, we do not use this
feature.

    Algorithm: Expanding an "RSAId" indexspec.

    Let R = [ ] (an empty list).

    Take the value n_bytes from the IndexSpec.

    For 0 <= b_idx < MIN( LEN(indexspec.members) * 8,
                          LEN(list of ENDIVERouterData) ):

       Let b = the b_idx'th bit of indexspec.members.

       If b is 1:
           Let m = the b_idx'th member of the ENDIVERouterData list.

           Verify that m has its RSAIdentityFingerprint set.

           Let pos = m.RSAIdentityFingerprint, truncated to n_bytes.

           Add (pos, b_idx) to the list R.

    Return INDEX_FROM_RING_KEYS(R).

    Sub-Algorithm: INDEX_FROM_RING_KEYS(R)

    First, sort R according to its 'pos' field.

    For each member (pos, idx) of the list R:

        If this is the first member of the list R:
            Let key_low = pos for the last member of R.
        else:
            Let key_low = pos for the previous member of R.

        Let key_high = predecessor(pos)

        Add (key_low, key_high) => idx to result_idx.

    Return result_idx.

<!-- Section 4.1.5 --> <a id='S4.1.5'></a>

### Ed25519 indices

If the IndexSpec type is Indextype_Ed25519, then the index is a set of
binary strings describing the routers' positions in a hash ring,
derived from their Ed25519 identity keys.

This algorithm is a generalization of the one used for hsv3 rings,
to be used to compute the hsv3 ring and other possible future
derivatives.

    Algorithm: Expanding an "Ed25519Id" indexspec.

    Let R = [ ] (an empty list).

    Take the values prefix, suffix, and n_bytes from the IndexSpec.

    Let H() be the digest algorithm specified by d_alg from the
    IndexSpec.

    For 0 <= b_idx < MIN( LEN(indexspec.members) * 8,
                          LEN(list of ENDIVERouterData) ):

       Let b = the b_idx'th bit of indexspec.members.

       If b is 1:
           Let m = the b_idx'th member of the ENDIVERouterData list.

           Let key = m's ed25519 identity key, as a 32-byte value.

           Compute pos = H(prefix || key || suffix)

           Truncate pos to n_bytes.

           Add (pos, b_idx) to the list R.

    Return INDEX_FROM_RING_KEYS(R).

<!-- Section 4.1.6 --> <a id='S4.1.6'></a>

### Building a SNIPLocation

After computing all the indices in an IndexGroup, relays combine
them into a series of SNIPLocation objects. Each SNIPLocation
MUST contain all the IndexId => IndexRange entries that point to a
given ENDIVERouterData, for the IndexIds listed in an IndexGroup.

    Algorithm: Build a list of SNIPLocation objects from a set of routing indices.

    Initialize R as [ { } ] * LEN(relays)   (A list of empty maps)

    For each IndexId "ID" in the IndexGroup:

       Let router_idx be the index map calculated for ID.
       (This is what we computed previously.)

       For each entry ( (LO, HI) => idx) in router_idx:

          Let R[idx][ID] = (LO, HI).

SNIPLocation objects are thus organized in the order in which they will
appear in the Merkle tree: that is, sorted by the position of their
corresponding ENDIVERouterData.

Because SNIPLocation objects are signed, they must be encoded as "canonical"
cbor, according to section 3.9 of RFC 7049.

If R[idx] is {} (the empty map) for any given idx, then no SNIP will be
generated for the SNIPRouterData at that routing index for this index group.

<!-- Section 4.2 --> <a id='S4.2'></a>

## Computing truncated SNIPRouterData.

An index group can include an `omit_from_snips` field to indicate that
certain fields from a SNIPRouterData should not be included in the
SNIPs for that index group.

Since a SNIPRouterData needs to be signed, this process has to be
deterministic.  Thus, the truncated SNIPRouterData should be computed by
removing the keys and values for EXACTLY the keys listed and no more.  The
remaining keys MUST be left in the same order that they appeared in the
original SNIPRouterData, and they MUST NOT be re-encoded.

(Two keys are "the same" if and only if they are integers encoding the same
value, or text strings with the same UT-8 content.)

There is no need to compute a SNIPRouterData when no SNIP is going to be
generated for a given router.

<!-- Section 4.3 --> <a id='S4.3'></a>

## Building the Merkle tree.

After computing a list of (SNIPLocation, SNIPRouterData) for every entry
in an index group, the relay needs to expand a Merkle tree to
authenticate every SNIP.

There are two steps here: First the relay generates the leaves, and then
it generates the intermediate hashes.

To generate the list of leaves for an index group, the relay first
removes all entries from the (SNIPLocation, SNIPRouterData) list that
have an empty index map.  The relay then puts `n_padding_entries` "nil"
entries at the end of the list.

To generate the list of leaves for the whole Merkle tree, the relay
concatenates these index group lists in the order in which they appear
in the ENDIVE, and pads the resulting list with "nil" entries until the
length of the list is a power of two: 2^`tree-depth` for some integer
`tree-depth`.  Let LEAF(IDX) denote the entry at position IDX in this
list, where IDX is a D-bit bitstring.  LEAF(IDX) is either a byte string
or nil.

The relay then recursively computes the hashes in the Merkle tree as
follows.  (Recall that `H_node()` and `H_leaf()` are hashes taking
a bit-string PATH, a LIFESPAN and NONCE from the signature information,
and a variable-length string ITEM.)

    Recursive defintion: HM(PATH)

    Given PATH a bitstring of length no more than tree-depth.

    Define S:
        S(nil) = an all-0 string of the same length as the hash output.
        S(x) = x, for all other x.

    If LEN(PATH) = tree-depth:   (Leaf case.)
       If LEAF(PATH) = nil:
         HM(PATH) = nil.
       Else:
         HM(PATH) = H_node(PATH, LIFESPAN, NONCE, LEAF(PATH)).

    Else:
       Let LEFT = HM(PATH || 0)
       Let RIGHT = HM(PATH || 1)
       If LEFT = nil and RIGHT = nil:
           HM(PATH) = nil
       else:
           HM(PATH) = H_node(PATH, LIFESPAN, NONCE, S(LEFT) || S(RIGHT))

Note that entries aren't computed for "nil" leaves, or any node all of
whose children are "nil".  The "nil" entries only exist to place all
leaves at a constant depth, and to enable spacing out different sections
of the tree.

If `signature-depth` for the ENDIVE is N, the relay does not need to
compute any Merkle tree entries for PATHs of length shorter than N bits.

<!-- Section 4.4 --> <a id='S4.4'></a>

## Assembling the SNIPs

Finally, the relay has computed a list of encoded (SNIPLocation,
RouterData) values, and a Merkle tree to authenticate them.  At this
point, the relay builds them into SNIPs, using the `sig_params` and
`signatures` from the ENDIVE.

    Algorithm: Building a SNIPSignature for a SNIP.

    Given a non-nil (SNIPLocation, RouterData) at leaf position PATH.

    Let SIG_IDX = PATH, truncated to signature-depth bits.
    Consider SIG_IDX as an integer.

    Let Sig = signatures[SIG_IDX] -- either the SingleSig or the MultiSig
    for this snip.

    Let HashPath = []   (an empty list).
    For bitlen = signature-depth+1 ... tree-depth-1:
        Let X = PATH, truncated to bitlen bits.
        Invert the final bit of PATH.
        Append HM(PATH) to HashPath.

    The SnipSignature's signature values is Sig, and its merkle_path is
    HashPath.

<!-- Section 4.5 --> <a id='S4.5'></a>

## Implementation considerations

A relay only needs to hold one set of SNIPs at a time: once one
ENDIVE's SNIPs have been extracted, then the SNIPs from the previous
ENDIVE can be discarded.

To save memory, a relay MAY store SNIPs to disk, and mmap them as
needed.

<!-- Section 5 --> <a id='S5'></a>

# Extending circuits with Walking Onions

When a client wants to extend a circuit, there are several
possibilities.  It might need to extend to an unknown relay with
specific properties.  It might need to extend to a particular relay
from which it has received a SNIP before.  In both cases, there are
changes to be made in the circuit extension process.

Further, there are changes we need to make for the handshake between
the extending relay and the target relay.  The target relay is no
longer told by the client which of its onion keys it should use... so
the extending relay needs to tell the target relay which keys are in
the SNIP that the client is using.

<!-- Section 5.1 --> <a id='S5.1'></a>

## Modifying the EXTEND/CREATE handshake

First, we will require that proposal 249 (or some similar proposal
for wide CREATE and EXTEND cells) is in place, so that we can have
EXTEND cells larger than can fit in a single cell.  (See
319-wide-everything.md for an example proposal to supersede 249.)

We add new fields to the CREATE2 cell so that relays can send each
other more information without interfering with the client's part of
the handshake.

The CREATE2, CREATED2, and EXTENDED2 cells change as follows:

      struct create2_body {
         // old fields
         u16 htype; // client handshake type
         u16 hlen; // client handshake length
         u8 hdata[hlen]; // client handshake data.

         // new fields
         u8 n_extensions;
         struct extension extension[n_extensions];
      }

      struct created2_body {
         // old fields
         u16 hlen;
         u8 hdata[hlen];

         // new fields
         u8 n_extensions;
         struct extension extension[n_extensions];
      }

      struct truncated_body {
         // old fields
         u8 errcode;

         // new fields
         u8 n_extensions;
         struct extension extension[n_extensions];
      }

      // EXTENDED2 cells can now use the same new fields as in the
      // created2 cell.

      struct extension {
         u16 type;
         u16 len;
         u8 body[len];
      }

These extensions are defined by this proposal:

  [01] -- `Partial_SNIPRouterData` -- Sent from an extending relay
          to a target relay. This extension holds one or more fields
          from the SNIPRouterData that the extending relay is using,
          so that the target relay knows (for example) what keys to
          use.  (These fields are determined by the
          "forward_with_extend" field in the ENDIVE.)

  [02] -- Full_SNIP -- an entire SNIP that was used in an attempt to
          extend the circuit.  This must match the client's provided
          index position.

  [03] -- Extra_SNIP -- an entire SNIP that was not used to extend
          the circuit, but which the client requested anyway.  This
          can be sent back from the extending relay when the client
          specifies multiple index positions, or uses a nonzero "nth" value
          in their `snip_index_pos` link specifier.

  [04] -- SNIP_Request -- a 32-bit index position, or a single zero
          byte, sent away from the client.  If the byte is 0, the
          originator does not want a SNIP.  Otherwise, the
          originator does want a SNIP containing the router and the
          specified index.  Other values are unspecified.

By default, EXTENDED2 cells are sent with a SNIP iff the EXTENDED2
cell used a `snip_index_pos` link specifier, and CREATED2 cells are
not sent with a SNIP.

<!-- Section 5.1.1 --> <a id='S5.1.1'></a>

### New link specifiers

We add a new link specifier type for a router index, using the
following coding for its contents:

    /* Using trunnel syntax here. */
    struct snip_index_pos {
        u32 index_id; // which index is it?
        u8 nth; // how many SNIPs should be skipped/included?
        u8 index_pos[]; // extends to the end of the link specifier.
    }

The `index_pos` field can be longer or shorter than the actual width of
the router index.  If it is too long, it is truncated.  If it is too
short, it is extended with zero-valued bytes.

Any number of these link specifiers may appear in an EXTEND cell.
If there is more then one, then they should appear in order of
client preference; the extending relay may extend to any of the
listed routers.

This link specifier SHOULD NOT be used along with IPv4, IPv6, RSA
ID, or Ed25519 ID link specifiers.  Relays receiving such a link
specifier along with a `snip_index_pos` link specifier SHOULD reject
the entire EXTEND request.

If `nth` is nonzero, then link specifier means "the n'th SNIP after
the one defined by the SNIP index position."  A relay MAY reject
this request if `nth` is greater than 4.  If the relay does not
reject this request, then it MUST include all snips between
`index_pos` and the one that was actually used in an Extra_Snip
extension.  (Otherwise, the client would not be able to verify that
it had gotten the correct SNIP.)

> I've avoided use of CBOR for these types, under the assumption that we'd
> like to use CBOR for directory stuff, but no more.  We already have
> trunnel-like objects for this purpose.

<!-- Section 5.2 --> <a id='S5.2'></a>

## Modified ntor handshake

We adapt the ntor handshake from tor-spec.txt for this use, with the
following main changes.

  * The NODEID and KEYID fields are omitted from the input.
    Instead, these fields _may_ appear in a PartialSNIPData extension.

  * The NODEID and KEYID fields appear in the reply.

  * The NODEID field is extended to 32 bytes, and now holds the
    relay's ed25519 identity.

So the client's message is now:

   CLIENT_PK [32 bytes]

And the relay's reply is now:

   NODEID    [32 bytes]
   KEYID     [32 bytes]
   SERVER_PK [32 bytes]
   AUTH      [32 bytes]

otherwise, all fields are computed as described in tor-spec.

When this handshake is in use, the hash function is SHA3-256 and keys
are derived using SHAKE-256, as in rend-spec-v3.txt.

> Future work: We may wish to update this choice of functions
> between now and the implementation date, since SHA3 is a bit
> pricey.  Perhaps one of the BLAKEs would be a better choice.  If
> so, we should use it more generally.  On the other hand, the
> presence of public-key operations in the handshake _probably_
> outweighs the use of SHA3.

We will have to give this version of the handshake a new handshake
type.

<!-- Section 5.3 --> <a id='S5.3'></a>

## New relay behavior on EXTEND and CREATE failure.

If an EXTEND2 cell based on an routing index fails, the relay should
not close the circuit, but should instead send back a TRUNCATED cell
containing the SNIP in an extension.

If a CREATE2 cell fails and a SNIP was requested, then instead of
sending a DESTROY cell, the relay SHOULD respond with a CREATED2
cell containing 0 bytes of handshake data, and the SNIP in an
extension.  Clients MAY re-extend or close the circuit, but should
not leave it dangling.

<!-- Section 5.4 --> <a id='S5.4'></a>

## NIL handshake type

We introduce a new handshake type, "NIL".  The NIL handshake always
fails.  A client's part of the NIL handshake is an empty bytestring;
there is no server response that indicates success.

The NIL handshake can used by the client when it wants to fetch a
SNIP without creating a circuit.

Upon receiving a request to extend with the NIL circuit type, a
relay SHOULD NOT actually open any connection or send any data to
the target relay.  Instead, it should respond with a TRUNCATED cell
with the SNIP(s) that the client requested in one or more Extra_SNIP
extensions.

<!-- Section 5.5 --> <a id='S5.5'></a>

## Padding handshake cells to a uniform size

To avoid leaking information, all CREATE/CREATED/EXTEND/EXTENDED
cells SHOULD be padded to the same sizes.  In all cases, the amount
of padding is controlled by a set of network parameters:
"create-pad-len", "created-pad-len", "extend-pad-len" and
"extended-pad-len".  These parameters determine the minimum length
that the cell body or relay cell bodies should be.

If a cell would be sent whose body is less than the corresponding
parameter value, then the sender SHOULD pad the body by adding
zero-valued bytes to the cell body.  As usual, receivers MUST ignore
extra bytes at the end of cells.

> ALTERNATIVE: We could specify a more complicated padding
> mechanism, eg. 32 bytes of zeros then random bytes.


<!-- Section 6 --> <a id='S6'></a>

# Client behavior with walking onions

Today's Tor clients have several behaviors that become somewhat
more difficult to implement with Walking Onions.  Some of these
behaviors are essential and achievable.  Others can be achieved with
some effort, and still others appear to be incompatible with the
Walking Onions design.

<!-- Section 6.1 --> <a id='S6.1'></a>

## Bootstrapping and guard selection

When a client first starts running, it has no guards on the Tor
network, and therefore can't start building circuits immediately.
To produce a list of possible guards, the client begins connecting
to one or more fallback directories on their ORPorts, and building
circuits through them.  These are 3-hop circuits.  The first hop of
each circuit is the fallback directory; the second and third hops
are chosen from the Middle routing index.  At the third hop, the
client then sends an informational request for a guard's SNIP.  This
informational request is an EXTEND2 cell with handshake type NIL,
using a random spot on the Guard routing index.

Each such request yields a single SNIP that the client will store.
These SNIPs, in the order in which they were _requested_, will form the
client's list of "Sampled" guards as described in guard-spec.txt.

Clients SHOULD ensure that their sampled guards are not
linkable to one another.  In particular, clients SHOULD NOT add more
than one guard retrieved from the same third hop on the same
circuit. (If it did, that third hop would realize that some client using
guard A was also using guard B.)

> Future work: Is this threat real?  It seems to me that knowing one or two
> guards at a time in this way is not a big deal, though knowing the whole
> set would sure be bad.  However, we shouldn't optimize this kind of
> defense away until we know that it's actually needless.

If a client's network connection or choice of entry nodes is heavily
restricted, the client MAY request more than one guard at a time, but if
it does so, it SHOULD discard all but one guard retrieved from each set.

After choosing guards, clients will continue to use them even after
their SNIPs expire.  On the first circuit through each guard after
opening a channel, clients should ask that guard for a fresh SNIP for
itself, to ensure that the guard is still listed in the consensus, and
to keep the client's information up-to-date.

<!-- Section 6.2 --> <a id='S6.2'></a>

## Using bridges

As now, clients are configured to use a bridge by using an address and a
public key for the bridge.  Bridges behave like guards, except that they
are not listed in any directory or ENDIVE, and so cannot prove
membership when the client connects to them.

On the first circuit through each channel to a bridge, the client
asks that bridge for a SNIP listing itself in the `Self` routing
index.  The bridge responds with a self-created unsigned SNIP:

     ; This is only valid when received on an authenticated connection
     ; to a bridge.
     UnsignedSNIP = [
        ; There is no signature on this SNIP.
        auth : nil,

        ; Next comes the location of the SNIP within the ENDIVE.  This
        ; SNIPLocation will list only the Self index.
        index : bstr .cbor SNIPLocation,

        ; Finally comes the information about the router.
        router : bstr .cbor SNIPRouterData,
     ]

*Security note*: Clients MUST take care to keep UnsignedSNIPs separated
from signed ones. These are not part of any ENDIVE, and so should not be
used for any purpose other than connecting through the bridge that the
client has received them from.  They should be kept associated with that
bridge, and not used for any other, even if they contain other link
specifiers or keys.  The client MAY use link specifiers from the
UnsignedSNIP on future attempts to connect to the bridge.

<!-- Section 6.3 --> <a id='S6.3'></a>

## Finding relays by exit policy

To find a relay by exit policy, clients might choose the exit
routing index corresponding to the exit port they want to use.  This
has negative privacy implications, however, since the middle node
discovers what kind of exit traffic the client wants to use.
Instead, we support two other options.

First, clients may build anonymous three-hop circuits and then use those
circuits to request the SNIPs that they will use for their exits.  This
may, however, be inefficient.

Second, clients may build anonymous three-hop circuits and then use a
BEGIN cell to try to open the connection when they want.  When they do
so, they may include a new flag in the begin cell, "DVS" to enable
Delegated Verifiable Selection.  As described in the Walking Onions
paper, DVS allows a relay that doesn't support the requested port to
instead send the client the SNIP of a relay that does.  (In the paper,
the relay uses a digest of previous messages to decide which routing
index to use. Instead, we have the client send an index field.)

This requires changes to the BEGIN and END cell formats.  After the
"flags" field in BEGIN cells, we add an extension mechanism:

    struct begin_cell {
        nulterm addr_port;
        u32 flags;
        u8 n_extensions;
        struct extension exts[n_extensions];
    }

We allow the `snip_index_pos` link specifier type to appear as a begin
extension.

END cells will need to have a new format that supports including policy and
SNIP information.  This format is enabled whenever a new `EXTENDED_END_CELL`
flag appears in the begin cell.

    struct end_cell {
        u8 tag IN [ 0xff ]; // indicate that this isn't an old-style end cell.
        u8 reason;
        u8 n_extensions;
        struct extension exts[n_extensions];
    }

We define three END cell extensions.  Two types are for addresses, that
indicate what address was resolved and the associated TTL:

    struct end_ext_ipv4 {
        u32 addr;
        u32 ttl;
    }
    struct end_ext_ipv6 {
        u8 addr[16];
        u32 ttl;
    }

One new END cell extension is used for delegated verifiable selection:

    struct end_ext_alt_snip {
        u16 index_id;
        u8 snip[..];
    }

This design may require END cells to become wider; see
319-wide-everything.md for an example proposal to
supersede proposal 249 and allow more wide cell types.

<!-- Section 6.4 --> <a id='S6.4'></a>

## Universal path restrictions

There are some restrictions on Tor paths that all clients should obey,
unless they are configured not to do so.  Some of these restrictions
(like "start paths with a Guard node" or "don't use an Exit as a middle
when Exit bandwidth is scarce") are captured by the index system. Some
other restrictions are not.  Here we describe how to implement those.

The general approach taken here is "build and discard".  Since most
possible paths will not violate these universal restrictions, we
accept that a fraction of the paths built will not be usable.
Clients tear them down a short time after they are built.

Clients SHOULD discard a circuit if, after it has been built, they
find that it contains the same relay twice, or it contains more than
one relay from the same family or from the same subnet.

Clients MAY remember the SNIPs they have received, and use those
SNIPs to avoid index ranges that they would automatically reject.
Clients SHOULD NOT store any SNIP for longer than it is maximally
recent.

> NOTE: We should continue to monitor the fraction of paths that are
> rejected in this way.  If it grows too high, we either need to amend
> the path selection rules, or change authorities to e.g. forbid more
> than a certain fraction of relay weight in the same family or subnet.

> FUTURE WORK: It might be a good idea, if these restrictions truly are
> 'universal', for relays to have a way to say "You wouldn't want that
> SNIP; I am giving you the next one in sequence" and send back both
> SNIPs.  This would need some signaling in the EXTEND/EXTENDED cells.

<!-- Section 6.5 --> <a id='S6.5'></a>

## Client-configured path restrictions

Sometimes users configure their clients with path restrictions beyond
those that are in ordinary use.  For example, a user might want to enter
only from US relays, but never exit from US.  Or they might be
configured with a short list of vanguards to use in their second
position.

<!-- Section 6.5.1 --> <a id='S6.5.1'></a>

### Handling "light" restrictions

If a restriction only excludes a small number of relays, then clients
can continue to use the "build and discard" methodology described above.

<!-- Section 6.5.2 --> <a id='S6.5.2'></a>

### Handling some "heavy" restrictions

Some restrictions can exclude most relays, and still be reasonably easy
to implement if they only _include_ a small fraction of relays.  For
example, if the user has a EntryNodes restriction that contains only a
small group of relays by exact IP address, the client can connect or
extend to one of those addresses specifically.

If we decide IP ranges are important, that IP addresses without
ports are important, or that key specifications are important, we
can add routing indices that list relays by IP, by RSAId, or by
Ed25519 Id.  Clients could then use those indices to remotely
retrieve SNIPs, and then use those SNIPs to connect to their
selected relays.

> Future work: we need to decide how many of the above functions to actually
> support.

<!-- Section 6.5.3 --> <a id='S6.5.3'></a>

### Recognizing too-heavy restrictions

The above approaches do not handle all possible sets of restrictions. In
particular, they do a bad job for restrictions that ban a large fraction
of paths in a way that is not encodeable in the routing index system.

If there is substantial demand for such a path restriction, implementors
and authority operators should figure out how to implement it in the
index system if possible.

Implementations SHOULD track what fraction of otherwise valid circuits
they are closing because of the user's configuration.  If this fraction
is above a certain threshold, they SHOULD issue a warning; if it is
above some other threshold, they SHOULD refuse to build circuits
entirely.

> Future work: determine which fraction appears in practice, and use that to
> set the appropriate thresholds above.

<!-- Section 7 --> <a id='S7'></a>

# Using and providing onion services with Walking Onions

Both live versions of the onion service design rely on a ring of
hidden service directories for use in uploading and downloading
hidden service descriptors.  With Walking Onions, we can use routing
indices based on Ed25519 or RSA identity keys to retrieve this data.

(The RSA identity ring is unchanging, whereas the Ed25519 ring
changes daily based on the shared random value: for this reason, we
have to compute two simultaneous indices for Ed25519 rings: one for
the earlier date that is potentially valid, and one for the later
date that is potentially valid. We call these `hsv3-early` and
`hsv3-late`.)

Beyond the use of these indices, however, there are other steps that
clients and services need to take in order to maintain their privacy.

<!-- Section 7.1 --> <a id='S7.1'></a>

## Finding HSDirs

When a client or service wants to contact an HSDir, it SHOULD do so
anonymously, by building a three-hop anonymous circuit, and then
extending it a further hop using the snip_span link specifier to
upload to any of the first 3 replicas on the ring.  Clients SHOULD
choose an 'nth' at random; services SHOULD upload to each replica.

Using a full 80-bit or 256-bit index position in the link specifier
would leak the chosen service to somebody other than the directory.
Instead, the client or service SHOULD truncate the identifier to a
number of bytes equal to the network parameter `hsv2-index-bytes` or
`hsv3-index-bytes` respectively.  (See Appendix C.)

<!-- Section 7.2 --> <a id='S7.2'></a>

## SNIPs for introduction points

When services select an introduction point, they should include the
SNIP for the introduction point in their hidden service directory
entry, along with the introduction-point fields.  The format for
this entry is:

    "snip" NL snip NL
      [at most once per introduction points]

Clients SHOULD begin treating the link specifier and onion-key
fields of each introduction point as optional when the "snip" field
is present, and when the `hsv3-tolerate-no-legacy` network parameter
is set to 1. If either of these fields _is_ present, and the SNIP is
too, then these fields MUST match those listed in the SNIPs.
Clients SHOULD reject descriptors with mismatched fields, and alert
the user that the service may be trying a partitioning attack.
The "legacy-key" and "legacy-key-cert" fields, if present, should be
checked similarly.

> Using the SNIPs in these ways allows services to prove that their
> introduction points have actually been listed in the consensus
> recently.  It also lets clients use introduction point features
> that the relay might not understand.

Services should include these fields based on a set of network
parameters: `hsv3-intro-snip` and `hsv3-intro-legacy-fields`.
(See appendix C.)

Clients should use these fields only when Walking Onions support is
enabled; see section 09.

<!-- Section 7.3 --> <a id='S7.3'></a>

## SNIPs for rendezvous points

When a client chooses a rendezvous point for a v3 onion service, it
similarly has the opportunity to include the SNIP of its rendezvous
point in the encrypted part of its INTRODUCE cell.  (This may cause
INTRODUCE cells to become fragmented; see proposal about fragmenting
relay cells.)

> Using the SNIPs in these ways allows services to prove that their
> introduction points have actually been listed in the consensus
> recently.  It also lets services use introduction point features
> that the relay might not understand.

To include the SNIP, the client places it in an extension in the
INTRODUCE cell.  The onion key can now be omitted[*], along with
the link specifiers.

> [*] Technically, we use a zero-length onion key, with a new type
> "implicit in SNIP".

To know whether the service can recognize this kind of cell, the
client should look for the presence of a "snips-allowed 1" field in
the encrypted part of the hidden service descriptor.

In order to prevent partitioning, services SHOULD NOT advertise
"snips-allowed 1" unless the network parameter
"hsv3-rend-service-snip" is set to 1.  Clients SHOULD NOT use this
field unless "hsv3-rend-client-snip" is set to 1.

<!-- Section 7.4 --> <a id='S7.4'></a>

## TAP keys and where to find them

If v2 hidden services are still supported when Walking Onions arrives
on the network, we have two choices:  We could migrate them to use
ntor keys instead of TAP, or we could provide a way for TAP keys to
be advertised with Walking Onions.

The first option would appear to be far simpler. See
proposal draft 320-tap-out-again.md.

The latter option would require us to put RSA-1024 keys in SNIPs, or
put a digest of them in SNIPs and give some way to retrieve them
independently.

(Of course, it's possible that we will have v2 onion services
deprecated by the time Walking Onions is implemented.  If so, that
will simplify matters a great deal too.)


<!-- Section 8 --> <a id='S8'></a>

# Tracking Relay honesty

Our design introduces an opportunity for dishonest relay behavior:
since multiple ENDIVEs are valid at the same time, a malicious relay
might choose any of several possible SNIPs in response to a client's
routing index value.

Here we discuss several ways to mitigate this kind of attack.

<!-- Section 8.1 --> <a id='S8.1'></a>

## Defense: index stability

First, the voting process should be designed such that relays do not
needlessly move around the routing index.  For example, it would
_not_ be appropriate to add an index type whose value is computed by
first putting the relays into a pseudorandom order.  Instead, index
voting should be deterministic and tend to give similar outputs for
similar inputs.

This proposal tries to achieve this property in its index voting
algorithms.  We should measure the degree to which we succeed over
time, by looking at all of the ENDIVEs that are valid at any
particular time, and sampling several points for each index to see
how many distinct relays are listed at each point, across all valid
ENDIVEs.

We do not need this stability property for routing indices whose
purpose is nonrandomized relay selection, such as those indices used
for onion service directories.

<!-- Section 8.2 --> <a id='S8.2'></a>

## Defense: enforced monotonicity

Once an honest relay has received an ENDIVE, it has no reason to
keep any previous ENDIVEs or serve SNIPs from them.  Because of
this, relay implementations SHOULD ensure that no data is served
from a new ENDIVE until all the data from an old ENDIVE is
thoroughly discarded.

Clients and relays can use this monotonicity property to keep relays
honest: once a relay has served a SNIP with some timestamp `T`, that
relay should never serve any other SNIP with a timestamp earlier than
`T`.  Clients SHOULD track the most recent SNIP timestamp that they
have received from each of their guards, and MAY track the most
recent SNIP timestamps that they have received from other relays as
well.

<!-- Section 8.3 --> <a id='S8.3'></a>

## Defense: limiting ENDIVE variance within the network.

The primary motivation for allowing long (de facto) lifespans on
today's consensus documents is to keep the network from grinding to
a halt if the authorities fail to reach consensus for a few hours.
But in practice, _if_ there is a consensus, then relays should have
it within an hour or two, so they should not be falling a full day out
of date.

Therefore we can potentially add a client behavior that, within N
minutes after the client has seen any SNIP with timestamp `T`,
the client should not accept any SNIP with timestamp earlier than
`T - Delta`.

Values for N and Delta are controlled by network parameters
(`enforce-endive-dl-delay-after` and `allow-endive-dl-delay`
respectively in appendix C).  N should be about as long as we expect
it to take for a single ENDIVE to propagate to all the relays on the
network; Delta should be about as long as we would like relays to go
between updating ENDIVEs under ideal circumstances.

<!-- Section 9 --> <a id='S9'></a>

# Migrating to Walking Onions

This proposal is a major change in the Tor network that will
eventually require the participation of all relays [*], and will make
clients who support it distinguishable from clients that don't.

> [*] Technically, the last relay in the path doesn't need support.

To keep the compatibility issues under control, here is the order in which it
should be deployed on the network.

1. First, authorities should add support for voting on ENDIVEs.

2. Relays may immediately begin trying to download and reconstruct
   ENDIVEs. (Relay versions are public, so they leak nothing by
   doing this.)

3. Once a sufficient number of authorities are voting on ENDIVEs and
   unlikely to downgrade, relays should begin serving parameter documents
   and responding to walking-onion EXTEND and CREATE cells.  (Again,
   relay versions are public, so this doesn't leak.)

4. In parallel with relay support, Tor should also add client
   support for Walking Onions.  This should be disabled by default,
   however, since it will only be usable with the subset of relays
   that support Walking Onions, and since it would make clients
   distinguishable.

5. Once enough of the relays (possibly, all) support Walking Onions,
   the client support can be turned on.  They will not be able to
   use old relays that do not support Walking Onions.

6. Eventually, relays that do not support Walking Onions should not
   be listed in the consensus.

Client support for Walking Onions should be enabled or disabled, at
first, with a configuration option.  Once it seems stable, the
option should have an "auto" setting that looks at a network
parameter. This parameter should NOT be a simple "on" or "off",
however: it should be the minimum client version whose support for
Walking Onions is believed to be correct.

<!-- Section 9.1 --> <a id='S9.1'></a>

## Future work: migrating away from sedentary onions

Once all clients are using Walking Onions, we can take a pass
through the Tor specifications and source code to remove
no-longer-needed code.

Clients should be the first to lose support for old directories,
since nobody but the clients depends on the clients having them.
Only after obsolete clients represent a very small fraction of the
network should relay or authority support be disabled.

Some fields in router descriptors become obsolete with Walking
Onions, and possibly router descriptors themselves should be
replaced with cbor objects of some kind.  This can only happen,
however, after no descriptor users remain.

<!-- Section A --> <a id='SA'></a>

# Appendices

<!-- Section A.1 --> <a id='SA.1'></a>

## Appendix A: Glossary

I'm going to put a glossary here so I can try to use these terms
consistently.

*SNIP* -- A "Separable Network Index Proof".  Each SNIP contains the
information necessary to use a single Tor relay, and associates the relay
with one or more index ranges. SNIPs are authenticated by the directory
authorities.

*ENDIVE* -- An "Efficient Network Directory with Individually Verifiable
Entries".  An ENDIVE is a collection of SNIPS downloaded by relays,
authenticated by the directory authorities.

*Routing index* -- A routing index is a map from binary strings to relays,
with some given property.  Each relay that is in the routing index is
associated with a single *index range*.

*Index range* -- A range of positions withing a routing index.  Each range
 contains many positions.

*Index position* -- A single value within a routing index.  Every position in
 a routing index corresponds to a single relay.

*ParamDoc* -- A network parameters document, describing settings for the
 whole network.  Clients download this infrequently.

*Index group* -- A collection of routing indices that are encoded in the same
 SNIPs.

<!-- Section A.2 --> <a id='SA.2'></a>

## Appendix B: More cddl definions

    ; These definitions are used throughout the rest of the
    ; proposal

    ; Ed25519 keys are 32 bytes, and that isn't changing.
    Ed25519PublicKey = bstr .size 32

    ; Curve25519 keys are 32 bytes, and that isn't changing.
    Curve25519PublicKey = bstr .size 32

    ; 20 bytes or fewer: legacy RSA SHA1 identity fingerprint.
    RSAIdentityFingerprint = bstr

    ; A 4-byte integer -- or to be cddl-pedantic, one that is
    ; between 0 and UINT32_MAX.
    uint32 = uint .size 4

    ; Enumeration to define integer equivalents for all the digest algorithms
    ; that Tor uses anywhere.  Note that some of these are not used in
    ; this spec, but are included so that we can use this production
    ; whenever we need to refer to a hash function.
    DigestAlgorithm = &(
        NoDigest: 0,
        SHA1    : 1,     ; deprecated.
        SHA2-256: 2,
        SHA2-512: 3,
        SHA3-256: 4,
        SHA3-512: 5,
        Kangaroo12-256: 6,
        Kangaroo12-512: 7,
    )

    ; A digest is represented as a binary blob.
    Digest = bstr

    ; Enumeration for different signing algorithms.
    SigningAlgorithm = &(
       RSA-OAEP-SHA1  : 1,     ; deprecated.
       RSA-OAEP-SHA256: 2,     ; deprecated.
       Ed25519        : 3,
       Ed448          : 4,
       BLS            : 5,     ; Not yet standardized.
    )

    PKAlgorithm = &(
       SigningAlgorithm,

       Curve25519: 100,
       Curve448  : 101
    )

    KeyUsage = &(
       ; A master unchangeable identity key for this authority.  May be
       ; any signing key type.  Distinct from the authority's identity as a
       ; relay.
       AuthorityIdentity: 0x10,
       ; A medium-term key used for signing SNIPs, votes, and ENDIVEs.
       SNIPSigning: 0x11,

       ; These are designed not to collide with the "list of certificate
       ; types" or "list of key types" in cert-spec.txt
    )

    CertType = &(
       VotingCert: 0x12,
       ; These are designed not to collide with the "list of certificate
       ; types" in cert-spec.txt.
    )

    LinkSpecifier = bstr

<!-- Section A.3 --> <a id='SA.3'></a>

## Appendix C: new numbers to assign.

Relay commands:

* We need a new relay command for "FRAGMENT" per proposal 319.

CREATE handshake types:

* We need a type for the NIL handshake.

* We need a handshake type for the new ntor handshake variant.

Link specifiers:

* We need a link specifier for extend-by-index.

* We need a link specifier for dirport URL.

Certificate Types and Key Types:

* We need to add the new entries from CertType and KeyUsage to
  cert-spec.txt, and possibly merge the two lists.

Begin cells:

* We need a flag for Delegated Verifiable Selection.

* We need an extension type for extra data, and a value for indices.

End cells:

* We need an extension type for extra data, a value for indices, a
  value for IPv4 addresses, and a value for IPv6 addresses.

Extensions for decrypted INTRODUCE2 cells:

* A SNIP for the rendezvous point.

Onion key types for decrypted INTRODUCE2 cells:

* An "onion key" to indicate that the onion key for the rendezvous point is
  implicit in the SNIP.

New URLs:

* A URL for fetching ENDIVEs.

* A URL for fetching client / relay parameter documents

* A URL for fetching detached SNIP signatures.

Protocol versions:

(In theory we could omit many new protovers here, since being listed
in an ENDIVE implies support for the new protocol variants.  We're
going to use new protovers anyway, however, since doing so keeps our
numbering consistent.)

We need new versions for these subprotocols:

* _Relay_ to denote support for new handshake elements.

* _DirCache_ to denote support for ENDIVEs, paramdocs, binary diffs, etc.

* _Cons_ to denote support for ENDIVEs


<!-- Section A.4 --> <a id='SA.4'></a>

## Appendix D: New network parameters.

We introduce these network parameters:

From section 5:

* `create-pad-len` -- Clients SHOULD pad their CREATE cell bodies
  to this size.

* `created-pad-len` -- Relays SHOULD pad their CREATED cell bodies to this
  size.

* `extend-pad-len` -- Clients SHOULD pad their EXTEND cell bodies to this
  size.

* `extended-pad-len` -- Relays SHOULD pad their EXTENDED cell bodies to this
size.

From section 7:

* `hsv2-index-bytes` -- how many bytes to use when sending an hsv2 index
  position to look up a hidden service directory.  Min: 1,
  Max: 40. Default: 4.

* `hsv3-index-bytes` -- how many bytes to use when sending an hsv3 index
  position to look up a hidden service directory.  Min: 1,
  Max: 128. Default: 4.

* `hsv3-intro-legacy-fields` -- include legacy fields in service descriptors.
  Min: 0. Max: 1. Default: 1.

* `hsv3-intro-snip` -- include intro point SNIPs in service descriptors.
  Min: 0. Max: 1. Default: 0.

* `hsv3-rend-service-snip` -- Should services advertise and accept rendezvous
  point SNIPs in INTRODUCE2 cells?    Min: 0. Max: 1. Default: 0.

* `hsv3-rend-client-snip` -- Should clients place rendezvous point SNIPS in
  INTRODUCE2 cells when the service supports it?
  Min: 0. Max: 1. Default: 0.

* `hsv3-tolerate-no-legacy` -- Should clients tolerate v3 service descriptors
  that don't have legacy fields? Min: 0. Max: 1. Default: 0.

From section 8:

* `enforce-endive-dl-delay-after` -- How many seconds after receiving a
  SNIP with some timestamp T does a client wait for rejecting older SNIPs?
  Equivalent to "N" in "limiting ENDIVE variance within the network."
  Min: 0. Max: INT32_MAX. Default: 3600 (1 hour).

* `allow-endive-dl-delay` -- Once a client has received an SNIP with
  timestamp T, it will not accept any SNIP with timestamp earlier than
  "allow-endive-dl-delay" seconds before T.
  Equivalent to "Delta" in "limiting ENDIVE variance within the network."
  Min: 0. Max: 2592000 (30 days). Default: 10800 (3 hours).

<!-- Section A.5 --> <a id='SA.5'></a>

## Appendix E: Semantic sorting for CBOR values.

Some voting operations assume a partial ordering on CBOR values.  We define
such an ordering as follows:

  * bstr and tstr items are sorted lexicographically, as if they were
    compared with a version of strcmp() that accepts internal NULs.
  * uint and int items are are sorted by integer values.
  * arrays are sorted lexicographically by elements.
  * Tagged items are sorted as if they were not tagged.
  * Maps do not have any sorting order.
  * False precedes true.
  * Otherwise, the ordering between two items is not defined.

More specifically:

     Algorithm: compare two cbor items A and B.

     Returns LT, EQ, GT, or NIL.

     While A is tagged, remove the tag from A.
     While B is tagged, remove the tag from B.

     If A is any integer type, and B is any integer type:
          return A cmp B

     If the type of A is not the same as the type of B:
          return NIL.

     If A and B are both booleans:
          return int(A) cmp int(B), where int(false)=0 and int(B)=1.

     If A and B are both tstr or both bstr:
          while len(A)>0 and len(B)>0:
             if A[0] != B[0]:
                  return A[0] cmp B[0]
             Discard A[0] and B[0]
          If len(A) == len(B) == 0:
             return EQ.
          else if len(A) == 0:
             return LT.  (B is longer)
          else:
             return GT.  (A is longer)

     If A and B are both arrays:
          while len(A)>0 and len(B)>0:
             Run this algorithm recursively on A[0] and B[0].
             If the result is not EQ:
                 Return that result.
             Discard A[0] and B[0]
          If len(A) == len(B) == 0:
             return EQ.
          else if len(A) == 0:
             return LT.  (B is longer)
          else:
             return GT.  (A is longer)

    Otherwise, A and B are a type for which we do not define an ordering,
    so return NIL.

<!-- Section A.6 --> <a id='SA.6'></a>

## Appendix F: Example voting rules

Here we give a set of voting rules for the fields described in our initial
VoteDocuments.

    {
      meta: {
         voting-delay: { op: "Mode", tie_low:false,
                           type:["tuple","uint","uint"] },
         voting-interval: { op: "Median", type:"uint" },
         snip-lifespan: {op: "Mode", type:["tuple","uint","uint","uint"] },
         c-param-lifetime: {op: "Mode", type:["tuple","uint","uint","uint"] },
         s-param-lifetime: {op: "Mode", type:["tuple","uint","uint","uint"] },
         cur-shared-rand: {op: "Mode", min_count: "qfield",
                             type:["tuple","uint","bstr"]},
         prev-shared-rand: {op: "Mode", min_count: "qfield",
                             type:["tuple","uint","bstr"]},
      client-params: {
         recommend-versions: {op:"SetJoin", min_count:"qfield",type:"tstr"},
         require-protos: {op:"BitThreshold", min_count:"sqauth"},
         recommend-protos: {op:"BitThreshold", min_count:"qauth"},
         params: {op:"MapJoin",key_min_count:"qauth",
                     keytype:"tstr",
                     item_op:{op:"Median",min_vote:"qauth",type:"uint"},
                     },
         certs: {op:"SetJoin",min_count:1, type: 'bstr'},
      },
      ; Use same value for server-params.
      relay: {
         meta: {
            desc: {op:"Mode", min_count:"qauth",tie_low:false,
                   type:["uint","bstr"] },
            flags: {op:"MapJoin", key_type:"tstr",
                    item_op:{op:"Mode",type:"bool"}},
            bw: {op:"Median", type:"uint" },
            mbw :{op:"Median", type:"uint" },
            rsa-id: {op:"Mode", type:"bstr"},
        },
        snip: {
           ; ed25519 key is handled as any other value.
           0: { op:"DerivedFrom", fields:[["RM","desc"]],
                 rule:{op:"Mode",type="bstr"} },

           ; ntor onion key.
           1: { op:"DerivedFrom", fields:[["RM","desc"]],
                 rule:{op:"Mode",type="bstr"} },

           ; link specifiers.
           2: { op: "CborDerived",
                 item-op: { op:"DerivedFrom", fields:[["RM","desc"]],
                            rule:{op:"Mode",type="bstr" } } },

           ; software description.
           3: { op:"DerivedFrom", fields:[["RM","desc"]],
                 rule:{op:"Mode",type=["tuple", "tstr", "tstr"] } },

           ; protovers.
           4: { op: "CborDerived",
                 item-op: { op:"DerivedFrom", fields:[["RM","desc"]],
                          rule:{op:"Mode",type="bstr" } } },

           ; families.
           5: { op:"SetJoin", min_count:"qfield", type:"bstr" },

           ; countrycode
           6: { op:"Mode", type="tstr" } ,

           ; 7: exitpolicy.
           7: { op: "CborDerived",
                 item-op: { op: "DerivedFrom", fields:[["RM","desc"],["CP","port-classes"]],
                          rule:{op:"Mode",type="bstr" } } },
        },
        legacy: {
          "sha1-desc": { op:"DerivedFrom",
                          fields:[["RM","desc"]],
                          rule:{op:"Mode",type="bstr"} },
          "mds": { op:"DerivedFrom",
                    fields:[["RM":"desc"]],
                    rule: { op:"ThresholdOp", min_count: "qauth",
                             multi_low:false,
                             type:["tuple", "uint", "uint",
                                   "bstr", "bstr" ] }},
        }
      }
      indices: {
         ; See appendix G.
      }
    }

<!-- Section A.7 --> <a id='SA.7'></a>

## Appendix G: A list of routing indices

Middle -- general purpose index for use when picking middle hops in
circuits.  Bandwidth-weighted for use as middle relays.  May exclude
guards and/or exits depending on overall balance of resources on the
network.

Formula:
      type: 'weighted',
      source: {
          type:'bw', require_flags: ['Valid'], 'bwfield' : ["RM", "mbw"]
      },
      weight: {
          [ "!Exit", "!Guard" ] => "Wmm",
          [ "Exit", "Guard" ] => "Wbm",
          [ "Exit", "!Guard" ] => "Wem",
          [ "!Exit", "Guard" ] => "Wgm",
      }

Guard -- index for choosing guard relays. This index is not used
directly when extending, but instead only for _picking_ guard relays
that the client will later connect to directly.  Bandwidth-weighted
for use as guard relays. May exclude guard+exit relays depending on
resource balance.

      type: 'weighted',
      source: {
           type:'bw',
           require_flags: ['Valid', "Guard"],
           bwfield : ["RM", "mbw"]
      },
      weight: {
          [ "Exit", ] => "Weg",
      }

HSDirV2 -- index for finding spots on the hsv2 directory ring.

Formula:
      type: 'rsa-id',

HSDirV3-early -- index for finding spots on the hsv3 directory ring
for the earlier of the two "active" days. (The active days are
today, and whichever other day is closest to the time at which the
ENDIVE becomes active.)

Formula:
      type: 'ed-id'
      alg: SHA3-256,
      prefix: b"node-idx",
      suffix: (depends on shared-random and time period)

HSDirV3-late -- index for finding spots on the hsv3 directory ring
for the later of the two "active" days.

Formula: as HSDirV3-early, but with a different suffix.

Self -- A virtual index that never appears in an ENDIVE.  SNIPs with
this index are unsigned, and occupy the entire index range.  This
index is used with bridges to represent each bridge's uniqueness.

Formula: none.

Exit0..ExitNNN -- Exits that can connect to all ports within a given
PortClass 0 through NNN.

Formula:

      type: 'weighted',
      source: {
           type:'bw',
           ; The second flag here depends on which portclass this is.
           require_flags: [ 'Valid', "P@3" ],
           bwfield : ["RM", "mbw"]
       },
      weight: {
          [ "Guard", ] => "Wge",
      }

<!-- Section A.8 --> <a id='SA.8'></a>

## Appendix H: Choosing good clusters of exit policies

With Walking Onions, we cannot easily support all the port
combinations [*] that we currently allow in the "policy summaries"
that we support in microdescriptors.

> [*] How many "short policy summaries" are there? The number would be
> 2^65535, except for the fact today's Tor doesn't permit exit policies to
> get maximally long.

In the Walking Onions whitepaper
(https://crysp.uwaterloo.ca/software/walkingonions/) we noted in
section 6 that we can group exit policies by class, and get down to
around 220 "classes" of port, such that each class was either
completely supported or completely unsupported by every relay.  But
that number is still impractically large: if we need ~11 bytes to
represent a SNIP index range, we would need an extra 2320 bytes per
SNIP, which seems like more overhead than we really want.

We can reduce the number of port classes further, at the cost of
some fidelity.  For example, suppose that the set {https,http} is
supported by relays {A,B,C,D}, and that the set {ssh,irc} is
supported by relays {B,C,D,E}.  We could combine them into a new
port class {https,http,ssh,irc}, supported by relays {B,C,D} -- at
the expense of no longer being able to say that relay A supported
{https,http}, or that relay E supported {ssh,irc}.

This loss would not necessarily be permanent: the operator of relay
A might be willing to add support for {ssh,irc}, and the operator of
relay E might be willing to add support for {https,http}, in order
to become useful as an exit again.

(We might also choose to add a configuration option for relays to
take their exit policies directly from the port classes in the
consensus.)

How might we select our port classes?  Three general categories of
approach seem possible: top-down, bottom-up, and hybrid.

In a top-down approach, we would collaborate with authority and exit
operators to identify _a priori_ reasonable classes of ports, such
as "Web", "Chat", "Miscellaneous internet", "SMTP", and "Everything
else".  Authorities would then base exit indices on these classes.

In a bottom-up approach, we would find an algorithm to run on the
current exit policies in order to find the "best" set of port
classes to capture the policies as they stand with minimal loss.
(Quantifying this loss is nontrivial: do we weight by bandwidth? Do
we weight every port equally, or do we call some more "important"
than others?)

> See exit-analysis for an example tool that runs a greedy algorithm
> to find a "good" partition using an unweighted,
> all-ports-are-equal cost function.  See the files
> "greedy-set-cov-{4,8,16}" for examples of port classes produced
> by this algorithm.

In a hybrid approach, we'd use top-down and bottom-up techniques
together. For example, we could start with an automated bottom-up
approach, and then evaluate it based feedback from operators.  Or we
could start with a handcrafted top-down approach, and then use
bottom-up cost metrics to look for ways to split or combine those
port classes in order to represent existing policies with better
fidelity.


<!-- Section A.9 --> <a id='SA.9'></a>

## Appendix I: Non-clique topologies with Walking Onions

For future work, we can expand the Walking Onions design to
accommodate network topologies where relays are divided into groups,
and not every group connects to every other.  To do so requires
additional design work, but here I'll provide what I hope will be a
workable sketch.

First, each SNIP needs to contain an ID saying which relay group it
belongs to, and an ID saying which relay group(s) may serve it.

When downloading an ENDIVE, each relay should report its own
identity, and receive an ENDIVE for that identity's group.  It
should contain both the identities of relays in the group, and the
SNIPs that should be served for different indices by members of that
group.

The easy part would be to add an optional group identity field to
SNIPs, defaulting to 0, indicating that the relay belongs to that
group, and an optional served-by field to each SNIP, indicating
groups that may serve the SNIP.  You'd only accept SNIPs if they
were served by a relay in a group that was allowed to serve them.

Would guards work?  Sure: we'd need to have guard SNIPS served by
middle relays.

For hsdirs, we'd need to have either multiple shards of the hsdir
ring (which seems like a bad idea?) or have all middle nodes able to
reach the hsdir ring.

Things would get tricky with making onion services work: if you need
to use an introduction point or a rendezvous point in group X, then
you need to get there from a relay that allows connections to group
X.  Does this imply indices meaning "Can reach group X" or
"two-degrees of group X"?

The question becomes: "how much work on alternative topologies does
it make sense to deploy in advance?"  It seems like there are
unknowns affecting both client and relay operations here, which
suggests that advance deployment for either case is premature: we
can't necessarily make either clients or relays "do the right thing"
in advance given what we now know of the right thing.

<!-- Section A.10 --> <a id='SA.10'></a>

## Appendix Z: acknowledgments

Thanks to Peter Palfrader for his original design in proposal 141,
and to the designers of PIR-Tor, both of which inspired aspects of
this Walking Onions design.

Thanks to Chelsea Komlo, Sajin Sasy, and Ian Goldberg for feedback on
an earlier version of this design.

Thanks to David Goulet, Teor, and George Kadianakis for commentary on
earlier versions of proposal 300.

Thanks to Chelsea Komlo and Ian Goldberg for their help fleshing out
so many ideas related to Walking Onions in their work on the design
paper.

Thanks to Teor for improvements to diff format, ideas about grouping
exit ports, and numerous ideas about getting topology and
distribution right.

These specifications were supported by a grant from the Zcash
Foundation.

