import os
import shutil
from pathlib import Path

import fire
from huggingface_hub import snapshot_download


def download_and_process_metadata(
    node_id: int,  # ID of the current node (0-indexed)
    num_nodes: int,  # Total number of nodes
    download_path: str,  # Directory to store metadata
):
    """
    Function to download and process metadata files, splitting the workload across multiple nodes.

    Args:
        node_id (int): ID of the current node (0-indexed).
        num_nodes (int): Total number of nodes.
        metadata_dir (Path): Directory to store metadata files.
    """
    # Constant repository name for the "datacomp_1b" scale
    hf_repo = "mlfoundations/datacomp_1b"

    # Always download metadata (simulate overwrite_metadata=True behavior)
    metadata_dir: Path = Path(download_path)
    if metadata_dir.exists():
        print(f"Cleaning up {metadata_dir}")
        shutil.rmtree(metadata_dir)
    metadata_dir.mkdir(parents=True)

    print(f"Node {node_id}: Downloading metadata to {metadata_dir}...")

    # Define cache directory for Hugging Face snapshot download
    cache_dir = metadata_dir.parent / "hf"
    hf_snapshot_args = dict(
        repo_id=hf_repo,
        allow_patterns="*.parquet",
        local_dir=metadata_dir,
        cache_dir=cache_dir,
        local_dir_use_symlinks=False,
        repo_type="dataset",
    )

    # Download metadata `.parquet` files
    snapshot_download(**hf_snapshot_args)

    # Get the list of downloaded `.parquet` (and optionally `.npz`) files
    metadata_files = list(metadata_dir.glob("*.parquet"))

    metadata_files.sort()  # Ensure a consistent order for distributed processing
    num_shards = len(metadata_files)

    print(f"Node {node_id}: Total metadata files (shards): {num_shards}")
    print(f"Distributing workload across {num_nodes} nodes...")

    # Calculate shard range for this node
    shards_per_node = num_shards // num_nodes
    excess_shards = num_shards % num_nodes
    start_idx = node_id * shards_per_node + min(node_id, excess_shards)
    end_idx = start_idx + shards_per_node + (1 if node_id < excess_shards else 0)
    assigned_files = metadata_files[start_idx:end_idx]

    print(f"Node {node_id}: Responsible for shards {start_idx} to {end_idx - 1}")
    print(f"Node {node_id}: Will process {len(assigned_files)} files.")

    # Delete all shards not assigned to this node
    for file in metadata_files:
        if file not in assigned_files:
            # Using os.remove() instead of Path.unlink() to avoid FileNotFoundError
            print(f"Node {node_id}: Deleting {file}")
            os.remove(file)

    # Cleanup the cache directory
    cleanup_dir(cache_dir)

    print(f"Node {node_id}: Done processing assigned metadata files.")


def cleanup_dir(directory):
    """
    Utility function to remove a directory if it exists.

    Args:
        directory (Path): Path of the directory to be removed.
    """
    if directory.exists() and directory.is_dir():
        shutil.rmtree(directory)


if __name__ == "__main__":
    fire.Fire(download_and_process_metadata)
