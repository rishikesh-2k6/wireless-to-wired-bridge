#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   Raspberry Pi Wi-Fi to Ethernet Bridge              ║
║   One-Click Full Setup Script                        ║
║   Just run: sudo python3 pi_bridge_setup.py          ║
╚══════════════════════════════════════════════════════╝

What this does:
  - Installs dnsmasq
  - Assigns static IP to eth0 (192.168.2.1)
  - Configures DHCP for connected devices (TV gets 192.168.2.10-50)
  - Enables IP forwarding (permanent)
  - Sets up NAT masquerading via iptables
  - Fixes MTU/TCPMSS issue (fixes streaming apps)
  - Saves all rules so they survive reboot
  - Auto-loads everything on boot

After running this script:
  - Plug Ethernet cable from Pi to TV
  - Set TV network to Wired/DHCP
  - Done! TV gets internet through Pi
"""

import subprocess
import sys
import os
import time

# ── Colors ──────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ  {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠  {msg}{RESET}")
def header(msg):
    print(f"\n{BOLD}{BLUE}┌─────────────────────────────────────────┐")
    print(f"│  {msg:<39}│")
    print(f"└─────────────────────────────────────────┘{RESET}")

def run(cmd, silent=False):
    """Run a shell command. Returns (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True
        )
        if not silent and result.returncode != 0 and result.stderr:
            pass  # We handle errors in each step
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def run_ok(description, cmd):
    """Run command and print result."""
    out, code = run(cmd)
    if code == 0:
        ok(description)
        return True
    else:
        fail(f"{description}")
        info(f"Command: {cmd}")
        return False

def write_file(path, content):
    """Write content to a file."""
    try:
        with open(path, "w") as f:
            f.write(content)
        return True
    except Exception as e:
        fail(f"Could not write {path}: {e}")
        return False

def append_to_file(path, content):
    """Append content to file if not already present."""
    try:
        try:
            with open(path, "r") as f:
                existing = f.read()
        except FileNotFoundError:
            existing = ""
        if content.strip() in existing:
            return True  # Already present
        with open(path, "a") as f:
            f.write("\n" + content + "\n")
        return True
    except Exception as e:
        fail(f"Could not update {path}: {e}")
        return False

# ════════════════════════════════════════════════════
# STEP 1: Root Check
# ════════════════════════════════════════════════════
def check_root():
    header("Step 1: Checking Permissions")
    if os.geteuid() != 0:
        fail("This script must be run as root!")
        print(f"\n  Run: {BOLD}sudo python3 pi_bridge_setup.py{RESET}\n")
        sys.exit(1)
    ok("Running as root")

# ════════════════════════════════════════════════════
# STEP 2: Detect Interfaces
# ════════════════════════════════════════════════════
def detect_interfaces():
    header("Step 2: Detecting Network Interfaces")
    out, _ = run("ip link show")
    
    wifi_iface = "wlan0"
    eth_iface  = "eth0"

    # Try to detect actual interface names
    for line in out.splitlines():
        if "wlan" in line:
            wifi_iface = line.split(":")[1].strip().split("@")[0]
        if "eth" in line or "enx" in line or "enp" in line:
            name = line.split(":")[1].strip().split("@")[0]
            if name != "lo":
                eth_iface = name

    # Check wlan0 has internet
    _, code = run(f"ping -c 1 -W 3 8.8.8.8 -I {wifi_iface}", silent=True)
    if code == 0:
        ok(f"Wi-Fi interface: {wifi_iface} (has internet)")
    else:
        warn(f"Wi-Fi interface: {wifi_iface} (no internet detected — make sure Pi is connected to Wi-Fi first!)")

    ok(f"Ethernet interface: {eth_iface}")
    return wifi_iface, eth_iface

# ════════════════════════════════════════════════════
# STEP 3: Install dnsmasq
# ════════════════════════════════════════════════════
def install_dnsmasq():
    header("Step 3: Installing dnsmasq")
    out, _ = run("dpkg -l dnsmasq 2>/dev/null | grep '^ii'", silent=True)
    if out:
        ok("dnsmasq already installed")
        return True
    info("Installing dnsmasq...")
    run("apt update -qq")
    return run_ok("dnsmasq installed", "apt install -y dnsmasq")

# ════════════════════════════════════════════════════
# STEP 4: Configure Static IP on eth0
# ════════════════════════════════════════════════════
def configure_eth0(eth_iface):
    header(f"Step 4: Setting Static IP on {eth_iface}")

    # Remove old eth0-static connection if exists
    run("nmcli connection delete eth0-static 2>/dev/null", silent=True)

    # Create new static connection
    success = run_ok(
        f"Created static IP profile for {eth_iface}",
        f"nmcli connection add type ethernet ifname {eth_iface} "
        f"con-name eth0-static ip4 192.168.2.1/24 ipv4.method manual"
    )
    if not success:
        return False

    # Modify to ensure correct interface binding
    run(f"nmcli connection modify eth0-static connection.interface-name {eth_iface}")

    # Bring it up
    run_ok(f"Activated eth0-static on {eth_iface}",
           "nmcli connection up eth0-static")

    # Verify
    out, _ = run(f"ip addr show {eth_iface}")
    if "192.168.2.1" in out:
        ok(f"{eth_iface} has IP: 192.168.2.1/24")
        return True
    else:
        # Fallback: manual assignment
        warn("nmcli profile not active, assigning IP manually")
        run(f"ip addr flush dev {eth_iface}")
        run(f"ip addr add 192.168.2.1/24 dev {eth_iface}")
        run(f"ip link set {eth_iface} up")
        ok(f"{eth_iface} IP assigned manually: 192.168.2.1/24")
        return True

