# Byteful Mac Proxy

Standalone helper (not part of the Pathline call path). It pastes a Byteful CSV and routes the Mac through a **local forwarder** so System Settings never stores the Byteful password (avoids Keychain loops and `Authenticated Proxy Enabled: 0`).

Apply probes sticky sessions and **skips Washington DC**. It prefers Portsmouth / Norfolk / Chesapeake.

## On the MacBook

```bash
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py
```

Or double-click `Byteful Mac Proxy.command`.

1. Paste the Byteful CSV (or pick the file).
2. Click **Apply to this Mac**. Keep this process running.
3. Turn **VPN** and **Limit IP address tracking** off.
4. Safari → https://ipinfo.io — expect Hampton Roads, Virginia, not DC.
5. **Turn proxy off** when done (also stops the forwarder).

macOS may ask for an administrator password once. `Authenticated Proxy Enabled: 0` is expected: the Mac talks to `127.0.0.1:8118` with no password; the forwarder adds Byteful auth.

Leave the Python GUI/forwarder running. If you quit it, Safari drops off Byteful.

## Without the GUI

```bash
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --apply "$(cat your-byteful.csv)"
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --off
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --self-test
```
