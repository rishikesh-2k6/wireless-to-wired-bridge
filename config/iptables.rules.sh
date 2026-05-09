#!/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║   iptables Rules — NAT & Forwarding                 ║
# ║   Reference script for manual configuration         ║
# ╚══════════════════════════════════════════════════════╝
#
# These rules are automatically applied by the setup script.
# This file is provided as a reference for manual setup.
#
# Usage: sudo bash config/iptables.rules.sh

set -e

WIFI_IFACE="wlan0"
ETH_IFACE="eth0"

echo "Flushing existing rules..."
iptables -F
iptables -t nat -F

echo "Setting default policies..."
iptables -P FORWARD ACCEPT
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT

echo "Adding NAT MASQUERADE rule..."
iptables -t nat -A POSTROUTING -o "$WIFI_IFACE" -j MASQUERADE

echo "Adding FORWARD rules..."
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i "$ETH_IFACE" -o "$WIFI_IFACE" -j ACCEPT

echo "Adding MTU/TCPMSS fix (prevents streaming issues)..."
iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1400

echo "Saving rules..."
iptables-save > /etc/iptables.ipv4.nat

echo "Done! Rules applied and saved."
