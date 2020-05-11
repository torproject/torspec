```
Filename: 320-tap-out-again.md
Title: Removing TAP usage from v2 onion services
Author: Nick Mathewson
Created: 11 May 2020
Status: Open
```

(This proposal is part of the Walking Onions spec project.  It updates
proposal 245.)

# Removing TAP from v2 onion services

Though v2 onion services akre obsolescent and their cryptographic
parameters are disturbing, we do not want to drop support for them
as part of the Walking Onions migration.  If we did so, then we
would force some users to choose between Walking Onions and v2 onion
services, which we do not want to do.

Instead, we describe here a phased plan to replace TAP in v2 onion
services with ntor.  This change improves the forward secrecy of
_some_ of the session keys used with v2 onion services, but does not
improve their authentication, which is strongly tied to truncated
SHA1 hashes of RSA1024 keys.

Implementing this change is more complex than similar changes
elsewhere in the Tor protocol, since we do not want clients or
services to leak whether they have support for this proposal, until
support is widespread enough that revealing it is no longer a
privacy risk.

## Ntor keys, link specifiers, and SNIPs in v2 descriptors.

We define these entries that may appear in v2 onion service
descriptors, once per introduction point.

    "identity-ed25519"
    "ntor-onion-key"

       [at most once each per intro point.]

       These values are in the same format as and follow the same
       rules as their equivalents in router descriptors.

    "link-specifiers"

       [at most once per introduction point]

       This value is the same as the link specifiers in a v3 onion
       service descriptor, and follows the same rules.

Services should not include any of these fields unless a new network
parameter, "hsv2-intro-updated" is set to 1. Clients should not parse
these fields or use them unless "hsv2-use-intro-updated" is set to 1.

We define a new field that can be used for hsv2 descriptors with
walking onions:

    "snip"
        [at most once]

        This value is the same as the snip field introduced to a v3
        onion service descriptor by proposal XXX, and follows the
        same rules.

Services should not include this field unless a new network parameter,
"hsv2-intro-snip" is set to 1. Clients should not parse this field or use it
unless the parameter "hsv2-use-intro-snip" is set to 1.

Additionally, relays SHOULD omit the following legacy intro point
parameters when a new network parameter, "hsv2-intro-legacy" is set
to 0: "ip-address", "onion-port", and "onion-key". Clients should
treat them as optional when "hsv2-tolerate-no-legacy" is set to 1.

## INTRODUCE cells, RENDEZVOUS cells, and ntor.

We allow clients to specify the rendezvous point's ntor key in the
INTRODUCE2 cell instead of the TAP key.  To do this, the client
simply sets KLEN to 32, and includes the ntor key for the relay.

Clients should only use ntor keys in this way if the network parameter
"hsv2-client-rend-ntor" is set to 1, and if the entry "allow-rend-ntor"
is present in the onion service descriptr.

Services should only advertise "allow-rend-ntor" in this way if the
network parameter "hsv2-service-rend-ntor" is set to 1.

## Migration steps

First, we implement all of the above, but set it to be disabled by
default.  We use torrc fields to selectively enable them for testing
purposes, to make sure they work.

Once all non-LTS versions of Tor without support for this proposal are
obsolete, we can safely enable "hsv2-client-rend-ntor",
"hsv2-service-rend-ntor", "hsv2-intro-updated", and
"hsv2-use-intro-updated".

Once all non-LTS versions of Tor without support for walking onions
are obsolete, we can safely enable "hsv2-intro-snip",
"hsv2-use-intro-snip", and "hsv2-tolerate-no-legacy".

Once all non-LTS versions of Tor without support for _both_ of the
above implementations are finally obsolete, we can finally set
"hsv2-intro-legacy" to 0.

## Future work

There is a final TAP-like protocol used for v2 hidden services: the
client uses RSA1024 and DH1024 to send information about the
rendezvous point and to start negotiating the session key to be used
for end-to-end encryption.

In theory we could get a benefit to forward secrecy by using ntor
instead of TAP here, but we would get not corresponding benefit for
authentication, since authentication is still ultimately tied to
HSv2's scary RSA1024-plus-truncated-SHA1 combination.

Given that, it might be just as good to allow the client to insert
a curve25519 key in place of their DH1024 key, and use that for the
DH handshake instead.  That would be a separate proposal, though:
this proposal is enough to allow all relays to drop TAP support.
