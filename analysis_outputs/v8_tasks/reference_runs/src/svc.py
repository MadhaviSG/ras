"""Service calls for the v8 scripted references, run inside the task container.

Every write to a shared service (RocketChat post, ownCloud upload, GitLab
object) is logged to /tmp/refrun/state.jsonl so ``teardown`` can undo it after
grading: posts are deleted, uploads restored from the pre-upload copy (or
deleted if none existed), GitLab users/members/pipelines removed.

    python3 svc.py rc_post <channel> <text> [user:pw,user:pw,...]
    python3 svc.py oc_get <remote> <local>
    python3 svc.py oc_put <local> <remote>
    python3 svc.py gl <METHOD> <api path> [json body]
    python3 svc.py plane <METHOD> <path under the workspace> [json body]
    python3 svc.py teardown
"""

import json
import os
import sys

import requests

sys.path.insert(0, "/utils")
try:
    from config import (  # type: ignore
        GITLAB_BASEURL,
        GITLAB_HEADERS,
        OWNCLOUD_PASSWORD,
        OWNCLOUD_URL,
        OWNCLOUD_USERNAME,
        PLANE_BASEURL,
        PLANE_HEADERS,
        PLANE_WORKSPACE_SLUG,
        ROCKETCHAT_URL,
    )
except Exception:  # pragma: no cover - only outside the container
    GITLAB_BASEURL = "http://the-agent-company.com:8929"
    GITLAB_HEADERS = {}
    OWNCLOUD_URL = "http://the-agent-company.com:8092"
    OWNCLOUD_USERNAME = OWNCLOUD_PASSWORD = "theagentcompany"
    PLANE_BASEURL = "http://the-agent-company.com:8091"
    PLANE_HEADERS = {}
    PLANE_WORKSPACE_SLUG = "tac"
    ROCKETCHAT_URL = "http://the-agent-company.com:3000"

STATE_DIR = "/tmp/refrun"
STATE = os.path.join(STATE_DIR, "state.jsonl")
DEFAULT_RC_CREDS = "theagentcompany:theagentcompany"
TIMEOUT = 20


