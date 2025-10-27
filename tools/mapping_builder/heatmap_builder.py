#!/usr/bin/env python3
"""
Heatmap Builder for Framework Mappings

This script creates a heatmap visualization showing the relationship scores
between source and target framework items from a mapping CSV file.
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional


def build_heatmap(
    csv_path: str,
    output_path: Optional[str] = None,
    use_labels: bool = False,
    figsize: tuple = (20, 16),
    cmap: str = "YlOrRd",
    vmin: float = 0.0,
    vmax: float = 1.0,
    title: Optional[str] = None,
):
    """
    Build a heatmap from a mapping CSV file

    Args:
        csv_path: Path to the mapping CSV file
        output_path: Path to save the heatmap image (PNG, PDF, etc.)
        use_labels: If True, use ref_ids as labels; if False, use indices
        figsize: Figure size as (width, height) in inches
        cmap: Colormap name (default: YlOrRd)
        vmin: Minimum value for colormap (default: 0.0)
        vmax: Maximum value for colormap (default: 1.0)
        title: Custom title for the heatmap
    """
    print(f"Reading mapping data from: {csv_path}")
    df = pd.read_csv(csv_path)

    # Get unique source and target items (maintaining order)
    source_items = df["source_ref_id"].unique()
    target_items = df["target_ref_id"].unique()

    print(f"Found {len(source_items)} source items")
    print(f"Found {len(target_items)} target items")

    # Create mapping matrix (source × target)
    # Initialize with zeros (no relationship by default)
    matrix = np.zeros((len(source_items), len(target_items)))

    # Create index mappings for fast lookup
    source_to_idx = {item: idx for idx, item in enumerate(source_items)}
    target_to_idx = {item: idx for idx, item in enumerate(target_items)}

    # Fill matrix with scores
    print("Building score matrix...")
    for _, row in df.iterrows():
        source_idx = source_to_idx[row["source_ref_id"]]
        target_idx = target_to_idx[row["target_ref_id"]]
        matrix[source_idx, target_idx] = row["score"]

    # Prepare labels
    if use_labels:
        row_labels = source_items
        col_labels = target_items
    else:
        row_labels = [f"S{i}" for i in range(len(source_items))]
        col_labels = [f"T{i}" for i in range(len(target_items))]

    # Create heatmap
    print("Generating heatmap...")
    fig, ax = plt.subplots(figsize=figsize)

    # Create heatmap with seaborn
    sns.heatmap(
        matrix,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        xticklabels=col_labels,
        yticklabels=row_labels,
        cbar_kws={"label": "Relationship Score"},
        square=False,
        linewidths=0.1 if len(source_items) < 50 and len(target_items) < 50 else 0,
        linecolor="gray",
        ax=ax,
    )

    # Set title
    if title:
        plt.title(title, fontsize=16, pad=20)
    else:
        csv_name = Path(csv_path).stem
        plt.title(f"Framework Mapping Heatmap: {csv_name}", fontsize=16, pad=20)

    # Adjust labels
    if use_labels:
        plt.xticks(rotation=90, fontsize=6)
        plt.yticks(rotation=0, fontsize=6)
    else:
        plt.xticks(rotation=90, fontsize=8)
        plt.yticks(rotation=0, fontsize=8)

    plt.xlabel("Target Items", fontsize=12)
    plt.ylabel("Source Items", fontsize=12)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save if output path specified
    if output_path:
        print(f"Saving heatmap to: {output_path}")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Heatmap saved successfully")
    else:
        print("Displaying heatmap...")
        plt.show()

    # Print statistics
    print("\n" + "=" * 60)
    print("HEATMAP STATISTICS")
    print("=" * 60)
    print(f"Matrix shape: {matrix.shape[0]} × {matrix.shape[1]}")
    print(f"Total cells: {matrix.size}")
    print(
        f"Non-zero cells: {np.count_nonzero(matrix)} ({np.count_nonzero(matrix) / matrix.size * 100:.1f}%)"
    )
    print(f"Mean score: {np.mean(matrix):.3f}")
    print(f"Max score: {np.max(matrix):.3f}")
    print(
        f"Min score (excluding zeros): {np.min(matrix[matrix > 0]) if np.any(matrix > 0) else 0:.3f}"
    )
    print("=" * 60)

    return matrix, source_items, target_items


def build_filtered_heatmap(
    csv_path: str,
    output_path: Optional[str] = None,
    threshold: float = 0.5,
    use_labels: bool = False,
    figsize: tuple = (20, 16),
    cmap: str = "YlOrRd",
    title: Optional[str] = None,
):
    """
    Build a filtered heatmap showing only relationships above a threshold

    Args:
        csv_path: Path to the mapping CSV file
        output_path: Path to save the heatmap image
        threshold: Minimum score to include in the heatmap
        use_labels: If True, use ref_ids as labels; if False, use indices
        figsize: Figure size as (width, height) in inches
        cmap: Colormap name
        title: Custom title for the heatmap
    """
    print(f"Building filtered heatmap (threshold >= {threshold})...")

    # Read and filter data
    df = pd.read_csv(csv_path)
    df_filtered = df[df["score"] >= threshold]

    print(f"Total mappings: {len(df)}")
    print(
        f"Mappings above threshold: {len(df_filtered)} ({len(df_filtered) / len(df) * 100:.1f}%)"
    )

    if df_filtered.empty:
        print("No mappings found above threshold!")
        return None, None, None

    # Get unique items from filtered data
    source_items = df_filtered["source_ref_id"].unique()
    target_items = df_filtered["target_ref_id"].unique()

    print(f"Source items with matches: {len(source_items)}")
    print(f"Target items with matches: {len(target_items)}")

    # Create matrix
    matrix = np.zeros((len(source_items), len(target_items)))
    source_to_idx = {item: idx for idx, item in enumerate(source_items)}
    target_to_idx = {item: idx for idx, item in enumerate(target_items)}

    for _, row in df_filtered.iterrows():
        source_idx = source_to_idx[row["source_ref_id"]]
        target_idx = target_to_idx[row["target_ref_id"]]
        matrix[source_idx, target_idx] = row["score"]

    # Prepare labels
    if use_labels:
        row_labels = source_items
        col_labels = target_items
    else:
        row_labels = [f"S{i}" for i in range(len(source_items))]
        col_labels = [f"T{i}" for i in range(len(target_items))]

    # Create heatmap
    print("Generating filtered heatmap...")
    fig, ax = plt.subplots(figsize=figsize)

    sns.heatmap(
        matrix,
        cmap=cmap,
        vmin=threshold,
        vmax=1.0,
        xticklabels=col_labels,
        yticklabels=row_labels,
        cbar_kws={"label": "Relationship Score"},
        square=False,
        linewidths=0.1 if len(source_items) < 50 and len(target_items) < 50 else 0,
        linecolor="gray",
        ax=ax,
    )

    # Set title
    if title:
        plt.title(title, fontsize=16, pad=20)
    else:
        csv_name = Path(csv_path).stem
        plt.title(
            f"Framework Mapping Heatmap (score >= {threshold}): {csv_name}",
            fontsize=16,
            pad=20,
        )

    # Adjust labels
    if use_labels:
        plt.xticks(rotation=90, fontsize=6)
        plt.yticks(rotation=0, fontsize=6)
    else:
        plt.xticks(rotation=90, fontsize=8)
        plt.yticks(rotation=0, fontsize=8)

    plt.xlabel("Target Items", fontsize=12)
    plt.ylabel("Source Items", fontsize=12)
    plt.tight_layout()

    # Save or show
    if output_path:
        print(f"Saving filtered heatmap to: {output_path}")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"✓ Filtered heatmap saved successfully")
    else:
        plt.show()

    return matrix, source_items, target_items


def main():
    parser = argparse.ArgumentParser(
        description="Heatmap Builder - Visualize framework mapping relationships"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to mapping CSV file (output from semantic_mapper.py)",
    )
    parser.add_argument(
        "--output",
        help="Output path for heatmap image (PNG, PDF, SVG, etc.)",
    )
    parser.add_argument(
        "--use-labels",
        action="store_true",
        help="Use ref_ids as axis labels instead of indices",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Show only relationships with score >= threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--width", type=float, default=20, help="Figure width in inches (default: 20)"
    )
    parser.add_argument(
        "--height", type=float, default=16, help="Figure height in inches (default: 16)"
    )
    parser.add_argument(
        "--cmap",
        default="YlOrRd",
        help="Matplotlib colormap name (default: YlOrRd). Try: viridis, plasma, RdYlGn, coolwarm",
    )
    parser.add_argument("--title", help="Custom title for the heatmap")

    args = parser.parse_args()

    # Validate input file
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return

    figsize = (args.width, args.height)

    # Build heatmap
    if args.threshold is not None:
        build_filtered_heatmap(
            csv_path=args.input,
            output_path=args.output,
            threshold=args.threshold,
            use_labels=args.use_labels,
            figsize=figsize,
            cmap=args.cmap,
            title=args.title,
        )
    else:
        build_heatmap(
            csv_path=args.input,
            output_path=args.output,
            use_labels=args.use_labels,
            figsize=figsize,
            cmap=args.cmap,
            title=args.title,
        )


if __name__ == "__main__":
    main()
