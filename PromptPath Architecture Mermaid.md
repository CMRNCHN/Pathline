flowchart LR
  subgraph ClientSide["Client / User Device"]
    C1[User App<br/>- Consent UI<br/>- Client-side encryption of secrets<br/>- Local STT/TTS (optional)<br/>- Local audio capture/injection]
    C2[Native Dialer / WebRTC<br/>(places call)]
  end

  subgraph Server["Server-side Services (optional)"]
    A[Auth Service<br/>(mint ephemeral tokens)]
    D[DID Manager<br/>(pool, cooldown, provider distribution)]
    O[Call Orchestrator<br/>(PJSIP/pjsua agent)<br/>- TLS + DTLS-SRTP enforced<br/>- In-memory audio handling]
    S[STT / NLP Service<br/>(local Whisper or secure cloud)]
    K[KMS / HSM<br/>(key release)]
    DB[Encrypted State Store<br/>(minimal status + hashed ids)]
    N[Notification Service<br/>(alerts / drift)]
    M[Monitoring & Audit<br/>(redacted logs)]
    L[Lab Testbed<br/>(Asterisk + SIPp)]
  end

  subgraph Providers["SIP Providers / Carriers"]
    P1[SIP Trunk Provider A]
    P2[SIP Trunk Provider B]
    IVR[Third-party IVR (target)]
  end

  %% Client-mediated flow (preferred)
  C1 -->|1: user requests check (consent + encrypted secrets)| A
  C1 -->|2: client places call directly| C2
  C2 -->|media| IVR
  C2 -->|local STT (optional) -> status| C1
  C1 -->|3: report status (encrypted) -> server| DB
  DB -->|4: notification| N

  %% Server-mediated flow (optional)
  A -->|mint token| O
  O -->|request DID| D
  D -->|select DID & provider| P1 & P2
  O -->|place call (SIP/TLS + DTLS-SRTP)| P1
  P1 -->|SIP/RTP| IVR
  O -->|in-memory record -> send audio| S
  S -->|transcript & classification| O
  O -->|store minimal status (encrypted)| DB
  O -->|alert on drift| N

  %% Key usage and monitoring
  O -->|request keys| K
  S -->|request keys| K
  A -->|audit + logs| M
  L -->|test & validate| O