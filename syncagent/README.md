# BCP Studio Sync Agent — Tailscale record → sync

A tiny standalone agent that watches a folder on your recording machine and
uploads every new recording to BCP Studio's ingest endpoint **over your Tailscale
tailnet**. Record locally; the agent quietly syncs each finished file into the
studio, where it becomes a media asset on the device's target project.

It uploads **asynchronously**, never re-uploads a file, resumes across restarts,
and survives flaky wifi (exponential-backoff retries, stable-size detection so
half-written files are left alone).

---

## 1. Put both machines on the same tailnet

Install [Tailscale](https://tailscale.com/download) on **both** the recording
machine and the media server, then bring each up:

```bash
tailscale up
```

Find the **media server's** tailnet address (run this on the server):

```bash
tailscale ip -4        # e.g. 100.101.102.103
```

You can also use the server's MagicDNS name (e.g. `temple`) from the Tailscale
admin console. Nothing needs to be exposed to the public internet — traffic
stays inside the tailnet.

## 2. Create a Device in BCP Studio

In the studio web app go to **Capture Devices → New device**. Give it a name
(optionally a client and target project), then open the device page and copy its
**API key** (starts with `bcpk_`). Keep it secret — anyone with the key can
upload media as this device.

## 3. Install the agent

On the recording machine (Python 3.8+):

```bash
pip install -r requirements.txt   # just `requests`
```

## 4. Run it

```bash
python agent.py \
  --server http://<media-server-tailnet-host>:8000 \
  --key bcpk_your_device_key \
  --watch ~/Recordings
```

- `--server` — the media server's tailnet IP/host + port (default Django port 8000).
- `--key` — the Device API key from step 2.
- `--watch` — folder to watch (recurses into subfolders).
- `--interval` — poll seconds (default 5).

Leave it running. Drop or record new files into the watch folder and they upload
automatically once they've finished writing. Each successful upload prints the
resulting `media_id` and `project_id`.

## How it stays reliable

- **No duplicates / resumable:** uploaded files are recorded in
  `~/.bcp_sync_state.json` keyed by path + mtime + size, so restarting the agent
  never re-sends anything.
- **Only complete files:** a file is uploaded only after its size is unchanged
  between two polls (i.e. the recorder finished writing it).
- **Flaky networks:** network errors retry with 2/4/8/16s backoff; anything still
  failing is simply retried on the next poll.

Run it as a background service (systemd, launchd, or `nohup python agent.py ... &`)
so it keeps syncing whenever the machine is on the tailnet.
