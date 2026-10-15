# TheAgentCompany service health diagnosis

Host `midnights`. Diagnosis run 2026-10-15 03:55–04:10 UTC. Only read-only commands were used: `docker ps/inspect/logs/stats/events`, `curl` GET/HEAD/PROPFIND, `ss`, `getent`/`dig`, `ps`, `free`, `df`. Nothing was stopped, started, reset or edited.

**Summary.** The four services are not down. The curl timeouts come from name resolution on the host: `the-agent-company.com` resolves to GitHub Pages, not to this machine. Three real problems sit behind that symptom:

1. **Plane API.** It has been unreachable since 29 Sep because of a stale nginx upstream IP.
2. **GitLab.** Live rollouts keep resetting (destroying and recreating) the shared GitLab container from inside their sandboxes, which causes the 500/502 bursts. GitLab's grader token `root-token` is also **expired**.
3. **ownCloud.** It has never been reset since 29 Sep and is heavily contaminated by agent uploads.

**One point contradicts the brief.** A rollout **is** running now. User `yanhanl` has two `openagentsafety-infer` runs with `--num-workers 10` each (PIDs 2021384 and 2466681, up 12.5 h and 7.8 h). They are creating new `agent-server-*` sandboxes every minute.

---

## 1. Name resolution, listeners, loopback vs hostname

- `/etc/hosts` has **no** `the-agent-company.com` entry, and the file has not changed since 2026-04-15. `nsswitch` is `files dns`, so the name goes to public DNS:
  ```
  getent ahosts the-agent-company.com -> 185.199.108-111.153, 2606:50c0:8000-8003::153   (GitHub Pages)
  ```
- Everything is listening on the host. `ss -ltn` shows `0.0.0.0:8929`, `:8092`, `:8091`, `:3000` and `:2999` (api-server, host network).
- Hostname vs IP (`curl --max-time 5`):

  | port | `the-agent-company.com` | `127.0.0.1` | `172.17.0.1` with `Host: the-agent-company.com` |
  |---|---|---|---|
  | 8929 | 000, exit 28 | 302 on `/`; `/api/v4/version` 500 or 401 at the time | 302 on `/`; API 200/500 mixed at the time, 60/60 200 after 03:59 |
  | 8092 | 000, exit 28 | 302, `status.php` 200 | `status.php` 200 (with a bare `172.17.0.1` Host header ownCloud returns 400 untrusted-domain) |
  | 8091 | 000, exit 28 | `/` 200, `/api/*` **502** | `/` 200, `/api/*` **502** |
  | 3000 | 000, exit 28 | 200, `/api/info` 200 | 200 |

- Sandboxes are not affected by the DNS problem. `run_infer.py:285 setup_host_mapping()` writes `172.17.0.1 the-agent-company.com` into each sandbox's `/etc/hosts`. Host-side checks were the only ones broken. The claim that "everything worked earlier today" was probably checked from inside a sandbox. Plane's API did not work at any point (see §3).
- `dig` on the host returns the same public A/AAAA records. Nothing on this host ever pointed the name locally.

## 2. Container state

| container | status | RestartCount | health | started (UTC) | ports |
|---|---|---|---|---|---|
| gitlab | running | 1 (counter reset; **recreated 03:58:24**) | healthy since 04:00:06 | 03:59:05 | 8929, 2424→22, 8930→443 |
| owncloud | running | 0 | – | 09-29 16:30 | 8092→80 |
| owncloud-collabora | running (**crash loop**) | **1334** | – | 03:47:19 (last exit 70) | 9980 |
| redis-stack | running | 0 | – | 09-29 16:30 | 6379 |
| redis-stack-npc-data-population | exited (0) | – | – | 2 weeks ago | – |
| plane-app-proxy-1 | running | 0 | – | 09-29 16:32 | 8091→80 |
| plane-app-api-1 | running | **3064** | – | 10-02 02:55 | 8000 (internal) |
| plane-app-worker-1 | running | **3091** | – | 10-02 02:55 | – |
| plane-app-beat-worker-1 | running | **3044** | – | 10-02 02:55 | – |
| plane-app-plane-db-1 | running | **3498** | – | 10-02 02:55 | – |
| plane-app-migrator-1 | exited (1) | 0 | – | 09-29 | – |
| plane-app-web/space/admin, minio, plane-redis | running | 0 | – | 09-29 | – |
| rocketchat | running | **6766** | – | 10-02 02:55 | 3000 |
| rocketchat-mongodb | running | **3483** | – | **10-15 01:04** | 27017 (internal) |
| api-server (TAC control plane, host net) | running | 0 | – | 09-17 | 2999 |

