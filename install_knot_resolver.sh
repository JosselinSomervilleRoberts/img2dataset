#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Step 1: Update system and install prerequisites..."
# Update package lists and install necessary tools
sudo apt update
sudo apt install -y wget gnupg2 vim bind9

echo "Step 2: Configure Knot Resolver..."
# Download and install the Knot Resolver repository
wget https://secure.nic.cz/files/knot-resolver/knot-resolver-release.deb
sudo dpkg -i knot-resolver-release.deb
sudo apt update
sudo apt install -y knot-resolver

# Start and enable Knot Resolver services
sudo systemctl enable kresd@{1..4}.service
sudo systemctl start kresd@{1..4}.service

# Verify Knot Resolver is working
if dig @127.0.0.1 example.com | grep -q "ANSWER SECTION"; then
    echo "Knot Resolver is working!"
else
    echo "ERROR: Knot Resolver failed to resolve domains. Check its logs."
    exit 1
fi

echo "Step 3: Configure BIND9 resolver to handle high query rates..."
# Configure BIND9
BIND_CONFIG="/etc/bind/named.conf.options"

# Update the BIND configuration file with necessary options
sudo cat >"$BIND_CONFIG" <<EOF
options {
	directory "/var/cache/bind";

	// Performance optimizations for BIND9 resolver
	recursive-clients 10000;
	resolver-query-timeout 30000;
	max-clients-per-query 10000;
	max-cache-size 2000m;

	// Default system settings
	dnssec-validation auto;
	listen-on-v6 { any; };
};
EOF

echo "BIND9 configuration updated in $BIND_CONFIG"

# Restart BIND9 for the changes to take effect
sudo systemctl restart bind9

echo "Step 4: Set up system DNS settings to use BIND9 and Knot Resolver..."
# Update /etc/hosts (prevent sudo hostname resolution warnings)
sudo sh -c "echo $(hostname -I | awk '{print $1}') $(hostname) >> /etc/hosts"

# Stop systemd-resolved if it's running (avoid conflicts)
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved

# Update /etc/resolv.conf to ensure system uses BIND9 on localhost (127.0.0.1) for DNS
sudo rm -f /etc/resolv.conf
sudo sh -c "echo nameserver 127.0.0.1 > /etc/resolv.conf"

echo "Step 5: Verify the overall DNS functionality..."
# Test BIND9 by running a query directly against it
if dig @127.0.0.1 google.com | grep -q "ANSWER SECTION"; then
    echo "BIND9 is working as expected!"
else
    echo "ERROR: BIND9 is not resolving domains. Check its logs."
    exit 1
fi

# Test Knot Resolver with a direct query
if dig @127.0.0.1 example.com | grep -q "ANSWER SECTION"; then
    echo "Knot Resolver is working as a backup resolver!"
else
    echo "ERROR: Knot Resolver failed to resolve domains. Check its logs."
    exit 1
fi

echo "Setup Complete! Both BIND9 and Knot Resolver are installed and configured."
