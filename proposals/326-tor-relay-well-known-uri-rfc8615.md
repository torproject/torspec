```
Filename: 326-tor-relay-well-known-uri-rfc8615.md
Title: The "tor-relay" Well-Known Resource Identifier 
Author: nusenu
Created: 14 August 2020
Status: Open
```

# The "tor-relay" Well-Known Resource Identifier

This is a specification for a well-known [registry](https://www.iana.org/assignments/well-known-uris/) entry according to [RFC8615](https://tools.ietf.org/html/rfc8615).

This resource identifier can be used for serving and finding proofs related to [Tor](https://www.torproject.org/) relay and bridge contact information.
It can also be used for autodiscovery of Tor relays run by a given entity, if the entity's domain is known.
It solves the issue that Tor relay/bridge contact information is an unidirectional and unverified claim by nature.
This well-known URI aims to allow the verification of the unidirectional claim.
It aims to reduce the risk of impersonation attacks, where a Tor relay/bridge claims to be operated by a certain entity, but actually isn't.
The automated verification will also support the [visualization of relay/bridge groups](https://gitlab.torproject.org/tpo/metrics/relay-search/-/issues/40001).

* An initially (unverified) Tor relay or bridge contact information might claim to be related to an
organization by pointing to its website: Tor relay/bridge contact information field -> website
* The "tor-relay" URI allows for the verification of that claim by fetching the files containing Tor relay ID(s) or hashed bridge fingerprints
under the specified URI, because attackers can not easily place these files at the given location.

* By publishing Tor relay IDs or hashed bridge IDs under this URI the website operator claims to be the responsible entity for these Tor relays/bridges.
The verification of listed Tor relay/bridge IDs only succeeds if the claim can be verified bidirectionally 
(website -> relay/bridge and relay/bridge -> website).

* This URI is not related to Tor onion services.

* The URL MUST be HTTPS and use a valid TLS certificate from a generally trusted root CA. Plain HTTP MUST not be used.

* The URL MUST be accessible by robots (no CAPTCHAs).

## /.well-known/tor-relay/rsa-fingerprint.txt

* The file contains one or more Tor relay RSA SHA1 fingerprints operated by the entity in control of this website.
* Each line contains one relay fingerprint.
* The file MUST NOT contain fingerprints of Tor bridges (or hashes of bridge fingerprints). For bridges see the file `hashed-bridge-rsa-fingerprint.txt`.
* The file may contain comments (starting with #).
* Non-comment lines must be exactly 40 characters long and consist of the following characters [a-fA-F0-9].
* Fingerprints are not case-sensitive.
* Each fingerprint MUST appear at most once.
* The file MUST not be larger than one MByte.
* The content MUST be a media type of "text/plain".

Example file content:

```
# we operate these Tor relays
A234567890123456789012345678901234567ABC
B234567890123456789012345678901234567890
```
The RSA SHA1 relay fingerprint can be found in the file named "fingerprint" located in the Tor data directory on the relay.

## /.well-known/tor-relay/ed25519-master-pubkey.txt

* The file contains one or more ed25519 Tor relay public master keys of relays operated by the entity in control of this website.
* This file is not relevant for bridges.
* Each line contains one public ed25519 master key in its base64 encoded form.
* The file may contain comments (starting with #).
* Non-comment lines must be exactly 43 characters long and consist of the following characters [a-zA-z0-9/+].
* Each key MUST appear at most once.
* The file MUST not be larger than one MByte.
* The content MUST be a media type of "text/plain".

Example file content:

```
# we operate these Tor relays
yp0fwtp4aa/VMyZJGz8vN7Km3zYet1YBZwqZEk1CwHI
kXdA5dmIhXblAquMx0M0ApWJJ4JGQGLsjUSn86cbIaU
bHzOT41w56KHh+w6TYwUhN4KrGwPWQWJX04/+tw/+RU
```

The base64 encoded ed25519 public master key can be found in the file named "fingerprint-ed25519" located in the Tor data directory on the relay.

## /.well-known/tor-relay/hashed-bridge-rsa-fingerprint.txt

* The file contains one or more SHA1 hashed Tor bridge SHA1 fingerprints operated by the entity in control of this website.
* Each line contains one hashed bridge fingerprint.
* The file may contain comments (starting with #).
* Non-comment lines must be exactly 40 characters long and consist of the following characters [a-fA-F0-9].
* Hashed fingerprints are not case-sensitive.
* Each hashed fingerprint MUST appear at most once.
* The file MUST not be larger than one MByte.
* The file MUST NOT contain fingerprints of Tor relays.
* The content MUST be a media type of "text/plain".

Example file content:

```
# we operate these Tor bridges
1234567890123456789012345678901234567ABC
4234567890123456789012345678901234567890
```

The hashed Tor bridge fingerprint can be found in the file named "hashed-fingerprint" located in the Tor data directory on the bridge.

# Change Controller

Tor Project Development Mailing List <tor-dev@lists.torproject.org>

# Related Information

* [https://gitweb.torproject.org/torspec.git/tree/tor-spec.txt](https://gitweb.torproject.org/torspec.git/tree/tor-spec.txt)
* [https://gitweb.torproject.org/torspec.git/tree/cert-spec.txt](https://gitweb.torproject.org/torspec.git/tree/cert-spec.txt)
* [https://nusenu.github.io/ContactInfo-Information-Sharing-Specification](https://nusenu.github.io/ContactInfo-Information-Sharing-Specification)
* [RFC8615](https://tools.ietf.org/html/rfc8615)






