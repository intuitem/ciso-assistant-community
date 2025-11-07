#!/usr/bin/env python3
"""
Model Comparison Tool for Semantic Framework Mapping

This script runs the semantic mapping with multiple models and generates a comparison report.
"""

import argparse
import subprocess
import pandas as pd
from pathlib import Path
from typing import Optional
import sys


def run_mapping(
    source: str,
    target: str,
    model: str,
    output_dir: Path,
    ollama_url: str,
    resume: bool = False,
    checkpoint_interval: int = 1,
    top_n: Optional[int] = None,
    threshold: Optional[float] = None,
) -> Path:
    """Run semantic mapping with a specific model"""
    output_file = output_dir / f"mapping_{model.replace(':', '_')}.csv"

    print(f"\n{'=' * 80}")
    print(f"Running mapping with model: {model}")
    print(f"{'=' * 80}")

    cmd = [
        sys.executable,
        "semantic_mapper.py",
        "--source",
        source,
        "--target",
        target,
        "--model",
        model,
        "--ollama-url",
        ollama_url,
        "--output",
        str(output_file),
        "--checkpoint-interval",
        str(checkpoint_interval),
    ]

    if resume:
        cmd.append("--resume")

    if top_n is not None:
        cmd.extend(["--top-n", str(top_n)])

    if threshold is not None:
        cmd.extend(["--threshold", str(threshold)])

    try:
        subprocess.run(cmd, check=True)
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error running mapping with {model}: {e}")
        return None


def compare_results(result_files: list[Path], output_file: Path):
    """Compare results from different models"""
    print(f"\n{'=' * 80}")
    print("COMPARISON REPORT")
    print(f"{'=' * 80}\n")

    # Load all results
    dfs = []
    for file in result_files:
        if file and file.exists():
            df = pd.read_csv(file)
            dfs.append(df)

    if not dfs:
        print("No results to compare!")
        return

    # Combine all results
    df_combined = pd.concat(dfs, ignore_index=True)

    # 1. Relationship distribution by model
    print("1. RELATIONSHIP DISTRIBUTION BY MODEL")
    print("-" * 80)
    rel_dist = (
        df_combined.groupby(["model", "relationship"]).size().unstack(fill_value=0)
    )
    print(rel_dist)
    print()

    # 2. Score statistics by model
    print("\n2. SCORE STATISTICS BY MODEL")
    print("-" * 80)
    score_stats = df_combined.groupby("model")["score"].describe()
    print(score_stats)
    print()

    # 3. Agreement analysis (where models agree/disagree)
    print("\n3. MODEL AGREEMENT ANALYSIS")
    print("-" * 80)

    if len(dfs) == 2:
        # Pivot to compare two models
        df1 = dfs[0].set_index("source_ref_id")
        df2 = dfs[1].set_index("source_ref_id")

        # Join on source_ref_id
        comparison = df1[["model", "relationship", "score", "target_ref_id"]].join(
            df2[["model", "relationship", "score", "target_ref_id"]],
            lsuffix="_1",
            rsuffix="_2",
            how="outer",
        )

        # Calculate agreement
        same_relationship = (
            comparison["relationship_1"] == comparison["relationship_2"]
        ).sum()
        same_target = (
            comparison["target_ref_id_1"] == comparison["target_ref_id_2"]
        ).sum()
        total = len(comparison)

        model1 = df1["model"].iloc[0]
        model2 = df2["model"].iloc[0]

        print(f"Comparing: {model1} vs {model2}")
        print(f"Total mappings: {total}")
        print(
            f"Same relationship type: {same_relationship} ({same_relationship / total * 100:.1f}%)"
        )
        print(f"Same target mapping: {same_target} ({same_target / total * 100:.1f}%)")

        # Score correlation
        score_corr = comparison["score_1"].corr(comparison["score_2"])
        print(f"Score correlation: {score_corr:.3f}")

        # Disagreements
        disagreements = comparison[
            comparison["relationship_1"] != comparison["relationship_2"]
        ]
        print(f"\nTop disagreements (different relationships):")
        print(
            disagreements[
                [
                    "relationship_1",
                    "score_1",
                    "relationship_2",
                    "score_2",
                    "target_ref_id_1",
                    "target_ref_id_2",
                ]
            ].head(10)
        )

    else:
        # For more than 2 models, show overall agreement
        pivot = df_combined.pivot_table(
            index="source_ref_id",
            columns="model",
            values="relationship",
            aggfunc="first",
        )

        # Count how many models agree per source item
        agreement_count = pivot.apply(lambda row: row.nunique(), axis=1)

        print(
            f"Source items where all {len(dfs)} models agree: {(agreement_count == 1).sum()}"
        )
        print(f"Source items with disagreement: {(agreement_count > 1).sum()}")

    # 4. Save combined results
    output_combined = output_file.parent / "mapping_combined.csv"
    df_combined.to_csv(output_combined, index=False)
    print(f"\n4. COMBINED RESULTS")
    print("-" * 80)
    print(f"All results saved to: {output_combined}")

    # 5. Save comparison report
    with open(output_file, "w") as f:
        f.write("MODEL COMPARISON REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("1. RELATIONSHIP DISTRIBUTION BY MODEL\n")
        f.write("-" * 80 + "\n")
        f.write(rel_dist.to_string() + "\n\n")

        f.write("\n2. SCORE STATISTICS BY MODEL\n")
        f.write("-" * 80 + "\n")
        f.write(score_stats.to_string() + "\n\n")

    print(f"Comparison report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare semantic mapping performance across multiple LLM models"
    )
    parser.add_argument(
        "--source", required=True, help="Path to source framework YAML file"
    )
    parser.add_argument(
        "--target", required=True, help="Path to target framework YAML file"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="List of models to compare (e.g., mistral llama3.1 llama3)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API endpoint URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--output-dir",
        default="./comparison_results",
        help="Directory to save results (default: ./comparison_results)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing output files if they exist",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=1,
        help="Save checkpoint every N source items (default: 1)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Return top N matches per source item (default: 1)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum score threshold for matches, 0.0-1.0 (default: None)",
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"Comparing {len(args.models)} models: {', '.join(args.models)}")
    print(f"Results will be saved to: {output_dir}")

    # Run mapping for each model
    result_files = []
    for model in args.models:
        result_file = run_mapping(
            args.source,
            args.target,
            model,
            output_dir,
            args.ollama_url,
            args.resume,
            args.checkpoint_interval,
            args.top_n,
            args.threshold,
        )
        result_files.append(result_file)

    # Compare results
    report_file = output_dir / "comparison_report.txt"
    compare_results(result_files, report_file)


if __name__ == "__main__":
    main()
