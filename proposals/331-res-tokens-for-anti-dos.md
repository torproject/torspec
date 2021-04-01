```
Filename: 331-res-tokens-for-anti-dos.md
Title: Res tokens: Anonymous Credentials for Onion Service DoS Resilience
Author: George Kadianakis, Mike Perry
Created: 11-02-2021
Status: Draft
```

                  +--------------+           +------------------+
                  | Token Issuer |           | Onion Service    |
                  +--------------+           +------------------+
                         ^                            ^
                         |        +----------+        |
                Issuance |  1.    |          |   2.   | Redemption
                         +------->|  Alice   |<-------+
                                  |          |
                                  +----------+


# 0. Introduction

  This proposal specifies a simple anonymous credential scheme based on Blind
  RSA signatures designed to fight DoS abuse against onion services. We call
  the scheme "Res tokens".

  Res tokens are issued by third-party issuance services, and are verified by
  onion services during the introduction protocol (through the INTRODUCE1
  cell).

  While Res tokens are used for denial of service protection in this proposal,
  we demonstrate how they can have application in other Tor areas as well, like
  improving the IP reputation of Tor exit nodes.

# 1. Motivation

  Denial of service attacks against onion services have been explored in the past
  and various defenses have been proposed:
  - Tor proposal #305 specifies network-level rate-limiting mechanisms.
  - Onionbalance allows operators to scale their onions horizontally.
  - Tor proposal #327 increases the attacker's computational requirements (not implemented yet).

  While the above proposals in tandem should provide reasonable protection
  against many DoS attackers, they fundamentally work by reducing the assymetry
  between the onion service and the attacker. This won't work if the attacker
  is extremely powerful because the assymetry is already huge and cutting it
  down does not help.

  we believe that a proposal based on cryptographic guarantees -- like Res
  tokens -- can offer protection against even extremely strong attackers.

# 2. Overview

  In this proposal we introduce an anonymous credential scheme -- Res tokens --
  that is well fitted for protecting onion services against DoS attacks. We
  also introduce a system where clients can acquire such anonymous credentials
  from various types of Token Issuers and then redeem them at the onion service
  to gain access even when under DoS conditions.

  In section [TOKEN_DESIGN], we list our requirements from an anonymous
  credential scheme and provide a high-level overview of how the Res token
  scheme works.

  In section [PROTOCOL_SPEC], we specify the token issuance and redemption protocols,
  as well as the mathematical operations that need to be conducted for these to work.

  In section [TOKEN_ISSUERS], we provide a few examples and guidelines for
  various token issuer services that could exist.

  In section [DISCUSSION], we provide more use cases for Res tokens as well as
  future improvements we can conduct to the scheme.

# 3. Design [TOKEN_DESIGN]

  In this section we will go over the high-level design of the system, and on
  the next section we will delve into the lower-level details of the protocol.

## 3.1. Anonymous credentials

  Anonymous credentials or tokens are cryptographic identifiers that allow
  their bearer to maintain an identity while also preserving anonymity.

  Clients can acquire a token in a variety of ways (e.g. registering on a
  third-party service, solving a CAPTCHA, completing a PoW puzzle) and then
  redeem it at the onion service proving this way that work was done, but
  without linking the act of token acquisition with the act of token
  redemption.

## 3.2. Anonymous credential properties

  The anonymous credential literature is vast and there are dozens of
  credential schemes with different properties [REF_TOKEN_ZOO], in this section
  we detail the properties we care about for this use case:

  - Public Verifiability: Because of the distributed trust properties of the
      Tor network, we need anonymous credentials that can be issued by one
      party (the token issuer) and verified by a different party (in this case
      the onion service).

  - Perfect unlinkability: Unlinkability between token issuance and token
      redemption is vital in private settings like Tor. For this reason we want
      our scheme to preserve its unlinkability even if its fundamental security
      assumption is broken. We want unlinkability to be protected by
      information theoretic security or random oracle, and not just
      computational security.

  - Small token size: The tokens will be transfered to the service through the
      INTRODUCE1 cell which is not flexible and has only a limited amount of
      space (about 200 bytes) [REF_INTRO_SPACE]. We need tokens to be small.

  - Quick Verification: Onions are already experiencing resource starvation
      because of the DoS attacks so it's important that the process of
      verifying a token should be as quick as possible. In section [TOKEN_PERF]
      we will go deeper into this requirement.

  After careful consideration of the above requirements, we have leaned towards
  using Blind RSA as the primitive for our tokens, since it's the fastest
  scheme by far that also allows public verifiability. See also Appendix B
  [BLIND_RSA_PROOF] for a security proof sketch of Blind RSA perfect unlinkability.

