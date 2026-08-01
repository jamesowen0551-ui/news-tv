# Stream Source Review

Review date: 2026-08-01 (Asia/Shanghai)

This project treats a broadcaster's official public live page as evidence that the channel is intentionally offered free of charge. A stream URL is accepted only when it is also delivered from the broadcaster's domain, a branded CDN hostname, or the exact delivery channel referenced by the official web player. Passing a technical check alone is not sufficient.

## Included

| Channel | Official public availability | Delivery evidence | Live result at review |
|---|---|---|---|
| Bloomberg TV | [Bloomberg Live](https://www.bloomberg.com/live) | `bloomberg.com` media manifest | PASS — 720p, 1.20 Mbps |
| Schwab Network | [Schwab Network](https://schwabnetwork.com/) and [Ways to Watch](https://schwabnetwork.com/waystowatch) | Official site JavaScript references Uplynk channel `f9aafa1f132e40af9b9e7238bc18d128`; the playlist uses the stable token-free channel URL | PASS — 1080p, 3.69 Mbps |
| CBS News 24/7 | [CBS News streaming information](https://www.cbsnews.com/streaming/) | `cbsnstream.cbsnews.com` | PASS — 720p, 2.56 Mbps |
| NBC News NOW | [NBC News NOW](https://www.nbcnews.com/now) | `fast.nbcuni.com` | PASS — 1080p, 5.06 Mbps |
| Scripps News | [Scripps News Live](https://www.scrippsnews.com/live) | Official page exposes Uplynk channel `4bb4901b934c4e029fd4c1abfc766c37` in its `data-m3u8` attribute | PASS — 720p, 6.00 Mbps |
| Sky News | [Sky News Live](https://news.sky.com/watch-live) | Official page exposes the `delivery.skycdp.com` master playlist | PASS — 1080p, 9.04 Mbps |
| DW English | [DW English Live TV](https://www.dw.com/en/live-tv/channel-english) | DW-branded Akamai delivery hostname | PASS — 1080p, 5.18 Mbps |
| NHK World-Japan | [NHK World Live](https://www3.nhk.or.jp/nhkworld/en/live/) | `nhkworld.jp` HLS domain | PASS — 1080p, 6.74 Mbps |
| Euronews English | [Euronews](https://www.euronews.com/) | Euronews-branded Akamai delivery hostname | PASS — 720p, 3.64 Mbps |
| Al Jazeera English | [Al Jazeera Live](https://www.aljazeera.com/live) | Al Jazeera `getaj.net` delivery hostname | PASS — 1080p, 4.79 Mbps |

Operational measurements are snapshots, not guarantees. The scheduled checker is the source of current health information.

## Not included in the first release

| Candidate | Technical result | Decision |
|---|---|---|
| Yahoo Finance | PASS — 1080p, 4.65 Mbps | The candidate uses an unbranded CloudFront distribution and its exact association could not be confirmed in the current official player configuration. Pending stronger first-party evidence. |
| ABC News Live | FAIL | The official Akamai master manifest returned successfully, but every advertised media variant tested returned HTTP 404. |
| LiveNOW from FOX | PASS — 720p, 2.78 Mbps | The official site confirms free distribution, but the tested Amagi LG feed was not found in the current official site configuration. Pending exact provenance confirmation. |
| France 24 English | FAIL | The official public URL returned a media playlist directly and did not contain the required `#EXT-X-STREAM-INF` variant playlist. |
| CNA | PASS — 1080p, 5.06 Mbps | The longstanding CloudFront feed is unbranded and its current mapping could not be confirmed from CNA's official player configuration. Pending stronger first-party evidence. |

CNN, CNBC, BBC News, and the Fox News cable channel were intentionally not researched for inclusion because unauthorized restreams of those channels are outside project policy. LiveNOW from FOX is a separate free streaming service, but is still withheld until its exact delivery URL is confirmed.

## Logos

No `tvg-logo` URLs are included in this release. Public visibility of a logo is not the same as permission to hotlink or redistribute it, and no stable first-party logo usage permission was established during review.
