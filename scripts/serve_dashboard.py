from __future__ import annotations

import argparse
import json
import os
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from job_search_lib import JOB_SOURCES_CONFIG, read_yaml, refresh_dashboard_data, write_yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the job-search dashboard locally on 127.0.0.1."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=4173, help="Bind port.")
    return parser.parse_args()


class DashboardHandler(SimpleHTTPRequestHandler):
    repo_root: Path

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _run_command(self, command: list[str], timeout: int = 1800) -> dict:
        completed = subprocess.run(
            command,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        store = refresh_dashboard_data()
        return {
            "ok": True,
            "command": command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "storeSummary": {
                "generatedAt": store.get("generatedAt", ""),
                "counts": store.get("counts", {}),
            },
        }

    def _handle_offer_action(self, payload: dict) -> dict:
        job_id = str(payload.get("jobId", "")).strip()
        action = str(payload.get("action", "")).strip()
        browser = str(payload.get("browser", "auto") or "auto").strip()
        if not job_id:
            raise ValueError("Missing jobId.")

        if action == "refresh_apply":
            command = ["python", "scripts/refresh_application_page.py", "--job-id", job_id, "--browser", browser]
        elif action == "score_offer":
            command = ["python", "scripts/score_job.py", "--job-id", job_id]
        elif action == "set_status":
            status = str(payload.get("status", "")).strip()
            note = str(payload.get("note", "")).strip()
            if not status:
                raise ValueError("Missing status.")
            command = ["python", "scripts/update_status.py", "--job-id", job_id, "--status", status]
            if note:
                command.extend(["--note", note])
        else:
            raise ValueError(f"Unsupported offer action: {action}")

        return self._run_command(command)

    def _handle_pipeline_action(self, payload: dict) -> dict:
        action = str(payload.get("action", "")).strip()
        limit = str(payload.get("limit", 3) or 3)
        days = str(payload.get("days", 7) or 7)

        if action == "discover_jobs":
            command = ["python", "scripts/discover_jobs.py"]
        elif action == "discover_top":
            command = ["python", "scripts/discover_jobs.py", "--limit", limit]
        elif action == "mark_followups_due":
            command = ["python", "scripts/mark_followups_due.py", "--days", days]
        else:
            raise ValueError(f"Unsupported pipeline action: {action}")

        return self._run_command(command)

    def _handle_source_action(self, payload: dict) -> dict:
        action = str(payload.get("action", "")).strip()
        source_id = str(payload.get("sourceId", "")).strip()
        config = read_yaml(JOB_SOURCES_CONFIG, {"version": 1, "sources": []})

        if action == "set_enabled":
            enabled = bool(payload.get("enabled"))
            updated = False
            for source in config.get("sources", []):
                if source.get("id") == source_id:
                    source["enabled"] = enabled
                    updated = True
                    break
            if not updated:
                raise ValueError(f"Unknown source id: {source_id}")
            write_yaml(JOB_SOURCES_CONFIG, config)
            store = refresh_dashboard_data()
            return {
                "ok": True,
                "sourceId": source_id,
                "enabled": enabled,
                "storeSummary": {
                    "generatedAt": store.get("generatedAt", ""),
                    "counts": store.get("counts", {}),
                },
            }

        if action == "discover_source":
            if not source_id:
                raise ValueError("Missing sourceId.")
            return self._run_command(["python", "scripts/discover_jobs.py", "--source-id", source_id])

        if action == "discover_enabled":
            return self._run_command(["python", "scripts/discover_jobs.py"])

        raise ValueError(f"Unsupported source action: {action}")

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json_body()
            if self.path == "/api/offer-action":
                result = self._handle_offer_action(payload)
            elif self.path == "/api/pipeline-action":
                result = self._handle_pipeline_action(payload)
            elif self.path == "/api/source-action":
                result = self._handle_source_action(payload)
            else:
                self._send_json(404, {"ok": False, "error": "Unknown API endpoint."})
                return
            self._send_json(200, result)
        except subprocess.CalledProcessError as error:
            self._send_json(
                500,
                {
                    "ok": False,
                    "error": "Command failed.",
                    "command": error.cmd,
                    "stdout": (error.stdout or "").strip(),
                    "stderr": (error.stderr or "").strip(),
                },
            )
        except subprocess.TimeoutExpired as error:
            self._send_json(
                504,
                {
                    "ok": False,
                    "error": "Command timed out.",
                    "command": error.cmd,
                },
            )
        except ValueError as error:
            self._send_json(400, {"ok": False, "error": str(error)})
        except Exception as error:  # pragma: no cover - local debug guard
            self._send_json(500, {"ok": False, "error": str(error)})


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    refresh_dashboard_data()

    DashboardHandler.repo_root = repo_root
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard available at http://{args.host}:{args.port}/dashboard/")
    print("This server is intended for local-only use.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
