from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from hermes_agent.handlers import (
    _capture_screenshot,
    _handle_read_local_file,
    _handle_restart_agent,
    _handle_restart_pc,
    _handle_screenshot,
    _schedule_reboot,
    handle_command,
)


class TestCaptureScreenshot:
    def test_browser_backend_success(self):
        url = "http://dashboard.local"
        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_pw = MagicMock()
        mock_pw.__enter__.return_value = mock_pw
        mock_pw.chromium.launch.return_value = mock_browser
        mock_sync_api = MagicMock()
        mock_sync_api.sync_playwright.return_value = mock_pw

        with patch.dict(os.environ, {"JARVIS_SCREENSHOT_BROWSER_URL": url}):
            with patch.dict(
                "sys.modules",
                {
                    "playwright": MagicMock(),
                    "playwright.sync_api": mock_sync_api,
                },
            ):
                path = _capture_screenshot()
                try:
                    assert Path(path).exists()
                    mock_page.goto.assert_called_once_with(
                        url, wait_until="networkidle"
                    )
                    mock_page.screenshot.assert_called_once_with(
                        path=path, full_page=True
                    )
                    mock_browser.close.assert_called_once()
                finally:
                    Path(path).unlink(missing_ok=True)

    def test_browser_backend_playwright_missing(self):
        with patch.dict(
            os.environ, {"JARVIS_SCREENSHOT_BROWSER_URL": "http://test.com"}
        ):
            with pytest.raises(
                RuntimeError,
                match="JARVIS_SCREENSHOT_BROWSER_URL is set but playwright "
                "is not available",
            ):
                _capture_screenshot()

    def test_windows_powershell_backend(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("hermes_agent.handlers.platform.system", return_value="Windows"):
                with patch(
                    "hermes_agent.handlers.subprocess.run"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )
                    path = _capture_screenshot()
                    try:
                        assert Path(path).exists()
                        mock_run.assert_called_once()
                        args, kwargs = mock_run.call_args
                        cmd = args[0]
                        assert cmd[0] == "powershell"
                        assert cmd[2] == "-Command"
                        assert "CopyFromScreen" in cmd[3]
                        assert tmp_path_in_script(cmd[3], path)
                    finally:
                        Path(path).unlink(missing_ok=True)

    def test_windows_powershell_failure(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("hermes_agent.handlers.platform.system", return_value="Windows"):
                with patch(
                    "hermes_agent.handlers.subprocess.run"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=1, stderr="Access denied"
                    )
                    with pytest.raises(
                        RuntimeError, match="PowerShell screenshot failed"
                    ):
                        _capture_screenshot()

    def test_no_backend_available(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("hermes_agent.handlers.platform.system", return_value="Linux"):
                with pytest.raises(
                    RuntimeError, match="No screenshot backend available"
                ):
                    _capture_screenshot()


class TestHandleScreenshot:
    def test_success_flow(self):
        mock_client = MagicMock()
        mock_client.upload_file.return_value = {
            "id": "file-123",
            "filename": "screenshot_2026_05_27.png",
            "size_bytes": 245760,
            "sha256": "abc123",
        }
        cmd = {"id": "cmd-456"}

        with patch(
            "hermes_agent.handlers._capture_screenshot",
            return_value="/tmp/test_scr.png",
        ):
            with patch("hermes_agent.handlers.Path.unlink") as mock_unlink:
                status, result, logs = _handle_screenshot(mock_client, cmd)

        assert status == "done"
        assert result["file_id"] == "file-123"
        assert result["filename"] == "screenshot_2026_05_27.png"
        assert result["size_bytes"] == 245760
        assert result["sha256"] == "abc123"
        mock_client.upload_file.assert_called_once_with("cmd-456", "/tmp/test_scr.png")
        mock_unlink.assert_called_once_with(missing_ok=True)

    def test_capture_failure(self):
        mock_client = MagicMock()
        cmd = {"id": "cmd-456"}

        with patch(
            "hermes_agent.handlers._capture_screenshot",
            side_effect=RuntimeError("no screen"),
        ):
            status, result, logs = _handle_screenshot(mock_client, cmd)

        assert status == "failed"
        assert "no screen" in result["error"]
        mock_client.upload_file.assert_not_called()

    def test_upload_failure(self):
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception("upload failed")
        cmd = {"id": "cmd-456"}

        with patch(
            "hermes_agent.handlers._capture_screenshot",
            return_value="/tmp/test_scr.png",
        ):
            with patch("hermes_agent.handlers.Path.unlink") as mock_unlink:
                status, result, logs = _handle_screenshot(mock_client, cmd)

        assert status == "failed"
        assert "upload failed" in result["error"]
        mock_unlink.assert_called_once_with(missing_ok=True)


class TestHandleReadLocalFile:
    def test_text_file_inline(self):
        cmd = {"id": "cmd-rlf-1", "type": "read_local_file", "payload": {"filepath": "/tmp/test_read.txt"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, this is test content!\nLine 2\n")
            fpath = f.name
        cmd["payload"]["filepath"] = fpath
        try:
            status, result, logs = _handle_read_local_file(None, cmd)
        finally:
            Path(fpath).unlink(missing_ok=True)

        assert status == "done"
        assert result["filename"] == Path(fpath).name
        assert result["content"] == "Hello, this is test content!\nLine 2\n"
        assert result["content_type"] == "text"
        assert result["size_bytes"] == 36

    def test_file_not_found(self):
        cmd = {"id": "cmd-rlf-2", "payload": {"filepath": "/tmp/nonexistent_file_xyz.txt"}}
        status, result, logs = _handle_read_local_file(None, cmd)
        assert status == "failed"
        assert "File not found" in result["error"]

    def test_missing_filepath(self):
        cmd = {"id": "cmd-rlf-3", "payload": {}}
        status, result, logs = _handle_read_local_file(None, cmd)
        assert status == "failed"
        assert "requires filepath" in result["error"]

    def test_binary_file_upload(self):
        cmd = {"id": "cmd-rlf-4", "payload": {"filepath": "/tmp/test_binary.bin"}}
        # Use content that is NOT valid UTF-8 to force binary path
        content = b"\xff\xfe\x80\x81" * 100
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(content)
            fpath = f.name
        cmd["payload"]["filepath"] = fpath
        mock_client = MagicMock()
        mock_client.upload_file.return_value = {
            "id": "file-uploaded-1",
            "filename": Path(fpath).name,
            "size_bytes": len(content),
            "sha256": "deadbeef",
        }
        try:
            status, result, logs = _handle_read_local_file(mock_client, cmd)
        finally:
            Path(fpath).unlink(missing_ok=True)

        assert status == "done"
        assert result["file_id"] == "file-uploaded-1"
        assert result["size_bytes"] == len(content)
        mock_client.upload_file.assert_called_once()

    def test_no_client_for_binary(self):
        content = b"\xff\xfe\x80\x81" * 100
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(content)
            fpath = f.name
        cmd = {"id": "cmd-rlf-5", "payload": {"filepath": fpath}}
        try:
            status, result, logs = _handle_read_local_file(None, cmd)
        finally:
            Path(fpath).unlink(missing_ok=True)

        assert status == "failed"
        assert "no client available" in result["error"]


class TestHandleRestartPc:
    def test_handle_restart_pc_returns_done_immediately(self):
        cmd = {"id": "cmd-reboot-1", "type": "restart_pc", "payload": {}}
        with patch("hermes_agent.handlers._schedule_reboot") as mock_schedule:
            status, result, logs = _handle_restart_pc(None, cmd)
        assert status == "done"
        assert result["rebooting"] is True
        assert "reiniciando" in result["message"].lower()
        assert logs is None
        mock_schedule.assert_called_once()

    def test_handle_restart_pc_integration_via_handle_command(self):
        cmd = {"id": "cmd-reboot-2", "type": "restart_pc", "payload": {}}
        with patch("hermes_agent.handlers._schedule_reboot") as mock_schedule:
            status, result, logs = handle_command(cmd, None)
        assert status == "done"
        assert result["rebooting"] is True
        mock_schedule.assert_called_once()

    def test_schedule_reboot_windows(self):
        with patch("hermes_agent.handlers.platform.system", return_value="Windows"):
            with patch("hermes_agent.handlers.subprocess.Popen") as mock_popen:
                _schedule_reboot()
                mock_popen.assert_called_once()
                args, kwargs = mock_popen.call_args
                cmd_list = args[0]
                assert cmd_list[0] == "powershell"
                assert "Restart-Computer -Force" in cmd_list[-1]


class TestHandleRestartAgent:
    def test_handle_restart_agent_returns_done_immediately(self):
        cmd = {"id": "cmd-restart-1", "type": "restart_agent", "payload": {}}
        with patch("hermes_agent.handlers._schedule_restart") as mock_schedule:
            status, result, logs = _handle_restart_agent(None, cmd)
        assert status == "done"
        assert result["restarting"] is True
        assert "restarting" in result["message"].lower()
        assert logs is None
        mock_schedule.assert_called_once()

    def test_handle_restart_agent_integration_via_handle_command(self):
        cmd = {"id": "cmd-restart-2", "type": "restart_agent", "payload": {}}
        with patch("hermes_agent.handlers._schedule_restart") as mock_schedule:
            status, result, logs = handle_command(cmd, None)
        assert status == "done"
        assert result["restarting"] is True
        mock_schedule.assert_called_once()


def tmp_path_in_script(script: str, path: str) -> bool:
    normalized = path.replace("\\", "\\\\").replace("'", "''")
    return normalized in script