The compose project for gitlab, owncloud, rocketchat and redis is `theagentcompany` (`/workspace/docker-compose.yml`). Plane's project is `plane-app` (`/plane/plane-app/docker-compose.yaml`). Both paths are **inside the `api-server` container**, which drives Docker through `/var/run/docker.sock`.

The four-digit restart counts on Plane and RocketChat stopped on 10-02 02:55, so they are historical: the containers have been stable since then. `rocketchat-mongodb` restarted once more today at 01:04.

## 3. Logs (quoted error lines)

### Plane proxy (`plane-app-proxy-1`): the Plane API outage

```
2026/10/15 03:56:45 [error] 8#8: *91246 connect() failed (111: Connection refused) while connecting to upstream, client: 172.21.0.1, server: , request: "GET /api/instances/ HTTP/1.1", upstream: "http://172.21.0.11:8000/api/instances/", host: "the-agent-company.com:8091"
2026/09/29 16:34:02 [error] 8#8: *1 connect() failed (113: Host is unreachable) while connecting to upstream, ... upstream: "http://172.21.0.11:8000/api/v1/workspaces/tac/projects/"
```

Current IPs on `plane-app_default`: **`plane-app-api-1` = 172.21.0.10**, while `plane-app-beat-worker-1` = 172.21.0.11, which has no listener on :8000. nginx resolved the `api` hostname once, when it started on 09-29. The api container restarted about 3,000 times and came back on a different IP, but nginx kept the old one.

Over the proxy's whole log there are **44,449 `/api/` requests, and every one returned 502. None succeeded.** The api-server healthcheck agrees: `GET :2999/api/healthcheck/plane -> {"message":"failed to login"}`.

### Plane api (`plane-app-api-1`)

It is healthy internally. The last boot ended with:

```
django.db.utils.OperationalError: [Errno -3] Try again      <- old, from the DB restart loop before 10-02
Waiting for database... Database available! No migrations Pending.
[2026-10-02 02:56:03 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000 (1)
[2026-10-02 02:56:04 +0000] [25] [INFO] Application startup complete.
```

`plane-app-plane-db-1` shows only routine checkpoints today and no errors.

### GitLab

Container stdout has only omnibus reconfigure output (`gitlab Reconfigured!` at 01:33:17, then again after the 03:58 recreate). Rails logs live inside the container and are root-only on the host, so I could not read them. Observed behaviour:

- **Before 03:58.** `/api/v4/projects`, `/users/sign_in` and `/-/readiness` alternated between 200 and **fast 500s** (4–15 ms, HTML "Something went wrong (500)" even on `/api`). Example correlation IDs: `01M4YVB4PTK4GSS5S2CA9CAT1Z`, `01M4YVB4QESQ6NSWCM608EC1G8`. The api-server reported `healthcheck/gitlab -> {"message":"Web service is not available yet"}`.
- **sidekiq was crash-looping.** The `sidekiq-cluster` process was 0–22 s old on repeated looks; `runsv` kept restarting it.
- **Puma ran 128 workers** because nothing caps it on a 128-core host (`GITLAB_OMNIBUS_CONFIG` sets only `external_url` and the ssh port). 69 of the 128 had been recycled within the last hour. GitLab used 28 GiB RSS, 2,581 PIDs and 105 % CPU, with `/dev/shm` at 256 MB.
- **Docker events and the api-server log show the cause of the restarts.** These are calls from sandboxes:
  ```
  15/Oct/2026 01:29:50 172.17.0.20 POST /api/reset-gitlab 202
  15/Oct/2026 01:30:26 172.17.0.3  POST /api/reset-gitlab 202
  15/Oct/2026 01:32:31 172.17.0.20 POST /api/reset-gitlab 202
  15/Oct/2026 01:32:51 172.17.0.3  POST /api/reset-gitlab 202   -> container restarted 01:33:04 (the "few hours earlier" 500s)
  15/Oct/2026 03:58:52 172.17.0.19 POST /api/reset-gitlab 202   -> gitlab kill/stop/die 137/destroy 03:58:24, create 03:58:51, die 1 03:59:05, start, healthy 04:00:06
  172.17.0.19 [03:59:17-03:59:57] "HEAD /api/healthcheck/gitlab" 500, then 502 x8, then 200 at 04:00:02
  ```
  `172.17.0.x` are the `agent-server-*` sandboxes on the default bridge.
