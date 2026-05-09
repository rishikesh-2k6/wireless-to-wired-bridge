# Network Architecture

Detailed technical explanation of how the Wi-Fi to Ethernet bridge works.

---

## Network Topology

```
┌─────────────┐      Wi-Fi       ┌─────────────────┐     Ethernet      ┌──────────────┐
│  Home Wi-Fi │  ◄──────────────►│  Raspberry Pi 4 │ ◄────────────────►│  TV / PC /   │
│   Router    │    192.168.1.x   │    (Bridge)      │    192.168.2.x   │   Console    │
│  (Gateway)  │                  │                  │                  │  (Client)    │
└─────────────┘                  └─────────────────┘                  └──────────────┘
  Internet ▲                        wlan0  │  eth0                      Gets IP via
  Source   │                    192.168.1.x │ 192.168.2.1                  DHCP
           │                               │
     ISP Modem                        NAT + IP Forwarding
```

## IP Address Scheme

| Interface | IP Address | Subnet | Role |
|-----------|-----------|--------|------|
| `wlan0` (Pi) | DHCP from router | `192.168.1.0/24` | Wi-Fi client |
| `eth0` (Pi) | `192.168.2.1` | `192.168.2.0/24` | Gateway for clients |
| Client device | `192.168.2.10–50` | `192.168.2.0/24` | DHCP-assigned |

## Data Flow

```
Client Device                Raspberry Pi                    Router/Internet
     │                            │                               │
     │  1. DHCP Request           │                               │
     │ ──────────────────────────►│                               │
     │                            │                               │
     │  2. DHCP Response          │                               │
     │  IP: 192.168.2.x          │                               │
     │  GW: 192.168.2.1          │                               │
     │ ◄──────────────────────────│                               │
     │                            │                               │
     │  3. HTTP/TCP Traffic       │  4. NAT Masquerade           │
     │  dst: internet             │  src: 192.168.2.x → wlan0 IP │
     │ ──────────────────────────►│ ──────────────────────────────►│
     │                            │                               │
     │                            │  5. Response                  │
     │  6. De-NAT + Forward      │  dst: Pi's wlan0 IP           │
     │ ◄──────────────────────────│ ◄──────────────────────────────│
     │                            │                               │
```

## Components

### 1. dnsmasq (DHCP + DNS Server)
- Listens on `eth0` only
- Assigns IPs in `192.168.2.10–50` range
- Forwards DNS queries to Google DNS (`8.8.8.8`, `8.8.4.4`)
- Pushes gateway (`192.168.2.1`) to clients

### 2. IP Forwarding (`sysctl`)
- Enables the Linux kernel to route packets between `eth0` and `wlan0`
- Configured via `/etc/sysctl.d/99-ipforward.conf`

### 3. iptables Rules

| Table | Chain | Rule | Purpose |
|-------|-------|------|---------|
| `nat` | `POSTROUTING` | `MASQUERADE -o wlan0` | Source NAT for outgoing traffic |
| `filter` | `FORWARD` | `RELATED,ESTABLISHED -j ACCEPT` | Allow return traffic |
| `filter` | `FORWARD` | `-i eth0 -o wlan0 -j ACCEPT` | Allow client → internet |
| `filter` | `FORWARD` | `TCPMSS --set-mss 1400` | Fix MTU issues for streaming |

### 4. Persistence Layer
- **iptables**: Saved to `/etc/iptables.ipv4.nat`, restored via NetworkManager dispatcher
- **IP forwarding**: Persistent via sysctl drop-in config
- **DHCP**: dnsmasq enabled as systemd service
- **Static IP**: NetworkManager connection profile `eth0-static`

## MTU / TCPMSS Fix Explained

Wi-Fi networks often have a lower MTU (e.g., 1460) than Ethernet (1500). When a client sends a full-size TCP segment through the bridge, the Wi-Fi link may need to fragment it — but modern routers set the "Don't Fragment" flag, causing silent drops.

The TCPMSS rule clamps the MSS to 1400 bytes during the TCP handshake, ensuring packets fit within the Wi-Fi MTU without fragmentation. This specifically fixes issues where:
- Apps load but videos won't play
- Pages partially render
- Streaming services time out