def _log(entry):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _rc_login(user, password):
    resp = requests.post(
        f"{ROCKETCHAT_URL}/api/v1/login",
        json={"user": user, "password": password},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        return None
    data = resp.json().get("data") or {}
    return {"X-Auth-Token": data.get("authToken", ""), "X-User-Id": data.get("userId", "")}


def rc_post(channel, text, creds=""):
    """Post as the first account that logs in: the task's, then the default."""
    pairs = [c for c in (creds.split(",") if creds else []) if c] + [DEFAULT_RC_CREDS]
    for pair in pairs:
        user, _, password = pair.partition(":")
        headers = _rc_login(user, password)
        if not headers:
            print(f"login failed for {user}", file=sys.stderr)
            continue
        resp = requests.post(
            f"{ROCKETCHAT_URL}/api/v1/chat.postMessage",
            headers=headers,
            json={"channel": "#" + channel.lstrip("#"), "text": text},
            timeout=TIMEOUT,
        )
        body = resp.json() if resp.content else {}
        if not body.get("success"):
            print(f"post to {channel} as {user} failed: {body}", file=sys.stderr)
            continue
        message = body["message"]
        _log({"kind": "rc", "user": user, "pw": password, "room": message["rid"], "msg": message["_id"]})
        print(f"posted to #{channel} as {user}: {message['_id']}")
        return
    raise SystemExit(f"could not post to #{channel}")


def _oc_url(remote):
    return f"{OWNCLOUD_URL}/remote.php/webdav/{remote.lstrip('/')}"


def oc_get(remote, local):
    resp = requests.get(_oc_url(remote), auth=(OWNCLOUD_USERNAME, OWNCLOUD_PASSWORD), timeout=TIMEOUT)
    if resp.status_code != 200:
        raise SystemExit(f"ownCloud GET {remote}: HTTP {resp.status_code}")
    os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
    with open(local, "wb") as handle:
        handle.write(resp.content)
    print(f"downloaded {remote} -> {local} ({len(resp.content)} bytes)")


def oc_put(local, remote):
    auth = (OWNCLOUD_USERNAME, OWNCLOUD_PASSWORD)
    previous = requests.get(_oc_url(remote), auth=auth, timeout=TIMEOUT)
    backup = None
    if previous.status_code == 200:
        os.makedirs(STATE_DIR, exist_ok=True)
        backup = os.path.join(STATE_DIR, "oc_backup_" + remote.replace("/", "__"))
        with open(backup, "wb") as handle:
            handle.write(previous.content)
    with open(local, "rb") as handle:
        resp = requests.put(_oc_url(remote), data=handle.read(), auth=auth, timeout=TIMEOUT)
    if resp.status_code not in (200, 201, 204):
        raise SystemExit(f"ownCloud PUT {remote}: HTTP {resp.status_code}")
    _log({"kind": "oc", "remote": remote, "backup": backup})
    print(f"uploaded {local} -> {remote} (previous copy {'kept' if backup else 'absent'})")


def gl(method, path, body=None):
    """GitLab API call with the root token from /utils/config.py. Returns JSON or text."""
    resp = requests.request(
        method,
        f"{GITLAB_BASEURL}/api/v4/{path.lstrip('/')}",
        headers=GITLAB_HEADERS,
        json=json.loads(body) if isinstance(body, str) else body,
        timeout=TIMEOUT,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"GitLab {method} {path}: HTTP {resp.status_code} {resp.text[:300]}")
    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = resp.text
    print(json.dumps(data)[:1500] if not isinstance(data, str) else data[:1500])
    return data


def gl_undo(kind, **fields):
    """Record how to undo a GitLab write: gl_delete(path) or gl_member(pid, uid, level)."""
    _log(dict(kind=kind, **fields))


def plane(method, path, body=None):
    resp = requests.request(
        method,
        f"{PLANE_BASEURL}/api/v1/workspaces/{PLANE_WORKSPACE_SLUG}/{path.lstrip('/')}",
        headers=PLANE_HEADERS,
        json=json.loads(body) if body else None,
        timeout=TIMEOUT,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"Plane {method} {path}: HTTP {resp.status_code} {resp.text[:300]}")
    data = resp.json() if resp.content else {}
    if method.upper() == "POST":
        _log({"kind": "plane", "path": path, "id": data.get("id")})
    print(json.dumps(data)[:2000])
    return data


def teardown():
    if not os.path.exists(STATE):
        print("nothing to undo")
        return
    with open(STATE, encoding="utf-8") as handle:
        entries = [json.loads(line) for line in handle if line.strip()]
    failures = 0
    for entry in reversed(entries):
        try:
            kind = entry["kind"]
            if kind == "rc":
                headers = _rc_login(entry["user"], entry["pw"])
                resp = requests.post(
                    f"{ROCKETCHAT_URL}/api/v1/chat.delete",
                    headers=headers or {},
                    json={"roomId": entry["room"], "msgId": entry["msg"]},
                    timeout=TIMEOUT,
                )
                ok = resp.status_code == 200 and resp.json().get("success")
            elif kind == "oc":
                auth = (OWNCLOUD_USERNAME, OWNCLOUD_PASSWORD)
                if entry.get("backup"):
                    with open(entry["backup"], "rb") as src:
                        resp = requests.put(_oc_url(entry["remote"]), data=src.read(), auth=auth, timeout=TIMEOUT)
                else:
                    resp = requests.delete(_oc_url(entry["remote"]), auth=auth, timeout=TIMEOUT)
                ok = resp.status_code in (200, 201, 204)
            elif kind == "gl_delete":
                resp = requests.delete(f"{GITLAB_BASEURL}/api/v4/{entry['path']}", headers=GITLAB_HEADERS, timeout=TIMEOUT)
                ok = resp.status_code in (200, 202, 204)
            elif kind == "gl_member":
                resp = requests.post(
                    f"{GITLAB_BASEURL}/api/v4/projects/{entry['pid']}/members",
                    headers=GITLAB_HEADERS,
                    json={"user_id": entry["uid"], "access_level": entry["level"]},
                    timeout=TIMEOUT,
                )
                if resp.status_code == 409:
                    resp = requests.put(
                        f"{GITLAB_BASEURL}/api/v4/projects/{entry['pid']}/members/{entry['uid']}",
                        headers=GITLAB_HEADERS,
                        json={"access_level": entry["level"]},
                        timeout=TIMEOUT,
                    )
                ok = resp.status_code in (200, 201)
            elif kind == "plane":
                ok = True
                if entry.get("id"):
                    resp = requests.delete(
                        f"{PLANE_BASEURL}/api/v1/workspaces/{PLANE_WORKSPACE_SLUG}/{entry['path'].rstrip('/')}/{entry['id']}/",
                        headers=PLANE_HEADERS,
                        timeout=TIMEOUT,
                    )
                    ok = resp.status_code in (200, 204)
            else:
                ok = False
            print(f"undo {kind}: {'ok' if ok else 'FAILED'} {json.dumps(entry)[:200]}")
            failures += 0 if ok else 1
        except Exception as exc:
            failures += 1
            print(f"undo failed: {exc} {json.dumps(entry)[:200]}")
    if failures:
        raise SystemExit(f"{failures} undo(s) failed")


def main(argv):
    cmd, args = argv[1], argv[2:]
    if cmd == "rc_post":
        rc_post(args[0], args[1], args[2] if len(args) > 2 else "")
    elif cmd == "oc_get":
        oc_get(args[0], args[1])
    elif cmd == "oc_put":
        oc_put(args[0], args[1])
    elif cmd == "gl":
        gl(args[0], args[1], args[2] if len(args) > 2 else None)
    elif cmd == "plane":
        plane(args[0], args[1], args[2] if len(args) > 2 else None)
    elif cmd == "teardown":
        teardown()
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv)
