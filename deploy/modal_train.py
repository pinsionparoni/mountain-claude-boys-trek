"""
Fine-tune Gemma 4 31B on Modal: runs training/train_lora.py on one H200.

Once: a Modal secret with a Hugging Face token (read access to google/gemma-4-31B-it,
write access for the upload):

    .venv/bin/modal secret create huggingface HF_TOKEN=<token>

Then, from the project root, one step at a time:

    .venv/bin/modal run deploy/modal_train.py --step check     # CPU: lengths + what is trained on
    .venv/bin/modal run deploy/modal_train.py --step smoke     # H200, 5 steps (~$1-2)
    .venv/bin/modal run --detach deploy/modal_train.py --step train    # H200, full run + merge
    .venv/bin/modal run deploy/modal_train.py --step upload --repo <hf-user>/gemma-coach-fi

The train step starts the run in the background (with --detach the app stays up after this
command returns), so the laptop can sleep; follow it in the Modal dashboard or with
`.venv/bin/modal app logs gemma-coach-train`. Everything (the base model download,
checkpoints, the adapter and the merged model) is kept on the Modal Volume
"gemma-coach-train", so later steps don't download or train again. Delete the volume
when the model is on Hugging Face: `.venv/bin/modal volume delete gemma-coach-train`.
"""

import subprocess
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
VOL = "/vol"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("unsloth", "hf_transfer")
    .env({"HF_HOME": f"{VOL}/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .add_local_file(str(ROOT / "training" / "train_lora.py"), "/root/training/train_lora.py")
    .add_local_file(str(ROOT / "training" / "train.jsonl"), "/root/training/train.jsonl")
    .add_local_file(str(ROOT / "training" / "val.jsonl"), "/root/training/val.jsonl")
)
volume = modal.Volume.from_name("gemma-coach-train", create_if_missing=True)
app = modal.App("gemma-coach-train", image=image)

COMMON = dict(
    volumes={VOL: volume},
    secrets=[modal.Secret.from_name("huggingface")],
    # The training data are synthetic customers, but keep them in Europe like the app does
    # (TECH_STACK.md). If no H200 is free in the EU for a long time, remove this line.
    region="eu",
)


def _train_lora(*args):
    subprocess.run(["python", "/root/training/train_lora.py", "--out", f"{VOL}/out", *args], check=True)
    volume.commit()


@app.function(cpu=4, memory=16 * 1024, timeout=30 * 60, **COMMON)
def check():
    _train_lora("--check")


@app.function(gpu="H200", timeout=8 * 60 * 60, **COMMON)
def train(*args: str):
    _train_lora(*args)


@app.function(cpu=4, memory=16 * 1024, timeout=2 * 60 * 60, **COMMON)
def upload(repo: str):
    from huggingface_hub import create_repo, upload_large_folder

    repo_id = create_repo(repo, private=True, exist_ok=True).repo_id
    upload_large_folder(repo_id=repo_id, folder_path=f"{VOL}/out/merged", repo_type="model")
    print(f"https://huggingface.co/{repo_id} (private)")


@app.local_entrypoint()
def main(step: str = "check", repo: str = "", epochs: float = 2.0):
    if step == "check":
        check.remote()
    elif step == "smoke":
        train.remote("--max-steps", "5")
    elif step == "train":
        # spawn, not remote: the run doesn't depend on this laptop staying connected
        # (a dropped connection cancelled a .remote() run on 15 Nov 2026).
        call = train.spawn("--epochs", str(epochs), "--merge-to", f"{VOL}/out/merged")
        print(f"Training started in the background: {call.object_id}. Follow it in the Modal dashboard or "
              f"with `.venv/bin/modal app logs gemma-coach-train`.")
    elif step == "upload":
        if not repo:
            raise SystemExit("give --repo <hf-user>/<name>")
        call = upload.spawn(repo)  # background, like train: a dropped client can't cancel it
        print(f"Upload started in the background: {call.object_id}")
    else:
        raise SystemExit("step is one of: check, smoke, train, upload")
