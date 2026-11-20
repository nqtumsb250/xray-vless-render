#!/usr/bin/env python3
"""Clean Vertos Compute entrypoint for a personal Xray VLESS node.

- Listens on $PORT (Vertos-assigned, fallback 3000) on 0.0.0.0.
- TLS is terminated by Vertos at the edge (Automatic HTTPS/SSL), so the
  Xray inbound is plain WebSocket here. No self-signed cert, no SNI
  impersonation of any other domain: the client SNI is the service's
  own Vertos domain.
- UUID and WS path come from environment variables, never hard-coded
  in a public repo. The Xray binary keeps its real name, `xray`.
"""
import json
import os
import stat
import subprocess
import sys
import urllib.request
import zipfile

XRAY_URL = "https://github.com/XTLS/Xray-core/releases/download/v26.11.9/Xray-linux-64.zip"
XRAY_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xray")


def download_xray():
    if os.path.exists(XRAY_BIN):
        return
    print("Downloading Xray v26.11.9 ...", flush=True)
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xray.zip")
    urllib.request.urlretrieve(XRAY_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extract("xray", os.path.dirname(os.path.abspath(__file__)))
    os.chmod(XRAY_BIN, os.stat(XRAY_BIN).st_mode | stat.S_IEXEC)
    os.remove(zip_path)
    print("Xray downloaded.", flush=True)


def main():
    port = int(os.environ.get("PORT", "3000"))
    uuid = os.environ.get("VLESS_UUID")
    if not uuid:
        print("ERROR: VLESS_UUID environment variable is not set", file=sys.stderr)
        sys.exit(1)
    ws_path = os.environ.get("WS_PATH", "/ws")

    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "listen": "0.0.0.0",
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": uuid, "level": 0}],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "none",
                    "wsSettings": {"path": ws_path},
                },
            }
        ],
        "outbounds": [
            {"protocol": "freedom", "settings": {}},
            {"protocol": "blackhole", "settings": {}, "tag": "blocked"},
        ],
    }
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"Config written: VLESS+WS on 0.0.0.0:{port}, path {ws_path}", flush=True)

    download_xray()
    print("Starting xray ...", flush=True)
    proc = subprocess.run([XRAY_BIN, "-config", cfg_path])
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
