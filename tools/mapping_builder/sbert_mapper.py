#!/usr/bin/env python3
"""
SBERT-based Framework Mapping Tool

This script compares two security framework YAML files using SBERT (Sentence-BERT)
for semantic similarity analysis. It's faster and more deterministic than LLM-based approaches.
"""

import argparse
import yaml
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import torch


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


class SBERTMapper:
    """Uses SBERT (Sentence-BERT) to compute semantic similarity between framework items"""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize SBERT mapper

        Args:
            model_name: Name of the sentence transformer model to use
                Popular options:
                - "all-MiniLM-L6-v2" (default): Fast, good quality, 384 dimensions
                - "all-mpnet-base-v2": Higher quality, slower, 768 dimensions
                - "paraphrase-multilingual-MiniLM-L12-v2": Multilingual support
            device: Device to run on ("cuda", "cpu", or None for auto-detection)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.model_name = model_name

        # Auto-detect device if not specified
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        print(f"Loading SBERT model: {model_name}")
        print(f"Using device: {self.device}")

        # Load model
        self.model = SentenceTransformer(model_name, device=self.device)

        if self.verbose:
            print(f"Model loaded successfully")
            print(
                f"Embedding dimensions: {self.model.get_sentence_embedding_dimension()}"
            )

    def encode_items(self, items: List[FrameworkItem]) -> np.ndarray:
        """
        Encode framework items into embeddings

        Args:
            items: List of framework items to encode

        Returns:
            numpy array of shape (num_items, embedding_dim)
        """
        # Extract text from items
        texts = [item.full_sentence for item in items]

        if self.verbose:
            print(f"Encoding {len(texts)} items...")

        # Encode in batches
        embeddings = self.model.encode(
            texts,
            convert_to_tensor=False,
            show_progress_bar=self.verbose,
            batch_size=32,
        )

        return embeddings

    def compute_similarity(
        self, source_embedding: np.ndarray, target_embedding: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            source_embedding: Source item embedding
            target_embedding: Target item embedding

        Returns:
            Cosine similarity score between -1 and 1 (typically 0-1 for semantic similarity)
        """
        # Convert to tensors if needed
        if not isinstance(source_embedding, torch.Tensor):
            source_embedding = torch.tensor(source_embedding)
        if not isinstance(target_embedding, torch.Tensor):
            target_embedding = torch.tensor(target_embedding)

        # Compute cosine similarity
        similarity = util.cos_sim(source_embedding, target_embedding).item()

        return similarity

    @staticmethod
    def similarity_to_relationship(
        similarity: float,
        equal_threshold: float = 0.85,
        intersect_threshold: float = 0.50,
    ) -> Tuple[str, float]:
        """
        Convert similarity score to relationship type

        Args:
            similarity: Cosine similarity score (0-1)
            equal_threshold: Threshold for "equal" relationship
            intersect_threshold: Threshold for "intersect" relationship

        Returns:
            Tuple of (relationship_type, normalized_score)
        """
        if similarity >= equal_threshold:
            return "equal", 1.0
        elif similarity >= intersect_threshold:
            # Normalize intersect scores to 0.3-0.9 range
            # Map [intersect_threshold, equal_threshold] -> [0.3, 0.9]
            normalized = (
                0.3
                + (similarity - intersect_threshold)
                / (equal_threshold - intersect_threshold)
                * 0.6
            )
            return "intersect", normalized
        else:
            return "no_relationship", 0.0


def build_mapping_table(
    source_path: str,
    target_path: str,
    model_name: str = "all-MiniLM-L6-v2",
    output_path: Optional[str] = None,
    top_n: Optional[int] = None,
    threshold: Optional[float] = None,
    equal_threshold: float = 0.85,
    intersect_threshold: float = 0.50,
    verbose: bool = False,
    device: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build a semantic mapping table between two frameworks using SBERT

    Args:
        source_path: Path to source framework YAML
        target_path: Path to target framework YAML
        model_name: SBERT model name
        output_path: Optional path to save output CSV/Excel
        top_n: Return top N matches per source item (default: None = all above threshold)
        threshold: Minimum similarity threshold for matches (0.0-1.0)
        equal_threshold: Similarity threshold for "equal" relationships (default: 0.85)
        intersect_threshold: Similarity threshold for "intersect" relationships (default: 0.50)
        verbose: Enable verbose logging
        device: Device to run on ("cuda", "cpu", or None for auto)

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

    print(f"\nInitializing SBERT mapper with model: {model_name}")
    mapper = SBERTMapper(model_name=model_name, device=device, verbose=verbose)

    # Encode all items
    print("\nEncoding source items...")
    source_embeddings = mapper.encode_items(source_items)

    print("Encoding target items...")
    target_embeddings = mapper.encode_items(target_items)

    # Compute similarity matrix
    print("\nComputing similarity matrix...")
    total_comparisons = len(source_items) * len(target_items)
    print(f"Total comparisons: {total_comparisons}")

    # Use PyTorch for efficient batch computation
    source_tensor = torch.tensor(source_embeddings).to(mapper.device)
    target_tensor = torch.tensor(target_embeddings).to(mapper.device)

    # Compute all similarities at once (matrix multiplication)
    similarity_matrix = util.cos_sim(source_tensor, target_tensor).cpu().numpy()

    print(f"Similarity matrix shape: {similarity_matrix.shape}")

    # Build results
    results = []
    print("\nBuilding mapping table...")

    for i, source_item in enumerate(source_items):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"Processing source item {i + 1}/{len(source_items)}...")

        # Get similarities for this source item
        similarities = similarity_matrix[i]

        # Create list of matches with scores
        matches = []
        for j, target_item in enumerate(target_items):
            similarity = similarities[j]

            # Convert similarity to relationship
            relationship, score = SBERTMapper.similarity_to_relationship(
                similarity, equal_threshold, intersect_threshold
            )

            matches.append(
                {
                    "target_item": target_item,
                    "relationship": relationship,
                    "score": score,
                    "similarity": similarity,
                }
            )

        # Sort by similarity descending
        matches.sort(key=lambda x: x["similarity"], reverse=True)

        # Apply filters
        filtered_matches = matches

        # Filter by threshold if specified
        if threshold is not None:
            filtered_matches = [
                m for m in filtered_matches if m["similarity"] >= threshold
            ]

        # Limit to top N if specified
        if top_n is not None:
            filtered_matches = filtered_matches[:top_n]

        # If no matches after filtering and we had matches before, keep at least the best one
        if not filtered_matches and matches:
            filtered_matches = matches[:1]

        # Create result rows for each match
        for match in filtered_matches:
            target_item = match["target_item"]
            result = {
                "model": model_name,
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
                "similarity": match["similarity"],
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
        description="SBERT Framework Mapping Tool - Compare security frameworks using SBERT"
    )
    parser.add_argument(
        "--source", required=True, help="Path to source framework YAML file"
    )
    parser.add_argument(
        "--target", required=True, help="Path to target framework YAML file"
    )
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="SBERT model name (default: all-MiniLM-L6-v2). "
        "Options: all-MiniLM-L6-v2 (fast), all-mpnet-base-v2 (quality), "
        "paraphrase-multilingual-MiniLM-L12-v2 (multilingual)",
    )
    parser.add_argument("--output", help="Output file path for results (CSV or XLSX)")
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Return top N matches per source item (default: None = all above threshold)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum similarity threshold for matches, 0.0-1.0 (default: None)",
    )
    parser.add_argument(
        "--equal-threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for 'equal' relationships (default: 0.85)",
    )
    parser.add_argument(
        "--intersect-threshold",
        type=float,
        default=0.50,
        help="Similarity threshold for 'intersect' relationships (default: 0.50)",
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu", "mps"],
        default=None,
        help="Device to run on (default: auto-detect)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Validate thresholds
    if args.equal_threshold <= args.intersect_threshold:
        parser.error("equal-threshold must be greater than intersect-threshold")

    # Set default top_n to 1 if neither top_n nor threshold is specified
    # This ensures we get best match only by default
    top_n = (
        args.top_n
        if args.top_n is not None
        else (None if args.threshold is not None else 1)
    )

    # Build mapping table
    df = build_mapping_table(
        source_path=args.source,
        target_path=args.target,
        model_name=args.model,
        output_path=args.output,
        top_n=top_n,
        threshold=args.threshold,
        equal_threshold=args.equal_threshold,
        intersect_threshold=args.intersect_threshold,
        verbose=args.verbose,
        device=args.device,
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

    if top_n:
        print(f"Top-N setting: {top_n}")
    if args.threshold:
        print(f"Threshold setting: {args.threshold}")

    print(f"\nRelationship distribution:")
    print(df["relationship"].value_counts())
    print(f"\nSimilarity score statistics:")
    print(df["similarity"].describe())
    print(f"\nNormalized score statistics:")
    print(df["score"].describe())
    print("\n" + "=" * 80)

    # Show sample of best matches
    print("\nTop 10 mappings (by similarity):")
    print(
        df.nlargest(10, "similarity")[
            [
                "source_ref_id",
                "target_ref_id",
                "relationship",
                "similarity",
                "score",
            ]
        ].to_string()
    )


if __name__ == "__main__":
    main()
