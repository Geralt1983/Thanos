# Thanos Wallpaper Guide

## Overview

The Thanos Shell Identity system uses 3 wallpapers to represent different workflow states in your Kitty terminal.

## Required Wallpapers

| State | Filename | Theme | Mood |
|-------|----------|-------|------|
| **CHAOS** | `nebula_storm.png` | Dark nebula, swirling chaos | Morning disorder, unsorted tasks |
| **FOCUS** | `infinity_gauntlet_fist.png` | Infinity Gauntlet, power | Deep work, execution mode |
| **BALANCE** | `farm_sunrise.png` | Peaceful farm at sunrise | Day complete, "The Garden" achieved |

## Installation

### Automatic Setup (Placeholders)

Run the setup script to create basic placeholder wallpapers:

```bash
./Shell/setup_wallpapers.sh
```

This creates simple colored backgrounds with text labels. Suitable for testing, but not ideal for daily use.

### Custom Wallpapers (Recommended)

For the full experience, use high-quality space and Marvel-themed images:

1. **Find Images:**
   - **CHAOS:** Dark space nebula, storm imagery, cosmic chaos
     - Sources: NASA Hubble images, deep space photography
     - Search: "dark nebula", "space storm", "cosmic chaos"

   - **FOCUS:** Infinity Gauntlet, power imagery, intense focus
     - Sources: Marvel promotional art, concept art
     - Search: "infinity gauntlet", "thanos hand", "power stone glow"

   - **BALANCE:** Peaceful farm, sunrise, tranquility
     - Sources: Landscape photography, rural sunrise images
     - Search: "farm sunrise", "peaceful landscape", "garden dawn"

2. **Image Specifications:**
   - Format: PNG (preferred) or JPEG
   - Resolution: 1920x1080 minimum (match your display)
   - Color depth: 24-bit RGB
   - File size: < 5MB per image (for fast switching)

3. **Rename and Copy:**
   ```bash
   cp /path/to/your/chaos-image.jpg ~/.thanos/wallpapers/nebula_storm.png
   cp /path/to/your/focus-image.jpg ~/.thanos/wallpapers/infinity_gauntlet_fist.png
   cp /path/to/your/balance-image.jpg ~/.thanos/wallpapers/farm_sunrise.png
   ```

## Recommended Image Sources

### Free & Legal Sources

1. **NASA Images**
   - URL: https://images.nasa.gov
   - License: Public domain
   - Best for: CHAOS (nebula, space storms)

2. **Unsplash**
   - URL: https://unsplash.com
   - License: Free for personal use
   - Best for: BALANCE (landscapes, sunrises)

3. **Pexels**
   - URL: https://pexels.com
   - License: Free for personal use
   - Best for: All states (variety of themes)

4. **Wikimedia Commons**
   - URL: https://commons.wikimedia.org
   - License: Various (check individual images)
   - Best for: Space imagery, landscapes

### Marvel Content

For Infinity Gauntlet imagery:
- Search Google Images with "infinity gauntlet wallpaper"
- Look for official promotional material from Marvel Studios
- Respect copyright: use for personal use only
- Alternative: fan art from DeviantArt (with attribution)

## Testing Wallpapers

Test wallpaper switching manually:

```bash
# CHAOS state
kitty @ set-background-image ~/.thanos/wallpapers/nebula_storm.png

# FOCUS state
kitty @ set-background-image ~/.thanos/wallpapers/infinity_gauntlet_fist.png

# BALANCE state
kitty @ set-background-image ~/.thanos/wallpapers/farm_sunrise.png
```

If the command fails:
- Ensure you're running from within a Kitty terminal
- Check that Kitty remote control is enabled: `kitty @ ls` should work
- Verify file paths and permissions

## Troubleshooting

### "Command not found: kitty"
You're not using Kitty terminal. The visual state system requires Kitty.

### "Permission denied"
```bash
chmod 644 ~/.thanos/wallpapers/*.png
```

### Images don't display
1. Check file format: `file ~/.thanos/wallpapers/nebula_storm.png`
2. Verify Kitty version supports backgrounds: `kitty --version` (need 0.19.0+)
3. Try absolute paths instead of `~`

### Background is stretched/distorted
Ensure image resolution matches or exceeds your display resolution.

## Customization Tips

### Color Grading

For maximum impact, color-grade your wallpapers:

- **CHAOS:** Increase contrast, boost purples/blues, add grain
- **FOCUS:** High contrast, saturated colors, sharp details
- **BALANCE:** Warm tones, soft glow, reduced contrast

### Terminal Transparency

Adjust Kitty's background opacity to let wallpapers show through:

```bash
# In ~/.config/kitty/kitty.conf
background_opacity 0.85
```

Lower opacity (0.7-0.85) works best with wallpapers.

## Advanced: Animated Wallpapers

Kitty doesn't support animated backgrounds natively, but you can:

1. Use a GIF and extract frames
2. Create a script to cycle through frames
3. Call `kitty @ set-background-image` in a loop

Not recommended for daily use (high CPU usage).

## File Structure

```
~/.thanos/
└── wallpapers/
    ├── nebula_storm.png       # CHAOS state
    ├── infinity_gauntlet_fist.png  # FOCUS state
    └── farm_sunrise.png       # BALANCE state
```

## Next Steps

Once wallpapers are set up:

1. Test state transitions: `python3 Shell/lib/visuals.py set CHAOS`
2. Run integration tests: `./Shell/test_integration.sh`
3. Start using Thanos: `Shell/thanos-cli "what's my energy?"`

The visual states will automatically transition based on your workflow patterns.
