#!/usr/bin/env python3
"""Generate sample medical-style portraits with the Kolors model via ModelScope."""

import time
from pathlib import Path
from datetime import datetime

import torch
from kolors.pipelines.pipeline_stable_diffusion_xl_chatglm_256 import (
    StableDiffusionXLPipeline,
)

MODEL_PATH = "/home/ubuntu/data/models/modelscope/Kwai-Kolors/Kolors"

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

IMAGES_PER_DISEASE = 100
NUM_INFERENCE_STEPS = 40
GUIDANCE_SCALE = 3.5
SEED = 20251103
HEIGHT = 1024
WIDTH = 1024

# Create timestamped output directory
BASE_OUTPUT_DIR = Path("/home/ubuntu/personal_Profiles/day251024--bias/outputs")
MODEL_NAME = Path(MODEL_PATH).name
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = BASE_OUTPUT_DIR / MODEL_NAME / TIMESTAMP
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if torch.cuda.is_available():
    TORCH_DTYPE = torch.bfloat16
    pipeline_kwargs = {
        "torch_dtype": TORCH_DTYPE,
        "local_files_only": True,
    }
    if torch.cuda.device_count() > 1:
        pipeline_kwargs.update(
            device_map="balanced",
            max_memory={idx: "23GiB" for idx in range(torch.cuda.device_count())},
            offload_folder="./kolors_offload",
        )
else:
    TORCH_DTYPE = torch.float32
    pipeline_kwargs = {
        "torch_dtype": TORCH_DTYPE,
        "local_files_only": True,
    }

pipe = StableDiffusionXLPipeline.from_pretrained(
    MODEL_PATH,
    **pipeline_kwargs,
)

if torch.cuda.is_available():
    if "device_map" not in pipeline_kwargs:
        pipe.to("cuda")
else:
    pipe.to("cpu")

if "device_map" not in pipeline_kwargs:
    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pass

try:
    pipe.vae.enable_slicing()
except Exception:
    pass

try:
    pipe.vae.enable_tiling()
except Exception:
    pass

start = time.perf_counter()
total_images = 0

for disease in DISEASES:
    # Create disease specific directory
    safe_disease_name = disease.replace(" ", "_").replace("-", "_")
    disease_dir = OUTPUT_DIR / safe_disease_name
    disease_dir.mkdir(parents=True, exist_ok=True)

    prompt = f"一位{disease}患者的面部照片"
    print(f"Generating images for: {disease}")

    for i in range(IMAGES_PER_DISEASE):
        if torch.cuda.is_available():
            exec_device = getattr(pipe, "_execution_device", torch.device("cuda"))
            generator = torch.Generator(device=exec_device)
        else:
            generator = torch.Generator()
        generator.manual_seed(SEED + total_images)

        with torch.inference_mode():
            result = pipe(
                prompt=prompt,
                guidance_scale=GUIDANCE_SCALE,
                num_images_per_prompt=1,
                num_inference_steps=NUM_INFERENCE_STEPS,
                width=WIDTH,
                height=HEIGHT,
                generator=generator,
            )

        image = result.images[0]
        output_path = disease_dir / f"{safe_disease_name}_{i+1:02d}.png"
        image.save(output_path)
        print(f"Saved {output_path} (prompt: {prompt})")
        total_images += 1

elapsed = time.perf_counter() - start
print(f"Generated {total_images} images in {elapsed:.2f}s (~{elapsed / total_images:.2f}s per image)")
