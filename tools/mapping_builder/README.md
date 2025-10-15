# Semantic Framework Mapping Tool

This tool performs semantic comparison between two security/compliance framework YAML files using LLM-powered analysis via Ollama.

## Features

- Extracts assessable items from framework YAML files
- Builds context-aware "full sentences" by combining item content with parent/grandparent context
- Uses Ollama LLM to semantically compare each source item with target items
- Generates a comprehensive mapping table with relationship types, scores, and explanations

## Prerequisites

1. **Python 3.8+** with the following packages:
   ```bash
   pip install pyyaml requests pandas openpyxl
   ```

2. **Ollama** installed and running locally:
   ```bash
   # Install Ollama (https://ollama.ai)
   # Pull a model (e.g., mistral, llama3.1, llama3)
   ollama pull mistral

   # Check if Ollama is already running
   curl http://localhost:11434/api/tags

   # If not running, start Ollama server
   ollama serve
   ```

## Usage

### Basic Usage

```bash
python semantic_mapper.py \
  --source path/to/source-framework.yaml \
  --target path/to/target-framework.yaml \
  --output mapping_results.csv
```

### With Custom Ollama Settings

```bash
python semantic_mapper.py \
  --source backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target backend/library/libraries/iso27001-2013.yaml \
  --ollama-url http://localhost:11434 \
  --model mistral \
  --output nist-to-iso-mapping.xlsx
```

## Arguments