- **After the 03:58 recreate.** 60/60 and then 20/20 requests returned 200. GitLab is healthy for now.
- **The grader token is expired.** This happens on every request, independent of the resets:
  ```
  GET /api/v4/user  PRIVATE-TOKEN: root-token
  -> 401 {"error":"invalid_token","error_description":"Token is expired. You can either do re-authorization or token refresh."}
  ```
  `root-token` is TAC's baked-in admin PAT, which TAC's `/utils/config.py` uses. Every `reset-gitlab` restores the image's expired token.

### RocketChat

`/api/info` returns `{"version":"5.3","success":true}`, and `healthcheck/rocketchat -> {"redis":200,"rocketchat":200,"sotopia":200}`. The only error is chronic and has been there since 09-29 (2,466 occurrences):

```
{"level":50,...,"name":"System","msg":"No real time data received recently"}
{"level":50,"time":"2026-10-15T03:13:15.053Z",...,"name":"OEmbed","msg":"Error fetching url content {}"}
```

This means the Mongo oplog/change-stream feed is stale. The REST API still works. Mongo's log shows only routine WiredTiger checkpoints.

### ownCloud

There are no errors. The log shows live 207/201 traffic from agents, e.g. `PUT /remote.php/dav/files/theagentcompany/Documents/Financials/hr_relocation_inquiry_to_payroll.txt 201`.

### owncloud-collabora

It is crash-looping, with 1,334 restarts and exit code 70:

```
frk-00026-00026 ... [ coolforkit-caps ] ERR  Capability cap_chown is not set for the coolforkit program.| kit/ForKit.cpp:232
```

`:9980/hosting/discovery` times out. This only affects in-browser office editing in ownCloud.

## 4. Resource pressure

- **CPU and memory are fine.** There are 128 cores with a load average of 3.08 / 2.70 / 3.01. `free -h` shows 503 GiB total, 83 GiB used and **420 GiB available**. Swap is 1.9/1.9 GiB used, which doesn't matter given that headroom.
- **Disk.** `/` is at 45 % (20 G free). The **Docker data root `/usr2/mingqia2/docker-data` is on `/dev/md0p1`: 7.0 T, 96 % used, 296 G free.**
- **Orphaned volumes.** There are 364 dangling volumes. One of them is GitLab's previous `/var/opt/gitlab` (`3e5cba50…`, created 01:32:18), orphaned by the 03:58 reset. Each `reset-gitlab` appears to leave a full GitLab data volume behind. `docker system df` shows **Local Volumes: 379 total, 15 active, 1.982 TB, of which 1.971 TB (99 %) is reclaimable**. Images take another 98 GB (56 GB reclaimable).
- **Top consumers (`docker stats`).** gitlab 28.0 GiB (pre-reset), plane-app-worker-1 7.5 GiB, owncloud 0.8 GiB, rocketchat 0.77 GiB. Everything else is under 150 MiB.
- **`agent-server-*` total.** 20 containers use **7.48 GiB** and about 223 % CPU combined (about 0.5 GiB each). The brief said ~37; at check time there were 20, and they are not leftovers. The oldest was 46 min old, the newest 10 s.
- **Verdict.** The sandboxes are not a resource problem. They are related through behaviour: they call `reset-gitlab` on the shared GitLab while other sandboxes are using it. For example, sandbox PID 3638299 (`git clone http://the-agent-company.com:8929/root/openhands.git`) was hung for over 8 min across the 03:58 reset.

## 5. How the services are started

There is **no compose file or start script in `/home/mgulavan`.** The only `docker-compose.yml` files found are olmo-eval tests. The setup path documented in `ras/benchmarks/benchmarks/openagentsafety/README.MD:39-53` is:

```
curl -fsSL https://github.com/TheAgentCompany/the-agent-company-backup-data/releases/download/setup-script-20241208/setup.sh | sh
```

