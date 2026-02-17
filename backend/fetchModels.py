import replicate
import os
from datetime import datetime, timezone

# 1. Set your API Token
os.environ["REPLICATE_API_TOKEN"] = "r8_UkYGYR2XOBk9AtgqXoutZjQHHvrHva53Lz0fI"
def fetch_trained_models():
    print(f"{'ID':<18} | {'Model':<28} | {'Source':<6} | {'Status':<10} | {'Queued':<8} | {'Running':<8} | {'Total':<8} | {'Created'}")
    print("-" * 120)
    
    # 1. List all trainings (paginated automatically)
    trainings = replicate.trainings.list()

    def _parse_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _duration_seconds(start, end):
        if not start or not end:
            return None
        return max(0.0, (end - start).total_seconds())

    def _fmt_duration(seconds):
        if seconds is None:
            return "-"
        if seconds < 1:
            return "<1s"
        seconds = int(seconds)
        if seconds >= 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h}h {m}m"
        if seconds >= 60:
            m = seconds // 60
            s = seconds % 60
            return f"{m}m {s}s"
        return f"{seconds}s"

    def _fmt_created(value):
        dt = _parse_dt(value)
        if not dt:
            return "-"
        return dt.isoformat()

    for t in trainings:
        # 2. Filter for only the Ostris Flux trainer
        # Use the specific trainer ID from your screenshot
        if "ostris/flux-dev-lora-trainer" in t.model:
            status = t.status # succeeded, failed, or processing
            created_at = _parse_dt(getattr(t, "created_at", None))
            started_at = _parse_dt(getattr(t, "started_at", None))
            completed_at = _parse_dt(getattr(t, "completed_at", None))
            now = datetime.now(timezone.utc)

            queued = _duration_seconds(created_at, started_at)
            running_end = completed_at or (now if started_at else None)
            total_end = completed_at or (now if created_at else None)
            running = _duration_seconds(started_at, running_end)
            total = _duration_seconds(created_at, total_end)

            print(
                f"{str(getattr(t, 'id', '-')):<18} | "
                f"{t.model:<28} | "
                f"{str(getattr(t, 'source', '-')):<6} | "
                f"{status:<10} | "
                f"{_fmt_duration(queued):<8} | "
                f"{_fmt_duration(running):<8} | "
                f"{_fmt_duration(total):<8} | "
                f"{_fmt_created(getattr(t, 'created_at', None))}"
            )

            # 3. Only grab 'succeeded' ones to get the final version ID
            if status == "succeeded":
                model_string = f"{t.destination}:{t.version}"
                print(f"  -> model_string: {model_string}")

if __name__ == "__main__":
    fetch_trained_models()
