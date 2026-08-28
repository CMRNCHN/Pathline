# Byteful Mac Proxy

A small local GUI that turns a Byteful residential proxy into the macOS system HTTP, HTTPS, and SOCKS proxies.

This is a standalone helper. It is not part of the Pathline desktop call path.

## On your MacBook

```bash
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py
```

Or double-click `Byteful Mac Proxy.command` in Finder. A browser window opens on `127.0.0.1` only.

1. Paste a Byteful CSV, a `curl -x` command, or a single proxy string. You can also choose the CSV with the file picker.
2. If the CSV has many sticky rows, pick a session from the dropdown (each `_s_` id is a different sticky IP).
3. Click **Apply to this Mac**.
4. Click **Test proxy** to hit `https://ipinfo.io/json` (SOCKS5h, then HTTP if needed).
5. Click **Turn proxy off** when you want your normal IP back.

Accepted paste formats:

```
Scheme,Host,Port,Username,Password
socks5,residential.byteful.com,8166,user_c_us_city_portsmouth_s_SESSION,password

curl -x http://user:pass@residential.byteful.com:8166 "https://ipinfo.io/json"

socks5h://user:pass@residential.byteful.com:8166
residential.byteful.com:8166:user:password
```

Username targeting (`_s_`, `_ttl_`, `_c_`, `_city_`, `_state_`, `_smartpath`) is left intact. Byteful auto-detects HTTP vs SOCKS on the same host and port. Apply enables **HTTP, HTTPS, and SOCKS** so Safari and `curl -x http://…` both follow the proxy.

## What it changes

For each selected network service it:

- Sets the HTTP, HTTPS, and SOCKS proxies to the Byteful host/port with your username and password
- Turns off FTP, streaming, Gopher, PAC, and auto-discovery
- Bypasses `localhost`, `127.0.0.1`, `::1`, and `*.local`

**Entire Mac** updates every enabled service (Wi-Fi, Ethernet, USB, Thunderbolt, …). **Active network only** updates the default-route service.

macOS may ask for an administrator password.

## Limits

- Run this on the Mac you want to proxy. It cannot push settings to an iPhone.
- Some apps ignore System Settings. Terminal programs that ignore the OS proxy still need:

```bash
export ALL_PROXY="socks5h://USER:PASS@HOST:PORT"
# or, matching a Byteful curl -x:
export https_proxy="http://USER:PASS@HOST:PORT"
export NO_PROXY="localhost,127.0.0.1,.local"
```

## Without the GUI

```bash
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --apply 'curl -x http://USER:PASS@residential.byteful.com:8166 https://ipinfo.io/json'
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --off
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --self-test
```
