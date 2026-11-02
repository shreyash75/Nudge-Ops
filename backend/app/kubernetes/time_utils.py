from datetime import datetime, timezone


def parse_kube_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def age_seconds(timestamp: str | None) -> int | None:
    parsed = parse_kube_time(timestamp)
    if parsed is None:
        return None
    return int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())
