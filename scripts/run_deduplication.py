#!/Users/jeremy/Projects/Thanos/.venv/bin/python

import sys
sys.path.append("/Users/jeremy/Projects/Thanos")

import logging
from Tools.memory_v2.deduplication import deduplicate_memories

# Configure logging
logging.basicConfig(
    filename="/Users/jeremy/Projects/Thanos/logs/memory_deduplication.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Run deduplication
results = deduplicate_memories(similarity_threshold=0.95)

# Log results
print(f"Deduplication Results: {results}")
logging.info(f"Deduplication Results: {results}")