#!/usr/bin/env python3
"""
Semantic Framework Mapping Tool

This script compares two security framework YAML files using semantic analysis via Ollama.
It builds a mapping table showing relationships between assessable items in source and target frameworks.
"""

import argparse
import yaml
import requests
import json
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


class FrameworkItem:
    """Represents an assessable item from a framework"""

    def __init__(
        self,
        ref_id: str,
        urn: str,
        name: str,
        description: str,
        depth: int,
        parent_urn: Optional[str] = None,
    ):
        self.ref_id = ref_id
        self.urn = urn
        self.name = name
        self.description = description
        self.depth = depth
        self.parent_urn = parent_urn
        self.full_sentence = ""

    def __repr__(self):
        return f"FrameworkItem({self.ref_id}, depth={self.depth})"


class FrameworkParser:
    """Parses framework YAML files and extracts assessable items"""

    def __init__(self, yaml_path: str):
        self.yaml_path = Path(yaml_path)
        self.items: List[FrameworkItem] = []
        self.items_by_urn: Dict[str, FrameworkItem] = {}
        self.framework_name = ""

    def parse(self) -> List[FrameworkItem]:
        """Parse the YAML file and extract assessable items"""
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.framework_name = data.get("name", "")
        framework = data.get("objects", {}).get("framework", {})
        requirement_nodes = framework.get("requirement_nodes", [])

        # First pass: collect all nodes
        all_nodes = {}
        for node in requirement_nodes:
            urn = node.get("urn", "")
            all_nodes[urn] = node

        # Second pass: extract assessable items and build full sentences
        for node in requirement_nodes:
            if node.get("assessable", False):
                item = FrameworkItem(
                    ref_id=node.get("ref_id", ""),
                    urn=node.get("urn", ""),
                    name=node.get("name", ""),
                    description=node.get("description", ""),
                    depth=node.get("depth", 0),
                    parent_urn=node.get("parent_urn"),
                )

                # Build full sentence
                item.full_sentence = self._build_full_sentence(item, all_nodes)

                self.items.append(item)
                self.items_by_urn[item.urn] = item

        return self.items

    def _build_full_sentence(self, item: FrameworkItem, all_nodes: Dict) -> str:
        """Build a full sentence combining item content with parent/grandparent context"""
        parts = []

        # Start with current item
        current_name = item.name.strip() if item.name else ""
        current_desc = item.description.strip() if item.description else ""

        if current_name and current_desc:
            parts.append(f"{current_name}: {current_desc}")
        elif current_desc:
            parts.append(current_desc)
        elif current_name:
            parts.append(current_name)

        # Add parent context if depth > 1
        if item.depth > 1 and item.parent_urn:
            parent_context = self._get_parent_context(
                item.parent_urn, all_nodes, max_depth=1
            )
            if parent_context:
                parts.insert(0, parent_context)

        return " | ".join(parts) if parts else "No description available"

    def _get_parent_context(
        self,
        parent_urn: str,
        all_nodes: Dict,
        max_depth: int = 1,
        current_depth: int = 0,
    ) -> str:
        """Recursively get parent context up to max_depth levels"""
        if current_depth >= max_depth or parent_urn not in all_nodes:
            return ""

        parent = all_nodes[parent_urn]
        parent_name = parent.get("name", "").strip()
        parent_desc = parent.get("description", "").strip()

        # Format parent info
        if parent_name and parent_desc:
            context = f"{parent_name}: {parent_desc}"
        elif parent_desc:
            context = parent_desc
        elif parent_name:
            context = parent_name
        else:
            context = ""

        # Get grandparent if needed
        grandparent_urn = parent.get("parent_urn")
        if grandparent_urn and current_depth < max_depth - 1:
            grandparent_context = self._get_parent_context(
                grandparent_urn, all_nodes, max_depth, current_depth + 1
            )
            if grandparent_context:
                context = (
                    f"{grandparent_context} | {context}"
                    if context
                    else grandparent_context
                )

        return context


