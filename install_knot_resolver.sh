#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status
set -u # Treat unset variables as errors

# Helper function for error handling
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

log "Starting setup for Knot Resolver and BIND9 DNS resolver"

# Exit on errors
trap 'log "Error occurred at $BASH_COMMAND on line $LINENO"; exit 1;' ERR

### SETUP KNOT RESOLVER ###
log "Setting up Knot Resolver..."

# Step 1: Download and install Knot Resolver package
log "Downloading Knot Resolver release package..."
wget -q https://secure.nic.cz/files/knot-resolver/knot-resolver-release.deb -O knot-resolver-release.deb

log "Installing Knot Resolver release package..."
sudo dpkg -i knot-resolver-release.deb || sudo apt-get install -f -y

log "Updating package repositories..."
sudo apt update -y

log "Installing Knot Resolver..."
sudo apt install -y knot-resolver

# Step 2: Update /etc/hosts to prevent host resolution failure
log "Updating /etc/hosts to map hostname..."
HOST_IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)
sudo sh -c "echo '$HOST_IP $HOSTNAME' >> /etc/hosts"

# Step 3: Configure resolv.conf
log "Configuring /etc/resolv.conf to point to Knot Resolver..."
sudo sh -c "echo 'nameserver 127.0.0.1' > /etc/resolv.conf"

# Step 4: Stop systemd-resolved to free up port 53
log "Stopping systemd-resolved..."
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved || true # Ignore errors if it's not enabled

# Step 5: Start the 4 Knot Resolver instances
log "Starting Knot Resolver instances..."
sudo systemctl start kresd@1.service
sudo systemctl start kresd@2.service
sudo systemctl start kresd@3.service
sudo systemctl start kresd@4.service

# Check that Knot Resolver is working
log "Testing Knot Resolver with dig..."
if dig @127.0.0.1 google.com | grep -q "ANSWER SECTION"; then
    log "Knot Resolver is working correctly."
else
    log "Knot Resolver did not resolve DNS properly. Check the configuration or logs."
    exit 1
fi

log "Knot Resolver setup completed."

### SETUP BIND9 ###
log "Setting up BIND9 DNS resolver..."

# Step 6: Install BIND9
log "Installing BIND9..."
sudo apt install -y bind9

# Step 7: Update BIND9 configuration
log "Configuring BIND9 resolver settings..."

BIND_CONF_OPTIONS="/etc/bind/named.conf.options"
sudo bash -c "cat > $BIND_CONF_OPTIONS" <<EOF
options {
    directory "/var/cache/bind";

    // Performance optimizations for high success rate
    recursive-clients 10000;
    resolver-query-timeout 30000;
    max-clients-per-query 10000;
    max-cache-size 2000m;

    dnssec-validation auto;
    listen-on-v6 { any; };
};
EOF

# Step 8: Restart BIND9 and apply configuration
log "Restarting BIND9..."
sudo systemctl restart bind9

# Step 9: Update resolver settings to ensure `/etc/resolv.conf` points to BIND9
log "Updating /etc/resolv.conf for BIND9 usage..."
sudo sh -c "echo 'nameserver 127.0.0.1' >> /etc/resolv.conf"

# Check that BIND9 is working
log "Testing BIND9 with dig..."
if dig @127.0.0.1 google.com | grep -q "ANSWER SECTION"; then
    log "BIND9 is working correctly."
else
    log "BIND9 did not resolve DNS queries properly. Check the configuration or logs."
    exit 1
fi

log "BIND9 setup completed."

# Final Output
log "Both Knot Resolver and BIND9 setup successfully! DNS resolving is now configured on this server."
