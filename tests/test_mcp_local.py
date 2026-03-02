import json
import os
import sys
import subprocess
import unittest
from pathlib import Path

# Ensure we can import hegelion
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMCPLocal(unittest.TestCase):
    def setUp(self):
        self.server_script = "hegelion.mcp.server"
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(Path(__file__).parent.parent)

    def test_server_handshake(self):
        """Test that the MCP server starts and responds to initialization."""

        # Start the server process
        process = subprocess.Popen(
            [sys.executable, "-m", self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            text=True,
            bufsize=0,  # Unbuffered
        )

        try:
            # 1. Initialize
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
            }

            # Write request
            process.stdin.write(json.dumps(init_req) + "\n")
            process.stdin.flush()

            # Read response
            response_line = process.stdout.readline()
            self.assertTrue(response_line, "Server returned no data")

            response = json.loads(response_line)
            self.assertEqual(response["id"], 1)
            self.assertIn("result", response)
            self.assertIn("serverInfo", response["result"])
            self.assertEqual(response["result"]["serverInfo"]["name"], "hegelion-server")

            # 2. List Tools
            list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            process.stdin.write(json.dumps(list_req) + "\n")
            process.stdin.flush()

            response_line = process.stdout.readline()
            response = json.loads(response_line)
            self.assertEqual(response.get("id"), 2)
            assert "result" in response, f"tools/list failed: {response}"
            tools = response["result"]["tools"]
            tool_names = [t["name"] for t in tools]
            self.assertIn("dialectic", tool_names)
            self.assertIn("autocode", tool_names)

        finally:
            process.terminate()
            process.wait(timeout=2)
            if process.stdout:
                process.stdout.close()
            if process.stdin:
                process.stdin.close()
            if process.stderr:
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
