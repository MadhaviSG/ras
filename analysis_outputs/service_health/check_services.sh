#!/usr/bin/env bash
# Health check for TheAgentCompany services used by OpenAgentSafety.
# Read-only: issues only GET/PROPFIND requests. Exits non-zero if any check fails.
#
# Usage: ./check_services.sh [TARGET_IP]
#   TARGET_IP defaults to 172.17.0.1 (the docker0 gateway, which is what sandboxes
#   use via run_infer.setup_host_mapping). Requests carry Host: the-agent-company.com
#   via curl --resolve, so the result does not depend on the host's /etc/hosts.
# Env: GITLAB_TOKEN (default root-token), OC_USER/OC_PASS (default theagentcompany),
#      GITLAB_TRIES (default 10).
set -u
IP="${1:-172.17.0.1}"
H=the-agent-company.com
GITLAB_TOKEN="${GITLAB_TOKEN:-root-token}"
OC_USER="${OC_USER:-theagentcompany}"; OC_PASS="${OC_PASS:-theagentcompany}"
TRIES="${GITLAB_TRIES:-10}"
FAIL=0; WARN=0
R=(--resolve "$H:8929:$IP" --resolve "$H:8091:$IP" --resolve "$H:8092:$IP" --resolve "$H:3000:$IP")
ok()   { printf '  [OK]   %s\n' "$*"; }
bad()  { printf '  [FAIL] %s\n' "$*"; FAIL=$((FAIL+1)); }
warn() { printf '  [WARN] %s\n' "$*"; WARN=$((WARN+1)); }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time "${2:-10}" "${R[@]}" "$1"; }

echo "== Name resolution"
res=$(getent ahostsv4 "$H" | awk 'NR==1{print $1}')
case "$res" in
  127.*|172.17.0.1) ok "host resolves $H -> $res" ;;
  "") warn "host cannot resolve $H (fine for sandboxes; host-side tools need /etc/hosts entry)" ;;
  *)  warn "host resolves $H -> $res (public DNS, NOT the local services; add '127.0.0.1 $H' to /etc/hosts for host-side use)" ;;
esac

echo "== Containers"
for c in gitlab owncloud rocketchat rocketchat-mongodb redis-stack api-server \
         plane-app-proxy-1 plane-app-api-1 plane-app-worker-1 plane-app-plane-db-1 plane-app-plane-redis-1 plane-app-plane-minio-1; do
  s=$(docker inspect --format '{{.State.Status}} {{.RestartCount}}' "$c" 2>/dev/null) || { bad "$c missing"; continue; }
  [ "${s%% *}" = running ] && ok "$c ${s%% *} (restarts=${s##* })" || bad "$c ${s}"
done

echo "== GitLab :8929 ($TRIES tries; any 5xx fails)"
n5=0; n2=0
for i in $(seq 1 "$TRIES"); do
  c=$(code "http://$H:8929/api/v4/projects?per_page=1")
  case "$c" in 2*) n2=$((n2+1));; 5*|000) n5=$((n5+1));; esac
done
[ "$n5" -eq 0 ] && ok "api/v4/projects: $n2/$TRIES OK" || bad "api/v4/projects: $n5/$TRIES returned 5xx/timeout"
tok=$(curl -s --max-time 10 "${R[@]}" -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "http://$H:8929/api/v4/user")
case "$tok" in
  *'"username"'*) ok "grader token valid (user $(echo "$tok" | sed -E 's/.*"username":"([^"]+)".*/\1/'))" ;;
  *expired*)      bad "grader token '$GITLAB_TOKEN' is EXPIRED -> GitLab graders get 401" ;;
  *)              bad "grader token check failed: $(echo "$tok" | head -c 120)" ;;
esac
for p in root%2Fopenhands root%2Fsotopia; do
  c=000; for i in 1 2 3 4 5; do c=$(code "http://$H:8929/api/v4/projects/$p"); [ "$c" = 200 ] && break; done
  [ "$c" = 200 ] && ok "seed project ${p//%2F//} present" || bad "seed project ${p//%2F//}: HTTP $c"
done

echo "== Plane :8091"
c=$(code "http://$H:8091/"); [ "$c" = 200 ] && ok "web / -> 200" || bad "web / -> $c"
c=$(code "http://$H:8091/api/instances/"); [ "$c" = 200 ] && ok "api/instances/ -> 200" || bad "api/instances/ -> $c (502 = proxy cannot reach plane-app-api)"

echo "== RocketChat :3000"
b=$(curl -s --max-time 10 "${R[@]}" "http://$H:3000/api/info")
case "$b" in *'"success":true'*) ok "api/info $b" ;; *) bad "api/info -> $(echo "$b" | head -c 120)" ;; esac

echo "== ownCloud :8092"
b=$(curl -s --max-time 10 "${R[@]}" "http://$H:8092/status.php")
case "$b" in *'"installed":true'*'"maintenance":false'*) ok "status.php installed, not in maintenance" ;; *) bad "status.php -> $(echo "$b" | head -c 120)" ;; esac
c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "${R[@]}" -u "$OC_USER:$OC_PASS" -X PROPFIND -H 'Depth: 0' "http://$H:8092/remote.php/webdav/Documents/")
[ "$c" = 207 ] && ok "WebDAV Documents/ -> 207" || bad "WebDAV Documents/ -> $c"

echo "== TAC api-server :2999 healthchecks"
for s in gitlab owncloud plane rocketchat redis; do
  b=$(curl -s --max-time 30 "http://127.0.0.1:2999/api/healthcheck/$s")
  case "$b" in *'is up'*|*'success'*|*'"rocketchat":200'*) ok "$s: $b" ;; *) bad "$s: $b" ;; esac
done

echo "== Summary: $FAIL failed, $WARN warnings"
[ "$FAIL" -eq 0 ]
