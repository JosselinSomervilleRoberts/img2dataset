# Env variables
# S3
export COREWEAVE_ACCESS_KEY=<YOUR-S3-KEY>
export COREWEAVE_SECRET_KEY=<YOUR-S3-SECRET-KEY>
export COREWEAVE_ENDPOINT=<YOUR-S3-ENDPOINT>
# HuggingFace (read-only)
export HF_TOKEN=<YOUR-HF-TOKEN>
# Wandb
export WANDB_API_KEY=<YOUR-WANDB-API-KEY>


export FSSPEC_S3_KEY=$COREWEAVE_ACCESS_KEY
export FSSPEC_S3_SECRET=$COREWEAVE_SECRET_KEY
export FSSPEC_S3_ENDPOINT_URL=$COREWEAVE_ENDPOINT

IMAGE_URLS_ROOT=/home/ubuntu/dataset/metadata
WANDB_PROJECT=laion2b-multi-images-128threads
IMAGE_ROOT="s3://${WANDB_PROJECT}-112224-${NODE_COUNT}nodes"

echo "======= Starting run ======"
echo "- Wandb project: ${WANDB_PROJECT}"
echo "- S3 bucket: ${IMAGE_ROOT}"
echo "- Node ${NODE_ID}/${NODE_COUNT}"

rm -rf ${IMAGE_URLS_ROOT}_temp # In case you run this several times
cd ~/code/img2dataset
python3 -m download_aws \
    --url_list $IMAGE_URLS_ROOT \
    --output_dir $IMAGE_ROOT \
    --temp_dir ${IMAGE_URLS_ROOT}_temp \
    --input_format parquet \
    --output_format webdataset \
    --save_additional_columns "'pwatermark,punsafe,similarity,TEXT,LANGUAGE,prediction'" \
    --local False \
    --processes_count 16 \
    --thread_count 128 \
    --enable_wandb True \
    --wandb_project $WANDB_PROJECT \
    --caption_col "ENG TEXT" \
    --use_public_dns False \
    --node_id $NODE_ID \
    --url_col "URL"