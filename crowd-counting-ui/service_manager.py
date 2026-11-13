import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from api_client import is_service_up
from config import MODELS, PROJECT_ROOT_OVERRIDE

PROJECT_ROOT = (
    Path(PROJECT_ROOT_OVERRIDE) if PROJECT_ROOT_OVERRIDE else Path(__file__).resolve().parent.parent
)
LOG_DIR = Path(__file__).resolve().parent / "logs"

STARTUP_TIMEOUT_SECONDS = 45
POLL_INTERVAL_SECONDS = 1.0
HEALTH_CHECK_TIMEOUT_SECONDS = 1.5

StatusCallback = Callable[[str, str], None]


class ServiceManager:
    def __init__(self):
        self._owned: dict[str, tuple[subprocess.Popen, object]] = {}
        self._lock = threading.Lock()

    def start_all(self, on_status: StatusCallback) -> None:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
            futures = [
                executor.submit(self.ensure_running, model_key, on_status)
                for model_key in MODELS
            ]
            for future in futures:
                future.result()

    def ensure_running(self, model_key: str, on_status: StatusCallback) -> None:
        cfg = MODELS[model_key]
        base_url = cfg["base_url"]
        port = cfg["port"]

        on_status(model_key, "checking")
        if is_service_up(base_url, HEALTH_CHECK_TIMEOUT_SECONDS):
            on_status(model_key, "ready")
            return

        service_dir = PROJECT_ROOT / cfg["service_dir"]
        venv_python = self._venv_python(service_dir)

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / f"{model_key}.log"

        if venv_python is None:
            self._log_line(
                log_path,
                f"Could not find a virtualenv Python at {service_dir}/.venv — "
                f"check that the service folder exists there, or set the "
                f"CROWD_COUNTING_PROJECT_ROOT / service-specific *_DIR env vars.",
            )
            on_status(model_key, "failed")
            return

        on_status(model_key, "starting")

        try:
            log_file = open(log_path, "ab")
        except OSError:
            on_status(model_key, "failed")
            return

        try:
            process = subprocess.Popen(
                [
                    str(venv_python),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=str(service_dir),
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        except OSError:
            log_file.close()
            on_status(model_key, "failed")
            return

        with self._lock:
            self._owned[model_key] = (process, log_file)

        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if process.poll() is not None:
                on_status(model_key, "failed")
                return
            if is_service_up(base_url, HEALTH_CHECK_TIMEOUT_SECONDS):
                on_status(model_key, "ready")
                return
            time.sleep(POLL_INTERVAL_SECONDS)

        on_status(model_key, "failed")

    def stop_owned(self) -> None:
        with self._lock:
            owned = list(self._owned.items())
            self._owned.clear()

        for _model_key, (process, log_file) in owned:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            except Exception:
                pass
            finally:
                try:
                    log_file.close()
                except Exception:
                    pass

    @staticmethod
    def _log_line(log_path: Path, message: str) -> None:
        try:
            with open(log_path, "a") as log_file:
                log_file.write(message + "\n")
        except OSError:
            pass

    @staticmethod
    def _venv_python(service_dir: Path) -> Path | None:
        if sys.platform == "win32":
            candidate = service_dir / ".venv" / "Scripts" / "python.exe"
        else:
            candidate = service_dir / ".venv" / "bin" / "python"
        return candidate if candidate.exists() else None
