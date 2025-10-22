# Semantic Framework Mapping Tools

This directory contains tools for semantic comparison between security/compliance framework YAML files.

## Available Tools

1. **semantic_mapper.py** - LLM-based mapping using Ollama (flexible, provides explanations)
2. **sbert_mapper.py** - SBERT-based mapping using sentence transformers (fast, deterministic)
3. **heatmap_builder.py** - Visualize mapping relationships as heatmaps
4. **compare_models.py** - Compare results from multiple LLM models

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

### With Ollama Embeddings (Enhanced Context)

You can enhance LLM analysis by generating embeddings first. The embedding similarity is passed as context to the LLM:

```bash
# First, pull an embedding model
ollama pull nomic-embed-text

# Run semantic mapper with embeddings
python semantic_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --model mistral \
  --embedding-model nomic-embed-text \
  --output mapping_with_embeddings.csv
```

**Benefits of using embeddings:**
- LLM gets semantic similarity context to make better decisions
- Helps LLM validate its reasoning against numerical similarity
- Output includes both embedding similarity and LLM scores for analysis

**Available embedding models:**
- `nomic-embed-text` - Good general purpose (768 dimensions)
- `mxbai-embed-large` - High quality (1024 dimensions)
- `snowflake-arctic-embed` - Optimized for retrieval

## Arguments

