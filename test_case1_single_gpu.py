"""
Case 1: 單 GPU 自動分派
Slurm 自動選一台有空閒 GPU 的機器執行
"""
import torch
import time
import os

def main():
    node = os.environ.get("SLURMD_NODENAME", "unknown")
    job_id = os.environ.get("SLURM_JOB_ID", "unknown")

    print(f"Job ID: {job_id}")
    print(f"執行節點: {node}")
    print(f"分配 GPU: {os.environ.get('CUDA_VISIBLE_DEVICES', 'unknown')}")
    print()

    if not torch.cuda.is_available():
        print("ERROR: 沒有可用的 GPU")
        return

    device = torch.device("cuda")
    print(f"GPU 型號: {torch.cuda.get_device_name(0)}")
    print(f"GPU 記憶體: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print()
    print("開始矩陣運算 (模擬 training)...")
    print("-" * 40)

    size = 4096
    for epoch in range(10):
        a = torch.randn(size, size, device=device)
        b = torch.randn(size, size, device=device)
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        mem = torch.cuda.memory_allocated() / 1024**2
        print(f"Epoch {epoch+1:2d}/10 完成 | GPU 記憶體: {mem:.1f} MB")
        time.sleep(20)

    print("-" * 40)
    print("Training 完成！")

if __name__ == "__main__":
    main()
