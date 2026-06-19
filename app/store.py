"""In-memory upload store. id -> saved file path. (No job store: this service returns the
stitched image in the same request, so there's nothing to poll.)"""
uploads: dict[str, str] = {}


def reset_state() -> None:
    uploads.clear()