## 3.3. Other security considerations

  Apart from the above properties we also want:

  - Double spending protection: We don't want Malory to be able to double spend
      her tokens in various onion services thereby amplifying her attack. For
      this reason our tokens are not global, and can only be redeemed at a
      specific destination onion service.

  - Metadata: We want to encode metadata/attributes in the tokens. In
      particular, we want to encode the destination onion service and an
      expiration date. For more information see section [DEST_DIGEST]. For
      blind RSA tokens this is usually done using "partially blind signatures"
      but to keep it simple we instead encode the destination directly in the
      message to be blind-signed and the expiration date using a set of
      rotating signing keys.

  - One-show: There are anonymous credential schemes with multi-show support
      where one token can be used multiple times in an unlinkable
      fashion. However, that might allow an adversary to use a single token to
      launch a DoS attack, since revocation solutions are complex and
      inefficient in anonymous credentials. For this reason, in this work we
      use one-show tokens that can only be redeemed once. That takes care of
      the revocation problem but it means that a client will have to get more
      tokens periodically.

## 3.4. Res tokens overview

  Throughout this proposal we will be using our own token scheme, named "Res",
  which is based on blind RSA signatures. In this modern cryptographic world,
  not only we have the audacity of using Chaum's oldest blind signature scheme
  of all times, but we are also using RSA with a modulus of 1024 bits...

  The reason that Res uses only 1024-bits RSA is because we care most about
  small token size and quick verification rather than the unforgeability of the
  token. This means that if the attacker breaks the issuer's RSA signing key
  and issues tokens for herself, this will enable the adversary to launch DoS
  attacks against onion services, but it won't allow her to link users (because
  of the "perfect unlinkability" property).

  Furthermore, Res tokens get a short implicit expiration date by having the
  issuer rapidly rotate issuance keys every few hours. This means that even if
  an adversary breaks an issuance key, she will be able to forge tokens for
  just a few hours before that key expires.

  For more ideas on future schemes and improvements see section [FUTURE_RES].