# ════════════════════════════════════════════════════
# STEP 5: Configure dnsmasq
# ════════════════════════════════════════════════════
def configure_dnsmasq(eth_iface):
    header("Step 5: Configuring dnsmasq (DHCP Server)")

    dnsmasq_config = f"""# Pi Bridge - dnsmasq config
interface={eth_iface}
dhcp-range=192.168.2.10,192.168.2.50,255.255.255.0,24h
server=8.8.8.8
server=8.8.4.4
dhcp-option=6,8.8.8.8,8.8.4.4
dhcp-option=3,192.168.2.1
bogus-priv
domain-needed
"""

    # Backup original config
    run("cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak 2>/dev/null", silent=True)

    # Read existing config and append if not already configured
    try:
        with open("/etc/dnsmasq.conf", "r") as f:
            existing = f.read()
    except:
        existing = ""

    if f"interface={eth_iface}" not in existing:
        with open("/etc/dnsmasq.conf", "a") as f:
            f.write(dnsmasq_config)
        ok("dnsmasq configured with DHCP range 192.168.2.10-50")
    else:
        ok("dnsmasq already configured")

    # Enable and restart
    run_ok("dnsmasq enabled on boot", "systemctl enable dnsmasq")
    run_ok("dnsmasq restarted", "systemctl restart dnsmasq")
    return True

# ════════════════════════════════════════════════════
# STEP 6: Enable IP Forwarding (Permanent)
# ════════════════════════════════════════════════════
def enable_ip_forward():
    header("Step 6: Enabling IP Forwarding (Permanent)")

    # Enable immediately
    run("sysctl -w net.ipv4.ip_forward=1")

    # Make permanent via sysctl.d
    sysctl_conf = "/etc/sysctl.d/99-ipforward.conf"
    write_file(sysctl_conf, "net.ipv4.ip_forward=1\n")
    ok("IP forwarding enabled permanently")

    # Also ensure it's in /etc/sysctl.conf
    append_to_file("/etc/sysctl.conf", "net.ipv4.ip_forward=1")

    # Verify
    out, _ = run("cat /proc/sys/net/ipv4/ip_forward")
    if out.strip() == "1":
        ok("IP forwarding is ON")
        return True
    else:
        fail("IP forwarding failed to enable")
        return False

# ════════════════════════════════════════════════════
# STEP 7: Setup iptables (NAT + Forwarding + MTU fix)
# ════════════════════════════════════════════════════
def setup_iptables(wifi_iface, eth_iface):
    header("Step 7: Configuring iptables Rules")

    # Flush existing rules cleanly
    run("iptables -F")
    run("iptables -t nat -F")
    run("iptables -P FORWARD ACCEPT")
    run("iptables -P INPUT ACCEPT")
    run("iptables -P OUTPUT ACCEPT")

    # NAT masquerade: share internet from wlan0
    run_ok("NAT MASQUERADE rule added",
           f"iptables -t nat -A POSTROUTING -o {wifi_iface} -j MASQUERADE")

    # Forward established connections back to TV
    run_ok("FORWARD rule: established connections",
           "iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT")

    # Forward new connections from eth0 to wlan0
    run_ok(f"FORWARD rule: {eth_iface} → {wifi_iface}",
           f"iptables -A FORWARD -i {eth_iface} -o {wifi_iface} -j ACCEPT")

    # MTU fix: prevents streaming apps from loading but not opening
    run_ok("MTU fix (TCPMSS) added — fixes YouTube/Netflix/Hotstar",
           "iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400")

    # Save rules
    run_ok("iptables rules saved",
           "sh -c 'iptables-save > /etc/iptables.ipv4.nat'")

    return True

# ════════════════════════════════════════════════════
# STEP 8: Auto-load iptables on Boot
# ════════════════════════════════════════════════════
def setup_autoload():
    header("Step 8: Setting Up Auto-load on Boot")

    dispatcher_path = "/etc/NetworkManager/dispatcher.d/99-iptables"
    dispatcher_content = """#!/bin/sh
# Auto-load iptables rules for Pi bridge
iptables-restore < /etc/iptables.ipv4.nat
"""
    write_file(dispatcher_path, dispatcher_content)
    run(f"chmod +x {dispatcher_path}")
    ok("iptables auto-load script created")

    # Also add to rc.local as backup
    rc_local = "/etc/rc.local"
    try:
        with open(rc_local, "r") as f:
            content = f.read()
    except:
        content = "#!/bin/sh -e\nexit 0\n"

    if "iptables-restore" not in content:
        content = content.replace(
            "exit 0",
            "iptables-restore < /etc/iptables.ipv4.nat\nexit 0"
        )
        write_file(rc_local, content)
        run(f"chmod +x {rc_local}")
        ok("rc.local backup auto-load configured")
    else:
        ok("rc.local already has iptables restore")

    return True

