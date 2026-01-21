#!/bin/bash
# Setup Thanos Wallpapers for Kitty Terminal Visual States
# Creates wallpaper directory and provides sourcing guidance

WALLPAPER_DIR="$HOME/.thanos/wallpapers"

echo "### DESTINY // WALLPAPER SETUP"
echo ""

# Create directory
mkdir -p "$WALLPAPER_DIR"
echo "✓ Created wallpaper directory: $WALLPAPER_DIR"
echo ""

# Check for existing wallpapers
MISSING=()
if [ ! -f "$WALLPAPER_DIR/nebula_storm.png" ]; then
    MISSING+=("nebula_storm.png")
fi
if [ ! -f "$WALLPAPER_DIR/infinity_gauntlet_fist.png" ]; then
    MISSING+=("infinity_gauntlet_fist.png")
fi
if [ ! -f "$WALLPAPER_DIR/farm_sunrise.png" ]; then
    MISSING+=("farm_sunrise.png")
fi

if [ ${#MISSING[@]} -eq 0 ]; then
    echo "✓ All wallpapers present"
    echo ""
    echo "The visual states are ready:"
    echo "  • CHAOS   → nebula_storm.png"
    echo "  • FOCUS   → infinity_gauntlet_fist.png"
    echo "  • BALANCE → farm_sunrise.png"
    exit 0
fi

echo "⚠ Missing wallpapers: ${MISSING[@]}"
echo ""
echo "### WALLPAPER SOURCING GUIDE"
echo ""
echo "1. CHAOS (nebula_storm.png)"
echo "   Search: 'purple nebula space 4k wallpaper'"
echo "   Style: Chaotic, swirling purple/blue energy"
echo "   Sources: unsplash.com, wallhaven.cc, pexels.com"
echo ""
echo "2. FOCUS (infinity_gauntlet_fist.png)"
echo "   Search: 'thanos infinity gauntlet wallpaper 4k'"
echo "   Style: Gauntlet with stones glowing, powerful pose"
echo "   Sources: wallpapersden.com, hdqwalls.com"
echo ""
echo "3. BALANCE (farm_sunrise.png)"
echo "   Search: 'peaceful farm sunrise 4k wallpaper'"
echo "   Style: Calm, golden hour, 'The Garden' aesthetic"
echo "   Sources: unsplash.com, pexels.com"
echo ""
echo "### QUICK COMMANDS"
echo ""
echo "# Download to correct location:"
echo "wget -O '$WALLPAPER_DIR/nebula_storm.png' [URL]"
echo "wget -O '$WALLPAPER_DIR/infinity_gauntlet_fist.png' [URL]"
echo "wget -O '$WALLPAPER_DIR/farm_sunrise.png' [URL]"
echo ""
echo "# Or place manually:"
echo "cp /path/to/your/image.png '$WALLPAPER_DIR/[name].png'"
echo ""
echo "The stones await their visual form."
