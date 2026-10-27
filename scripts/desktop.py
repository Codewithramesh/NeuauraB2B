"""One-click local service controls. Starts only loopback services; installs nothing automatically."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings


def get_json(url, timeout=3):
    try:
        with urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except (OSError, URLError, ValueError):
        return None


def wait_for(url, process, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if get_json(url, 1) is not None:
            return
        if process.poll() is not None:
            raise RuntimeError("Service exited. See local-data/logs for details.")
        time.sleep(.25)
    raise RuntimeError("Service did not become ready. See local-data/logs for details.")


def launch(command, log_file, env=None):
    with log_file.open("ab") as log:
        return subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)


def process_start(pid):
    result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True)
    return result.stdout.strip()


def start(settings, open_browser):
    ollama_base = settings.llm_base_url.rstrip("/")
    if settings.extraction_provider == "ollama" and get_json(ollama_base + "/api/tags") is None:
        parsed = urlparse(ollama_base)
        if parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.scheme != "http" or parsed.path:
            raise RuntimeError("This launcher starts local Ollama only. Start your configured inference server separately.")
        binary = shutil.which("ollama") or next((p for p in ["/opt/homebrew/bin/ollama", "/usr/local/bin/ollama"] if Path(p).is_file()), None)
        if not binary:
            raise RuntimeError("Ollama is missing. Install it with brew install ollama; see docs/LOCAL_SETUP.md.")
        env = {**os.environ, "OLLAMA_MODELS": str(ROOT / "models/ollama"),
               "OLLAMA_HOST": f"127.0.0.1:{parsed.port or 11434}", "OLLAMA_NUM_PARALLEL": "1",
               "OLLAMA_MAX_LOADED_MODELS": "1", "OLLAMA_KEEP_ALIVE": "1m", "OLLAMA_FLASH_ATTENTION": "1",
               "OLLAMA_KV_CACHE_TYPE": "q8_0", "OLLAMA_NO_CLOUD": "1"}
        process = launch([binary, "serve"], ROOT / "local-data/logs/ollama.log", env)
        state = {"pid": process.pid, "started": process_start(process.pid), "binary": str(Path(binary).resolve())}
        (ROOT / "local-data/ollama-process.json").write_text(json.dumps(state))
        wait_for(ollama_base + "/api/tags", process)
    if get_json("http://127.0.0.1:8000/api/v1/health") is None:
        process = launch([str(ROOT / "scripts/start.sh")], ROOT / "local-data/logs/server.log")
        wait_for("http://127.0.0.1:8000/api/v1/health", process)
    print("NEUAURA web app is ready: http://localhost:8000")
    print("Project: " + str(ROOT))
    print("Speech model: " + str(settings.whisper_model_path))
    if settings.extraction_provider == "ollama":
        tags = get_json(ollama_base + "/api/tags") or {}
        installed = any(m.get("name") == settings.llm_model for m in tags.get("models", []))
        print("AI model: " + settings.llm_model + (" — installed" if installed else " — needs download: ollama pull " + settings.llm_model))
    health = get_json("http://127.0.0.1:8000/api/v1/health") or {}
    if health.get("bootstrap_required"):
        print("First use: double-click 'Copy setup token.command', paste into the browser, then choose your email/password.")
    if open_browser:
        subprocess.run(["/usr/bin/open", "http://localhost:8000"], check=True)


def stop():
    subprocess.run([str(ROOT / "scripts/stop.sh")], cwd=ROOT, check=True)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and get_json("http://127.0.0.1:8000/api/v1/health", 1) is not None:
        time.sleep(.2)
    state_file = ROOT / "local-data/ollama-process.json"
    if state_file.exists():
        state = json.loads(state_file.read_text())
        pid = state.get("pid")
        if isinstance(pid, int) and state.get("started") and process_start(pid) == state["started"]:
            command = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
            if "ollama serve" in command:
                os.kill(pid, 15)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and process_start(pid) == state["started"]:
                    status = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True).stdout
                    if "Z" in status: break
                    time.sleep(.2)
                print("NEUAURA's local Ollama service stopped.")
        state_file.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status", "copy-setup-token"])
    parser.add_argument("--no-open", action="store_true", help="Start services without opening a browser")
    args = parser.parse_args()
    os.umask(0o077)
    (ROOT / "local-data/logs").mkdir(parents=True, exist_ok=True, mode=0o700)
    settings = Settings()
    with (ROOT / "local-data/desktop-launch.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == "start":
            start(settings, not args.no_open)
        elif args.action == "stop":
            stop()
        elif args.action == "status":
            print("NEUAURA: " + ("running" if get_json("http://127.0.0.1:8000/api/v1/health") else "stopped"))
            tags = get_json(settings.llm_base_url.rstrip("/") + "/api/tags")
            print("Ollama: " + ("running" if tags else "stopped"))
            print("Configured AI model: " + settings.llm_model)
            print("Project: " + str(ROOT))
        else:
            token_file = settings.data_dir / "setup-token"
            if not token_file.exists():
                print("Workspace already configured. Open http://localhost:8000 and sign in.")
                return
            subprocess.run(["/usr/bin/pbcopy"], input=token_file.read_text().strip(), text=True, check=True)
            print("Setup token copied. Paste it into the Setup token field in NEUAURA. It is not your password.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("NEUAURA: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
