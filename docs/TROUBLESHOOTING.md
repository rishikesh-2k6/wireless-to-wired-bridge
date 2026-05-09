# Troubleshooting Guide

Comprehensive guide for diagnosing and resolving common issues with the Wi-Fi to Ethernet bridge.

---

## Quick Fix

Run the automated troubleshooter first — it resolves most issues automatically:

```bash
sudo python3 scripts/troubleshoot.py
```

---

## Common Issues

### 1. TV/Device Gets No IP Address

**Symptoms:** Device shows "No network" or "DHCP failed"

**Diagnosis:**
```bash
# Check if dnsmasq is running
sudo systemctl status dnsmasq

# Check DHCP leases
cat /var/lib/misc/dnsmasq.leases

# Check eth0 has the correct IP
ip addr show eth0
```

**Fix:**
```bash
sudo systemctl restart dnsmasq
# If eth0 has no IP:
sudo ip addr add 192.168.2.1/24 dev eth0
sudo ip link set eth0 up
```

---

### 2. Device Gets IP But No Internet

**Symptoms:** Device connects but can't browse or stream

**Diagnosis:**
```bash
# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward
# Should output: 1

# Check NAT rules
sudo iptables -t nat -L POSTROUTING -v -n
# Should show MASQUERADE on wlan0

# Check FORWARD rules
sudo iptables -L FORWARD -v -n
```

**Fix:**
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
sudo sh -c 'iptables-save > /etc/iptables.ipv4.nat'
```

---

### 3. Streaming Apps Won't Play (YouTube, Netflix, Hotstar)

**Symptoms:** App opens and loads thumbnails, but videos buffer forever

**Root Cause:** MTU mismatch between Wi-Fi and Ethernet causes TCP fragmentation issues

**Fix:**
```bash
# Add TCPMSS clamping rule
sudo iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400
sudo sh -c 'iptables-save > /etc/iptables.ipv4.nat'
```

---

### 4. Bridge Stops Working After Reboot

**Diagnosis:**
```bash
# Check if iptables rules persisted
sudo iptables -L -n
# If empty, rules didn't survive reboot

# Check auto-load script
cat /etc/NetworkManager/dispatcher.d/99-iptables
```

**Fix:** Re-run the setup script:
```bash
sudo python3 scripts/setup.py
```

---

### 5. Pi Has No Wi-Fi Connection

**Diagnosis:**
```bash
# Check Wi-Fi status
nmcli device status
nmcli connection show

# Test connectivity
ping -c 3 8.8.8.8
```

**Fix:**
```bash
# Reconnect to Wi-Fi
sudo nmcli device wifi connect "YOUR_WIFI_NAME" password "YOUR_PASSWORD"
```

---

### 6. Duplicate TCPMSS Rules

**Symptoms:** Slow network or routing issues

**Diagnosis:**
```bash
sudo iptables -L FORWARD -v -n | grep TCPMSS
# Should show exactly ONE TCPMSS rule
```

**Fix:**
```bash
# Flush and re-apply rules
sudo iptables -F FORWARD
sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
sudo iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400
sudo sh -c 'iptables-save > /etc/iptables.ipv4.nat'
```

---

## Diagnostic Commands Reference

| Command | Purpose |
|---------|---------|
| `ip addr show eth0` | Check Ethernet IP |
| `ip addr show wlan0` | Check Wi-Fi IP |
| `cat /proc/sys/net/ipv4/ip_forward` | Verify IP forwarding |
| `sudo iptables -t nat -L -v -n` | View NAT rules |
| `sudo iptables -L FORWARD -v -n` | View FORWARD rules |
| `sudo systemctl status dnsmasq` | Check DHCP server |
| `cat /var/lib/misc/dnsmasq.leases` | View DHCP leases |
| `ping -c 3 8.8.8.8` | Test internet |
| `sudo tcpdump -i eth0 -n -c 20` | Capture Ethernet traffic |
| `nmcli device status` | Network interface overview |

---

## Still Having Issues?

1. Run the troubleshooter: `sudo python3 scripts/troubleshoot.py`
2. Reboot the Pi: `sudo reboot`
3. Re-run setup: `sudo python3 scripts/setup.py`
4. [Open an issue](https://github.com/rishikesh-2k6/wireless-to-wired-bridge/issues) with the output of:
   ```bash
   ip addr show
   sudo iptables -L -v -n
   sudo iptables -t nat -L -v -n
   sudo systemctl status dnsmasq
   cat /proc/sys/net/ipv4/ip_forward
   ```
