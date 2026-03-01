import runpod
import requests
import os
import json
import time
import uuid
import shutil
import boto3
from botocore.config import Config

WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Qwen-Image-Edit-2506-Lightning-Control-Net-Pose.json",
)

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT_DIR = "/comfyui/input"

R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_INPUT_BUCKET = os.environ.get("R2_INPUT_BUCKET", R2_BUCKET)
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", R2_BUCKET)

# Workflow node IDs
NODE_INPUT_IMAGE = "162"   # LoadImage — the subject / image to be edited
NODE_POSE_IMAGE = "164"    # LoadImage — pose reference image (fed to DWPreprocessor)
NODE_SAVE_IMAGE = "153"    # SaveImage — final output

DISPLAY_NODE_CLASSES = {
    "PreviewImage",
    "MaskPreview",
    "MaskPreview+",
    "ImageAndMaskPreview",
    "PreviewBridge",
    "Image Comparer (rgthree)",
}

SKIP_NODE_TYPES = {"Note", "NoteNode", "Reroute"}


# ---------------------------------------------------------------------------
# R2 helpers
# ---------------------------------------------------------------------------

def _r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"].strip()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _parse_r2_ref(url: str):
    """Return (bucket, key) from an r2:// URI, bare key, or https:// R2 URL."""
    if url.startswith("r2://"):
        parts = url[5:].split("/", 1)
        return parts[0], parts[1]
    if url.startswith("https://") and "r2.cloudflarestorage.com" in url:
        path = url.split("r2.cloudflarestorage.com/", 1)[1]
        bucket, key = path.split("/", 1)
        return bucket, key
    return R2_INPUT_BUCKET, url


def download_to_input(image_ref: str, dest_filename: str) -> str:
    """Download an image from R2 (or any https:// URL) into ComfyUI's input dir."""
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    dest = os.path.join(COMFYUI_INPUT_DIR, dest_filename)
    tmp_path = f"/tmp/dl_{dest_filename}"

    if image_ref.startswith("https://") and "r2.cloudflarestorage.com" not in image_ref:
        print(f"Downloading {image_ref} via HTTP")
        r = requests.get(image_ref, timeout=60)
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            f.write(r.content)
    else:
        bucket, key = _parse_r2_ref(image_ref)
        print(f"Downloading s3://{bucket}/{key} from R2")
        _r2_client().download_file(bucket, key, tmp_path)

    shutil.copy(tmp_path, dest)
    os.remove(tmp_path)
    print(f"Image ready at {dest}")
    return dest_filename


# ---------------------------------------------------------------------------
# Graph → API format converter
# ---------------------------------------------------------------------------

def _graph_to_api(graph: dict) -> dict:
    """
    Convert a ComfyUI graph/UI-format workflow (nodes + links arrays)
    to the API prompt format expected by POST /prompt.
    """
    # link_id -> (str(source_node_id), source_output_slot)
    link_map = {}
    for link in graph.get("links", []):
        link_id, src_node, src_slot, dst_node, dst_slot, _type = link
        link_map[link_id] = (str(src_node), src_slot)

    # Index reroute nodes for chain resolution
    reroute_nodes = {
        str(n["id"]): n
        for n in graph.get("nodes", [])
        if n.get("type") == "Reroute"
    }

    def resolve_link(link_id):
        src_node_id, src_slot = link_map[link_id]
        visited = set()
        while src_node_id in reroute_nodes and src_node_id not in visited:
            visited.add(src_node_id)
            inp_link = reroute_nodes[src_node_id].get("inputs", [{}])[0].get("link")
            if inp_link is None:
                break
            src_node_id, src_slot = link_map[inp_link]
        return src_node_id, src_slot

    api = {}
    for node in graph.get("nodes", []):
        ntype = node.get("type", "")
        nid = str(node["id"])

        if node.get("mode", 0) == 4:          # muted
            continue
        if ntype in SKIP_NODE_TYPES:
            continue
        if ntype in DISPLAY_NODE_CLASSES:
            continue

        inputs = {}
        widget_values = list(node.get("widgets_values", []))
        widget_idx = 0

        for inp in node.get("inputs", []):
            name = inp.get("name")
            if not name:
                continue
            link_id = inp.get("link")

            if link_id is not None:
                src_node_id, src_slot = resolve_link(link_id)
                inputs[name] = [src_node_id, src_slot]
            elif "widget" in inp:
                if widget_idx < len(widget_values):
                    inputs[name] = widget_values[widget_idx]
                    widget_idx += 1

        api[nid] = {"class_type": ntype, "inputs": inputs}

    return api


