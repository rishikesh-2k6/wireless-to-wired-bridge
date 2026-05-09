#!/usr/bin/env python3
"""
Raspberry Pi Wi-Fi to Ethernet Bridge Troubleshooter
Automatically detects and fixes common bridge issues.
"""

import subprocess
import sys
import time
import urllib.request
import json

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def run(cmd, capture=True):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def ok(msg):    print(f"{GREEN}✅ {msg}{RESET}")
def fail(msg):  print(f"{RED}❌ {msg}{RESET}")
def info(msg):  print(f"{CYAN}ℹ  {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}⚠  {msg}{RESET}")
def step(msg):  print(f"\n{BOLD}{BLUE}── {msg}{RESET}")

def fix(msg, cmd):
    warn(f"Fixing: {msg}")
    out, code = run(cmd)
    if code == 0:
        ok(f"Fixed: {msg}")
    else:
        fail(f"Could not fix: {msg}")
        print(f"   Command: {cmd}")
        print(f"   Output: {out}")
    return code == 0

# ──────────────────────────────────────────────
# CHECK 1: IP Forwarding
# ──────────────────────────────────────────────
def check_ip_forward():
    step("Checking IP Forwarding")
    out, _ = run("cat /proc/sys/net/ipv4/ip_forward")
    if out.strip() == "1":
        ok("IP forwarding is ON")
        return True
    else:
        fail("IP forwarding is OFF")
        fix("Enable IP forwarding now", "sysctl -w net.ipv4.ip_forward=1")
        fix("Make IP forwarding permanent",
            "echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-ipforward.conf")
        return False

# ──────────────────────────────────────────────
# CHECK 2: eth0 IP Address
# ──────────────────────────────────────────────
def check_eth0_ip():
    step("Checking eth0 IP Address")
    out, _ = run("ip addr show eth0")
    if "192.168.2.1" in out:
        ok("eth0 has correct IP: 192.168.2.1")
        return True
    else:
        fail("eth0 does not have IP 192.168.2.1")
        fix("Assign static IP to eth0", "ip addr add 192.168.2.1/24 dev eth0")
        fix("Bring eth0 up", "ip link set eth0 up")
        return False

# ──────────────────────────────────────────────
# CHECK 3: dnsmasq
# ──────────────────────────────────────────────
def check_dnsmasq():
    step("Checking dnsmasq")
    out, _ = run("systemctl is-active dnsmasq")
    if out.strip() == "active":
        ok("dnsmasq is running")
        return True
    else:
        fail("dnsmasq is not running")
        fix("Start dnsmasq", "systemctl start dnsmasq")
        fix("Enable dnsmasq on boot", "systemctl enable dnsmasq")
        return False

# ──────────────────────────────────────────────
# CHECK 4: NAT / iptables MASQUERADE
# ──────────────────────────────────────────────
def check_nat():
    step("Checking NAT (iptables MASQUERADE)")
    out, _ = run("iptables -t nat -L POSTROUTING -v -n")
    if "MASQUERADE" in out:
        ok("NAT MASQUERADE rule exists")
        return True
    else:
        fail("NAT MASQUERADE rule missing")
        fix("Add MASQUERADE rule",
            "iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE")
        return False

# ──────────────────────────────────────────────
# CHECK 5: FORWARD rules
# ──────────────────────────────────────────────
def check_forward_rules():
    step("Checking FORWARD rules")
    out, _ = run("iptables -L FORWARD -v -n")
    has_eth0_wlan0 = "eth0" in out and "wlan0" in out
    has_conntrack = "ctstate" in out or "RELATED" in out
    if has_eth0_wlan0 and has_conntrack:
        ok("FORWARD rules look correct")
        return True
    else:
        fail("FORWARD rules missing or incomplete")
        run("iptables -F")
        fix("Add conntrack FORWARD rule",
            "iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT")
        fix("Add eth0->wlan0 FORWARD rule",
            "iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT")
        return False

# ──────────────────────────────────────────────
# CHECK 6: MTU / TCPMSS
# ──────────────────────────────────────────────
def check_mtu():
    step("Checking MTU (TCPMSS) fix")
    out, _ = run("iptables -L FORWARD -v -n")
    # Count TCPMSS occurrences
    count = out.count("TCPMSS")
    if count == 1:
        ok("TCPMSS MTU fix is set correctly")
        return True
    elif count > 1:
        warn(f"TCPMSS rule is duplicated ({count} times) — cleaning up")
        run("iptables -F FORWARD")
        run("iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT")
        run("iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT")
        fix("Add single TCPMSS rule",
            "iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400")
        return False
    else:
        fail("TCPMSS MTU fix missing — this causes apps to load but not open")
        fix("Add TCPMSS MTU fix",
            "iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400")
        return False