## 3.5. Token performance requirements [TOKEN_PERF]

  As discussed above, verification performance is extremely important in the
  anti-DoS use case. In this section we provide some concrete numbers on what
  we are looking for.

  In proposal #327 [REF_POW_PERF] we measured that the total time spent by the
  onion service on processing a single INTRODUCE2 cell ranges from 5 msec to 15
  msecs with a mean time around 5.29 msec. This time also includes the launch
  of a rendezvous circuit, but does not include the additional blocking and
  time it takes to process future cells from the rendezvous point.

  We also measured that the parsing and validation of INTRODUCE2 cell ("top
  half") takes around 0.26 msec; that's the lightweight part before the onion
  service decides to open a rendezvous circuit and do all the path selection
  and networking.

  This means that any defenses introduced by this proposal should add minimal
  overhead to the above "top half" procedure, so as to apply access control in
  the lightest way possible.

  For this reason we implemented a basic version of the Res token scheme in
  Rust and benchmarked the verification and issuance procedure [REF_RES_BENCH].

  We measured that the verification procedure from section [RES_VERIFY] takes
  about 0.104 ms, which we believe is a reasonable verification overhead for
  the purposes of this proposal.

  We also measured that the issuance procedure from [RES_ISSUANCE] takes about
  0.614 ms.

# 4. Specification [PROTOCOL_SPEC]

                  +--------------+           +------------------+
                  | Token Issuer |           | Onion Service    |
                  +--------------+           +------------------+
                         ^                            ^
                         |        +----------+        |
                Issuance |  1.    |          |   2.   | Redemption
                         +------->|  Alice   |<-------+
                                  |          |
                                  +----------+

## 4.0. Notation

  Let `a || b` be the concatenation of a with b.

  Let `a^b` denote the exponentiation of a to the bth power.

  Let `a == b` denote a check for equality between a and b.

  Let FDH_N(msg) be a Full Domain Hash (FDH) of 'msg' using SHA256 and
  stretching the digest to be equal to the size of an RSA modulus N.

## 4.1. Token issuer setup

  The Issuer creates a set of ephemeral RSA-1024 "issuance keys" that will be
  used during the issuance protocol. Issuers will be rotating these ephemeral
  keys every 6 hours.

  The Issuer exposes the set of active issuance public keys through a REST HTTP
  API that can be accessed by visiting /issuers.keys.

  Tor directory authorities periodically fetch the issuer's public keys and
  vote for those keys in the consensus so that they are readily available by
  clients. The keys in the current consensus are considered active, whereas the
  ones that have fallen off have expired.

  XXX how many issuance public keys are active each time? how does overlapping
      keys work? clients and onions need to know precise expiration date for
      each key. this needs to be specified and tested for robustness.

  XXX every how often does the fetch work? how does the voting work? which
      issuers are considered official? specify consensus method.

  XXX An alternative approach: Issuer has a long-term ed25519 certification key
      that creates expiring certificates for the ephemeral issuance keys. Alice
      shows the certificate to the service to prove that the token comes from
      an issuer. The consensus includes the long-term certification key of the
      issuers to establish ground truth.
      This way we avoid the synchronization between dirauths and issuers, and
      the multiple overlapping active issuance keys. However, certificates
      might not fit in the INTRODUCE1 cell (prop220 certs take 104 bytes on
      their own).  Also certificate metadata might create a vector for
      linkability attacks between the issuer and the verifier.

## 4.2. Onion service signals ongoing DoS attack

  When an onion service is under DoS attack it adds the following line in the
  "encrypted" (inner) part of the v3 descriptor as a way to signal to its
  clients that tokens are required for gaining access:

    "token-required" SP token-type SP issuer-list NL

    [At most once]

    token-type: Is the type of token supported ("res" for this proposal)
    issuer: A comma separated list of issuers which are supported by this onion service

## 4.3. Token issuance

  When Alice visits an onion service with an active "token-required" line in
  its descriptor it checks whether there are any tokens available for this
  onion service in its token store. If not, it needs to acquire some and hence
  the token issuance protocol commences.

### 4.3.1. Client preparation [DEST_DIGEST]

  Alice first chooses an issuer supported by the onion service depending on her
  preferences by looking at the consensus and her Tor configuration file for
  the current list of active issuers.

  After picking a supported issuer, she performs the following preparation
  before contacting the issuer:

  1) Alice extracts the issuer's public key (N,e) from the consensus

  2) Alice computes a destination digest as follows:

           dest_digest = FDH_N(destination || salt)

              where:
              - 'destination' is the 32-byte ed25519 public identity key of the destination onion
              - 'salt' is a random 32-byte value,

  3) Alice samples a blinding factor 'r' uniformly at random from [1, N)

  4) Alice computes:
           blinded_message = dest_digest * r^e (mod N)

  After this phase is completed, Alice has a blinded message that is tailored
  specifically for the destination onion service. Alice will send the blinded
  message to the Token Issuer, but because of the blinding the Issuer does not
  get to learn the dest_digest value.

  XXX Is the salt needed? Reevaluate.

### 4.3.3. Token Issuance [RES_ISSUANCE]

  Alice now initiates contact with the Token Issuer and spends the resources
  required to get issued a token (e.g. solve a CAPTCHA or a PoW, create an
  account, etc.). After that step is complete, Alice sends the blinded_message
  to the issuer through a JSON-RPC API.

  After the Issuer receives the blinded_message it signs it as follows:

        blinded_signature = blinded_message ^ d (mod N)

          where:
          - 'd' is the private RSA exponent.

  and returns the blinded_signature to Alice.

  XXX specify API (JSON-RPC? Needs SSL + pubkey pinning.)

