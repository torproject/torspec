```
Filename: 321-happy-families.md
Title: Better performance and usability for the MyFamily option (v2)
Author: Nick Mathewson
Created: 27 May 2020
Status: Accepted
```

## Problem statement.

The current family mechanism allows well-behaved relays to
identify that they all belong to the same 'family', and should
not be used in the same circuits.

Right now, families work by having every family member list every
other family member in its server descriptor.  This winds up using
O(n^2) space in microdescriptors and server descriptors. (For RAM,
we can de-duplicate families which sometimes helps.)  Adding or
removing a server from the family requires all the other servers to
change their torrc settings.

This growth in size is not just a theoretical problem. Family
declarations currently make up a little over 55% of the
microdescriptors in the directory--around 24% after compression.
The largest family has around 270 members.  With Walking Onions, 270
members times a 160-bit hashed identifier leads to over 5 kilobytes
per SNIP, which is much greater than we'd want to use.

This is an updated version of proposal 242.  It differs by clarifying
requirements and providing a more detailed migration plan.

## Design overview.

In this design, every family has a master ed25519 "family key".  A node
is in the family iff its server descriptor includes a certificate of its
ed25519 identity key with the family key.  The certificate
format is the one in the tor-certs.txt spec; we would allocate a new
certificate type for this usage.  These certificates would need to
include the signing key in the appropriate extension.

Note that because server descriptors are signed with the node's
ed25519 signing key, this creates a bidirectional relationship
between the two keys, so that nodes can't be put in families without
their consent.

## Changes to router descriptors

We add a new entry to server descriptors:

    "family-cert" NL
    "-----BEGIN FAMILY CERT-----" NL
    cert
    "-----END FAMILY CERT-----".

This entry contains a base64-encoded certificate as described
above.  It may appear any number of times; authorities MAY reject
descriptors that include it more than three times.

## Changes to microdescriptors

We add a new entry to microdescriptors: `family-keys`.

This line contains one or more space-separated strings describing
families to which the node belongs.  These strings MUST be sorted in
lexicographic order.  These strings MAY be base64-formated nonpadded
ed25519 family keys, or may represent some future encoding.

Clients SHOULD accept unrecognized key formats.

## Changes to voting algorithm

We allocate a new consensus method number for voting on these keys.

When generating microdescriptors using a suitable consensus method,
the authorities include a "family-keys" line if the underlying
server descriptor contains any valid family-cert lines.  For each
valid family-cert in the server descriptor, they add a
base-64-encoded string of that family-cert's signing key.

> See also "deriving family lines from family-keys?" below for an
> interesting but more difficult extension mechanism that I would
> not recommend.

## Relay configuration

There are several ways that we could configure relays to let them
include family certificates in their descriptors.

The easiest would be putting the private family key on each relay,
so that the relays could generate their own certificates.  This is
easy to configure, but slightly risky: if the private key is
compromised on any relay, anybody can claim membership in the
family.  That isn't so very bad, however -- all the relays would
need to do in this event would be to move to a new private family
key.

A more orthodox method would be to keep the private key somewhere
offline, and use it to generate a certificate for each relay in
the family as needed.  These certificates should be made with
long-enough lifetimes, and relays should warn when they are going to
expire soon.

## Changes to relay behavior

Each relay should track which other relays they have seen using the
same family-key as itself.  When generating a router descriptor,
each relay should list all of these relays on the legacy 'family'
line.  This keeps the "family" lines up-to-date with "family-keys"
lines for compliant relays.

Relays should continue listing relays in their family lines if they
have seen a relay with that identity using the same family-key at
any time in the last 7 days.

The presence of this line should be configured by a network
parameter, `derive-family-line`.

Relays whose family lines do not stay at least mostly in sync with
their family keys should be marked invalid by the authorities.

## Client behavior

Clients should treat node A and node B as belonging to the same
family if ANY of these is true:

* The client has descriptors for A and B, and A's descriptor lists B
  in its family line, and B's descriptor lists A in its family line.

* Client A has descriptors for A and B, and they both contain the
  same entry in their family-keys or family-cert.  (Note that a
  family-cert key may match a base64-encoded entry in the family-keys
  entry.)

## Migration

For some time, existing relays and clients will not support family
certificates.  Because of this, we try to make sure above the
well-behaved relays will list the same entries in both places.

Once enough clients have migrated to using family
certificates, authorities SHOULD disable `derive-family-line`.

## Security

Listing families remains as voluntary in this design as in today's
Tor, though bad-relay hunters can continue to look for families that
have not adopted a family key.

A hostile relay family could list a "family" line that did not match
its "family-certs" values.  However, the only reason to do so would
be in order to launch a client partitioning attack, which is
probably less valuable than the kinds of attacks that they could run
by simply not listing families at all.

## Appendix: deriving family lines from family-keys?

As an alternative, we might declare that _authorities_ should keep
family lines in sync with family-certs.  Here is a design sketch of
how we might do that, but I don't think it's actually a good idea,
since it would require major changes to the data flow of the
voting system.

In this design, authorties would include a "family-keys" line in
each router section in their votes corresponding to a relay with any
family-cert.  When generating final microdescriptors using this
method, the authorities would use these lines to add entries to the
microdescriptors' family lines:

1. For every relay appearing in a routerstatus's family-keys, the
   relays calculate a consensus family-keys value by listing including
   all those keys that are listed by a majority of those voters listing
   the same router with the same descriptor.  (This is the algorithm we
   use for voting on other values derived from the descriptor.)

2. The authorities then compute a set of "expanded families": one
   for each family key.  Each "expanded family" is a set containing
   every router in the consensus associated with that key in its consensus
   family-keys value.

3. The authorities discard all "expanded families" of size 1 or
   smaller.

4. Every router listed for the "expanded family" has every other
   router added to the "family" line in its microdescriptor.  (The
   "family" line is then re-canonicalized according to the rules of
   proposal 298 to remove its )

5. Note that the final microdescriptor consensus will include the
   digest of the derived microdescriptor in step 4, rather than the
   digest of the microdescriptor listed in the original votes.  (This
   calculation is deterministic.)

The problem with this approach is that authorities would have to
fetch microdescriptors they do not have in order to replace their
family lines.  Currently, voting never requires an authority to
fetch a microdescriptor from another authority.  If we implement
vote compression and diffs as in the Walking Onions proposal,
however, we might suppose that votes could include microdescriptors
directly.

Still, this is likely more complexity than we want for a transition
mechanism.

## Appendix: Deriving family-keys from families??

We might also imagine that authorities could infer which families
exist from the graph of family relationships, and then include
synthetic "family-keys" entries for routers that belong to the same
family.

This has two challenges: first, to compute these synthetic family
keys, the authorities would need to have the same graph of family
relationships to begin with, which once again would require them to
include the complete list of families in their votes.

Secondly, finding all the families is equivalent to finding all
maximal cliques in a graph.  This problem is NP-hard in its general
case.  Although polynomial solutions exist for nice well-behaved
graphs, we'd still need to worry about hostile relays including
strange family relationships in order to drive the algorithm into
its exponential cases.

## Appendix: New assigned values

We need a new assigned value for the certificate type used for
family signing keys.

We need a new consensus method for placing family-keys lines in
microdescriptors.

## Appendix: New network parameters

* `derive-family-line`: If 1, relays should derive family lines from
  observed family-keys.  If 0, they do not. Min: 0, Max: 1. Default: 1.

