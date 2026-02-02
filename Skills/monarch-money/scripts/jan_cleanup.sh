#!/bin/bash
# January 2026 cleanup - clear categorizations

CLI="cd /Users/jeremy/Projects/Thanos/skills/monarch-money && node dist/cli/index.js"

# School expenses
$CLI tx update 234566839020058408 -c 225122967611274982 -m "Walsworth Yearbook" # School expense
$CLI tx update 234566839020058495 -c 225122967611274982 -m "Walsworth Yearbook" # School expense

# Sam's Club → Groceries
$CLI tx update 234566839020058442 -c 162777981853398771 -m "Sam's Club"

# Target → likely baby/household (based on prior pattern), use Household
$CLI tx update 234566839020058323 -c 162959461244237526 -m "Target" 
$CLI tx update 234566839020058462 -c 162959461244237526 -m "Target"
$CLI tx update 234566839020058461 -c 162959461244237526 -m "Target"
$CLI tx update 234566839021106182 -c 162959461244237526 -m "Target"

# Software/Services
$CLI tx update 234566839020058454 -c 224956793438106936 -m "Tailscale" # Software
$CLI tx update 234566839020058490 -c 224956793438106936 -m "Bolt (Stackblitz)" # Software
$CLI tx update 234566839020058225 -c 224956793438106936 -m "Airslate" # Software

# Household services
$CLI tx update 234566839020058492 -c 162959461244237526 -m "Old Sarge's Junk Removal" # Household

# Phone/telecom
$CLI tx update 234566839020058362 -c 162777981853398770 -m "Talkiatalk" # Phone
$CLI tx update 234566839020058544 -c 162777981853398770 -m "Talkiatalk" # Phone

# Business/Professional
$CLI tx update 234566839020058353 -c 178527072205960399 -m "Google CamScanner" # Business Expenses

# Miscellaneous small items
$CLI tx update 234566839020058332 -c 162782301949818821 -m "Railway.app" # Jeremy Spending (dev tool)
$CLI tx update 234566839020058515 -c 162782301949818821 -m "Misc" # $6 unknown
$CLI tx update 234566839020058539 -c 162782301949818821 -m "Misc" # $6 unknown
$CLI tx update 234566839020058533 -c 162782301949818821 -m "Misc" # $12 unknown
$CLI tx update 234566839021106215 -c 162782301949818821 -m "Lot Winston Sale" # $12.84

echo "Auto-categorized 19 clear transactions"
