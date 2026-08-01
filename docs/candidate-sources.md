# Candidate Source Review

Review date: 2026-08-01 (Asia/Shanghai)

Only an official public page with a concrete, token-free official HLS delivery chain can enter `channels/candidates.json`. A broadcaster name, YouTube-only stream, event page, geo/account-restricted player, guessed URL, or third-party IPTV listing is insufficient.

## Initial candidate

### Arirang TV

- Official page: [Arirang TV live](https://www.arirang.com/live)
- Official delivery evidence: the live page loads `main.add9a540.chunk.js`. Its World TV player payload publishes the global Akamai HLS at `amdlive-ch01-g-ctnd-com.akamaized.net`.
- Stored URL: token-free HTTPS master playlist with no query string or fragment.
- Technical review: PASS — HTTP 200, HLS Content-Type, 3 variants, 1280x720 selected, and first segment accessible.
- Status: `candidate`. No China household manual test has been recorded.

The external Kollus player URL contains a long-lived signed player payload and is not stored. Only the token-free HLS explicitly published inside the official page's player configuration is retained.

## Researched but withheld

| Direction | Official evidence reviewed | Why it is not in the candidate pool |
|---|---|---|
| KBS World | [KBS Korea availability](https://kbsworld.kbs.co.kr/about/kbskorea.php) | The official page points international live viewing to KBS World YouTube and local platforms; no stable official public HLS was confirmed. |
| ABC Australia | [ABC overseas access](https://help.abc.net.au/hc/en-us/articles/13845760226831-How-can-I-access-ABC-services-overseas) | ABC Australia is distributed through regional providers/satellite. ABC NEWS is a distinct service; no qualifying ABC Australia HLS was confirmed. |
| SBS Australia | [SBS live streaming policy](https://help.sbs.com.au/hc/en-au/articles/360002023135-Information-on-Live-Streaming-SBS-and-the-SBS-On-Demand-Guide) | SBS states its live service is Australia-only and IP-geoblocked; no suitable public global HLS was confirmed. |
| NASA | [NASA ways to watch](https://www.nasa.gov/ways-to-watch/) | NASA+ focuses on scheduled live events, apps, and partner FAST distribution; no stable continuous public HLS was confirmed. |
| ESA | [ESA Web TV](https://watch.esa.int/) | The official service is event/schedule oriented and did not expose a stable continuous HLS during review. |
| TRT World | [TRT World](https://www.trtworld.com/) | The official site exposes LIVE TV, but its page could not be reliably retrieved to prove the concrete player-to-HLS chain. Third-party listings were disregarded. |
| NYSE | [NYSE TV](https://tv.nyse.com/) | The official VHX service presents signup/login flows and did not publish a stable anonymous HLS in the reviewed page. |
| Nasdaq | [Nasdaq Watch](https://www.nasdaq.com/videos) | Official output centers on scheduled bells, TradeTalks, and event webcasts; no continuous public HLS was confirmed. |
| Reuters | [Reuters](https://www.reuters.com/) | No broadcaster-controlled public continuous HLS was confirmed. |
| WION | [WION](https://www.wionews.com/) | No concrete official token-free HLS chain was confirmed. |
| India Today | [India Today Live TV](https://www.indiatoday.in/livetv) | The official live page exists, but its concrete reusable official HLS was not established. |
| Apple, Google I/O, NVIDIA | Official event pages | These are time-bounded events, not stable news channels. They remain future `events` research directions. |

## Recommended next manual/research batch

1. Manually test Arirang TV on China mainland residential broadband and Sony Android TV.
2. Revisit TRT World using a reliably accessible official player session.
3. Research ABC NEWS as a distinct channel from ABC Australia, without weakening TLS or geographic rules.
4. Trace India Today's official player configuration.
5. Keep NASA, ESA, Apple, Google I/O, and NVIDIA work in the event-stream workflow rather than the continuous news candidate pool.