class SemanticMapper:
    """Uses Ollama LLM to semantically compare framework items"""

    def __init__(
        self, ollama_url: str = "http://localhost:11434", model: str = "mistral"
    ):
        self.ollama_url = ollama_url
        self.model = model
        # Create persistent HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})
        self._verify_model()

    def __del__(self):
        """Cleanup: close HTTP session"""
        if hasattr(self, "session"):
            self.session.close()

    def _verify_model(self):
        """Verify that the specified model is available in Ollama"""
        try:
            response = self.session.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            available_models = [m["name"] for m in data.get("models", [])]

            if self.model not in available_models:
                # Try with :latest suffix
                if f"{self.model}:latest" in available_models:
                    self.model = f"{self.model}:latest"
                else:
                    raise ValueError(
                        f"Model '{self.model}' not found in Ollama.\n"
                        f"Available models: {', '.join(available_models)}\n"
                        f"Install a model with: ollama pull <model-name>"
                    )

            print(f"Using Ollama model: {self.model}")

            # Pre-warm: load model into memory and keep it loaded
            print(f"Pre-loading model into memory...")
            self.session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "warmup",
                    "stream": False,
                    "keep_alive": "30m",  # Keep model loaded for 30 minutes
                },
                timeout=30,
            )
            print(f"Model loaded and ready")

        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.ollama_url}.\n"
                f"Make sure Ollama is running with: ollama serve\n"
                f"Error: {e}"
            )

    def compare_items(
        self, source_item: FrameworkItem, target_item: FrameworkItem
    ) -> tuple[str, float, str]:
        """
        Compare two framework items using LLM

        Returns:
            tuple: (relationship_type, score, explanation)
            - relationship_type: "equal", "intersect", or "no_relationship"
            - score: float between 0 and 1
            - explanation: text explanation
        """
        prompt = f"""Compare these two security/compliance framework requirements and determine their semantic relationship:

SOURCE REQUIREMENT:
Reference: {source_item.ref_id}
Content: {source_item.full_sentence}

TARGET REQUIREMENT:
Reference: {target_item.ref_id}
Content: {target_item.full_sentence}

Analyze the semantic similarity and determine:
1. Relationship type:
   - "equal": They address the same topic/requirement with equivalent scope
   - "intersect": They are related but not entirely equivalent (partial overlap)
   - "no_relationship": They address different topics with no meaningful overlap

2. Confidence score (0.0 to 1.0):
   - equal: score = 1.0
   - intersect: score between 0.1 and 0.9 based on strength of relation
   - no_relationship: score = 0.0

3. Brief explanation (1-2 sentences)

Respond in JSON format:
{{"relationship": "equal|intersect|no_relationship", "score": 0.0, "explanation": "..."}}"""

        try:
            response = self.session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "30m",  # Keep model loaded for 30 minutes
                    "options": {
                        "temperature": 0.1,  # Lower for more consistent results
                        "num_ctx": 2048,  # Context window size
                        "num_predict": 200,  # Max tokens to generate
                        "top_p": 0.9,  # Nucleus sampling
                    },
                },
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "{}")

            # Parse JSON response
            parsed = json.loads(response_text)
            relationship = parsed.get("relationship", "no_relationship")
            score = float(parsed.get("score", 0.0))
            explanation = parsed.get("explanation", "No explanation provided")

            # Validate relationship type
            if relationship not in ["equal", "intersect", "no_relationship"]:
                relationship = "no_relationship"
                score = 0.0

            # Ensure score is in valid range
            score = max(0.0, min(1.0, score))

            return relationship, score, explanation

        except Exception as e:
            print(f"Error comparing items: {e}")
            return "no_relationship", 0.0, f"Error: {str(e)}"


