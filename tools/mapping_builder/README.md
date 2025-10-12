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

## Performance Notes

- Processing time depends on:
  - Number of assessable items in each framework
  - LLM model speed
  - Ollama server performance

- For frameworks with 100 items each, expect:
  - ~10,000 LLM API calls
  - Processing time: 30-60 minutes (depending on model and hardware)

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
```

This will:
- Run the mapping with each model
- Generate individual result files
- Create a comparison report showing:
  - Relationship distribution by model
  - Score statistics by model
  - Agreement/disagreement analysis
  - Combined results file

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

- Use faster/smaller models (e.g., `mistral`, `llama3`) for quicker results
- Use larger models (e.g., `llama3.1:70b`) for more accurate analysis if available
- List available models with: `ollama list`
- Save results to CSV format when comparing models (easier to programmatically merge)
- Save results to XLSX format for better readability in spreadsheet applications
- Review items with scores between 0.3-0.7 manually as they may need human judgment
- The `model` column in output allows tracking and comparing results from different LLMs
