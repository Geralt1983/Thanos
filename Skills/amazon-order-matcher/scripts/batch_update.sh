#!/bin/bash
# Batch update Amazon transactions with proper categories

cd /Users/jeremy/Projects/Thanos
CLI="node skills/monarch-money/dist/cli/index.js"

echo "Updating 33 Amazon transactions..."

# Baby items
$CLI tx update 234566839020058309 -c 225123032227674020 -m "Amazon - Cabinet Locks" 2>&1 | grep -i success || true
$CLI tx update 234566839020058330 -c 225123032227674020 -m "Amazon - Baby Gate" 2>&1 | grep -i success || true
$CLI tx update 234566839020058382 -c 225123032227674020 -m "Amazon - Baby Gate" 2>&1 | grep -i success || true
$CLI tx update 234566839020058381 -c 225123032227674020 -m "Amazon - Corner Protector" 2>&1 | grep -i success || true
$CLI tx update 234566839020058452 -c 225123032227674020 -m "Amazon - Cabinet Locks" 2>&1 | grep -i success || true
$CLI tx update 234566839021106184 -c 225123032227674020 -m "Amazon - Baby Wagon" 2>&1 | grep -i success || true
$CLI tx update 234566839021106218 -c 225123032227674020 -m "Amazon - Edge Protectors" 2>&1 | grep -i success || true

# Household items
$CLI tx update 234566839020058308 -c 162959461244237526 -m "Amazon - Tudca Supplement" 2>&1 | grep -i success || true
$CLI tx update 234566839020058331 -c 162959461244237526 -m "Amazon - Humidifier" 2>&1 | grep -i success || true
$CLI tx update 234566839020058351 -c 162959461244237526 -m "Amazon - Thermometer" 2>&1 | grep -i success || true
$CLI tx update 234566839020058455 -c 162959461244237526 -m "Amazon - Oil Heater" 2>&1 | grep -i success || true
$CLI tx update 234566839020058494 -c 162959461244237526 -m "Amazon - Flannel Sheets" 2>&1 | grep -i success || true
$CLI tx update 234566839020058513 -c 162959461244237526 -m "Amazon - Extension Cord" 2>&1 | grep -i success || true
$CLI tx update 234566839020058511 -c 162959461244237526 -m "Amazon - Mouse Traps" 2>&1 | grep -i success || true
$CLI tx update 234566839020058510 -c 162959461244237526 -m "Amazon - Creatine + Cord" 2>&1 | grep -i success || true
$CLI tx update 234566839020058582 -c 162959461244237526 -m "Amazon - Melatonin" 2>&1 | grep -i success || true
$CLI tx update 234566839021106192 -c 162959461244237526 -m "Amazon - Light Therapy Lamp" 2>&1 | grep -i success || true
$CLI tx update 234566839021106179 -c 162959461244237526 -m "Amazon - Creatine" 2>&1 | grep -i success || true

# Business expense (work cables/tools)
$CLI tx update 234566839020058514 -c 178462006985127548 -m "Amazon - 3M Adhesion Promoter" 2>&1 | grep -i success || true
$CLI tx update 234566839020058538 -c 178462006985127548 -m "Amazon - Allen Wrench Set" 2>&1 | grep -i success || true
$CLI tx update 234566839020058597 -c 178462006985127548 -m "Amazon - Cable Organizer" 2>&1 | grep -i success || true
$CLI tx update 234566839020058612 -c 178462006985127548 -m "Amazon - Cable Labels" 2>&1 | grep -i success || true
$CLI tx update 234566839021106190 -c 178462006985127548 -m "Amazon - Cable Ties" 2>&1 | grep -i success || true
$CLI tx update 234566839021106189 -c 178462006985127548 -m "Amazon - Cord Holder" 2>&1 | grep -i success || true
$CLI tx update 234566839021106188 -c 178462006985127548 -m "Amazon - Drill Kit" 2>&1 | grep -i success || true
$CLI tx update 234566839021106187 -c 178462006985127548 -m "Amazon - DisplayPort Cable" 2>&1 | grep -i success || true
$CLI tx update 234566839021106186 -c 178462006985127548 -m "Amazon - Torx Screws" 2>&1 | grep -i success || true
$CLI tx update 234566839021106217 -c 178462006985127548 -m "Amazon - USB C Cable" 2>&1 | grep -i success || true

# Electronics (Jeremy spending money)
$CLI tx update 234566839020058310 -c 162782301949818821 -m "Amazon - Roku Remote" 2>&1 | grep -i success || true
$CLI tx update 234566839020058329 -c 162782301949818821 -m "Amazon - Kindle Tips" 2>&1 | grep -i success || true
$CLI tx update 234566839021106193 -c 162782301949818821 -m "Amazon - Flashlight" 2>&1 | grep -i success || true
$CLI tx update 234566839021106194 -c 162782301949818821 -m "Amazon - Lightning Cable" 2>&1 | grep -i success || true

# Auto
$CLI tx update 234566839020058599 -c 162777981853398770 -m "Amazon - Car Charger" 2>&1 | grep -i success || true

echo "Done! Check Monarch for updated categories."
