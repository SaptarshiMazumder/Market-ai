import os
import uuid
from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.config import Config
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from orchestration.state import create_pipeline, get_pipeline, list_pipelines, get_queue_counts
from orchestration import orchestrator

app = Flask(__name__)
CORS(app)

# ── R2 helpers ────────────────────────────────────────────────────────────────
R2_ENDPOINT_URL      = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET            = os.environ.get("R2_OUTPUT_BUCKET", "")


def _r2():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _upload_product(file_bytes: bytes, original_filename: str) -> tuple[str, str]:
    """Upload to R2 products/ prefix. Returns (r2_path, preview_url)."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "png"
    key = f"products/{uuid.uuid4()}.{ext}"
    client = _r2()
    client.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=f"image/{ext}",
    )
    r2_path = f"r2://{R2_BUCKET}/{key}"
    preview_url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return r2_path, preview_url


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/pipeline/upload", methods=["POST"])
def upload_product():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "file is required"}), 400
    try:
        r2_path, preview_url = _upload_product(f.read(), secure_filename(f.filename))
        return jsonify({"r2_path": r2_path, "preview_url": preview_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pipeline/submit", methods=["POST"])
def submit():
    body = request.json or {}
    subject    = body.get("subject", "").strip()
    mode       = body.get("mode", "").strip()
    product_r2 = body.get("product_r2", "").strip()
    lora_name         = (body.get("lora_name") or "").strip() or None
    keyword           = (body.get("keyword") or "").strip() or None
    template_name     = (body.get("template_name") or "").strip() or None
    preview_image_url = (body.get("preview_image_url") or "").strip() or None
    run_masking    = bool(body.get("run_masking", True))
    run_inpainting = bool(body.get("run_inpainting", True))

    if not subject:
        return jsonify({"error": "subject is required"}), 400
    if mode not in ("template", "no_template"):
        return jsonify({"error": "mode must be 'template' or 'no_template'"}), 400
    if not product_r2:
        return jsonify({"error": "product_r2 is required"}), 400
    if mode == "template" and not lora_name:
        return jsonify({"error": "lora_name is required for template mode"}), 400

    pipeline_id = create_pipeline(
        subject=subject,
        mode=mode,
        product_r2=product_r2,
        lora_name=lora_name,
        keyword=keyword,
        template_name=template_name,
        preview_image_url=preview_image_url,
        run_masking=run_masking,
        run_inpainting=run_inpainting,
    )
    orchestrator.start(pipeline_id)
    print(f"[Pipeline] Started {pipeline_id} subject='{subject}' mode={mode}")
    return jsonify({"pipeline_id": pipeline_id, "status": "running"}), 202


@app.route("/api/pipeline/status/<pipeline_id>", methods=["GET"])
def status(pipeline_id):
    p = get_pipeline(pipeline_id)
    if not p:
        return jsonify({"error": "Pipeline not found"}), 404
    return jsonify(p)


@app.route("/api/pipeline/list", methods=["GET"])
def list_all():
    return jsonify({"pipelines": list_pipelines()})


@app.route("/api/pipeline/queues", methods=["GET"])
def queues():
    return jsonify(get_queue_counts())


@app.route("/api/pipeline/preview", methods=["GET"])
def preview():
    """Generate a presigned URL for any r2:// path."""
    r2_path = request.args.get("r2_path", "").strip()
    if not r2_path.startswith("r2://"):
        return jsonify({"error": "invalid r2_path"}), 400
    try:
        parts = r2_path[5:].split("/", 1)
        bucket, key = parts[0], parts[1]
        url = _r2().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600,
        )
        return jsonify({"preview_url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5009, debug=True)
