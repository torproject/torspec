```
Filename: 332-ntor-v3-with-extra-data.md
Title: Ntor protocol with extra data, version 3.
Author: Nick Mathewson
Created: 12 July 2021
Status: Accepted
```

# Overview

The ntor handshake is our current protocol for circuit
establishment.

So far we have two variants of the ntor handshake in use: the "ntor
v1" that we use for everyday circuit extension (see `tor-spec.txt`)
and the "hs-ntor" that we use for v3 onion service handshake (see
`rend-spec-v3.txt`).  This document defines a third version of ntor,
adapting the improvements from hs-ntor for use in regular circuit
establishment.

These improvements include:

 * Support for sending additional encrypted and authenticated
   protocol-setup handshake data as part of the ntor handshake.  (The
   information sent from the client to the relay does not receive
   forward secrecy.)

 * Support for using an external shared secret that both parties must
   know in order to complete the handshake.  (In the HS handshake, this
   is the subcredential.  We don't use it for circuit extension, but in
   theory we could.)

 * Providing a single specification that can, in the future, be used
   both for circuit extension _and_ HS introduction.

# The improved protocol: an abstract view

Given a client "C" that wants to construct a circuit to a
relay "S":

The client knows:
  * B: a public "onion key" for S
  * ID: an identity for S, represented as a fixed-length
    byte string.
  * CM: a message that it wants to send to S as part of the
    handshake.
  * An optional "verification" string.

The relay knows:
  * A set of [(b,B)...] "onion key" keypairs.  One of them is
    "current", the others are outdated, but still valid.
  * ID: Its own identity.
  * A function for computing a server message SM, based on a given
    client message.
  * An optional "verification" string. This must match the "verification"
    string from the client.

Both parties have a strong source of randomness.

Given this information, the client computes a "client handshake"
and sends it to the relay.

The relay then uses its information plus the client handshake to see
if the incoming message is valid; if it is, then it computes a
"server handshake" to send in reply.

The client processes the server handshake, and either succeeds or fails.

At this point, the client and the relay both have access to:
  * CM (the message the client sent)
  * SM (the message the relay sent)
  * KS (a shared byte stream of arbitrary length, used to compute
    keys to be used elsewhere in the protocol).

Additionally, the client knows that CM was sent _only_ to the relay
whose public onion key is B, and that KS is shared _only_ with that
relay.

The relay does not know which client participated in the handshake,
but it does know that CM came from the same client that generated
the key X, and that SM and KS were shared _only_ with that client.

Both parties know that CM, SM, and KS were shared correctly, or not
at all.

Both parties know that they used the same verification string; if
they did not, they do not learn what the verification string was.
(This feature is required for HS handshakes.)

# The handshake in detail

## Notation

We use the following notation:

  * `|` -- concatenation
  * `"..."` -- a byte string, with no terminating NUL.
  * `ENCAP(s)` -- an encapsulation function.  We define this
     as `htonll(len(s)) | s`.  (Note that `len(ENCAP(s)) = len(s) + 8`).
  * `PARTITION(s, n1, n2, n3, ...)` -- a function that partitions a
     bytestring `s` into chunks of length `n1`, `n2`, `n3`, and so
     on. Extra data is put into a final chunk.  If `s` is not long
     enough, the function fails.

We require the following crypto operations:

  * `KDF(s,t)` -- a tweakable key derivation function, returning a
     keystream of arbitrary length.
  * `H(s,t)` -- a tweakable hash function of output length
     `DIGEST_LEN`.
  * `MAC(k, msg, t)` -- a tweakable message-authentication-code function,
     with key length `MAC_KEY_LEN` and output length `MAC_LEN`.
  * `EXP(pk,sk)` -- our Diffie Hellman group operation, taking a
     public key of length `PUB_KEY_LEN`.
  * `KEYGEN()` -- our Diffie-Hellman keypair generation algorithm,
    returning a (secret-key,public-key) pair.
  * `ENC(k, m)` -- a stream cipher with key of length `ENC_KEY_LEN`.
    `DEC(k, m)` is its inverse.

Parameters:

  * `PROTOID` -- a short protocol identifier
  * `t_*` -- a set of "tweak" strings, used to derive distinct
    hashes from a single hash function.
  * `ID_LEN` -- the length of an identity key that uniquely identifies
    a relay.

Given our cryptographic operations and a set of tweak strings, we
define:

```
H_foo(s) = H(s, t_foo)
MAC_foo(k, msg) = MAC(k, msg, t_foo)
KDF_foo(s) = KDF(s, t_foo)
```

