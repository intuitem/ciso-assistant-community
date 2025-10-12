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
        self._verify_model()

    def _verify_model(self):
        """Verify that the specified model is available in Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
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
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
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
) -> pd.DataFrame:
    """
    Build a semantic mapping table between two frameworks

    Args:
        source_path: Path to source framework YAML
        target_path: Path to target framework YAML
        ollama_url: Ollama API endpoint
        model: LLM model to use
        output_path: Optional path to save output CSV/Excel

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

    # Build mapping table
    results = []
    total_comparisons = len(source_items) * len(target_items)
    comparison_count = 0

    print(f"\nPerforming {total_comparisons} semantic comparisons...")

    for source_item in source_items:
        best_match = None
        best_score = 0.0
        best_relationship = "no_relationship"
        best_explanation = ""

        for target_item in target_items:
            comparison_count += 1
            if comparison_count % 10 == 0:
                print(
                    f"Progress: {comparison_count}/{total_comparisons} comparisons..."
                )

            relationship, score, explanation = mapper.compare_items(
                source_item, target_item
            )

            # Track best match for this source item
            if score > best_score:
                best_score = score
                best_relationship = relationship
                best_explanation = explanation
                best_match = target_item

        # Add result row
        result = {
            "model": model,
            "source_ref_id": source_item.ref_id,
            "source_urn": source_item.urn,
            "source_name": source_item.name,
            "source_full_sentence": source_item.full_sentence,
            "target_ref_id": best_match.ref_id if best_match else "",
            "target_urn": best_match.urn if best_match else "",
            "target_name": best_match.name if best_match else "",
            "target_full_sentence": best_match.full_sentence if best_match else "",
            "relationship": best_relationship,
            "score": best_score,
            "explanation": best_explanation,
        }
        results.append(result)

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

    args = parser.parse_args()

    # Build mapping table
    df = build_mapping_table(
        source_path=args.source,
        target_path=args.target,
        ollama_url=args.ollama_url,
        model=args.model,
        output_path=args.output,
    )

    # Print summary
    print("\n" + "=" * 80)
    print("MAPPING SUMMARY")
    print("=" * 80)
    print(f"Model used: {args.model}")
    print(f"Total source items: {len(df)}")
    print(f"\nRelationship distribution:")
    print(df["relationship"].value_counts())
    print(f"\nScore statistics:")
    print(df["score"].describe())
    print("\n" + "=" * 80)

    # Show sample of best matches
    print("\nTop 5 matches (by score):")
    print(
        df.nlargest(5, "score")[
            ["source_ref_id", "target_ref_id", "relationship", "score", "explanation"]
        ]
    )


if __name__ == "__main__":
    main()
