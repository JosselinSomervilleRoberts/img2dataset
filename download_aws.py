import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Union

import fire
import pandas as pd
import tqdm
from cloudpathlib import S3Client, S3Path

import img2dataset


def download_images(
    url_list: str,
    output_dir: str,
    temp_dir: str,
    local: bool = False,
    processes_count: int = 96,
    thread_count: int = 256,
    image_size: int = 4096,
    resize_mode: str = "keep_ratio_largest",
    min_image_size: int = 0,
    max_aspect_ratio: float = float("inf"),
    input_format: str = "json",
    url_col: str = "url",
    caption_col: str = "caption",
    bbox_col: Optional[str] = None,
    encode_format: str = "jpg",
    output_format: str = "webdataset",
    distributor: str = "multiprocessing",
    save_additional_columns: Optional[str] = None,
    number_sample_per_shard: int = 10000,
    retries: int = 3,
    enable_wandb: bool = True,
    wandb_project: str = "img_download",
    url_list_already_in_temp_dir: bool = False,
    resume: bool = False,
    use_public_dns: bool = False,
    dns_cache_host: str = "localhost",
    dns_cache_type: str = "shared_lru",
    dns_cache_size: int = 10_000_000,
    node_id: int = 0,
) -> None:
    """
    Download images from a list of URLs using img2dataset.

    Args:
        url_list: local folder of files of URLs to download
        output_dir: local folder or s3 bucket ("s3://...") where to save the images
        temp_dir: temporary directory to store intermediate URLs to download for each
         node - TODO this is only needed because Spark output folders are currently
         read-only
        nodes_count: number of nodes for download
        processes_count: number of processes per node
        thread_count: number of threads per process - increase until CPU close to 100%,
         default 256 is good on our CPU nodes

    More details in https://github.com/rom1504/img2dataset
    """
    assert resize_mode == "keep_ratio_largest"
    assert input_format in ["json", "parquet"]
    assert encode_format == "jpg"
    assert output_format == "webdataset"
    assert distributor == "multiprocessing"

    args_dict = locals()
    args_dict.pop("local")
    args_dict.pop("temp_dir")
    args_dict.pop("resume")
    args_dict.pop("node_id")
    args = args_dict.copy()

    url_path = Path(url_list)
    assert url_path.is_dir()
    url_paths = list(Path(url_list).glob(f"*.{input_format}"))

    if output_dir.startswith("s3://"):
        client = S3Client(
            aws_access_key_id=os.getenv("COREWEAVE_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("COREWEAVE_SECRET_KEY"),
            endpoint_url=os.getenv("COREWEAVE_ENDPOINT"),
        )
        output_path: Union[S3Path, Path] = S3Path(output_dir, client=client)
    else:
        output_path = Path(output_dir)

    # if not resume:
    #     assert not output_path.exists(), f"{output_path} already exists"

    output_path.mkdir(exist_ok=True)

    temp_path = Path(temp_dir)
    if not url_list_already_in_temp_dir:
        if not resume:
            assert not temp_path.exists(), f"{temp_path} already exists"

        temp_path.mkdir(exist_ok=True)

    output_path_id = output_path / f"node_{node_id}_output"
    args["output_dir"] = output_path_id
    url_path_id = temp_path / f"node_{node_id}_input"
    args["url_list"] = url_path_id

    if not url_list_already_in_temp_dir:
        url_path_id.mkdir(exist_ok=True)
        for path in url_paths:
            if not resume or not (url_path_id / path.name).exists():
                (url_path_id / path.name).symlink_to(path)

    # We directly lauch the download here:
    print(f"args: {args}")
    _download_images(**args)


def _download_images(
    url_list: Path,
    output_dir: Union[Path, S3Path],
    processes_count: int,
    thread_count: int,
    image_size: int,
    resize_mode: str,
    min_image_size: int,
    max_aspect_ratio: float,
    input_format: str,
    url_col: str,
    caption_col: str,
    encode_format: str,
    output_format: str,
    distributor: str,
    save_additional_columns: Optional[str],
    number_sample_per_shard: int,
    retries: int,
    enable_wandb: bool,
    wandb_project: str,
    url_list_already_in_temp_dir: bool,
    bbox_col: Optional[str] = None,
    use_public_dns: bool = False,
    dns_cache_host: str = "localhost",
    dns_cache_type: str = "shared_lru",
    dns_cache_size: int = 10_000_000,
) -> None:
    if input_format == "json":
        url_list_parquet = Path(str(url_list) + "_parquet")

        if not url_list_already_in_temp_dir:
            url_list_parquet.mkdir()
            _json_url_list_to_parquet(url_list, url_list_parquet)

        url_list = url_list_parquet
        input_format = "parquet"

    save_additional_columns_list = None
    if save_additional_columns is not None:
        save_additional_columns_list = save_additional_columns.split(",")

    img2dataset.download(
        url_list=str(url_list),  # img2dataset expects a string
        image_size=image_size,
        output_folder=str(output_dir),  # img2dataset expects a string
        processes_count=processes_count,
        thread_count=thread_count,
        resize_mode=resize_mode,
        min_image_size=min_image_size,
        max_aspect_ratio=max_aspect_ratio,
        input_format=input_format,
        encode_format=encode_format,
        output_format=output_format,
        distributor=distributor,
        url_col=url_col,
        caption_col=caption_col,
        bbox_col=bbox_col,
        number_sample_per_shard=number_sample_per_shard,
        oom_shard_count=8,
        retries=retries,
        enable_wandb=enable_wandb,
        wandb_project=wandb_project,
        # ignore_ssl_certificate=True,
        save_additional_columns=save_additional_columns_list,
        resize_only_if_bigger=True,
        disallowed_header_directives=[],  # By default ["noai", "noimageai", "noindex", "noimageindex"], we want to avoid this
        use_public_dns=use_public_dns,
        dns_cache_host=dns_cache_host,
        dns_cache_type=dns_cache_type,
        dns_cache_size=dns_cache_size,
    )


def _json_file_to_parquet(file_path: Path, temp_dir: Path) -> int:
    """
    Converts a single JSON file to Parquet format and writes it to temp_dir.
    """
    new_file_name = temp_dir / file_path.with_suffix(".parquet").name
    df = pd.read_json(file_path, lines=True)
    df.to_parquet(new_file_name)
    return len(df)


def _json_url_list_to_parquet(url_list: Path, temp_dir: Path) -> None:
    json_files = list(url_list.glob("*.json"))

    total_line_count = 0
    print(
        f"Writing URL list to a new temp directory {temp_dir} because of Spark permissions"
    )
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_file = {
            executor.submit(_json_file_to_parquet, file, temp_dir): file
            for file in json_files
        }
        for future in tqdm.tqdm(
            as_completed(future_to_file), total=len(future_to_file)
        ):
            line_count = future.result()
            exception = future.exception()
            if exception:
                print(exception)
            total_line_count += line_count

    print(f"Number of URLs to attempt downloading: {total_line_count}")


def _split_list_into_chunks(lst: list, n: int) -> list:
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]


if __name__ == "__main__":
    """
    # Crawl
    DEDUP_IMAGE_URLS_ROOT=/mnt/vast/datasets/multimodal_crawl/dedup_image_urls
    IMAGE_ROOT=/mnt/vast/datasets/multimodal_crawl/images
    python -m zephyr.image.download \
        --url_list $DEDUP_IMAGE_URLS_ROOT \
        --output_dir $IMAGE_ROOT \
        --input_format json \
        --output_format webdataset \
        --save_additional_columns "meta" \
        --local False \
        --nodes_count 10 \
        --processes_count 96 \
        --thread_count 256 \
        --enable_wandb True \
        --wandb_project crawl-with-images
    """
    fire.Fire(download_images)
