"""
Case 3: 多 GPU 資源匹配
需要多個 GPU 時，Slurm 自動找有足夠資源的機器
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

    gpu_count = torch.cuda.device_count()
    print(f"分配到 {gpu_count} 個 GPU：")
    for i in range(gpu_count):
        props = torch.cuda.get_device_properties(i)
        print(f"  GPU {i}: {props.name} ({props.total_memory / 1024**3:.1f} GB)")
    print()
    print(f"開始多 GPU 並行運算...")
    print("-" * 40)

    size = 4096
    tensors = [torch.randn(size, size, device=f"cuda:{i}") for i in range(gpu_count)]

    for epoch in range(10):
        results = []
        for i in range(gpu_count):
            c = torch.matmul(tensors[i], tensors[i])
            results.append(c)

        for i in range(gpu_count):
            torch.cuda.synchronize(i)

        mem_info = " | ".join(
            [f"GPU{i}: {torch.cuda.memory_allocated(i)/1024**2:.0f}MB" for i in range(gpu_count)]
        )
        print(f"Epoch {epoch+1:2d}/10 完成 | {mem_info}")
        time.sleep(20)

    print("-" * 40)
    print(f"多 GPU Training 完成！共使用 {gpu_count} 個 GPU")

if __name__ == "__main__":
    main()