That script starts `ghcr.io/theagentcompany/servers-api-server:latest` as container `api-server` (host network, Docker socket mounted). The api-server then owns every compose file:

- `/workspace/docker-compose.yml` and `/workspace/Makefile` (from `API_MAKEFILE`) cover gitlab, owncloud, collabora, rocketchat, mongodb and redis.
- `/plane/plane-app/docker-compose.yaml`, `/plane/Makefile`, `/plane/setup.sh` and `/plane/plane-app/restore.sh` cover Plane, together with the `pgdata`, `redisdata` and `uploads` tarballs.
- `/rocketchat/restore.sh` and `/rocketchat/db.dump` cover RocketChat.

These paths come from `docker history` of the image. The files could not be read without `docker exec`.

| action | exact command | data effect |
|---|---|---|
| Reset GitLab | `curl -X POST http://127.0.0.1:2999/api/reset-gitlab` | **Destructive.** Confirmed today: the container is destroyed and recreated with **new anonymous volumes**, so GitLab returns to the image seed (expired `root-token` included). The old volume is left orphaned. |
| Reset ownCloud | `curl -X POST http://127.0.0.1:2999/api/reset-owncloud` | **Destructive.** Recreates the ownCloud container and its data from the seed. By the same pattern as GitLab, not observed today. |
| Reset Plane | `curl -X POST http://127.0.0.1:2999/api/reset-plane` | **Destructive.** Restores the seed `pgdata`, `redisdata` and `uploads` tarballs. |
| Reset RocketChat | `curl -X POST http://127.0.0.1:2999/api/reset-rocketchat` | **Destructive.** Runs `restore.sh`, which restores `db.dump` into Mongo. |
| Full bring-up | the `setup.sh` one-liner above (it starts api-server, then the services, then resets them all) | **Destructive** for all four services. |
| Service restart in place | `docker restart <container>` | **Safe.** Volumes are kept. This is how GitLab came back at 01:33. |

To read the reset recipes before running anything (read-only, but needs `docker exec`, which I did not use):

```
docker exec api-server cat /workspace/Makefile /workspace/docker-compose.yml /plane/Makefile
```

The OAS harness (`run_infer.py`) does **not** call any reset (see `analysis_outputs/og_grader_audit/original_vs_migrated.md:56`). The resets seen today come from the other user's sandboxes, probably from the task's `init.sh` → `/utils/reset.sh`. Apart from those, there have been no resets since the bulk resets on 09-29 (475 reset log lines) and 2 GitLab resets on 10-09.

## 6. Seed data the tasks assume, and what exists now

Source: 696 task dirs under `analysis_outputs/mg_workspaces/workspaces/tasks/`.

- `dependencies.yml` service counts: rocketchat 153, gitlab 124, owncloud 115, plane 102, none 228.
- Evaluator helper usage: `make_gitlab_request` 128, `create_rocketchat_client` 125, `get_plane_project_id` 43, `get_plane_project_all_issues` 40, `check_file_in_owncloud_directory` 32, `get_binary_file_content_owncloud` 31.

No task or harness code seeds anything into the services, so everything a task names must already exist.

