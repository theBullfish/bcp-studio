# The five pillars

How the newer systems fit the platform. All ride the same Django app + Skote
front-end; heavy/streaming work is designed to move to Celery/CDN when needed.

## 1. Capture → sync (Tailscale)
Take a laptop anywhere, record locally, and footage lands on the media server.

- **Tailscale** is the transport: each machine joins your private tailnet and gets
  a stable address regardless of location. It's installed per-machine (`tailscale up`),
  not bundled in the app.
- **`syncagent/agent.py`** runs on the laptop: watches a record folder, uploads new
  (finished-writing) files to the server's ingest endpoint over the tailnet, resumable,
  with exponential-backoff retries and a local state file so it never re-uploads.
- **Server ingest** (`/ingest/`, key-authenticated per `Device`) stores the file and
  creates a `MediaAsset` on the device's target `Project` — so a play can auto-run on arrival.

## 2. Socials & distribution
Manage each client's channels and how produced media is divided across platforms.

- **`SocialAccount`** per client/platform, now with authorization fields.
- **`DistributionRule`**: `source_format → [platforms]` (e.g. `reel_9x16 → IG, TikTok, YT`),
  with `auto_post`. Drives where a play's outputs go.
- **`PlatformProfile`**: per-client, per-platform cadence, hashtags, best times.

## 3. Client-as-tenant + authorize the app
Each `Client` has a **type** (artist / group / news agency / business / creator). An
authorized rep grants the app permission to act on their channels — recorded on
`SocialAccount.authorized_by/authorized_at`. This is the real basis for auto-posting
(the per-platform OAuth token exchange plugs in here; currently the connect action
marks the channel authorized and stores tokens when present).

## 4. Store (Stripe)
Sell merch, digital goods, and tickets — reusing the **GritBox Stripe account**.

- Models: `Product`, `Price`, `Order`, `OrderItem`, `StoreCustomer`.
- **Stripe hosted Checkout** (`studio/stripe_service.py`) — no card data touches this app.
- **Webhook** (`/shop/webhook/`) fulfills orders on `checkout.session.completed`.
- Public storefront at `/shop/`; management inside the app. Keys come from env/secrets.

## 5. Paid video platform (self-hosted Floatplane/YouTube)
Produce → post to socials for reach → funnel to your own paid platform for depth + recurring revenue.

- Models: `Channel`, `Video` (PUBLIC / MEMBERS / TIER), `MembershipPlan`, `Membership`, `VideoView`.
- **Self-hosted HLS**: `services.transcode_to_hls()` (ffmpeg) produces adaptive `.m3u8`,
  stored locally under `HLS_ROOT`. Played with **hls.js** (vendored) + native HTML5 video.
- **Access gating**: `Video.accessible_to(memberships)` — public is open; members/tier
  require an active Stripe subscription (`create_subscription_checkout`).
- Scale path: move transcode to Celery, front the segments with a CDN, add signed URLs.

## Where the money flows
Both the store and the video subscriptions run through the same GritBox Stripe account
(env keys). One dashboard, one payout. Switch to a dedicated account by changing env vars.
