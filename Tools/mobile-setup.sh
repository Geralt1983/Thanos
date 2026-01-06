#!/data/data/com.termux/files/usr/bin/bash
# Run this on Termux to set up Life OS mobile access

# Install dependencies
pkg install -y git openssh

# Clone Life OS
cd ~
git clone git@github.com:Geralt1983/Thanos.git .claude

# Set up auto-pull on Termux startup
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/lifeos-sync.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/.claude && git pull --quiet
EOF
chmod +x ~/.termux/boot/lifeos-sync.sh

echo "✓ Life OS cloned to ~/.claude"
echo "✓ Auto-sync on Termux boot enabled"
echo ""
echo "State/ and History/ now accessible on mobile"