### 4.3.4. Unblinding step

  Alice verifies the received blinded signature, and unblinds it to get the
  final token as follows:

        token = blinded_signature * r^{-1} (mod N)
              = blinded_message ^ d * r^{-1] (mod N)
              = (dest_digest * r^e) ^d * r^{-1} (mod N)
              = dest_digest ^ d * r * r^{-1} (mod N)
              = dest_digest ^ d (mod N)

          where:
          - r^{-1} is the multiplicative inverse of the blinding factor 'r'

  Alice will now use the 'token' to get access to the onion service.

  By verifying the received signature using the issuer keys in the consensus,
  Alice ensures that a legitimate token was received and that it has not
  expired (since the issuer keys are still in the consensus).

## 4.4. Token redemption

### 4.4.1. Alice sends token to onion service

  Now that Alice has a valid 'token' it can request access to the onion
  service. It does so by embedding the token into the INTRODUCE1 cell to the
  onion service.

  To do so, Alice adds an extension to the encrypted portion of the INTRODUCE1
  cell by using the EXTENSIONS field (see [PROCESS_INTRO2] section in
  rend-spec-v3.txt). The encrypted portion of the INTRODUCE1 cell only gets
  read by the onion service and is ignored by the introduction point.

  We propose a new EXT_FIELD_TYPE value:

    [02] -- ANON_TOKEN

  The EXT_FIELD content format is:

       TOKEN_VERSION    [1 byte]
       ISSUER_KEY       [4 bytes]
       DEST_DIGEST      [32 bytes]
       TOKEN            [128 bytes]
       SALT             [32 bytes]

  where:
   - TOKEN_VERSION is the version of the token ([0x01] for Res tokens)
   - ISSUER_KEY is the public key of the chosen issuer (truncated to 4 bytes)
   - DEST_DIGEST is the 'dest_digest' from above
   - TOKEN is the 'token' from above
   - SALT is the 32-byte 'salt' added during blinding

  This will increase the INTRODUCE1 payload size by 199 bytes since the data
  above is 197 bytes, the extension type and length is 2 extra bytes, and the
  N_EXTENSIONS field is always present. According to ticket #33650, INTRODUCE1
  cells currently have more than 200 bytes available so we should be able to
  fit the above fields in the cell.

  XXX maybe we don't need to pass DEST_DIGEST and we can just derive it

  XXX maybe with a bit of tweaking we can even use a 1536-bit RSA signature here...

### 4.4.2. Onion service verifies token  [RES_VERIFY]

  Upon receiving an INTRODUCE1 cell with the above extension the service
  verifies the token. It does so as follows:

  1) The service checks its double spend protection cache for an element that
     matches DEST_DIGEST. If one is found, verification fails.
  2) The service checks: DEST_DIGEST == FDH_N(service_pubkey || SALT), where
     'service_pubkey' is its own long-term identity pubkey.
  3) The service finds the corresponding issuer pubkey 'e' based on ISSUER_KEY
     from the consensus or its configuration file
  4) The service checks: TOKEN ^ e == DEST_DIGEST

  Finally the onion service adds the DEST_DIGEST to its double spend protection
  cache to avoid the same token getting redeemed twice.  Onion services keep a
  double spend protection cache by maintaining a sorted array of truncated
  DEST_DIGEST elements.

  If any of the above steps fail, the verification process aborts and the
  introduction request gets discarded.

  If all the above verification steps have been completed successfully, the
  service knows that this a valid token issued by the token issuer, and that
  the token has been created for this onion service specifically. The service
  considers the token valid and the rest of the onion service protocol carries
  out as normal.

# 5. Token issuers [TOKEN_ISSUERS]

  In this section we go over some example token issuers. While we can have
  official token issuers that are supported by the Tor directory authorities,
  it is also possible to have unofficial token issuers between communities that
  can be embedded directly into the configuration file of the onion service and
  the client.

  In general, we consider the design of token issuers to be independent from
  this proposal so we will touch the topic but not go too deep into it.

