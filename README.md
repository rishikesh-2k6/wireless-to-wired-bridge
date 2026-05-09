<div align="center">

# 🍓 Wireless-to-Wired Bridge

### *Turn your Raspberry Pi into a Wi-Fi to Ethernet adapter — one command, zero hassle.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4-C51A4A?logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Raspberry%20Pi%20OS-FCC624?logo=linux&logoColor=black)](https://www.raspberrypi.com/software/)
[![Maintenance](https://img.shields.io/badge/Maintained-Yes-green.svg)](https://github.com/rishikesh-2k6/wireless-to-wired-bridge/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)

<br>

**Share your home Wi-Fi over Ethernet using a Raspberry Pi 4.**
Connect smart TVs, gaming consoles, PCs, or any device that needs a wired connection — automatically configured and reboot-persistent.

<br>

[**Quick Start**](#-quick-start) · [**Features**](#-features) · [**Architecture**](#-architecture) · [**Troubleshooting**](#-troubleshooting) · [**Contributing**](#-contributing)

---

</div>

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Screenshots & Demo](#-screenshots--demo)
- [Tech Stack](#-tech-stack)
- [Future Improvements](#-future-improvements)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## 🔍 Overview

Many devices — smart TVs, gaming consoles, desktop PCs — work better with a wired Ethernet connection but are too far from the router. This project solves that problem by turning a **Raspberry Pi 4** into a transparent **Wi-Fi to Ethernet bridge**.

The Pi connects to your home Wi-Fi and forwards internet through its Ethernet port to any connected device. A single Python script handles the entire setup: installing packages, configuring DHCP, setting up NAT, and persisting everything across reboots.

```
   📶 Wi-Fi Router                🍓 Raspberry Pi 4              🖥️ TV / PC / Console
  ┌──────────────┐    Wireless    ┌──────────────────┐   Ethernet   ┌──────────────────┐
  │              │ ◄────────────► │   wlan0 ←→ eth0  │ ◄──────────► │                  │
  │   Internet   │  192.168.1.x   │   NAT + DHCP     │ 192.168.2.x  │   Gets Internet  │
  │   Source     │                │   Bridge          │              │   Automatically   │
  └──────────────┘                └──────────────────┘              └──────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🚀 **One-Click Setup** | Single script configures everything automatically |
| 🔧 **Auto Troubleshooter** | Diagnoses and fixes common issues with one command |
| 🌐 **NAT Masquerading** | Transparent internet sharing via iptables |
| 📡 **Built-in DHCP Server** | Automatic IP assignment via dnsmasq |
| 🔄 **Reboot Persistent** | All rules and configs survive power cycles |
| 🎬 **Streaming Fix** | MTU/TCPMSS clamping for YouTube, Netflix, Hotstar |
| 🔍 **Interface Auto-Detection** | Automatically finds wlan0/eth0 interfaces |
| 🎨 **Rich Terminal UI** | Color-coded progress with step-by-step feedback |
| 🛡️ **Safe & Idempotent** | Re-run safely without breaking existing config |
| 📋 **9-Point Verification** | Post-setup health check validates everything |

---

## 🏗️ Architecture

### Network Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RASPBERRY PI 4                              │
│                                                                     │
│   ┌──────────┐    IP Forwarding    ┌──────────┐                    │
│   │  wlan0   │ ◄─────────────────► │   eth0   │                    │
│   │ (Wi-Fi)  │    NAT Masquerade   │ (Wired)  │                    │
│   │ DHCP IP  │                     │192.168.2.1│                    │
│   └────┬─────┘                     └────┬─────┘                    │
│        │                                │                          │
│   ┌────┴────────────────────────────────┴─────┐                    │
│   │              iptables Rules               │                    │
│   │  • POSTROUTING → MASQUERADE on wlan0      │                    │
│   │  • FORWARD → RELATED,ESTABLISHED accept   │                    │
│   │  • FORWARD → eth0 → wlan0 accept          │                    │
│   │  • FORWARD → TCPMSS clamp to 1400         │                    │
│   └───────────────────────────────────────────┘                    │
│                                                                     │
│   ┌───────────────────┐    ┌──────────────────────┐                │
│   │     dnsmasq       │    │   Persistence Layer  │                │
│   │  DHCP: .2.10–.50  │    │  • sysctl.d config   │                │
│   │  DNS: 8.8.8.8     │    │  • iptables-save     │                │
│   │  GW:  192.168.2.1 │    │  • NM dispatcher     │                │
│   └───────────────────┘    └──────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
         ▲                                    │
         │ Wi-Fi                              │ Ethernet
         ▼                                    ▼
   ┌──────────┐                        ┌──────────────┐
   │  Router  │                        │  Client      │
   │ Internet │                        │  Device      │
   └──────────┘                        └──────────────┘
```

### Setup Pipeline

```
sudo python3 scripts/setup.py
         │
         ├── 1. Root permission check
         ├── 2. Auto-detect wlan0 & eth0 interfaces
         ├── 3. Install dnsmasq (DHCP/DNS server)
         ├── 4. Assign static IP 192.168.2.1 to eth0
         ├── 5. Configure DHCP range (192.168.2.10–50)
         ├── 6. Enable IP forwarding (kernel + persistent)
         ├── 7. Configure iptables (NAT + forward + MTU fix)
         ├── 8. Persist rules (dispatcher + rc.local)
         └── 9. Run 8-point verification suite
                  │
                  └── ✅ Done — plug in your device!
```

> 📖 For a deeper technical dive, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 📦 Prerequisites

| Requirement | Details |
|-------------|---------|
| **Hardware** | Raspberry Pi 4 (Model B recommended) |
| **OS** | Raspberry Pi OS Bookworm or Bullseye |
| **Network** | Pi connected to Wi-Fi with internet access |
| **Cable** | Ethernet cable (Cat5e or better) |
| **Python** | Python 3.7+ (pre-installed on Raspberry Pi OS) |
| **Privileges** | Root access (`sudo`) |

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/rishikesh-2k6/wireless-to-wired-bridge.git
cd wireless-to-wired-bridge
```

### 2. Run the Setup Script

```bash
sudo python3 scripts/setup.py
```

### 3. Connect Your Device

```
Raspberry Pi [eth0] ──── Ethernet Cable ────► TV / PC / Console
```

Set your device's network to **Wired / DHCP / Automatic** — that's it! 🎉

---

## 📖 Usage

### One-Click Setup

```bash
# SSH into your Raspberry Pi
ssh pi@<your-pi-ip>

# Clone and run
git clone https://github.com/rishikesh-2k6/wireless-to-wired-bridge.git
cd wireless-to-wired-bridge
sudo python3 scripts/setup.py
```

The script will display a step-by-step progress log:

```
╔══════════════════════════════════════════════════════╗
║   🍓 Raspberry Pi Wi-Fi → Ethernet Bridge Setup      ║
║      One-Click Full Automatic Configuration          ║
╚══════════════════════════════════════════════════════╝

┌─────────────────────────────────────────┐
│  Step 1: Checking Permissions           │
└─────────────────────────────────────────┘
  ✅ Running as root

┌─────────────────────────────────────────┐
│  Step 2: Detecting Network Interfaces   │
└─────────────────────────────────────────┘
  ✅ Wi-Fi interface: wlan0 (has internet)
  ✅ Ethernet interface: eth0

  ... (continues through all 9 steps)

╔══════════════════════════════════════════════════════╗
║                    SETUP COMPLETE                    ║
╚══════════════════════════════════════════════════════╝

  🎉 Everything configured successfully!
```

### Troubleshooting Mode

If something isn't working, run the diagnostics tool:

```bash
sudo python3 scripts/troubleshoot.py
```

It will automatically detect and fix common issues:

```
╔══════════════════════════════════════════════╗
║   Raspberry Pi Bridge Troubleshooter v1.0    ║
║   Wi-Fi → Ethernet Internet Sharing Fix      ║
╚══════════════════════════════════════════════╝

── Checking IP Forwarding
✅ IP forwarding is ON

── Checking eth0 IP Address
✅ eth0 has correct IP: 192.168.2.1

── Checking dnsmasq
✅ dnsmasq is running

── Checking NAT (iptables MASQUERADE)
❌ NAT MASQUERADE rule missing
⚠  Fixing: Add MASQUERADE rule
✅ Fixed: Add MASQUERADE rule

  ... (8 checks total)
```

---

## 📁 Project Structure

```
wireless-to-wired-bridge/
│
├── scripts/
│   ├── setup.py              # One-click bridge setup (main script)
│   └── troubleshoot.py       # Diagnostic & auto-fix tool
│
├── config/
│   ├── dnsmasq.conf          # Reference DHCP/DNS configuration
│   ├── sysctl.conf           # IP forwarding sysctl config
│   └── iptables.rules.sh     # Reference iptables rules script
│
├── docs/
│   ├── ARCHITECTURE.md       # Technical architecture deep-dive
│   ├── TROUBLESHOOTING.md    # Comprehensive troubleshooting guide
│   └── images/               # Screenshots and diagrams
│       └── .gitkeep
│
├── .gitignore                # Python + OS gitignore rules
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guidelines
├── LICENSE                   # MIT License
└── README.md                 # This file
```

---

## ⚙️ Configuration

### Default Network Settings

| Setting | Value | Configurable In |
|---------|-------|-----------------|
| **Bridge subnet** | `192.168.2.0/24` | `scripts/setup.py` |
| **Gateway IP** | `192.168.2.1` | `scripts/setup.py` |
| **DHCP range** | `192.168.2.10 – 192.168.2.50` | `config/dnsmasq.conf` |
| **DHCP lease time** | `24 hours` | `config/dnsmasq.conf` |
| **DNS servers** | `8.8.8.8`, `8.8.4.4` | `config/dnsmasq.conf` |
| **TCP MSS** | `1400 bytes` | `scripts/setup.py` |

### Customization

To change the bridge subnet (e.g., to `10.0.0.x`):

1. Edit `scripts/setup.py` — update all `192.168.2` references
2. Edit `config/dnsmasq.conf` — update DHCP range and gateway
3. Re-run: `sudo python3 scripts/setup.py`

---

## 🔧 Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| TV gets no IP | `sudo systemctl restart dnsmasq` |
| IP assigned but no internet | `sudo sysctl -w net.ipv4.ip_forward=1` |
| Streaming apps buffer forever | `sudo iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400` |
| Bridge dies after reboot | Re-run `sudo python3 scripts/setup.py` |
| Pi has no Wi-Fi | `sudo nmcli device wifi connect "SSID" password "PASS"` |

> 📖 For detailed solutions, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 📸 Screenshots & Demo

> 🚧 *Screenshots and demo GIFs will be added here.*

<!-- 
### Setup Script Output
![Setup Script](docs/images/setup-output.png)

### Troubleshooter Output  
![Troubleshooter](docs/images/troubleshoot-output.png)

### Network Topology Diagram
![Network Diagram](docs/images/network-diagram.png)

### Demo GIF
![Demo](docs/images/demo.gif)
-->

<details>
<summary>📌 How to capture screenshots</summary>

```bash
# Record setup output to a file
sudo python3 scripts/setup.py 2>&1 | tee setup-output.log

# Take a screenshot on Pi Desktop
scrot docs/images/setup-output.png

# Or use SSH + script recording
script -q setup-recording.txt
sudo python3 scripts/setup.py
exit
```

</details>

---

## 🛠️ Tech Stack

| Technology | Role |
|------------|------|
| **Python 3** | Setup & troubleshooting automation |
| **iptables** | NAT masquerading & packet forwarding |
| **dnsmasq** | DHCP server & DNS forwarding |
| **NetworkManager** | Interface management & persistence |
| **sysctl** | Kernel parameter configuration |
| **systemd** | Service management |

---

## 🔮 Future Improvements

- [ ] 📊 Web-based dashboard for monitoring connected devices & bandwidth
- [ ] 🔒 Firewall rules for enhanced security on the bridge subnet
- [ ] 📱 Support for Raspberry Pi 5 and Pi Zero 2 W
- [ ] 🐳 Docker-based deployment option
- [ ] 📈 Bandwidth monitoring and logging
- [ ] 🌐 IPv6 support and dual-stack bridging
- [ ] ⚡ Performance benchmarks and optimization guide
- [ ] 🔄 Automatic Wi-Fi reconnection handler
- [ ] 📝 Configuration file (`bridge.yaml`) for customization without editing scripts
- [ ] 🧪 Automated integration test suite

---

## 🤝 Contributing

Contributions are welcome! Whether it's a bug fix, feature suggestion, or documentation improvement — every contribution matters.

1. **Fork** this repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m "feat: add amazing feature"`
4. **Push** to your fork: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

> 📖 See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this project for personal and commercial purposes.

---

## 🙏 Acknowledgments

- [Raspberry Pi Foundation](https://www.raspberrypi.com/) — for the incredible hardware platform
- [dnsmasq](https://thekelleys.org.uk/dnsmasq/doc.html) — lightweight DHCP and DNS server
- [iptables](https://www.netfilter.org/) — the Linux packet filtering framework
- The open-source community for inspiration and knowledge sharing

---

<div align="center">

**Built with ❤️ on a Raspberry Pi 4**

If this project helped you, consider giving it a ⭐

[Report a Bug](https://github.com/rishikesh-2k6/wireless-to-wired-bridge/issues) · [Request a Feature](https://github.com/rishikesh-2k6/wireless-to-wired-bridge/issues) · [Contribute](CONTRIBUTING.md)

</div>