# ════════════════════════════════════════════════════
# STEP 9: Final Verification
# ════════════════════════════════════════════════════
def verify_setup(wifi_iface, eth_iface):
    header("Step 9: Final Verification")

    checks = {
        "IP forwarding ON":
            ("cat /proc/sys/net/ipv4/ip_forward", "1"),
        f"{eth_iface} has 192.168.2.1":
            (f"ip addr show {eth_iface}", "192.168.2.1"),
        "dnsmasq running":
            ("systemctl is-active dnsmasq", "active"),
        "NAT MASQUERADE rule exists":
            (f"iptables -t nat -L POSTROUTING -n", "MASQUERADE"),
        "FORWARD rule exists":
            ("iptables -L FORWARD -n", eth_iface),
        "MTU fix exists":
            ("iptables -L FORWARD -n", "TCPMSS"),
        "iptables rules saved":
            ("cat /etc/iptables.ipv4.nat", "MASQUERADE"),
        "Pi has internet":
            (f"ping -c 1 -W 3 8.8.8.8", "1 received"),
    }

    all_ok = True
    for label, (cmd, expected) in checks.items():
        out, code = run(cmd, silent=True)
        if expected in out or code == 0 and expected == "1 received" and "1 received" in out:
            ok(label)
        elif expected in out:
            ok(label)
        else:
            # Recheck ping differently
            if "internet" in label.lower():
                _, code2 = run("ping -c 1 -W 3 8.8.8.8")
                if code2 == 0:
                    ok(label)
                    continue
            fail(f"{label} — may need manual check")
            all_ok = False

    return all_ok

# ════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════
def main():
    print(f"""
{BOLD}{CYAN}
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   🍓 Raspberry Pi Wi-Fi → Ethernet Bridge Setup      ║
║      One-Click Full Automatic Configuration          ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
{RESET}
  This script will:
  {GREEN}→{RESET} Install dnsmasq
  {GREEN}→{RESET} Set static IP on eth0 (192.168.2.1)
  {GREEN}→{RESET} Configure DHCP for your TV
  {GREEN}→{RESET} Enable IP forwarding permanently
  {GREEN}→{RESET} Set up NAT and iptables rules
  {GREEN}→{RESET} Fix MTU issue (streaming apps)
  {GREEN}→{RESET} Auto-load everything on reboot

  {YELLOW}Make sure your Pi is connected to Wi-Fi first!{RESET}
""")

    input(f"  {BOLD}Press Enter to start setup...{RESET}")

    start = time.time()

    check_root()
    wifi_iface, eth_iface = detect_interfaces()
    install_dnsmasq()
    configure_eth0(eth_iface)
    configure_dnsmasq(eth_iface)
    enable_ip_forward()
    setup_iptables(wifi_iface, eth_iface)
    setup_autoload()
    all_ok = verify_setup(wifi_iface, eth_iface)

    elapsed = round(time.time() - start, 1)

    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗
║                    SETUP COMPLETE                    ║
╚══════════════════════════════════════════════════════╝{RESET}
""")

    if all_ok:
        print(f"""  {GREEN}{BOLD}🎉 Everything configured successfully in {elapsed}s!{RESET}

  {BOLD}Next steps:{RESET}
  {GREEN}1.{RESET} Plug Ethernet cable from Pi → TV
  {GREEN}2.{RESET} On TV: Settings → Network → Wired → Automatic
  {GREEN}3.{RESET} TV will get IP: 192.168.2.10-50
  {GREEN}4.{RESET} Open YouTube, Netflix, Hotstar — enjoy! 🎬

  {BOLD}To troubleshoot anytime:{RESET}
  {CYAN}sudo python3 pi_bridge_fix.py{RESET}

  {BOLD}This setup survives reboots automatically.{RESET}
  {BOLD}No HDMI or keyboard needed on Pi after this.{RESET}
""")
    else:
        print(f"""  {YELLOW}{BOLD}⚠  Setup done but some checks failed.{RESET}
  {YELLOW}Try rebooting the Pi:{RESET} {BOLD}sudo reboot{RESET}
  {YELLOW}Then run the troubleshooter:{RESET} {BOLD}sudo python3 pi_bridge_fix.py{RESET}
""")

    # Ask about reboot
    print(f"  {BOLD}Reboot Pi now to apply all changes? (y/n): {RESET}", end="")
    try:
        ans = input().strip().lower()
        if ans == "y":
            print(f"\n  {CYAN}Rebooting in 3 seconds...{RESET}")
            time.sleep(3)
            run("reboot")
    except KeyboardInterrupt:
        print()

if __name__ == "__main__":
    main()