## 5.1. CAPTCHA token issuer

  A use case resembling the setup of Cloudflare's PrivacyPass would be to have
  a CAPTCHA service that issues tokens after a successful CAPTCHA solution.

  Tor Project, Inc runs https://ctokens.torproject.org which serves hCaptcha
  CAPTCHAs. When the user solves a CAPTCHA the server gives back a list of
  tokens. The amount of tokens rewarded for each solution can be tuned based on
  abuse level.

  Clients reach this service via a regular Tor Exit connection, possibly via a
  dedicated exit enclave-like relay that can only connect to https://ctokens.torproject.org.

  Upon receiving tokens, Tor Browser delivers them to the Tor client via the
  control port, which then stores the tokens into a token cache to be used when
  connecting to onion services.

  In terms of UX, most of the above procedure can be hidden from the user by
  having Tor Browser do most of the things under the scenes and only present
  the CAPTCHA to the user if/when needed (if the user doesn't have tokens
  available for that destination).

  XXX specify control port API between browser and tor

## 5.2. PoW token issuer

  An idea that mixes the CAPTCHA issuer with proposal#327, would be to have a
  token issuer that accepts PoW solutions and provides tokens as a reward.

  This solution tends to be less optimal than applying proposal#327 directly
  because it doesn't allow us to fine-tune the PoW difficulty based on the
  attack severity; which is something we are able to do with proposal#327.

  However, we can use the fact that token issuance happens over HTTP to
  introduce more advanced PoW-based concepts. For example, we can design token
  issuers that accept blockchain shares as a reward for tokens. For example, a
  system like Monero's Primo could be used to provide DoS protection and also
  incentivize the token issuer by being able to use those shares for pool
  mining [REF_PRIMO].

## 5.3. Onion service self-issuing

  The onion service itself can also issue tokens to its users and then use
  itself as an issuer for verification. This way it can reward trusted users by
  giving it tokens for the future. The tokens can be rewarded from within the
  website of the onion service and passed to the Tor Client through the control
  port, or they can be provided in an out-of-bands way for future use
  (e.g. from a journalist to a future source using a QR code).

  Unfortunately, the anonymous credential scheme specified in this proposal is
  one-show, so the onion service cannot provide a single token that will work
  for multiple "logins". In the future we can design multi-show credential
  systems that also have revocation to further facilitate this use case (see
  [FUTURE_RES] for more info).

# 6. User Experience

  This proposal has user facing UX consequences.

  Ideally we want this process to be invisible to the user and things to "just
  work". This can be achieved with token issuers that don't require manual work
  by the user (e.g. the PoW issuer, or the onion service itself), since both the
  token issuance and the token redemption protocols don't require any manual work.

  In the cases where manual work is needed by the user (e.g. solving a CAPTCHA)
  it's ideal if the work is presented to the user right before visiting the
  destination and only if it's absolutely required. An explanation about the
  service being under attack should be given to the user when the CAPTCHA is
  provided.

# 7. Security

  In this section we analyze potential security threats of the above system:

  - An evil client can hoard tokens for hours and unleash them all at once to
    cause a denial of service attack. We might want to make the key rotation
    even more frequent if we think that's a possible threat.

  - A trusted token issuer can always DoS an onion service by forging tokens.

  - Overwhelming attacks like "top half attacks" and "hybrid attacks" from
    proposal#327 is valid for this proposal as well.

  - A bad RNG can completely wreck the linkability properties of this proposal.

  XXX Actually analyze the above if we think there is merit to listing them

# 8. Discussion [DISCUSSION]

## 8.1. Using Res tokens on Exit relays

  There are more scenarios within Tor that could benefit from Res tokens
  however we didn't expand on those use cases to keep the proposal short.  In
  the future, we might want to split this document into two proposals: one
  proposal that specifies the token scheme, and another that specifies how to
  use it in the context of onion servicves, so that we can then write more
  proposals that use the token scheme as a primitive.

  An extremely relevant use case would be to use Res tokens as a way to protect
  and improve the IP reputation of Exit relays. We can introduce an exit pool
  that requires tokens in exchange for circuit streams. The idea is that exits
  that require tokens will see less abuse, and will not have low scores in the
  various IP address reputation systems that now govern who gets access to
  websites and web services on the public Internet. We hope that this way we
  will see  less websites blocking Tor.

