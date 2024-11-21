import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import fire
import requests
from tqdm import tqdm  # For progress bar


def download_part(
    part_number: int,
    progress_bar: tqdm,
    base_url: str,
    file_prefix: str,
    file_suffix: str,
    uuid: str,
    hf_token: str,
    download_path: str,
) -> None:
    """
    Function to download a specific part of the data, with progress.
    """
    formatted_part = f"{part_number:05d}"
    part_filename = f"{file_prefix}{formatted_part}-{uuid}{file_suffix}"
    url = f"{base_url}{part_filename}"
    save_path = os.path.join(download_path, part_filename)

    headers = {
        "Authorization": f"Bearer {hf_token}",
    }

    try:
        # Perform the GET request for downloading with chunking for large files
        with requests.get(url, headers=headers, stream=True) as response:
            response.raise_for_status()  # Ensure we handle errors

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))  # Update progress bar

        print(f"Downloaded {part_filename}")

    except Exception as e:
        print(f"Error downloading {part_filename}: {e}")


def download(
    download_path: str,
    uuid: str,
    base_url: str,
    start_part: int,
    num_parts: int,
    num_workers: int,
) -> None:
    """
    Download all parts of a file in parallel with progress.
    """
    num_workers = min(num_workers, num_parts)

    hf_token = os.getenv("HF_TOKEN", None)
    if hf_token is None:
        raise ValueError("Please set the HF_TOKEN environment variable")

    # File format config
    file_prefix = "part-"
    file_suffix = ".snappy.parquet"

    # Ensure download directory exists
    os.makedirs(download_path, exist_ok=True)

    # Calculate the total size of all parts by summing the Content-Length of each part
    # NOTE(josselin): total size is wrong but we don't care
    total_size = 1

    # Initialize a progress bar for bytes (total size)
    with tqdm(
        total=total_size, desc="Overall Progress", unit="B", unit_scale=True
    ) as overall_bar:
        # Create a thread pool and submit the download tasks
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(
                    download_part,
                    part,
                    overall_bar,
                    base_url,
                    file_prefix,
                    file_suffix,
                    uuid,
                    hf_token,
                    download_path,
                )
                for part in range(start_part, start_part + num_parts)
            ]

            # Collect future results (wait for all parallel tasks to complete)
            for future in as_completed(futures):
                future.result()  # Will raise any exception that occurred during download


if __name__ == "__main__":
    """
    Example usage:

    mkdir -p "/mnt/vast/datasets/multimodal/pretrain/relaion2B-en/metadata"
    pip install requests
    pip install tqdm
    python download_hf_metadata.py \
    --download_path "/home/ec2-user/relaion2B-en/metadata" \
    --uuid "339dc23d-0869-4dc0-9390-b4036fcc80c2-c000" \
    --base_url "https://huggingface.co/datasets/laion/relaion2B-en-research-safe/resolve/main/" \
    --start_part 0 \
    --num_parts 16 \
    --num_workers 96
    """
    fire.Fire(download)
