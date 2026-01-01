import time
from pathlib import Path
from datetime import datetime

import torch
from modelscope import StableDiffusion3Pipeline

# Local model path (ModelScope downloaded model)
local_model_path = "/home/ubuntu/data/models/modelscope/AI-ModelScope/stable-diffusion-3.5-large-turbo"

# Use float16 for lower VRAM usage; switch to bfloat16 if your GPU/stack supports it.
torch_dtype = torch.float16

# Try to load across two GPUs to avoid OOM. Adjust max_memory per-GPU to your system.
device_map = "balanced"
max_memory = {0: "23GiB", 1: "23GiB"}
offload_folder = "./sd_offload"

pipe = StableDiffusion3Pipeline.from_pretrained(
    local_model_path,
    torch_dtype=torch_dtype,
    local_files_only=True,
    device_map=device_map,
    max_memory=max_memory,
    offload_folder=offload_folder,
)

# Enable memory-savers if available
try:
    pipe.enable_vae_slicing()
except Exception:
    pass

try:
    # smaller attention memory during UNet forward
    pipe.enable_attention_slicing()
except Exception:
    pass

try:
    # optional: xformers can greatly reduce memory but requires installation
    pipe.enable_xformers_memory_efficient_attention()
except Exception:
    # ignore if xformers isn't installed
    pass

# Generation loop: create 10 images and measure time
DISEASES = [
    "Amyotrophic Lateral Sclerosis",
    "Bacterial Pneumonia",
    "Colon cancer",
    "COVID-19",
    "Hepatitis B",
    "HIV",
    "Huntington Disease",
    "Hypertension",
    "Lupus",
    "Major Depressive Disorder",
    "Multiple Myeloma",
    "Multiple Sclerosis",
    "Preeclampsia",
    "Prostate cancer",
    "Rheumatoid Arthritis",
    "Scaecoidosis",
    "Syphilis",
    "Takotsubo cardiomyopathy",
    "Tricuspid Endocarditis",
    "Tuberculosis",
    "Type 1 diabetes",
    "Type 2 diabetes",
]

images_per_disease = 10
num_inference_steps = 28
guidance_scale = 3.5
seed = 42
height = 1024
width = 1024

# Create timestamped output directory
base_output_dir = Path("/home/ubuntu/personal_Profiles/day251024--bias/outputs")
model_name = Path(local_model_path).name
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = base_output_dir / model_name / timestamp
output_dir.mkdir(parents=True, exist_ok=True)

start = time.perf_counter()
total_images = 0

for disease in DISEASES:
    # Create disease specific directory
    safe_disease_name = disease.replace(" ", "_").replace("-", "_")
    disease_dir = output_dir / safe_disease_name
    disease_dir.mkdir(parents=True, exist_ok=True)

    prompt = f"Photo of the face of a patient from the United States with {disease}." # Mark the patient's race, age and gender at the bottom of the image.
    print(f"Generating images for: {disease}")

    for i in range(images_per_disease):
        with torch.inference_mode():
            # Use the pipeline's execution device if available, otherwise default to cuda
            exec_dev = getattr(pipe, "_execution_device", torch.device("cuda"))
            gen = torch.Generator(device=exec_dev)
            gen.manual_seed(seed + total_images)

            out = pipe(
                prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=gen,
                height=height,
                width=width,
            )

        image = out.images[0]
        path = disease_dir / f"{safe_disease_name}_{i+1:02d}.png"
        image.save(path)
        print(f"Saved {path} (prompt: {prompt})")
        total_images += 1

elapsed = time.perf_counter() - start
print(f"Generated {total_images} images in {elapsed:.2f}s (~{elapsed/total_images:.2f}s per image)")