See Appendix A.1 below for a set of instantiations for these operations
and constants.

## Client operation, phase 1

The client knows:
    B, ID -- the onion key and ID of the relay it wants to use.
    CM -- the message that it wants to send as part of its
           handshake.
    VER -- a verification string.

First, the client generates a single-use keypair:

    x,X = KEYGEN()

and computes:

    Bx = EXP(B,x)
    secret_input_phase1 = Bx | ID | X | B | PROTOID | ENCAP(VER)
    phase1_keys = KDF_msgkdf(secret_input_phase1)
    (ENC_K1, MAC_K1) = PARTITION(phase1_keys, ENC_KEY_LEN, MAC_KEY_LEN)

    encrypted_msg = ENC(ENC_K1, CM)
    msg_mac = MAC_msgmac(MAC_K1, ID | B | X | encrypted_msg)

and sends:

    NODEID      ID               [ID_LEN bytes]
    KEYID       B                [PUB_KEY_LEN bytes]
    CLIENT_PK   X                [PUB_KEY_LEN bytes]
    MSG         encrypted_msg    [len(CM) bytes]
    MAC         msg_mac          [last MAC_LEN bytes of message]

The client remembers x, X, B, ID, Bx, and msg_mac.

## Server operation

The relay checks whether NODEID is as expected, and looks up
the (b,B) keypair corresponding to KEYID.  If the keypair is
missing or the NODEID is wrong, the handshake fails.

Now the relay uses `X=CLIENT_PK` to compute:

    Xb = EXP(X,b)
    secret_input_phase1 = Xb | ID | X | B | PROTOID | ENCAP(VER)
    phase1_keys = KDF_msgkdf(secret_input_phase1)
    (ENC_K1, MAC_K1) = PARTITION(phase1_keys, ENC_KEY_LEN, MAC_KEY_LEN)

    expected_mac = MAC_msgmac(MAC_K1, ID | B | X | MSG)

If `expected_mac` is not `MAC`, the handshake fails.  Otherwise
the relay computes `CM` as:

    CM = DEC(MSG, ENC_K1)

The relay then checks whether `CM` is well-formed, and in response
composes `SM`, the reply that it wants to send as part of the
handshake. It then generates a new ephemeral keypair:

    y,Y = KEYGEN()

and computes the rest of the handshake:

    Xy = EXP(X,y)
    secret_input = Xy | Xb | ID | B | X | Y | PROTOID | ENCAP(VER)
    ntor_key_seed = H_key_seed(secret_input)
    verify = H_verify(secret_input)

    RAW_KEYSTREAM = KDF_final(ntor_key_seed)
    (ENC_KEY, KEYSTREAM) = PARTITION(RAW_KEYSTREAM, ENC_KEY_LKEN, ...)

    encrypted_msg = ENC(ENC_KEY, SM)

    auth_input = verify | ID | B | Y | X | MAC | ENCAP(encrypted_msg) |
        PROTOID | "Server"
    AUTH = H_auth(auth_input)

The relay then sends:

    Y          Y              [PUB_KEY_LEN bytes]
    AUTH       AUTH           [DIGEST_LEN bytes]
    MSG        encrypted_msg  [len(SM) bytes, up to end of the message]

The relay uses KEYSTREAM to generate the shared secrets for the
newly created circuit.

## Client operation, phase 2

The client computes:

    Yx = EXP(Y, x)
    secret_input = Yx | Bx | ID | B | X | Y | PROTOID | ENCAP(VER)
    ntor_key_seed = H_key_seed(secret_input)
    verify = H_verify(secret_input)

    auth_input = verify | ID | B | Y | X | MAC | ENCAP(MSG) |
        PROTOID | "Server"
    AUTH_expected = H_auth(auth_input)

If AUTH_expected is equal to AUTH, then the handshake has
succeeded.  The client can then calculate:

    RAW_KEYSTREAM = KDF_final(ntor_key_seed)
    (ENC_KEY, KEYSTREAM) = PARTITION(RAW_KEYSTREAM, ENC_KEY_LKEN, ...)

    SM = DEC(ENC_KEY, MSG)

SM is the message from the relay, and the client uses KEYSTREAM to
generate the shared secrets for the newly created circuit.

# Security notes

Whenever comparing bytestrings, implementations SHOULD use
constant-time comparison function to avoid side-channel attacks.

