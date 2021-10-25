# Tor specifications

This repository holds the specifications that describe how Tor works.
They try to present Tor's protocols in sufficient detail to allow
the reader to implement a compatible implementation of Tor without ever
having to read the Tor source code.

The [proposals](/proposals) directory holds our design proposals.  These
include historical documents that have now been merged into.  For more
information on the proposal process, including an explanation of how to
make new proposals, see, see
[001-process.txt](/proposals/001-process.txt).

## What you can find here

Tor's specification is pretty big, and we've broken it into a bunch of
files.

* General interest
  * [tor-spec.txt](tor-spec.txt)
    contains the specification for the core Tor protocol
    itself; this is a good place to start reading.
  * [cert-spec.txt](cert-spec.txt) describes a certificate format used
    in the other parts of the protocol.
  * [dir-spec.txt](dir-spec.txt) specifies the operations and formats used to
    maintain a view of the network directory.
  * [padding-spec.txt](padding-spec.txt) describes a set of padding mechanisms
    used to impede traffic analysis.
  * [version-spec.txt](version-spec.txt) explains how to parse Tor
    version numbers.
  * [glossary.txt](glossary.txt) is a glossary of terms used
    in the other specifications.
* Client operations
  * [address-spec.txt](address-spec.txt) lists a set of special
    addresses that Tor handles differently from the regular DNS system.
  * [guard-spec.txt](guard-spec.txt) explains the "guard node" algorithm
    that Tor clients use to avoid sampling attacks.
  * [path-spec.txt](path-spec.txt) explains how clients choose their paths
    through the Tor network.
  * [socks-extensions](socks-extensions.txt) specifies Tor-specific
    extensions to the SOCKS protocol.
* Onion services
  * [rend-spec-v2.txt](rend-spec-v2.txt) is the old, deprecated version
    of the onion service protocol.
  * [rend-spec-v3.txt](rend-spec-v3.txt) is the current version of the
    onion service protocol.
* Censorship resistance
  * [bridgedb-spec.txt](bridgedb-spec.txt) explains how the `bridgedb`
    server gives out bridges to censored clients.
  * [gettor-spec.txt](gettor-spec.txt) describes the `gettor` tool,
    which is used to download Tor in censored areas.
  * [pt-spec.txt](pt-spec.txt) describes the protocol that Tor clients
    and relays  use to communicate with pluggable transports used for
    traffic obfuscation.
* Directory authorities
  * [bandwidth-file-spec.txt](bandwidth-file-spec.txt) specifies the
    file format used by bandwidth-measuring tools to report their
    observations to directory authorities.
  * [srv-spec.txt](src-spec.txt) specifies the protocol that
    directory authorities use to securely compute shared random values
    for the network.
* Controller protocol
  * [control-spec.txt](control-spec.txt) explains the protocol used by
    controllers to communicate with a running Tor process.
* Miscellaneous
  * [dir-list-spec.txt](dir-list-spec.txt) explains the format used by
    tools like the fallback directory scripts to output a list of
    Tor directories for inclusion in the Tor source code.
  * The [attic](attic) directory has obsolete or historical documents.
