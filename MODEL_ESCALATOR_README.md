# OpenClaw Model Escalation Proxy

## Overview
This lightweight service monitors session transcripts and automatically triggers model escalation based on message complexity.

## Key Components
- `model_escalator.py`: Python script that:
  1. Monitors transcript files
  2. Analyzes message complexity
  3. Triggers model escalation when complexity threshold is met

## Complexity Analysis
The script uses a multi-factor approach to determine message complexity:
- Message length
- Presence of technical keywords
- Detection of code or structured content

## Installation
1. Ensure Python 3.7+ is installed
2. Copy `model_escalator.py` to your project directory
3. Set up systemd service (optional but recommended):
   ```bash
   sudo cp model_escalator.service /etc/systemd/system/
   sudo systemctl enable model_escalator
   sudo systemctl start model_escalator
   ```

## Configuration
Modify `model_escalator.py` to adjust:
- Transcript and processed file directories
- Complexity calculation method
- Escalation threshold

## Logging
Logs are written to `/Users/jeremy/Projects/Thanos/model_escalator.log`

## Notes
- Requires OpenClaw's session transcript mechanism
- Assumes transcripts are written as JSONL files
- Polls transcript directory every 10 seconds