To avoid small-subgroup attacks against the Diffie-Hellman function,
implementations SHOULD either:

   * Make sure that all incoming group members are in fact in the DH
     group.
   * Validate all outputs from the EXP function to make sure that
     they are not degenerate.


# Notes on usage

We don't specify what should actually be done with the resulting
keystreams; that depends on the usage for which this handshake is
employed.  Typically, they'll be divided up into a series of tags
and symmetric keys.

The keystreams generated here are (conceptually) unlimited.  In
practice, the usage will determine the amount of key material
actually needed: that's the amount that clients and relays will
actually generate.

The PROTOID parameter should be changed not only if the
cryptographic operations change here, but also if the usage changes
at all, or if the meaning of any parameters changes.  (For example,
if the encoding of CM and SM changed, or if ID were a different
length or represented a different type of key, then we should start
using a new PROTOID.)


# A.1 Instantiation

Here are a set of functions based on SHA3, SHAKE-256, Curve25519, and
AES256:

```
H(s, t) = SHA3_256(ENCAP(t) | s)
MAC(k, msg, t) = SHA3_256(ENCAP(t) | ENCAP(k) | s)
KDF(s, t) = SHAKE_256(ENCAP(t) | s)
ENC(k, m) = AES_256_CTR(k, m)

EXP(pk,sk), KEYGEN: defined as in curve25519

DIGEST_LEN = MAC_LEN = MAC_KEY_LEN = ENC_KEY_LEN = PUB_KEY_LEN = 32

ID_LEN = 32  (representing an ed25519 identity key)
```

Notes on selected operations: SHA3 can be pretty slow, and AES256 is
likely overkill.  I'm choosing them anyway because they are what we
use in hs-ntor, and in my preliminary experiments they don't account
for even 1% of the time spent on this handshake.

```
t_msgkdf = PROTOID | ":kdf_phase1"
t_msgmac = PROTOID | ":msg_mac"
t_key_seed = PROTOID | ":key_seed"
t_verify = PROTOID | ":verify"
t_final = PROTOID | ":kdf_final"
t_auth = PROTOID | ":auth_final"
```

# A.2 Encoding for use with Tor circuit extension

Here we give a concrete instantiation of ntor-v3 for use with
circuit extension in Tor, and the parameters in A.1 above.

If in use, this is a new CREATE2 type.  Clients should not use it
unless the relay advertises support by including an appropriate
version of the `Relay=X` subprotocol in its protocols list.

When the encoding and methods of this section, along with the
instantiations from the previous section, are in use, we specify:

    PROTOID = "ntor3-curve25519-sha3_256-1"

The key material is extracted as follows, unless modified by the
handshake (see below).  See tor-spec.txt for more info on the
specific values:

    Df    Digest authentication, forwards  [20 bytes]
    Db    Digest authentication, backwards [20 bytes]
    Kf    Encryption key, forwards         [16 bytes]
    Kb    Encryption key, backwards        [16 bytes]
    KH    Onion service nonce              [20 bytes]

We use the following meta-encoding for the contents of client and
server messages.

    [Any number of times]:
    EXTENSION
       EXT_FIELD_TYPE     [one byte]
       EXT_FIELD_LEN      [one byte]
       EXT_FIELD          [EXT_FIELD_LEN bytes]

(`EXT_FIELD_LEN` may be zero, in which case EXT_FIELD is absent.)

All parties MUST reject messages that are not well-formed per the
rules above.

We do not specify specific TYPE semantics here; we leave those for
other proposals and specifications.

Parties MUST ignore extensions with `EXT_FIELD_TYPE` bodies they do not
recognize.

Unless otherwise specified in the documentation for an extension type:
* Each extension type SHOULD be sent only once in a message.
* Parties MUST ignore any occurrences all occurrences of an extension
  with a given type after the first such occurrence.
* Extensions SHOULD be sent in numerically ascending order by type.

(The above extension sorting and multiplicity rules are only defaults;
they may be overridden in the description of individual extensions.)

# A.3 How much space is available?

We start with a 498-byte payload in each relay cell.

The header of the EXTEND2 cell, including link specifiers and other
headers, comes to 89 bytes.

The client handshake requires 128 bytes (excluding CM).

That leaves 281 bytes, "which should be plenty".

# X.1 Negotiating proposal-324 circuit windows

(We should move this section into prop324 when this proposal is
finished.)

We define a type value, CIRCWINDOW_INC.

We define a triplet of consensus parameters: `circwindow_inc_min`,
`cincwindow_inc_max`, and `circwindow_inc_dflt`.  These all have
range (1,65535).

