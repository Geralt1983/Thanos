#!/bin/bash
# January 2026 final cleanup - Klarna + remaining

CLI="/Users/jeremy/Projects/Thanos/skills/monarch-money/dist/cli/index.js"

echo "Categorizing Klarna transactions (mostly eBay → Shopping)..."

# Klarna → Jeremy Spending Money (eBay purchases mostly)
node $CLI tx update 234566839020058305 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839020058365 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839020058446 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839020058507 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839020058506 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839020058573 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839021106197 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839021106224 -c 162782301949818821 -m "Klarna (eBay)"
node $CLI tx update 234566839021106214 -c 162782301949818821 -m "Klarna (eBay)"

echo "Categorizing Target → Baby/Household..."
# Target → Baby formula (based on previous pattern)
node $CLI tx update 234566839020058323 -c 225123032227674020 -m "Target"
node $CLI tx update 234566839020058462 -c 225123032227674020 -m "Target"
node $CLI tx update 234566839020058461 -c 225123032227674020 -m "Target"
node $CLI tx update 234566839021106182 -c 225123032227674020 -m "Target"

echo "Categorizing Sam's Club → Groceries..."
node $CLI tx update 234566839020058442 -c 162777981853398771 -m "Sam's Club"

echo "Categorizing Court payment → Financial/Legal..."
# Court payment → Financial & Legal Services
node $CLI tx update 234566839020058307 -c 162777981853398791 -m "Stokes County Court"

echo "Categorizing software/services..."
# Tailscale → Software
node $CLI tx update 234566839020058454 -c 224956793438106936 -m "Tailscale"
# Bolt/Stackblitz → Software
node $CLI tx update 234566839020058490 -c 224956793438106936 -m "Stackblitz"
# Airslate → Software
node $CLI tx update 234566839021106225 -c 224956793438106936 -m "Airslate"
# Google CamScanner → Business Expenses
node $CLI tx update 234566839020058353 -c 178527072205960399 -m "CamScanner"

echo "Categorizing phone service..."
# Talkiatalk → Phone
node $CLI tx update 234566839020058362 -c 162777981853398770 -m "Talkiatalk"
node $CLI tx update 234566839020058544 -c 162777981853398770 -m "Talkiatalk"

echo "Categorizing school expenses..."
# Yearbook → School expense
node $CLI tx update 234566839020058408 -c 225122967611274982 -m "Walsworth Yearbook"
node $CLI tx update 234566839020058495 -c 225122967611274982 -m "Walsworth Yearbook"

echo "Categorizing household services..."
# Old Sarge's Junk Removal → Household
node $CLI tx update 234566839020058492 -c 162959461244237526 -m "Old Sarge's Junk Removal"
# Sneak a Peek (ultrasound?) → Medical
node $CLI tx update 234566839020058536 -c 162777981853398787 -m "Sneak a Peek"

echo "Categorizing miscellaneous..."
# Railway.app → Software
node $CLI tx update 234566839020058332 -c 224956793438106936 -m "Railway.app"
# Small misc → Jeremy Spending
node $CLI tx update 234566839020058515 -c 162782301949818821 -m "Misc"
node $CLI tx update 234566839020058539 -c 162782301949818821 -m "Misc"
node $CLI tx update 234566839020058533 -c 162782301949818821 -m "Misc"
node $CLI tx update 234566839021106215 -c 162782301949818821 -m "Winston-Salem"

echo "Done!"