def build_mapping_table(
    source_path: str,
    target_path: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "mistral",
    output_path: Optional[str] = None,
    resume: bool = False,
    checkpoint_interval: int = 1,
    top_n: Optional[int] = None,
    threshold: Optional[float] = None,
) -> pd.DataFrame:
    """
    Build a semantic mapping table between two frameworks

    Args:
        source_path: Path to source framework YAML
        target_path: Path to target framework YAML
        ollama_url: Ollama API endpoint
        model: LLM model to use
        output_path: Optional path to save output CSV/Excel
        resume: If True, resume from existing output file
        checkpoint_interval: Save progress every N source items (default: 1)
        top_n: Return top N matches per source item (default: 1 = best match only)
        threshold: Minimum score threshold for matches (0.0-1.0)

    Returns:
        pandas DataFrame with mapping results
    """
    print(f"Parsing source framework: {source_path}")
    source_parser = FrameworkParser(source_path)
    source_items = source_parser.parse()
    print(f"Found {len(source_items)} assessable items in source")

    print(f"\nParsing target framework: {target_path}")
    target_parser = FrameworkParser(target_path)
    target_items = target_parser.parse()
    print(f"Found {len(target_items)} assessable items in target")

    print(f"\nInitializing semantic mapper with model: {model}")
    mapper = SemanticMapper(ollama_url=ollama_url, model=model)

    # Check for existing results to resume from
    results = []
    processed_source_refs = set()
    start_index = 0

    if resume and output_path and Path(output_path).exists():
        print(f"\nResuming from existing file: {output_path}")
        existing_df = (
            pd.read_csv(output_path)
            if output_path.endswith(".csv")
            else pd.read_excel(output_path)
        )

        # Filter results for current model only
        existing_df = existing_df[existing_df["model"] == model]

        results = existing_df.to_dict("records")
        processed_source_refs = set(existing_df["source_ref_id"].tolist())
        start_index = len(processed_source_refs)

        print(f"Loaded {len(processed_source_refs)} existing mappings")
        print(f"Resuming from source item {start_index + 1}/{len(source_items)}")

    # Build mapping table
    total_comparisons = len(source_items) * len(target_items)
    comparison_count = start_index * len(target_items)

    print(f"\nPerforming semantic comparisons...")
    print(f"Total comparisons needed: {total_comparisons}")
    print(f"Already completed: {comparison_count}")
    print(f"Remaining: {total_comparisons - comparison_count}")

    for idx, source_item in enumerate(source_items):
        # Skip already processed items
        if source_item.ref_id in processed_source_refs:
            continue

        # Collect all matches for this source item
        matches = []

        for target_item in target_items:
            comparison_count += 1
            if comparison_count % 10 == 0:
                print(
                    f"Progress: {comparison_count}/{total_comparisons} comparisons..."
                )

            relationship, score, explanation = mapper.compare_items(
                source_item, target_item
            )

            # Collect all matches with their scores
            matches.append(
                {
                    "target_item": target_item,
                    "relationship": relationship,
                    "score": score,
                    "explanation": explanation,
                }
            )

        # Sort by score descending (best matches first)
        matches.sort(key=lambda x: x["score"], reverse=True)

        # Apply filters
        filtered_matches = matches

        # Filter by threshold if specified
        if threshold is not None:
            filtered_matches = [m for m in filtered_matches if m["score"] >= threshold]

        # Limit to top N if specified
        if top_n is not None:
            filtered_matches = filtered_matches[:top_n]

        # If no matches after filtering and we had matches before, keep at least the best one
        if not filtered_matches and matches:
            filtered_matches = matches[:1]

        matches = filtered_matches

        # Create result rows for each match
        for match in matches:
            target_item = match["target_item"]
            result = {
                "model": model,
                "source_ref_id": source_item.ref_id,
                "source_urn": source_item.urn,
                "source_name": source_item.name,
                "source_full_sentence": source_item.full_sentence,
                "target_ref_id": target_item.ref_id,
                "target_urn": target_item.urn,
                "target_name": target_item.name,
                "target_full_sentence": target_item.full_sentence,
                "relationship": match["relationship"],
                "score": match["score"],
                "explanation": match["explanation"],
            }
            results.append(result)

        # Checkpoint: save progress every N items
        if output_path and (idx + 1) % checkpoint_interval == 0:
            df_checkpoint = pd.DataFrame(results)
            output_file = Path(output_path)

            if output_file.suffix == ".xlsx":
                df_checkpoint.to_excel(output_path, index=False, engine="openpyxl")
            else:
                df_checkpoint.to_csv(output_path, index=False)

            print(
                f"\n✓ Checkpoint saved: {idx + 1}/{len(source_items)} items completed"
            )

    # Create DataFrame
    df = pd.DataFrame(results)

    # Save if output path specified
    if output_path:
        output_file = Path(output_path)
        if output_file.suffix == ".xlsx":
            df.to_excel(output_path, index=False, engine="openpyxl")
        else:
            df.to_csv(output_path, index=False)
        print(f"\nMapping table saved to: {output_path}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Framework Mapping Tool - Compare security frameworks using LLM"
    )
    parser.add_argument(
        "--source", required=True, help="Path to source framework YAML file"
    )
    parser.add_argument(
        "--target", required=True, help="Path to target framework YAML file"
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API endpoint URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--model", default="mistral", help="LLM model to use (default: mistral)"
    )
    parser.add_argument("--output", help="Output file path for results (CSV or XLSX)")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing output file if it exists",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=1,
        help="Save checkpoint every N source items (default: 1 = after each item)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Return top N matches per source item (default: 1 = best match only)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum score threshold for matches, 0.0-1.0 (default: None = all matches)",
    )

    args = parser.parse_args()

    # Set default top_n to 1 if neither top_n nor threshold is specified
    top_n = (
        args.top_n
        if args.top_n is not None
        else (None if args.threshold is not None else 1)
    )

    # Build mapping table
    df = build_mapping_table(
        source_path=args.source,
        target_path=args.target,
        ollama_url=args.ollama_url,
        model=args.model,
        output_path=args.output,
        resume=args.resume,
        checkpoint_interval=args.checkpoint_interval,
        top_n=top_n,
        threshold=args.threshold,
    )

    # Print summary
    print("\n" + "=" * 80)
    print("MAPPING SUMMARY")
    print("=" * 80)
    print(f"Model used: {args.model}")

    # Count unique source items
    unique_sources = df["source_ref_id"].nunique()
    total_mappings = len(df)
    avg_matches_per_source = (
        total_mappings / unique_sources if unique_sources > 0 else 0
    )

    print(f"Total source items: {unique_sources}")
    print(f"Total mappings (source→target): {total_mappings}")
    print(f"Average matches per source: {avg_matches_per_source:.2f}")

    if args.top_n:
        print(f"Top-N setting: {args.top_n}")
    if args.threshold:
        print(f"Threshold setting: {args.threshold}")

    print(f"\nRelationship distribution:")
    print(df["relationship"].value_counts())
    print(f"\nScore statistics:")
    print(df["score"].describe())
    print("\n" + "=" * 80)

    # Show sample of best matches
    print("\nTop 5 mappings (by score):")
    print(
        df.nlargest(5, "score")[
            ["source_ref_id", "target_ref_id", "relationship", "score", "explanation"]
        ]
    )


if __name__ == "__main__":
    main()