When the authority operators want to experiment with different
values for `circwindow_inc_dflt`, they set `circwindow_inc_min` and
`circwindow_inc_max` to the range in which they want to experiment,
making sure that the existing `circwindow_inc_dflt` is within that
range.

vWhen a client sees that a relay supports the ntor3 handshake type
(subprotocol `Relay=X`), and also supports the flow control
algorithms of proposal 324 (subprotocol `FlowCtrl=X`), then the
client sends a message, with type `CIRCWINDOW_INC`, containing a
two-byte integer equal to `circwindow_inc_dflt`.

The relay rejects the message if the value given is outside of the
[`circwindow_inc_min`, `circwindow_inc_max`] range.  Otherwise, it
accepts it, and replies with the same message that the client sent.

# X.2: Test vectors

The following test values, in hex, were generated by a Python reference
implementation.

Inputs:

b = "4051daa5921cfa2a1c27b08451324919538e79e788a81b38cbed097a5dff454a"
B = "f8307a2bc1870b00b828bb74dbb8fd88e632a6375ab3bcd1ae706aaa8b6cdd1d"
ID = "9fad2af287ef942632833d21f946c6260c33fae6172b60006e86e4a6911753a2"
x = "b825a3719147bcbe5fb1d0b0fcb9c09e51948048e2e3283d2ab7b45b5ef38b49"
X = "252fe9ae91264c91d4ecb8501f79d0387e34ad8ca0f7c995184f7d11d5da4f46"
CM = "68656c6c6f20776f726c64"
VER = "78797a7a79"
y = "4865a5b7689dafd978f529291c7171bc159be076b92186405d13220b80e2a053"
Y = "4bf4814326fdab45ad5184f5518bd7fae25dc59374062698201a50a22954246d"
SM = "486f6c61204d756e646f"

Intermediate values:

ENC_K1 = "4cd166e93f1c60a29f8fb9ec40ea0fc878930c27800594593e1c4d0f3b5fbd02"
MAC_K1 = "f5b69e85fdd26e1b0bdbbc8128e32d8123040255f11f744af3cc98fc13613cda"
msg_mac = "9e044d53565f04d82bbb3bebed3d06cea65db8be9c72b68cd461942088502f67"
key_seed = "b9a092741098e1f5b8ab37ce74399dd57522c974d7ae4626283a1077b9273255"
verify = "1dc09fb249738a79f1bc3a545eee8c415f27213894a760bb4df58862e414799a"
ENC_KEY (server) = "cab8a93eef62246a83536c4384f331ec26061b66098c61421b6cae81f4f57c56"
AUTH = "2fc5f8773ca824542bc6cf6f57c7c29bbf4e5476461ab130c5b18ab0a9127665"

Messages:

client_handshake = "9fad2af287ef942632833d21f946c6260c33fae6172b60006e86e4a6911753a2f8307a2bc1870b00b828bb74dbb8fd88e632a6375ab3bcd1ae706aaa8b6cdd1d252fe9ae91264c91d4ecb8501f79d0387e34ad8ca0f7c995184f7d11d5da4f463bebd9151fd3b47c180abc9e044d53565f04d82bbb3bebed3d06cea65db8be9c72b68cd461942088502f67"

server_handshake = "4bf4814326fdab45ad5184f5518bd7fae25dc59374062698201a50a22954246d2fc5f8773ca824542bc6cf6f57c7c29bbf4e5476461ab130c5b18ab0a91276651202c3e1e87c0d32054c"

First 256 bytes of keystream:

KEYSTREAM = "9c19b631fd94ed86a817e01f6c80b0743a43f5faebd39cfaa8b00fa8bcc65c3bfeaa403d91acbd68a821bf6ee8504602b094a254392a07737d5662768c7a9fb1b2814bb34780eaee6e867c773e28c212ead563e98a1cd5d5b4576f5ee61c59bde025ff2851bb19b721421694f263818e3531e43a9e4e3e2c661e2ad547d8984caa28ebecd3e4525452299be26b9185a20a90ce1eac20a91f2832d731b54502b09749b5a2a2949292f8cfcbeffb790c7790ed935a9d251e7e336148ea83b063a5618fcff674a44581585fd22077ca0e52c59a24347a38d1a1ceebddbf238541f226b8f88d0fb9c07a1bcd2ea764bbbb5dacdaf5312a14c0b9e4f06309b0333b4a"
