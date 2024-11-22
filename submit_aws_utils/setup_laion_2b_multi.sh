# Input values
TOTAL_PARTS=128

# reLAION-2B-multi
# region: us-west-2
HF_DATASET_URL="https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main/"
HF_UUID="00478b7a-941e-4176-b569-25f4be656991-c000"

# Compute intermediate values
NUM_PARTS=$((TOTAL_PARTS / NODE_COUNT))
START_PART=$((NUM_PARTS * NODE_ID))

# Set non-interactive mode (IMPORTANT: required for apt to avoid pop-ups)
export DEBIAN_FRONTEND=noninteractive

# Update and install packages without any prompts
echo "======= Install packages + pip ======"
sudo apt update -y
sudo apt install -y --no-install-recommends python3-pip > /dev/null 2>&1 || { echo "Failed to install python3-pip"; exit 1; }

# Prepare directories, clone repository, and install Python dependencies
cd ~
mkdir -p ~/code
# rm -rf ~/dataset/metadata # In case we relaunch
mkdir -p ~/dataset/metadata
cd code
git clone https://github.com/JosselinSomervilleRoberts/img2dataset.git
cd img2dataset

# Install Python dependencies
pip install -r requirements.txt
pip install boto3
pip install s3fs
pip install opencv-python
sudo apt update
sudo apt install -y libgl1
cd ~

# Env variables
# S3
export COREWEAVE_ACCESS_KEY=<YOUR-S3-KEY>
export COREWEAVE_SECRET_KEY=<YOUR-S3-SECRET-KEY>
export COREWEAVE_ENDPOINT=<YOUR-S3-ENDPOINT>
# HuggingFace (read-only)
export HF_TOKEN=<YOUR-HF-TOKEN>
# Wandb
export WANDB_API_KEY=<YOUR-WANDB-API-KEY>
mkdir -p ~/.aws
cat <<EOF > ~/.aws/credentials
[default]
aws_access_key_id = <YOUR-S3-KEY>
aws_secret_access_key = <YOUR-S3-SECRET-KEY>
EOF
mkdir -p ~/.config/fsspec
cat <<EOF > ~/.config/fsspec/s3.json
{
  "s3": {
    "client_kwargs": {
            "endpoint_url": "<YOUR-S3-ENDPOINT>",
            "aws_access_key_id": "<YOUR-S3-KEY>",
           "aws_secret_access_key": "<YOUR-S3-SECRET-KEY>"
    }
  }
}
EOF
echo "===================================\n"


# Setup Knot + bind9 resolver
echo "======= Install knot + bind9 ======"
sudo apt-get update
sudo apt-get -y install apt-transport-https ca-certificates wget
sudo wget -O /usr/share/keyrings/cznic-labs-pkg.gpg https://pkg.labs.nic.cz/gpg
echo "deb [signed-by=/usr/share/keyrings/cznic-labs-pkg.gpg] https://pkg.labs.nic.cz/knot-resolver jammy main" | sudo tee /etc/apt/sources.list.d/cznic-labs-knot-resolver.list 
sudo apt-get update
sudo apt-get install knot-resolver -y
sudo sh -c 'echo `hostname -I` `hostname` >> /etc/hosts'
sudo sh -c 'echo nameserver 127.0.0.1 > /etc/resolv.conf'
sudo systemctl stop systemd-resolved
sudo systemctl start kresd@1.service
sudo systemctl start kresd@2.service
sudo systemctl start kresd@3.service
sudo systemctl start kresd@4.service

# Bind9 install
sudo apt install bind9 -y
BIND_CONFIG=/etc/bind/named.conf.options
sudo tee "$BIND_CONFIG" > /dev/null <<EOF
options {
	directory "/var/cache/bind";

	// Performance optimizations for BIND9 resolver
	recursive-clients 10000;
	resolver-query-timeout 30000;
	max-clients-per-query 10000;
	max-cache-size 2000m;

	// Default system settings
	dnssec-validation auto;
	listen-on-v6 { any; };
};
EOF
sudo systemctl restart bind9
echo nameserver 127.0.0.1 | sudo tee -a /etc/resolv.conf
echo "------------- Dig test -------------"
dig @localhost google.com
echo "===================================\n"


# Download HF metadata
echo "======= Downloading metadata ======"
cd ~/code/img2dataset
git pull
python3 download_hf_metadata.py \
    --download_path "/home/ubuntu/dataset/metadata" \
    --uuid $HF_UUID \
    --base_url $HF_DATASET_URL \
    --start_part $START_PART \
    --num_parts $NUM_PARTS \
    --num_workers 16
echo "===================================\n"


# Pinting done
echo "======= Checks on sharding ======"
echo "- Node ${NODE_ID}/${NODE_COUNT} treating ${NUM_PARTS}/${TOTAL_PARTS} (starting at $START_PART)"
echo "- Num parts check: ${NUM_PARTS} [expected], $(ls /home/ubuntu/dataset/metadata | wc -l) [actual]"
echo "======= Setup done, ready to run ========"