# ---------------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------------

def build_workflow(input_filename: str, pose_filename: str) -> dict:
    with open(WORKFLOW_PATH) as f:
        graph = json.load(f)

    workflow = _graph_to_api(graph)

    workflow[NODE_INPUT_IMAGE]["inputs"]["image"] = input_filename
    workflow[NODE_POSE_IMAGE]["inputs"]["image"] = pose_filename

    # Strip any display-only nodes that slipped through
    for nid in [k for k, v in workflow.items() if v.get("class_type") in DISPLAY_NODE_CLASSES]:
        print(f"Stripping display node {nid} ({workflow[nid]['class_type']})")
        del workflow[nid]

    return workflow


# ---------------------------------------------------------------------------
# ComfyUI communication
# ---------------------------------------------------------------------------

def queue_workflow(workflow: dict) -> str:
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_for_job(prompt_id: str, timeout: int = 600) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        history = r.json()
        if prompt_id in history:
            job = history[prompt_id]
            if job.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"ComfyUI job failed: {job['status'].get('messages')}")
            return job
        time.sleep(2)
    raise TimeoutError(f"Job {prompt_id} timed out after {timeout}s")


def upload_output_to_r2(history: dict) -> list:
    """Fetch the SaveImage output and upload to R2."""
    client = _r2_client()
    results = []

    for img in history["outputs"].get(NODE_SAVE_IMAGE, {}).get("images", []):
        r = requests.get(
            f"{COMFYUI_URL}/view",
            params={
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            },
            timeout=60,
        )
        r.raise_for_status()

        key = f"generated/{uuid.uuid4()}_{img['filename']}"
        client.put_object(
            Bucket=R2_OUTPUT_BUCKET,
            Key=key,
            Body=r.content,
            ContentType="image/png",
        )
        print(f"Uploaded to R2: {R2_OUTPUT_BUCKET}/{key}")
        results.append({
            "r2_path": f"r2://{R2_OUTPUT_BUCKET}/{key}",
            "key": key,
            "filename": img["filename"],
        })

    return results


# ---------------------------------------------------------------------------
# RunPod handler
# ---------------------------------------------------------------------------

def handler(job):
    job_input = job["input"]

    input_url = job_input.get("input_image")  # subject / image to be edited
    pose_url = job_input.get("pose_image")    # reference image to extract pose from

    if not input_url:
        return {"error": "input_image is required"}
    if not pose_url:
        return {"error": "pose_image is required"}

    start_time = time.time()

    input_filename = download_to_input(input_url, "input_image.png")
    pose_filename = download_to_input(pose_url, "pose_image.png")

    workflow = build_workflow(input_filename, pose_filename)

    prompt_id = queue_workflow(workflow)
    print(f"Queued prompt_id={prompt_id}")

    history = wait_for_job(prompt_id)
    images = upload_output_to_r2(history)

    return {
        "images": images,
        "duration_seconds": round(time.time() - start_time, 2),
    }


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def wait_for_comfyui(timeout: int = 300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(f"{COMFYUI_URL}/system_stats", timeout=2).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError("ComfyUI failed to start")


print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()
print("ComfyUI ready. Starting RunPod handler.")

runpod.serverless.start({"handler": handler})
