import os
import subprocess
import uuid
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import List, Tuple, Dict
import fire


def ensure_remote_directories(
    ssh_host: str, ssh_key_path: str, ssh_username: str
) -> bool:
    """Ensure the required remote directories (runs/ and scripts/) exist."""
    try:
        command = f"mkdir -p /home/{ssh_username}/runs /home/{ssh_username}/scripts"
        ssh_command = [
            "ssh",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",  # Automatically accept host key
            f"{ssh_username}@{ssh_host}",
            command,
        ]
        #print(ssh_command)
        result = subprocess.run(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(f"Error creating remote directories on {ssh_host}: {result.stderr}")
        return True
    except Exception as e:
        print(f"Exception ensuring remote directories on {ssh_host}: {e}")
        return False


def copy_script_to_remote(
    ssh_key_path: str, ssh_username: str, ssh_host: str, local_script_path: str, remote_script_path: str
) -> bool:
    """Copy the local script to the remote machine."""
    try:
        scp_command = [
            "scp",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",  # Automatically accept host key
            local_script_path,
            f"{ssh_username}@{ssh_host}:{remote_script_path}",
        ]
        print(f"Copying script to {ssh_host}:{remote_script_path}")
        result = subprocess.run(
            scp_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(f"Error copying script: {result.stderr}")
        return True
    except Exception as e:
        print(f"Exception during script copy: {e}")
        return False


def run_command(
    ssh_host: str,
    ssh_key_path: str,
    ssh_username: str,
    remote_script_path: str,
    remote_stdout_file: str,
    remote_stderr_file: str,
    node_id: int,
    node_count: int,
) -> Tuple[bool, str]:
    """Run the provided script on the remote machine."""
    try:
        # Assemble the remote execution command
        command = f"""
export NODE_ID={node_id} &&
export NODE_COUNT={node_count} &&
bash {remote_script_path} > {remote_stdout_file} 2> {remote_stderr_file}
"""
        ssh_command = [
            "ssh",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",  # Automatically accept host key
            f"{ssh_username}@{ssh_host}",
            command,
        ]
        print(f"Runnning the command for {ssh_username}@{ssh_host}")
        result = subprocess.run(
            ssh_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(f"Error on {ssh_host}: {result.stderr}")
        return True, None
    except Exception as e:
        return False, str(e)


def scp_logs(
    ssh_key_path: str, ssh_username: str, ssh_host: str, remote_file: str, local_file: str
) -> bool:
    """Copy a file from the remote machine to the local machine."""
    try:
        scp_command = [
            "scp",
            "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",  # Automatically accept host key
            f"{ssh_username}@{ssh_host}:{remote_file}",
            local_file,
        ]
        result = subprocess.run(
            scp_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(f"Error during SCP: {result.stderr}")
        return True
    except Exception as e:
        print(f"Exception during SCP: {e}")
        return False


def save_job_metadata(unique_id: str, hosts: List[str], ssh_username: str, jobs_file: str):
    """Save job metadata to a JSON file."""
    job_metadata = {
        "id": unique_id,
        "hosts": [{"host": host, "username": ssh_username, "base_path": f"/home/{ssh_username}/runs/script_{unique_id}"} for host in hosts],
    }
    if os.path.exists(jobs_file):
        with open(jobs_file, "r") as f:
            all_jobs = json.load(f)
    else:
        all_jobs = []

    all_jobs.append(job_metadata)

    with open(jobs_file, "w") as f:
        json.dump(all_jobs, f, indent=2)
    print(f"Saved job metadata to {jobs_file}")


def fetch_logs(output_path: str, ssh_key_path: str, jobs_file: str = "launched_jobs"):
    """Fetch previously launched jobs' logs."""
    if not os.path.exists(jobs_file):
        print(f"No job metadata found in {jobs_file}")
        return

    with open(jobs_file, "r") as f:
        all_jobs = json.load(f)

    os.makedirs(output_path, exist_ok=True)

    for job in all_jobs:
        unique_id = job["id"]
        print(f"Fetching logs for job {unique_id}")
        for node_id, host_data in tqdm(enumerate(job["hosts"]), total=len(job["hosts"])):
            ssh_host = host_data["host"]
            ssh_username = host_data["username"]
            remote_stdout = f"{host_data['base_path']}.stdout"
            remote_stderr = f"{host_data['base_path']}.stderr"
            local_stdout = os.path.join(output_path, f"node_{node_id}_{unique_id}.stdout")
            local_stderr = os.path.join(output_path, f"node_{node_id}_{unique_id}.stderr")

            # Fetch stdout
            if not scp_logs(ssh_key_path, ssh_username, ssh_host, remote_stdout, local_stdout):
                print(f"Failed to fetch stdout for {ssh_host}")

            # Fetch stderr
            if not scp_logs(ssh_key_path, ssh_username, ssh_host, remote_stderr, local_stderr):
                print(f"Failed to fetch stderr for {ssh_host}")


def parallel_run(
    script: str,
    ssh_key_path: str,
    ssh_hosts: str,
    ssh_username: str = "ubuntu",
    output_path: str = None,
    wait: bool = False,
    jobs_file: str = "launched_jobs"
):
    """
    Run a script on multiple SSH machines in parallel.

    Args:
        script (str): Path to the script file on the local machine.
        ssh_key_path (str): Path to the SSH private key.
        ssh_hosts (str): File containing a list of SSH hosts (one per line).
        ssh_username (str): SSH username for all machines. Defaults to "ubuntu".
        output_path (str): Local directory to save outputs if `--wait` is used.
        wait (bool): Whether to wait for execution and fetch logs. Defaults to False.
    """
    with open(ssh_hosts, "r") as f:
        hosts = [line.strip() for line in f if line.strip()]

    if not hosts:
        print("Error: No SSH hosts provided!")
        return

    unique_id = str(uuid.uuid4())
    node_count = len(hosts)

    print(f"Launching job {unique_id} on {len(hosts)} machines.")
    tasks = []

    with ThreadPoolExecutor() as executor:
        for node_id, ssh_host in enumerate(hosts):
            remote_script_path = f"/home/{ssh_username}/scripts/script_{unique_id}.sh"
            remote_stdout_path = f"/home/{ssh_username}/runs/script_{unique_id}.stdout"
            remote_stderr_path = f"/home/{ssh_username}/runs/script_{unique_id}.stderr"

            # Ensure remote directories exist
            if not ensure_remote_directories(ssh_host, ssh_key_path, ssh_username):
                print(f"Failed to ensure directories on {ssh_host}. Skipping...")
                continue

            # Copy script to remote machine
            if not copy_script_to_remote(ssh_key_path, ssh_username, ssh_host, script, remote_script_path):
                print(f"Failed to copy script to {ssh_host}. Skipping...")
                continue

            # Submit command execution
            tasks.append(
                executor.submit(
                    run_command,
                    ssh_host,
                    ssh_key_path,
                    ssh_username,
                    remote_script_path,
                    remote_stdout_path,
                    remote_stderr_path,
                    node_id,
                    node_count,
                )
            )

        if wait:
            if output_path:
                os.makedirs(output_path, exist_ok=True)

            progress_bar = tqdm(total=len(tasks), desc="Job Progress")
            for future in as_completed(tasks):
                future.result()  # Ensure all tasks complete
                progress_bar.update(1)
            progress_bar.close()

            if output_path:
                fetch_logs(output_path, ssh_key_path)
        else:
            save_job_metadata(unique_id, hosts, ssh_username, jobs_file)
            print(f"Job launched! Logs are stored remotely. To fetch logs later, use `fetch_logs`.")
            exit(0)

def main():
    """Main entry point."""
    fire.Fire({"launch": parallel_run, "fetch-logs": fetch_logs})


if __name__ == "__main__":
    main()