"""Runtime settings. Env-overridable, single place for tunables."""

import dataclasses
import os


@dataclasses.dataclass(frozen=True)
class Settings:
    screenshot_max_width: int = 1440
    screenshot_quality: int = 75
    ocr_min_conf: int = 30
    ocr_upscale: int = 2
    focus_settle_s: float = 0.3
    click_settle_s: float = 0.2
    event_timeout_s: float = 10.0
    launch_timeout_s: float = 30.0
    dispatch_retries: int = 2
    send_shortcut_retries: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        def _int(name: str, default: int) -> int:
            try:
                return int(os.environ.get(name, default))
            except ValueError:
                return default

        def _float(name: str, default: float) -> float:
            try:
                return float(os.environ.get(name, default))
            except ValueError:
                return default

        return cls(
            screenshot_max_width=_int("HYPR_MCP_MAX_WIDTH", 1440),
            screenshot_quality=_int("HYPR_MCP_JPEG_QUALITY", 75),
            ocr_min_conf=_int("HYPR_MCP_OCR_MIN_CONF", 30),
            ocr_upscale=_int("HYPR_MCP_OCR_UPSCALE", 2),
            focus_settle_s=_float("HYPR_MCP_FOCUS_SETTLE", 0.3),
            click_settle_s=_float("HYPR_MCP_CLICK_SETTLE", 0.2),
            event_timeout_s=_float("HYPR_MCP_EVENT_TIMEOUT", 10.0),
            launch_timeout_s=_float("HYPR_MCP_LAUNCH_TIMEOUT", 30.0),
        )


DEFAULTS = Settings()
