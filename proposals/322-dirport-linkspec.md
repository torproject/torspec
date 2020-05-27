```
Filename: 322-dirport-linkspec.md
Title: Extending link specifiers to include the directory port
Author: Nick Mathewson
Created: 27 May 2020
Status: Open
```

## Motivation

Directory ports remain the only way to contact a (non-bridge) Tor
relay that isn't expressible as a Link Specifier.  We haven't
specified a link specifier of this kind so far, since it isn't a way
to contact a relay to create a channel.

But authorities still expose directory ports, and encourage relays
to use them preferentially for uploading and downloading.  And with
Walking Onions, it would be convenient to try to make every kind of
"address" a link specifier -- we'd like want authorities to be able
to specify a list of link specifiers that can be used to contact
them for uploads and downloads.

> It is possible that after revision, Walking Onions won't need a way
> to specify this information.  If so, this proposal should be moved
> to "Reserve" status as generally unuseful.

## Proposal

We reserve a new link specifier type "dir-url", for use with the
directory system.  This is a variable-length link specifier, containing
a URL prefix.  The only currently supported URL schema is "http://".
Implementations SHOULD ignore unrecognized schemas.  IPv4 and IPv6
addresses MAY be used directory; hostnames are also allowed.
Implementations MAY ignore hostnames and only use raw addresses.

The URL prefix includes everything through the string "tor" in the
directory hierarchy.

A dir-url link specifier SHOULD NOT appear in an EXTEND cell;
implementations SHOULD reject them if they do appear.

