# Submit img2dataset jobs to AWS

Make sure to replace all the secrets keys in the bash files first.
Then request some `m6i.4xlarge` instances. They are the nmost cost efficient for our application.
We cannot scrape more than 1000 images/s per instance otherwise some rates on AWS are exceedeed and basically the network connextion is shutdown (for a few seconds). At the given rate, 16vCPUs is therefore the maximum that does not exceed this amount of requests.

Copy from the dashboard all the domaine names and put them in a txt file. You can copy everything and then use this regex `\n^(?!.*\.com$).*` and replace every match by nothing. You will keep only the domain names.

### VERY IMPORTANT
When you launch a job below, due to some bad piping (my fault I guess), some scripts might be copied but not run. Here is an example:
```bash
Launching job de2e5a90-7beb-4693-8e07-9b7259c57437 on 32 machines.
Copying script to ec2-16-171-195-77.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-171-195-77.eu-north-1.compute.amazonaws.com
Copying script to ec2-13-61-2-87.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-13-61-2-87.eu-north-1.compute.amazonaws.com
Copying script to ec2-16-171-196-117.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-171-196-117.eu-north-1.compute.amazonaws.com
Copying script to ec2-16-170-241-55.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-170-241-55.eu-north-1.compute.amazonaws.com
Copying script to ec2-16-171-0-26.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-171-0-26.eu-north-1.compute.amazonaws.com
Copying script to ec2-13-51-72-150.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-13-51-72-150.eu-north-1.compute.amazonaws.com
Copying script to ec2-13-60-78-243.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-13-60-78-243.eu-north-1.compute.amazonaws.com
Copying script to ec2-16-170-215-98.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-170-215-98.eu-north-1.compute.amazonaws.com
Copying script to ec2-16-171-151-80.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-171-151-80.eu-north-1.compute.amazonaws.com
Copying script to ec2-16-171-40-197.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-16-171-40-197.eu-north-1.compute.amazonaws.com
Copying script to ec2-13-60-156-58.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-13-60-156-58.eu-north-1.compute.amazonaws.com
Copying script to ec2-13-60-214-96.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Runnning the command for ubuntu@ec2-13-60-214-96.eu-north-1.compute.amazonaws.com
Copying script to ec2-13-60-211-243.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Copying script to ec2-13-60-240-213.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Copying script to ec2-13-61-8-137.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
```
You should see one `Running` line per `Copying`. My laptop stops at 12 SSH connexions. In this case, wait and you might see after a few minutes the commands appearing, like this:
```bash
Copying script to ec2-16-171-25-98.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Copying script to ec2-13-60-54-88.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Copying script to ec2-13-60-187-33.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Copying script to ec2-13-51-207-17.eu-north-1.compute.amazonaws.com:/home/ubuntu/scripts/script_de2e5a90-7beb-4693-8e07-9b7259c57437.sh
Saved job metadata to launched_setup_laion_2b_en.json
Job launched! Logs are stored remotely. To fetch logs later, use `fetch_logs`.
Runnning the command for ubuntu@ec2-13-60-211-243.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-60-240-213.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-61-8-137.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-61-4-114.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-16-171-39-104.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-51-56-205.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-48-193-60.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-61-9-200.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-51-168-108.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-51-172-187.eu-north-1.compute.amazonaws.com
Runnning the command for ubuntu@ec2-13-60-95-59.eu-north-1.compute.amazonaws.com
```
If you do not see that, press `Ctrl + C`, this will break the pipes and submit instantly 12 more jobs, wait a bit and continue until all your jobs are submitted.

Even if you do not use `--wait`, again due to some bad piping logic, the script will not end. You can safely press `Ctrl + C` if all the commands have started to run (i.e. as many `Running` as `Copying`).


### Kill a job
```bash
python3 ssh_parallel_launch.py launch \
    --script cancel.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-north-1.pem \
    --ssh_hosts hosts_laion_2b_en.txt \
    --ssh_username ubuntu \
    --jobs_file cancel.json
```

## LAION2B-en
```bash
python3 ssh_parallel_launch.py launch \
    --script setup_laion_2b_en.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-north-1.pem \
    --ssh_hosts hosts_laion_2b_en.txt \
    --ssh_username ubuntu \
    --jobs_file launched_setup_laion_2b_en.json

python3 ssh_parallel_launch.py launch \
    --script run_laion_2b_en.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-north-1.pem \
    --ssh_hosts hosts_laion_2b_en.txt \
    --ssh_username ubuntu \
    --jobs_file launched_run_laion_2b_en.json
```
Gather logs:
```bash
python3 ssh_parallel_launch.py fetch-logs \
    --output_path ./logs_setup_laion_2b_en \
    --jobs_file launched_setup_laion_2b_en.json \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-north-1.pem

python3 ssh_parallel_launch.py fetch-logs \
    --output_path ./logs_srun_laion_2b_en \
    --jobs_file launched_run_laion_2b_en.json \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-north-1.pem
```

## LAION2B-multi
```bash
python3 ssh_parallel_launch.py launch \
    --script setup_laion_2b_multi.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-us-west-2.pem \
    --ssh_hosts hosts_laion_2b_multi.txt \
    --ssh_username ubuntu \
    --jobs_file launched_setup_laion_2b_multi.json

python3 ssh_parallel_launch.py launch \
    --script run_laion_2b_multi.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-us-west-2.pem \
    --ssh_hosts hosts_laion_2b_multi.txt \
    --ssh_username ubuntu \
    --jobs_file launched_run_laion_2b_multi.json
```
Gather logs:
```bash
python3 ssh_parallel_launch.py fetch-logs \
    --output_path ./logs_setup_laion_2b_multi \
    --jobs_file launched_setup_laion_2b_multi.json \
    --ssh_key_path /Users/josselin/Downloads/joss-key-us-west-2.pem

python3 ssh_parallel_launch.py fetch-logs \
    --output_path ./logs_srun_laion_2b_multi \
    --jobs_file launched_run_laion_2b_multi.json \
    --ssh_key_path /Users/josselin/Downloads/joss-key-us-west-2.pem
```

## LAION1B-nolang
```bash
python3 ssh_parallel_launch.py launch \
    --script setup_laion_1b_nolang.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-west-3.pem \
    --ssh_hosts hosts_laion_1b_nolang.txt \
    --ssh_username ubuntu \
    --jobs_file launched_setup_laion_1b_nolang.json

python3 ssh_parallel_launch.py launch \
    --script run_laion_1b_nolang.sh \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-west-3.pem \
    --ssh_hosts hosts_laion_1b_nolang.txt \
    --ssh_username ubuntu \
    --jobs_file launched_run_laion_1b_nolang.json
```
Gather logs:
```bash
python3 ssh_parallel_launch.py fetch-logs \
    --output_path ./logs_setup_laion_1b_nolang \
    --jobs_file launched_setup_laion_1b_nolang.json \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-west-3.pem

python3 ssh_parallel_launch.py fetch-logs \
    --output_path ./logs_srun_laion_1b_nolang \
    --jobs_file launched_run_laion_1b_nolang.json \
    --ssh_key_path /Users/josselin/Downloads/joss-key-eu-west-3.pem
```