- `--source` (required): Path to source framework YAML file
- `--target` (required): Path to target framework YAML file
- `--ollama-url` (optional): Ollama API endpoint URL (default: http://localhost:11434)
- `--model` (optional): LLM model to use (default: mistral). Available models can be listed with `ollama list`
- `--embedding-model` (optional): Ollama embedding model (e.g., nomic-embed-text, mxbai-embed-large). When specified, embeddings are generated and passed as context to the LLM
- `--output` (optional): Output file path for results (CSV or XLSX format)
- `--resume` (optional): Resume from existing output file if it exists
- `--checkpoint-interval` (optional): Save checkpoint every N source items (default: 1 = after each item)
- `--top-n` (optional): Return top N matches per source item (default: 1 = best match only)
- `--threshold` (optional): Minimum score threshold for matches, 0.0-1.0 (default: None)
- `--verbose` (optional): Enable verbose logging for debugging

## Output Format

The tool generates a table with the following columns:

### Model Information
- `model`: Name of the LLM model used for this mapping
- `embedding_model`: Name of the embedding model used (if applicable)

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
- `embedding_similarity`: Cosine similarity from embeddings (0.0 to 1.0, if embedding model was used)
- `relationship`: Type of relationship (determined by LLM)
  - `equal`: Same topic/requirement with equivalent scope (score = 1.0)
  - `intersect`: Related but not entirely equivalent (0 < score < 1)
  - `no_relationship`: Different topics with no overlap (score = 0)
- `score`: LLM confidence score (0.0 to 1.0)
- `explanation`: Brief explanation of the relationship from LLM

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

---

# SBERT-Based Mapping (sbert_mapper.py)

For a **faster, more deterministic** alternative to LLM-based mapping, use the SBERT-based mapper.

## Why SBERT?

**Advantages over LLM-based mapping:**
- ⚡ **10-100x faster** - processes entire frameworks in seconds/minutes instead of hours
- 🎯 **Deterministic** - same inputs always produce identical results
- 🔄 **No external services** - runs completely offline, no Ollama required
- 📊 **Cosine similarity scores** - mathematically grounded semantic similarity
- 🚫 **No JSON parsing issues** - direct numerical computation

**Trade-offs:**
- No natural language explanations (only similarity scores)
- Less flexibility in interpretation
- Purely similarity-based (no reasoning about relationships)

## Prerequisites

```bash
pip install sentence-transformers torch
```

## Basic Usage

```bash
python sbert_mapper.py \
  --source path/to/source-framework.yaml \
  --target path/to/target-framework.yaml \
  --output mapping_results.csv
```

## Model Selection

The tool supports different SBERT models with varying trade-offs:

### Fast & Lightweight (Recommended)
```bash
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --model all-MiniLM-L6-v2 \
  --output mapping.csv
```
- Speed: **Very Fast** (~1000 sentences/sec on CPU)
- Quality: Good
- Dimensions: 384

### High Quality
```bash
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --model all-mpnet-base-v2 \
  --output mapping.csv
```
- Speed: Moderate (~200 sentences/sec on CPU)
- Quality: **Excellent**
- Dimensions: 768

### Multilingual
```bash
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --model paraphrase-multilingual-MiniLM-L12-v2 \
  --output mapping.csv
```
- Speed: Fast
- Quality: Good
- Languages: **50+ languages**

## Arguments

- `--source` (required): Path to source framework YAML
- `--target` (required): Path to target framework YAML
- `--model` (optional): SBERT model name (default: all-MiniLM-L6-v2)
- `--output` (optional): Output file path (CSV or XLSX)
- `--top-n` (optional): Return top N matches per source item
- `--threshold` (optional): Minimum similarity threshold (0.0-1.0)
- `--equal-threshold` (optional): Similarity for "equal" relationships (default: 0.85)
- `--intersect-threshold` (optional): Similarity for "intersect" relationships (default: 0.50)
- `--device` (optional): Device to use (cuda/cpu/mps, default: auto)
- `--verbose` (optional): Enable verbose logging

## Threshold Configuration

SBERT uses **cosine similarity** (0-1) to determine relationship types:

### Default Thresholds
- **≥ 0.85**: "equal" relationship (score = 1.0)
- **0.50 - 0.85**: "intersect" relationship (score = 0.3-0.9, normalized)
- **< 0.50**: "no_relationship" (score = 0.0)

### Custom Thresholds
```bash
# Stricter matching (higher quality, fewer matches)
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --equal-threshold 0.90 \
  --intersect-threshold 0.60 \
  --output strict_mapping.csv

# Looser matching (more matches, lower precision)
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --equal-threshold 0.80 \
  --intersect-threshold 0.40 \
  --output loose_mapping.csv
```

## Multiple Matches (Top-N & Thresholds)

By default, SBERT returns only the best match per source item. You can get multiple matches:

### Top-N Matches
Get the top N most similar items for each source requirement:

```bash
# Get top 3 matches for each source item
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --top-n 3 \
  --output mapping_top3.csv
```

### Threshold-Based Filtering
Get all matches above a similarity threshold:

```bash
# Get all matches with similarity >= 0.6
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --threshold 0.6 \
  --output mapping_threshold.csv
```

### Combined: Top-N + Threshold
Combine both for controlled matching:

```bash
# Get top 5 matches, but only if similarity >= 0.5
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --top-n 5 \
  --threshold 0.5 \
  --output mapping_combined.csv
```

**Note:** With multiple matches, you'll get multiple rows per source item (one row per matching target). Results are sorted by similarity (best first).

## Output Format

The output includes:
- All standard mapping columns (source/target ref_id, urn, name, full_sentence)
- `relationship`: equal/intersect/no_relationship
- `score`: Normalized score (0-1) based on relationship type
- `similarity`: Raw cosine similarity (0-1) from SBERT

## Performance Examples

Typical processing times on modern hardware:

| Framework Size | Model | Device | Time |
|---------------|-------|--------|------|
| 50 x 50 items | MiniLM | CPU | ~2 seconds |
| 100 x 100 items | MiniLM | CPU | ~5 seconds |
| 500 x 500 items | MiniLM | CPU | ~30 seconds |
| 100 x 100 items | mpnet | CPU | ~15 seconds |
| 100 x 100 items | MiniLM | GPU | <1 second |

## GPU Acceleration

For large frameworks, use GPU acceleration:

```bash
# Auto-detect GPU (CUDA/MPS)
python sbert_mapper.py \
  --source large-source.yaml \
  --target large-target.yaml \
  --output mapping.csv

# Force specific device
python sbert_mapper.py \
  --source large-source.yaml \
  --target large-target.yaml \
  --device cuda \
  --output mapping.csv
```

## Complete Example

```bash
# High-quality mapping with custom thresholds
python sbert_mapper.py \
  --source ../../backend/library/libraries/nist-csf-2.0.yaml \
  --target ../../backend/library/libraries/iso27001-2022.yaml \
  --model all-mpnet-base-v2 \
  --equal-threshold 0.88 \
  --intersect-threshold 0.55 \
  --top-n 5 \
  --threshold 0.50 \
  --output nist-to-iso-mapping.xlsx \
  --verbose
```

## Comparing SBERT vs LLM Results

You can run both and compare:

```bash
# Run SBERT mapping
python sbert_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --output mapping_sbert.csv

# Run LLM mapping
python semantic_mapper.py \
  --source source.yaml \
  --target target.yaml \
  --model mistral \
  --output mapping_llm.csv

# Compare results in Python
import pandas as pd

sbert = pd.read_csv('mapping_sbert.csv')
llm = pd.read_csv('mapping_llm.csv')

# Merge on source/target pairs
merged = sbert.merge(
    llm,
    on=['source_ref_id', 'target_ref_id'],
    suffixes=('_sbert', '_llm')
)

# Compare scores
print(merged[['source_ref_id', 'target_ref_id', 'score_sbert', 'score_llm', 'similarity']])
```

## When to Use SBERT vs LLM

**Use SBERT when:**
- Speed is important
- You need deterministic/reproducible results
- You're doing exploratory analysis
- You want to process large frameworks quickly
- You don't need explanations

**Use LLM when:**
- You need natural language explanations
- You want nuanced reasoning about relationships
- Quality is more important than speed
- You need to justify mappings to stakeholders
- You're working with complex, context-dependent requirements

**Best Practice:** Start with SBERT for rapid exploration, then use LLM for detailed analysis of important mappings.

---

# Heatmap Visualization (heatmap_builder.py)

Visualize mapping relationships as heatmaps showing the score matrix between source and target items.

## Prerequisites

```bash
pip install matplotlib seaborn numpy pandas
```

## Basic Usage

```bash
python heatmap_builder.py \
  --input mapping_results.csv \
  --output heatmap.png
```

## Arguments

- `--input` (required): Path to mapping CSV file
- `--output` (optional): Output path for heatmap image (PNG, PDF, SVG)
- `--use-labels` (optional): Use ref_ids as axis labels instead of indices
- `--threshold` (optional): Show only relationships with score >= threshold
- `--width` (optional): Figure width in inches (default: 20)
- `--height` (optional): Figure height in inches (default: 16)
- `--cmap` (optional): Matplotlib colormap (default: YlOrRd)
- `--title` (optional): Custom title for heatmap

## Examples

### Basic heatmap with indices
```bash
python heatmap_builder.py \
  --input mapping_cyfun.csv \
  --output heatmap.png
```

### With ref_id labels
```bash
python heatmap_builder.py \
  --input mapping_cyfun.csv \
  --output heatmap_labeled.png \
  --use-labels
```

### Filtered heatmap (high-quality matches only)
```bash
python heatmap_builder.py \
  --input mapping_cyfun.csv \
  --output heatmap_filtered.png \
  --threshold 0.7
```

### Custom styling
```bash
python heatmap_builder.py \
  --input mapping_cyfun.csv \
  --output heatmap_custom.png \
  --cmap viridis \
  --width 24 \
  --height 20 \
  --title "Framework Mapping: NIST CSF 2.0 → ISO 27001"
```

## Available Colormaps

Popular options:
- `YlOrRd` (default): Yellow-Orange-Red, good for highlighting strong relationships
- `viridis`: Perceptually uniform, colorblind-friendly
- `plasma`: Purple-pink-yellow gradient
- `RdYlGn`: Red-Yellow-Green (diverging)
- `coolwarm`: Blue-Red (diverging)

See [Matplotlib colormaps](https://matplotlib.org/stable/tutorials/colors/colormaps.html) for more options.
