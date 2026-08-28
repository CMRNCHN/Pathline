# Byteful Mac Proxy

A small local GUI that pastes a Byteful residential proxy string and turns it into the macOS system SOCKS proxy.

This is a standalone helper. It is not part of the Pathline desktop call path.

## On your MacBook

```bash
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py
```

Or double-click `Byteful Mac Proxy.command` in Finder. A browser window opens on `127.0.0.1` only.

1. Copy a proxy from the Byteful dashboard (Residential generator).
2. Paste it into the GUI. Host, port, username, and password fill in automatically.
3. Click **Apply to this Mac**.
4. Click **Test SOCKS5h** to confirm Byteful returns an exit IP.
5. Click **Turn proxy off** when you want your normal IP back.

Accepted paste formats:

```
residential.byteful.com:8000:username:password
socks5h://username:password@residential.byteful.com:8000
socks5://username:password@residential.byteful.com:8864
username:password@residential.byteful.com:8000
```

Username targeting from Byteful (`_s_`, `_ttl_`, `_c_`, `_city_`, `_smartpath`, and so on) is left intact. Byteful auto-detects HTTP vs SOCKS on the same host and port; this helper always enables **SOCKS**.

## What it changes

For each selected network service it:

- Turns on the macOS SOCKS firewall proxy with your Byteful host/port/user
- Turns off HTTP, HTTPS, FTP, streaming, Gopher, PAC, and auto-discovery so they do not bypass SOCKS
- Bypasses `localhost`, `127.0.0.1`, `::1`, and `*.local`

**Entire Mac** updates every enabled service (Wi-Fi, Ethernet, USB, Thunderbolt, …). **Active network only** updates the default-route service.

macOS may ask for an administrator password.

## Limits

- Run this on the Mac you want to proxy. It cannot push settings to an iPhone.
- Safari and most Cocoa apps follow System Settings. Some apps (and some CLI tools) ignore the OS proxy.
- The Test button uses `curl --proxy socks5h://…` (remote DNS). The system SOCKS setting is not full SOCKS5h for every app; some DNS can still leak locally.
- Terminal programs need extra env vars if they ignore System Settings:

```bash
export ALL_PROXY="socks5h://USER:PASS@HOST:PORT"
export NO_PROXY="localhost,127.0.0.1,.local"
```

## Without the GUI

```bash
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --apply 'residential.byteful.com:8000:USER:PASS'
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --off
python3 tools/byteful-mac-proxy/byteful_mac_proxy.py --self-test
```
