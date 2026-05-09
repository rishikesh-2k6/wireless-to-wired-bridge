# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-09

### Added

- **One-click setup script** (`scripts/setup.py`) — fully automated Raspberry Pi Wi-Fi to Ethernet bridge configuration
- **Troubleshooter script** (`scripts/troubleshoot.py`) — automatic diagnosis and repair of common networking issues
- **Reference configuration files** for dnsmasq, sysctl, and iptables
- Auto-detection of Wi-Fi (`wlan0`) and Ethernet (`eth0`) interfaces
- DHCP server configuration via dnsmasq (IP range: `192.168.2.10–50`)
- Static IP assignment (`192.168.2.1/24`) on the Ethernet interface
- NAT masquerading via iptables for internet sharing
- MTU/TCPMSS fix to resolve streaming app issues (YouTube, Netflix, Hotstar)
- Persistent iptables rules that survive reboots
- NetworkManager dispatcher integration for automatic rule loading
- Colored terminal output with step-by-step progress indicators
- Comprehensive verification checks after setup
- Interactive troubleshooter with fix-and-verify workflow
- Professional documentation and repository structure
