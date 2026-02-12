#!/bin/bash

# Example usage scripts for semantic framework mapper

# Example 1: Basic mapping with automatic checkpoints (single best match per source)
echo "Example 1: Basic mapping with checkpoints"
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --output mapping_basic.csv

# Example 2: Top-3 matches per source item
echo -e "\nExample 2: Top 3 matches per source item"
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --top-n 3 \
  --output mapping_top3.csv

# Example 3: Threshold-based matching (all matches >= 0.5)
echo -e "\nExample 3: All matches with score >= 0.5"
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --threshold 0.5 \
  --output mapping_threshold.csv

# Example 4: Combined top-N and threshold
echo -e "\nExample 4: Top 5 matches, but only if score >= 0.3"
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --top-n 5 \
  --threshold 0.3 \
  --output mapping_combined.csv \
  --resume

# Example 5: Resume interrupted job
echo -e "\nExample 5: Resume from checkpoint"
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --output mapping_resume.csv \
  --resume

# Example 6: Large framework with less frequent checkpoints and multiple matches
echo -e "\nExample 6: Large framework with checkpoint every 10 items, top 3 matches"
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-sp-800-53-rev5.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --top-n 3 \
  --output mapping_large.csv \
  --checkpoint-interval 10 \
  --resume

# Example 7: Compare multiple models with multiple matches
echo -e "\nExample 7: Compare models with top-3 matches"
python compare_models.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --models mistral llama3.1 llama3 \
  --output-dir ./comparison_results \
  --top-n 3 \
  --threshold 0.3 \
  --resume \
  --checkpoint-interval 5

echo -e "\nDone! Check the output files for results."
