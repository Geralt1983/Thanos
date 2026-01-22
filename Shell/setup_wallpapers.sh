#!/usr/bin/env bash
# Thanos Wallpaper Setup Script
# Creates placeholder wallpapers for the 3 visual states

set -e

WALLPAPER_DIR="$HOME/.thanos/wallpapers"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "### THANOS WALLPAPER SETUP ###"
echo

# Create directory if it doesn't exist
mkdir -p "$WALLPAPER_DIR"

# Function to create a placeholder image using ImageMagick (if available)
create_placeholder() {
    local filename="$1"
    local color="$2"
    local text="$3"

    if command -v convert &> /dev/null; then
        convert -size 1920x1080 "xc:$color" \
                -font Arial-Bold -pointsize 72 -fill white \
                -gravity center -annotate +0+0 "$text" \
                "$WALLPAPER_DIR/$filename"
        echo "✓ Created $filename (ImageMagick)"
    else
        # Fallback: create a simple colored PNG using Python PIL
        if command -v python3 &> /dev/null; then
            python3 - <<EOF
try:
    from PIL import Image, ImageDraw, ImageFont
    import os

    # Create image
    img = Image.new('RGB', (1920, 1080), '$color')
    draw = ImageDraw.Draw(img)

    # Try to add text (may fail if no font available)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
    except:
        try:
            font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 72)
        except:
            font = ImageFont.load_default()

    # Calculate text position
    bbox = draw.textbbox((0, 0), "$text", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (1920 - text_width) / 2
    y = (1080 - text_height) / 2

    draw.text((x, y), "$text", fill='white', font=font)

    # Save
    img.save(os.path.join('$WALLPAPER_DIR', '$filename'))
    print('✓ Created $filename (Python PIL)')
except ImportError:
    print('✗ Python PIL not available')
except Exception as e:
    print(f'✗ Error creating $filename: {e}')
EOF
        else
            echo "✗ Cannot create $filename - no image tools available"
        fi
    fi
}

echo "Creating placeholder wallpapers..."
echo

# Create the 3 state wallpapers
create_placeholder "nebula_storm.png" "#1a0033" "CHAOS"
create_placeholder "infinity_gauntlet_fist.png" "#330066" "FOCUS"
create_placeholder "farm_sunrise.png" "#ffaa44" "BALANCE"

echo
echo "Checking wallpaper files..."
echo

# Verify files exist
all_ok=true
for file in nebula_storm.png infinity_gauntlet_fist.png farm_sunrise.png; do
    if [ -f "$WALLPAPER_DIR/$file" ]; then
        size=$(du -h "$WALLPAPER_DIR/$file" | cut -f1)
        echo "✓ $file ($size)"
    else
        echo "✗ $file - MISSING"
        all_ok=false
    fi
done

echo
if [ "$all_ok" = true ]; then
    echo "✓ All wallpapers created successfully"
    echo
    echo "Directory: $WALLPAPER_DIR"
    echo
    echo "To use custom wallpapers:"
    echo "1. Find high-quality space/marvel themed images"
    echo "2. Name them: nebula_storm.png, infinity_gauntlet_fist.png, farm_sunrise.png"
    echo "3. Copy to $WALLPAPER_DIR"
    echo
    echo "Recommended sources:"
    echo "  - NASA image gallery (https://images.nasa.gov)"
    echo "  - Unsplash space category (https://unsplash.com/s/photos/space)"
    echo "  - Marvel concept art (search for official promotional images)"
else
    echo "✗ Some wallpapers are missing"
    echo
    echo "See WALLPAPER_GUIDE.md for manual setup instructions"
    exit 1
fi

# Test with Kitty if available
if command -v kitty &> /dev/null; then
    echo
    echo "Testing Kitty integration..."
    kitty @ set-background-image "$WALLPAPER_DIR/nebula_storm.png" 2>/dev/null && echo "✓ Kitty can load wallpapers" || echo "✗ Kitty test failed (may need to run from within Kitty)"
fi

echo
echo "### SETUP COMPLETE ###"