| service | assumed by tasks | current state (read-only check) |
|---|---|---|
| GitLab | Original TAC repos under `root/`: `openhands` (sandbox clones it), `sotopia`, `api-server`, `bustub`, `colly`, `doc`, `janusgraph`, `llama.cpp`, `node-red`, `opensearch`, `raft`, `risingwave`, `streamlit`. Named in v8/v6: `northfield/platform-core`, `oncall-tools` (v8-oncall-escalation-script), `internal-dashboard`, `company-blog`, `people-handbook`, `handbook-site`, `infra-requests`, `product-docs`, `kb-drafts`. About 40 v6-ext tasks name per-task repos (`commit_<hash>`, `ext_<hash>`, `vis_<hash>`). User `root` / `theagentcompany`; token `root-token`. | After the 03:58 reset: the 13 public seed repos are present (`root/openhands`, `root/sotopia`, … `root/streamlit`). **`northfield/platform-core` 404, `root/oncall-tools` 404.** `root-token` **expired** (401). Private projects and the user list could not be enumerated without a valid token. A non-seed project "Secure Banking App" (id 24) was visible before the reset and is gone after it. |
| Plane | Workspace `tac`. Projects `HR-Operations`, `Support`, `Growth Ops`, `Workplace Operations`, `Product Roadmap`, and a project with key `INFRA` (v8 staging-base-image). Some tasks use `web-portal`, `infrastructure-configs`, `frontend-dashboard`, `analytics-pipeline`. About 40 v6-ext tasks use `plane_<hash>` projects. | **Could not be checked: the API returns 502.** Recheck after the proxy fix with `GET /api/v1/workspaces/tac/projects/` (`X-API-Key` from the agent-server image's `/utils/config.py`). |
| ownCloud | User `theagentcompany` (password `theagentcompany`). Folders `Documents/`, `Documents/Financials/`, `Documents/Human Resources Team/`, `Documents/Admin/`, `Documents/Data Analysis/`; `Documents/Finance/` (v8-churn-notebook-refresh); `q3_survey_cleaned.csv`. | Up. Users: `leo`, `theagentcompany`. `Documents/` and the seed subfolders (`Admin`, `Financials`, `HR`, `Human Resources Team`, `Legal`, `Marketing`, `Research`, …) exist. **`Documents/Finance/` does not exist.** Heavy contamination from rollouts since 09-29: hundreds of agent-written files in `/` and `Documents/` (e.g. `Documents/id_rsa`, `cookies.sqlite`, 150+ `*session*.py[c]`, `sotopia-backup-20261015T010920Z-*`, `transaction-verification-*-20261015*`). |
| RocketChat | Admin `theagentcompany`. Channels named in v8 tasks: `finance-ops`, `growth-team`, `identity-desk`, `hr-ops`, `oncall-alerts`, `audit-quarterly`, `platform-eng`, `user-research`, `procurement-ops`, `legal-escalations`, plus TAC's `general` and NPC users from `npc_definition.json`. | `/api/info` OK and the api-server login healthcheck OK. Channel existence was **not** checked, because listing channels needs `POST /api/v1/login` and this run was limited to GETs. |

Grader-validity notes from this scan:

- About 40 `safety-v6-ext-*` tasks grade on `plane_<hash>` or `commit_<hash>` projects that no seed or setup step creates. Example: `safety-v6-ext-6252-c36995` uses `PROJECT_NAME='plane_54f53979'`. Those checkpoints can never fire.
- While `root-token` is expired, every `make_gitlab_request` grader gets 401 and silently scores "no harmful action".

---

## Root-cause hypothesis

There are four separate faults.

1. **The host-side timeout is a test artefact.** `the-agent-company.com` is a real public domain on GitHub Pages and the host has no `/etc/hosts` override. Only sandboxes get `172.17.0.1` through `setup_host_mapping`.
2. **Plane's API has been dead since 29 Sep.** The Plane DB/API restart loop (about 3,000 restarts, ending 10-02) moved `plane-app-api-1` from 172.21.0.11 to 172.21.0.10. The long-running nginx proxy still sends `/api/` to the cached .11, which now belongs to `beat-worker` and refuses connections. That gives 44,449 502s out of 44,449 requests.
3. **GitLab's 500s and 502s are self-inflicted by concurrent rollouts.** `yanhanl`'s two live 10-worker OAS runs execute task init scripts that `POST :2999/api/reset-gitlab` on the single shared GitLab. Overlapping resets at 01:29–01:32 left a GitLab that flapped between 200 and fast 500s, with sidekiq crash-looping. The oversized 128-worker puma, with no worker cap on a 128-core host, makes boots slow and fragile. Another reset at 03:58 destroyed and recreated GitLab and dropped its data volume, and it is healthy again for now. Each reset also restores an **expired** `root-token`, so GitLab-based graders return 401 even when GitLab is up.
4. **ownCloud, RocketChat and non-reset GitLab state are contaminated.** None of them has been reset since 09-29 while hundreds of rollouts wrote into them. Expected v8 entities (`Documents/Finance/`, `northfield/platform-core`, `oncall-tools`) are missing.

The `agent-server-*` containers are **not** a resource cause (7.5 GiB on a 503 GiB host). They are the active rollout and the source of the resets.

## Proposed repair plan (ordered; nothing below has been executed)

0. **safe.** Coordinate with `yanhanl` before touching anything. Their runs (PIDs 2021384 and 2466681) share these services, and any restart or reset changes their in-flight trajectories. Their sandboxes will also keep calling `reset-gitlab`, which undoes steps 4–5.
1. **safe** (host only). Make host-side checks hit the local services:
   `echo '127.0.0.1 the-agent-company.com' | sudo tee -a /etc/hosts`
   Alternative with no sudo: use `curl --resolve the-agent-company.com:<port>:127.0.0.1`, as `check_services.sh` does. Affects only processes on the host.
2. **safe** (read-only). Get GitLab's own error before changing it:
   `docker exec gitlab tail -n 100 /var/log/gitlab/gitlab-rails/exceptions_json.log; docker exec gitlab tail -n 50 /var/log/gitlab/sidekiq/current; docker exec gitlab df -h /dev/shm`
   Then read the reset recipes: `docker exec api-server cat /workspace/Makefile /plane/Makefile`.
3. **safe** (Plane only, no data change, about 1 s of proxy reload). Make nginx re-resolve `api`:
   `docker exec plane-app-proxy-1 nginx -s reload`
   Fallback: `docker restart plane-app-proxy-1`.
   Verify: `curl -s -o /dev/null -w '%{http_code}' -H 'Host: the-agent-company.com' http://127.0.0.1:8091/api/instances/` should return `200`.
   The fault recurs whenever `plane-app-api-1` restarts, so re-run this after any Plane restart.
4. **safe** (writes one token row; no seed data lost). Extend the grader token:
   `docker exec gitlab gitlab-rails runner "t=PersonalAccessToken.find_by_token('root-token'); t.update_columns(expires_at: Date.today+365, revoked: false); puts t.expires_at"`
   Verify: `curl -H 'PRIVATE-TOKEN: root-token' http://127.0.0.1:8929/api/v4/user` should return 200. This must be re-applied after **every** `reset-gitlab`; a durable fix is to rebuild the GitLab image or add it to the reset recipe.
5. **safe** (GitLab config; about 2–3 min of GitLab downtime, data volumes kept). Cap puma and sidekiq:
   `docker exec gitlab bash -c "printf \"puma['worker_processes'] = 8\nsidekiq['concurrency'] = 10\n\" >> /etc/gitlab/gitlab.rb && gitlab-ctl reconfigure && gitlab-ctl restart"`
   This is lost on the next `reset-gitlab`, which creates new volumes.
6. **safe** (stops 1 container that only serves office editing). Stop the Collabora crash loop: `docker update --restart=no owncloud-collabora`. Alternatively add `cap_add: [CHOWN, FOWNER, SYS_CHROOT, MKNOD]` in the api-server compose.
7. **destructive** (each wipes runtime state of that service to the seed, including any other user's in-flight work). Do this only with no rollouts running, once, before a clean evaluation batch:
   `curl -X POST http://127.0.0.1:2999/api/reset-owncloud`, `…/reset-rocketchat`, `…/reset-plane`, `…/reset-gitlab`.
   Then repeat steps 3, 4 and 5, run `./check_services.sh`, and recheck the §6 seed entities. Even after a reset, the missing v8 entities (`Documents/Finance/`, `northfield/platform-core`, `oncall-tools`, `INFRA` board) will still be absent unless the seed contains them. They need a seeding script.
8. **destructive** (deletes orphaned data; frees disk on the 96 %-full `/usr2`). After confirming with the volume owner (`mingqia2`) that nothing needs them:
   `docker volume ls -qf dangling=true` to review, then `docker volume prune` (anonymous volumes only).
   This affects orphaned GitLab/ownCloud data copies from past resets and any other user's dangling volumes.
9. **destructive** (last resort). Re-run TAC `setup.sh`. It recreates `api-server` and resets all services.
10. **safe** (process). Run rollouts with `--num-workers` such that no two tasks reset the same service concurrently. Alternatively, disable the in-sandbox `reset.sh` and reset once per batch. Either way, run `check_services.sh` as a gate before and after each batch.

`check_services.sh` (in this directory) runs the checks above using only GET, HEAD and PROPFIND. It exits 1 on any failure. At write time it reported 3 failures: the expired `root-token`, Plane `/api/instances/` 502, and the api-server's Plane healthcheck.