- `--source` (required): Path to source framework YAML file
- `--target` (required): Path to target framework YAML file
- `--ollama-url` (optional): Ollama API endpoint URL (default: http://localhost:11434)
- `--model` (optional): LLM model to use (default: mistral). Available models can be listed with `ollama list`
- `--output` (optional): Output file path for results (CSV or XLSX format)
- `--resume` (optional): Resume from existing output file if it exists
- `--checkpoint-interval` (optional): Save checkpoint every N source items (default: 1 = after each item)
- `--top-n` (optional): Return top N matches per source item (default: 1 = best match only)
- `--threshold` (optional): Minimum score threshold for matches, 0.0-1.0 (default: None)

## Output Format

The tool generates a table with the following columns:

### Model Information
- `model`: Name of the LLM model used for this mapping

### Source Framework Columns
- `source_ref_id`: Reference ID of source item
- `source_urn`: URN of source item
- `source_name`: Name of source item
- `source_full_sentence`: Full context sentence for source item

### Target Framework Columns (Best Match)
- `target_ref_id`: Reference ID of best matching target item
- `target_urn`: URN of target item
- `target_name`: Name of target item
- `target_full_sentence`: Full context sentence for target item

### Relationship Analysis
- `relationship`: Type of relationship
  - `equal`: Same topic/requirement with equivalent scope (score = 1.0)
  - `intersect`: Related but not entirely equivalent (0 < score < 1)
  - `no_relationship`: Different topics with no overlap (score = 0)
- `score`: Confidence score (0.0 to 1.0)
- `explanation`: Brief explanation of the relationship

## How It Works

1. **Parse Frameworks**: Extracts all assessable items (where `assessable: true`) from both YAML files

2. **Build Context**: For each assessable item with depth > 1, combines:
   - Current item's name and description
   - Parent's name and description
   - Grandparent's name and description (up to depth 1)

3. **Semantic Comparison**: For each source item, compares against all target items using LLM to determine:
   - Semantic similarity
   - Relationship type
   - Confidence score
   - Explanation

4. **Best Match Selection**: For each source item, selects the target item with the highest score

5. **Output Generation**: Creates a comprehensive mapping table with all results

## Example

```bash
# Map NIST AI RMF to ISO 27001
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --output nist-ai-to-iso27001-mapping.xlsx
```

## Multiple Target Mappings

By default, each source item maps to only its best match (top-1). You can configure this to find multiple related target items:

### Top-N Matches

Get the top N best matches per source item:

```bash
# Get top 3 matches for each source requirement
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --top-n 3 \
  --output mapping_top3.csv
```

### Threshold-Based Matching

Get all matches above a score threshold:

```bash
# Get all matches with score >= 0.5
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --threshold 0.5 \
  --output mapping_threshold.csv
```

### Combined: Top-N + Threshold

Combine both approaches for better control:

```bash
# Get top 5 matches, but only if score >= 0.3
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --top-n 5 \
  --threshold 0.3 \
  --output mapping_combined.csv
```

**Output Format**: With multiple matches, you'll get multiple rows per source item - one for each matching target. The results are sorted by score (best matches first).

**Use Cases**:
- **Top-N**: When you want a fixed number of alternatives per requirement
- **Threshold**: When you want all semantically related items above a quality bar
- **Combined**: When you want "up to N matches, but only good ones"

## Checkpoint & Resume (For Long-Running Jobs)

Large frameworks can take hours to process. The tool includes checkpoint/resume functionality:

### Automatic Checkpointing

By default, progress is saved after each source item:

```bash
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --output mapping.csv
```

If interrupted, resume with:

```bash
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --output mapping.csv \
  --resume
```

### Checkpoint Interval

For very large frameworks, save checkpoints less frequently to improve performance:

```bash
# Save every 5 items instead of every item
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --output mapping.csv \
  --checkpoint-interval 5 \
  --resume
```

**Note:** Lower checkpoint intervals (e.g., 10-20) can improve processing speed by reducing I/O, but you may lose more progress if interrupted.

## Performance Notes

- Processing time depends on:
  - Number of assessable items in each framework
  - LLM model speed
  - Ollama server performance
  - Checkpoint interval (more frequent = slower)

- For frameworks with 100 items each, expect:
  - ~10,000 LLM API calls
  - Processing time: 30-60 minutes (depending on model and hardware)
  - Use `--checkpoint-interval 10` to reduce overhead by ~10-20%

### Performance Optimizations (Built-in)

The tool includes several optimizations for faster Ollama inference:

1. **HTTP Connection Pooling**: Reuses persistent connections (saves ~50-100ms per request)
2. **Model Keep-Alive**: Keeps model loaded in memory for 30 minutes (prevents 10-30s reload delays)
3. **Pre-warming**: Loads model into memory at startup
4. **Optimized Parameters**:
   - `temperature=0.1` for consistent results
   - `num_predict=200` to limit token generation
   - `num_ctx=2048` for appropriate context window

**Additional Tips**:
- Use smaller models for speed: `qwen2.5:3b`, `phi3:mini` (3-4x faster)
- Set `OLLAMA_NUM_PARALLEL=4` environment variable for parallel processing
- Increase checkpoint interval (`--checkpoint-interval 10`) for large frameworks

## Comparing Model Performance

To compare how different models perform on the same mapping task, use the `compare_models.py` script:

### Automated Comparison

```bash
# Compare multiple models automatically
python compare_models.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --models mistral llama3.1 llama3 \
  --output-dir ./comparison_results

# With resume support (if interrupted, run same command)
python compare_models.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --models mistral llama3.1 llama3 \
  --output-dir ./comparison_results \
  --resume \
  --checkpoint-interval 5
```

This will:
- Run the mapping with each model
- Generate individual result files
- Create a comparison report showing:
  - Relationship distribution by model
  - Score statistics by model
  - Agreement/disagreement analysis
  - Combined results file
- Resume from where it left off if interrupted (with `--resume`)

### Manual Comparison

Alternatively, run mappings separately:

```bash
# Run with Mistral
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model mistral \
  --output mapping_mistral.csv

# Run with Llama3.1
python semantic_mapper.py \
  --source ../../backend/library/libraries/nist-ai-rmf-1.0.yaml \
  --target ../../backend/library/libraries/iso27001-2013.yaml \
  --model llama3.1 \
  --output mapping_llama3.1.csv
```

### Analyzing Results with Python

The output includes a `model` column, so you can combine and analyze results:

```python
import pandas as pd

# Load results from different models
df_mistral = pd.read_csv('mapping_mistral.csv')
df_llama = pd.read_csv('mapping_llama3.1.csv')

# Combine results
df_combined = pd.concat([df_mistral, df_llama])

# Compare relationship distributions
print(df_combined.groupby('model')['relationship'].value_counts())

# Compare average scores
print(df_combined.groupby('model')['score'].describe())

# Compare specific mappings
comparison = df_combined.pivot_table(
    index='source_ref_id',
    columns='model',
    values=['relationship', 'score'],
    aggfunc='first'
)
print(comparison)
```

## Tips

### Model Selection
- Use faster/smaller models (e.g., `mistral`, `llama3`) for quicker results
- Use larger models (e.g., `llama3.1:70b`) for more accurate analysis if available
- List available models with: `ollama list`

### Output Formats
- Save results to CSV format when comparing models (easier to programmatically merge)
- Save results to XLSX format for better readability in spreadsheet applications
- The `model` column in output allows tracking and comparing results from different LLMs

### Long-Running Jobs
- Always use `--resume` flag to enable recovery from interruptions
- Start with `--checkpoint-interval 1` (default) for safety
- For very large frameworks (100+ items), use `--checkpoint-interval 5-10` for better performance
- Monitor progress - checkpoints show completion status
- If a checkpoint file exists, you can safely Ctrl+C and resume later

### Multiple Matches Strategy
- **Use `--top-n 3` or `--top-n 5`** for comprehensive mapping where you want alternatives
- **Use `--threshold 0.5` or `--threshold 0.7`** for high-quality matches only (stricter control)
- **Use `--top-n 5 --threshold 0.3`** for balanced approach: "best 5, but only decent ones"
- Default (single best match) works well for 1:1 framework alignment
- Multiple matches are essential for many-to-many relationship discovery

### Quality Review
- Review items with scores between 0.3-0.7 manually as they may need human judgment
- Compare results from multiple models to validate mappings
- Check disagreement cases - they often indicate edge cases or nuanced requirements
- With multiple matches: review all matches per source to understand coverage
- Low-scoring matches (0.2-0.4) might reveal tangential relationships worth documenting
