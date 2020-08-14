```
Filename: xxx-tor-relay-well-known-uri-rfc8615.md
Title: The "tor-relay" Well-Known Resource Identifier 
Author: nusenu
Created: 14 August 2020
Status: Open
```

This is a specification for a well-known registry submission according to [RFC8615](https://tools.ietf.org/html/rfc8615)

# The "tor-relay" Well-Known Resource Identifier

This resource identifier is used for the the verification of [Tor](https://www.torproject.org/) relay contact information 
(more specifically the [operatorurl](https://nusenu.github.io/ContactInfo-Information-Sharing-Specification/#operatorurl)).
It can also be used for autodiscovery of Tor relays run by a given entity, if the entity domain is known.
It solves the issue that Tor relay contact information is an unidirectional and unverified claim by nature.
This well-known URI aims to allow the verification of the unidirectional claim.
It aims to reduce the risk of impersonation attacks, where a Tor relay claims to be operated by a certain entity, but actually isn't.
The automated verification will also support the [visualization of relay groups](https://gitlab.torproject.org/tpo/metrics/relay-search/-/issues/40001).

* An initially (unverified) Tor relay contact information might claim to be related to an
organization by pointing to its website: Tor relay contact information field -> website
* The "tor-relay" URI allows for the verification of that claim by fetching the files containing Tor relay ID(s) under the specified URI, 
because attackers can not easily place these files at the given location.

* By publishing Tor relay IDs under this URI the website operator claims to operate these relays.
The verification of listed Tor relay IDs only succeeds if the claim can be verified bidirectionally (website -> relay and relay -> website).

* This URI is not related to Tor bridges or Tor onion services.

* The URL MUST be HTTPS and use a valid TLS certificate from a generally trusted root CA. Plain HTTP MUST not be used.

* The URL MUST be accessible by robots (no CAPTCHAs).

## /.well-known/tor-relay/rsa-fingerprint.txt

* The file contains one or more Tor relay RSA SHA1 fingerprints operated by the entity in control of this website.
* Each line contains one fingerprint.
* The file may contain comments (starting with #).
* Non-comment lines must be exactly 40 characters long and consist of the following characters [a-fA-F0-9].
* Fingerprints are not case-sensitive.
* Each fingerprint MUST appear at most once.
* The file MUST not be larger than one MByte.
* The file MUST NOT contain fingerprints of Tor bridges (or hashes of bridge fingerprints).
* The content MUST be a media type of "text/plain".

Example file content:

```
# we operate these Tor relays
A234567890123456789012345678901234567ABC
B234567890123456789012345678901234567890
```
The RSA SHA1 relay fingerprint can be found in the file named "fingerprint" located in the Tor data directory on the relay.


# Change Controller

tor-dev AT lists.torproject.org

# Related Information

* [https://gitweb.torproject.org/torspec.git/tree/tor-spec.txt](https://gitweb.torproject.org/torspec.git/tree/tor-spec.txt)
* [https://gitweb.torproject.org/torspec.git/tree/cert-spec.txt](https://gitweb.torproject.org/torspec.git/tree/cert-spec.txt)
* [https://nusenu.github.io/ContactInfo-Information-Sharing-Specification/#operatorurl](https://nusenu.github.io/ContactInfo-Information-Sharing-Specification/#operatorurl)
* [RFC8615](https://tools.ietf.org/html/rfc8615)