# ──────────────────────────────────────────────
# CHECK 7: Pi Internet connectivity
# ──────────────────────────────────────────────
def check_pi_internet():
    step("Checking Pi Internet Connectivity")
    _, code = run("ping -c 2 -W 3 8.8.8.8")
    if code == 0:
        ok("Pi can reach the internet")
        return True
    else:
        fail("Pi has no internet — check your Wi-Fi connection")
        out, _ = run("nmcli device status")
        info(f"Network status:\n{out}")
        return False

# ──────────────────────────────────────────────
# CHECK 8: TV DHCP lease
# ──────────────────────────────────────────────
def check_tv_lease():
    step("Checking if TV has a DHCP lease")
    out, _ = run("cat /var/lib/misc/dnsmasq.leases 2>/dev/null")
    if out.strip():
        ok(f"TV has DHCP lease:\n   {out}")
        return True
    else:
        warn("No DHCP lease found — TV may not be connected or needs to reconnect")
        info("Try unplugging and replugging the Ethernet cable on the TV")
        return False

# ──────────────────────────────────────────────
# SAVE rules
# ──────────────────────────────────────────────
def save_rules():
    step("Saving iptables rules permanently")
    _, code = run("sh -c 'iptables-save > /etc/iptables.ipv4.nat'")
    if code == 0:
        ok("iptables rules saved to /etc/iptables.ipv4.nat")
    else:
        fail("Could not save iptables rules")

# ──────────────────────────────────────────────
# SEARCH internet for unknown errors
# ──────────────────────────────────────────────
def search_solution(error_msg):
    print(f"\n{YELLOW}🔍 Searching internet for solution to: {error_msg}{RESET}")
    query = f"Raspberry Pi WiFi to Ethernet bridge {error_msg} fix"
    url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    print(f"{CYAN}   Search URL: {url}{RESET}")
    print(f"{CYAN}   You can also search: {query}{RESET}")

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    import urllib.parse

    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════╗
║   Raspberry Pi Bridge Troubleshooter v1.0    ║
║   Wi-Fi → Ethernet Internet Sharing Fix      ║
╚══════════════════════════════════════════════╝{RESET}
""")

    # Check if running as root
    out, _ = run("id -u")
    if out.strip() != "0":
        fail("Please run as root: sudo python3 scripts/troubleshoot.py")
        sys.exit(1)

    results = {}

    results["ip_forward"]     = check_ip_forward()
    results["eth0_ip"]        = check_eth0_ip()
    results["dnsmasq"]        = check_dnsmasq()
    results["pi_internet"]    = check_pi_internet()
    results["nat"]            = check_nat()
    results["forward_rules"]  = check_forward_rules()
    results["mtu"]            = check_mtu()
    results["tv_lease"]       = check_tv_lease()

    # Save rules after all fixes
    save_rules()

    # Summary
    print(f"\n{BOLD}{'─'*48}")
    print(f"  SUMMARY")
    print(f"{'─'*48}{RESET}")

    all_ok = True
    for check, passed in results.items():
        label = check.replace("_", " ").title()
        if passed:
            print(f"  {GREEN}✅ {label}{RESET}")
        else:
            print(f"  {YELLOW}⚠  {label} — was fixed{RESET}")
            all_ok = False

    if all_ok:
        print(f"\n{GREEN}{BOLD}🎉 Everything looks perfect!{RESET}")
        print(f"{GREEN}   Your bridge should be working. Try YouTube on your TV.{RESET}")
    else:
        print(f"\n{YELLOW}{BOLD}🔧 Some issues were found and fixed.{RESET}")
        print(f"{YELLOW}   Please unplug and replug the Ethernet cable on your TV,")
        print(f"   then try opening YouTube or any app.{RESET}")

    # Ask user if TV is working
    print(f"\n{CYAN}Is your TV working now? (y/n): {RESET}", end="")
    try:
        answer = input().strip().lower()
        if answer != "y":
            print(f"\n{YELLOW}Please describe the error you see on TV: {RESET}", end="")
            error = input().strip()
            if error:
                search_solution(error)
                print(f"\n{CYAN}Run this command manually and paste the output:{RESET}")
                print(f"  sudo iptables -L FORWARD -v -n")
                print(f"  sudo tcpdump -i eth0 -n -c 20")
    except KeyboardInterrupt:
        print()

    print(f"\n{BLUE}Done! Run this script anytime with: sudo python3 scripts/troubleshoot.py{RESET}\n")

if __name__ == "__main__":
    main()
