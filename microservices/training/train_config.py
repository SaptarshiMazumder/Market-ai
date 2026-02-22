"""Generates an ai-toolkit YAML config from API input parameters."""

import yaml
import os

VOLUME_MODEL_PATH = os.environ.get("VOLUME_MODEL_PATH", "/runpod-volume/FLUX.1-dev")
DEFAULT_CONFIG = {
    "trigger_word": "TOK",
    "steps": 2000,
    "lr": 1e-4,
    "resolution": [512, 768, 1024],
    "lora_rank": 16,
    "batch_size": 2,
    "sample_every": 500,
    "save_every": 500,
}


def build_config(params: dict, dataset_dir: str, output_dir: str) -> dict:
    """Build the ai-toolkit config dict from job params."""
    p = {**DEFAULT_CONFIG, **{k: v for k, v in params.items() if v is not None}}
    lora_name = p.get("lora_name", "lora_output")
    trigger_word = p["trigger_word"]

    resolution = p["resolution"]
    if isinstance(resolution, int):
        resolution = [resolution]

    config = {
        "job": "extension",
        "config": {
            "name": lora_name,
            "process": [
                {
                    "type": "sd_trainer",
                    "training_folder": output_dir,
                    "device": "cuda:0",
                    "trigger_word": trigger_word,
                    "network": {
                        "type": "lora",
                        "linear": p["lora_rank"],
                        "linear_alpha": p["lora_rank"],
                    },
                    "save": {
                        "dtype": "float16",
                        "save_every": p["save_every"],
                        "max_step_saves_to_keep": 2,
                    },
                    "datasets": [
                        {
                            "folder_path": dataset_dir,
                            "caption_ext": "txt",
                            "caption_dropout_rate": 0.05,
                            "shuffle_tokens": False,
                            "cache_latents_to_disk": True,
                            "resolution": resolution,
                        }
                    ],
                    "train": {
                        "batch_size": p["batch_size"],
                        "steps": p["steps"],
                        "gradient_accumulation_steps": 1,
                        "train_unet": True,
                        "train_text_encoder": False,
                        "gradient_checkpointing": True,
                        "noise_scheduler": "flowmatch",
                        "optimizer": "adamw8bit",
                        "lr": p["lr"],
                        "ema_config": {"use_ema": True, "ema_decay": 0.99},
                        "dtype": "bf16",
                    },
                    "model": {
                        "name_or_path": VOLUME_MODEL_PATH,
                        "is_flux": True,
                        "quantize": True,
                    },
                    "sample": {
                        "sampler": "flowmatch",
                        "sample_every": p["sample_every"],
                        "width": 1024,
                        "height": 1024,
                        "prompts": [
                            f"a photo of {trigger_word}",
                            f"a professional photo of {trigger_word} in a studio",
                        ],
                        "neg": "",
                        "seed": 42,
                        "walk_seed": True,
                        "guidance_scale": 4,
                        "sample_steps": 20,
                    },
                }
            ],
        },
    }
    return config


def write_config(params: dict, dataset_dir: str, output_dir: str, config_path: str) -> str:
    """Write the ai-toolkit YAML config to disk and return the path."""
    config = build_config(params, dataset_dir, output_dir)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    return config_path