## 8.2. Future improvements to this proposal [FUTURE_RES]

  The Res token scheme is a pragmatic scheme that works for the space/time
  constraints of this use case but it's far from ideal for the greater future
  (RSA? RSA-1024?).

  After Tor proposal#319 gets implemented we will be able to pack more data in
  RELAY cells and that opens the door to token schemes with bigger token
  sizes. For example, we could design schemes based on BBS+ that can provide
  more advanced features like multi-show and complex attributes but currently
  have bigger token sizes (300+ bytes). That would greatly improve UX since the
  client won't have to solve multiple CAPTCHAs to gain access. Unfortunately,
  another problem here is that right now pairing-based schemes have
  significantly worse verification performance than RSA (e.g. in the order of
  4-5 ms compared to <0.5 ms). We expect pairing-based cryptography performance
  to only improve in the future and we are looking forward to these advances.

  When we switch to a multi-show scheme, we will also need revocation support
  otherwise a single client can abuse the service with a single multi-show
  token. To achieve this we would need to use blacklisting schemes based on
  accumulators (or other primitives) that can provide more flexible revocation
  and blacklisting; however these come at the cost of additional verification
  time which is not something we can spare at this time. We warmly welcome
  research on revocation schemes that are lightweight on the verification side
  but can be heavy on the proving side.

## 8.3. Other uses for tokens in Tor

  There is more use cases for tokens in Tor but we think that other token
  schemes with different properties would be better suited for those.

  In particular we could use tokens as authentication mechanisms for logging
  into services (e.g. acquiring bridges, or logging into Wikipedia). However
  for those use cases we would ideally need multi-show tokens with revocation
  support. We can also introduce token schemes that help us build a secure name
  system for onion services.

  We hope that more research will be done on how to combine various token
  schemes together, and how we can maintain agility while using schemes with
  different primitives and properties.

# 9. Acknowledgements

  Thanks to Jeff Burdges for all the information about Blind RSA and anonymous
  credentials.

  Thanks to Michele Orrù for the help with the unlinkability proof and for the
  discussions about anonymous credentials.

  Thanks to Chelsea Komlo for pointing towards anonymous credentials in
  the context of DoS defenses for onion services.

---

# Appendix A: RSA Blinding Security Proof [BLIND_RSA_PROOF]

  This proof sketch was provided by Michele Orrù:

  ```
  RSA Blind Sigs: https://en.wikipedia.org/wiki/Blind_signature#Blind_RSA_signatures

  As you say, blind RSA should be perfectly blind.

  I tried to look at Boneh-Shoup, Katz-Lindell, and Bellare-Goldwasser for a proof, but didn't find any :(

  The basic idea is proving that:
  for any  message "m0" that is blinded with "r0^e" to obtain "b" (that is sent to the server), it is possible to freely choose another message "m1" that blinded with another opening "r1^e" to obtain the same "b".

  As long as r1, r0 are chosen uniformly at random, you have no way of telling if what message was picked and therefore it is *perfectly* blind.

  To do so:
  Assume the messages ("m0" and "m1") are invertible mod N=pq (this happens at most with overwhelming probability phi(N)/N if m is uniformly distributed as a result of a hash, or you can enforce it at signing time).

  Blinding happens by computing:
     b = m0 * (r0^e).

  However, I can also write:
     b = m0 * r0^e = (m1/m1) * m0 * r0^e = m1 * (m0/m1*r0^e).

  This means that r1 = (m0/m1)^d * r0 is another valid blinding factor for b, and it's distributed exactly as r0 in the group of invertibles (it's unif at random, because r0 is so).
  ```

---

[REF_TOKEN_ZOO]: https://tokenzoo.github.io/
[REF_INTRO_SPACE]: https://gitlab.torproject.org/legacy/trac/-/issues/33650#note_2350910
[REF_CHAUM]: https://eprint.iacr.org/2001/002.pdf
[REF_PRIMO]: https://repo.getmonero.org/selene/primo
             https://www.monerooutreach.org/stories/RPC-Pay.html
[REF_POW_PERF]: https://gitlab.torproject.org/tpo/core/torspec/-/blob/master/proposals/327-pow-over-intro.txt#L1050
[REF_RES_BENCH]: https://github.com/asn-d6/res_tokens_benchmark
