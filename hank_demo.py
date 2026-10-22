"""
Hank's personal demo script - hank/demo branch
"""
import torch
import time
import os

def main():
    node = os.environ.get("SLURMD_NODENAME", "unknown")
    job_id = os.environ.get("SLURM_JOB_ID", "unknown")

    print(f"=== Hank Demo Job ===")
    print(f"Job ID : {job_id}")
    print(f"Node   : {node}")
    print(f"Branch : hank/demo")
    print(f"GPUs   : {os.environ.get('CUDA_VISIBLE_DEVICES', 'unknown')}")
    print()

    if not torch.cuda.is_available():
        print("ERROR: No GPU available")
        return

    device = torch.device("cuda")
    props = torch.cuda.get_device_properties(0)
    print(f"GPU    : {props.name} ({props.total_memory / 1024**3:.1f} GB)")
    print()
    print("Running matrix ops...")
    print("-" * 40)

    size = 4096
    a = torch.randn(size, size, device=device)

    for epoch in range(5):
        c = torch.matmul(a, a)
        torch.cuda.synchronize()
        mem = torch.cuda.memory_allocated() / 1024**2
        print(f"Epoch {epoch+1}/5 | Mem: {mem:.0f} MB | Node: {node}")
        time.sleep(15)

    print("-" * 40)
    print("Done!")

if __name__ == "__main__":
    main()
