#!/usr/bin/env python3
"""
Standalone test script for LangServe API endpoints.

This script can be run directly to test LangServe endpoints:
    python scripts/test_langserve.py

It requires:
1. Backend server running on http://localhost:8000
2. Valid authentication token (or will use test credentials)
"""

import asyncio
import json
import sys
from typing import Any
import httpx

# Try to import rich for pretty output, fallback to basic print
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


class LangServeTester:
    """Test client for LangServe endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", token: str | None = None):
        self.base_url = base_url
        self.token = token
        self.client = httpx.AsyncClient(timeout=60.0)
        self.results = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token if available."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def test_health(self) -> bool:
        """Test health endpoint."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/langserve/health",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                self.results.append(("Health Check", "✅ PASS", data))
                return True
            else:
                self.results.append(("Health Check", "❌ FAIL", f"Status: {response.status_code}"))
                return False
        except Exception as e:
            self.results.append(("Health Check", "❌ ERROR", str(e)))
            return False

    async def test_info(self) -> bool:
        """Test info endpoint."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/langserve/info",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                self.results.append(("Info Endpoint", "✅ PASS", data))
                return True
            else:
                self.results.append(("Info Endpoint", "❌ FAIL", f"Status: {response.status_code}"))
                return False
        except Exception as e:
            self.results.append(("Info Endpoint", "❌ ERROR", str(e)))
            return False

    async def test_invoke(self, message: str = "Hello! This is a test message.") -> bool:
        """Test invoke endpoint."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/langserve/chat/invoke",
                json={"input": {"message": message}},
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                self.results.append(("Invoke Endpoint", "✅ PASS", data))
                return True
            elif response.status_code == 401:
                self.results.append(("Invoke Endpoint", "⚠️  AUTH REQUIRED", "Need authentication token"))
                return False
            else:
                self.results.append(("Invoke Endpoint", "❌ FAIL", f"Status: {response.status_code}: {response.text}"))
                return False
        except Exception as e:
            self.results.append(("Invoke Endpoint", "❌ ERROR", str(e)))
            return False

    async def test_stream(self, message: str = "Count from 1 to 3.") -> bool:
        """Test stream endpoint."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/langserve/chat/stream",
                json={"input": {"message": message}},
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                # Read stream
                content_parts = []
                async for chunk in response.aiter_bytes():
                    content_parts.append(chunk)
                
                full_content = b"".join(content_parts).decode("utf-8")
                
                # Check for SSE format
                if "data: " in full_content:
                    self.results.append(("Stream Endpoint", "✅ PASS", f"Received {len(content_parts)} chunks"))
                    return True
                else:
                    self.results.append(("Stream Endpoint", "⚠️  WARNING", "SSE format not detected"))
                    return False
            elif response.status_code == 401:
                self.results.append(("Stream Endpoint", "⚠️  AUTH REQUIRED", "Need authentication token"))
                return False
            else:
                self.results.append(("Stream Endpoint", "❌ FAIL", f"Status: {response.status_code}: {response.text}"))
                return False
        except Exception as e:
            self.results.append(("Stream Endpoint", "❌ ERROR", str(e)))
            return False

    async def test_batch(self) -> bool:
        """Test batch endpoint."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/langserve/chat/batch",
                json={
                    "inputs": [
                        {"message": "Say 'first'"},
                        {"message": "Say 'second'"},
                    ]
                },
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                if "outputs" in data and len(data["outputs"]) == 2:
                    self.results.append(("Batch Endpoint", "✅ PASS", f"Processed {len(data['outputs'])} inputs"))
                    return True
                else:
                    self.results.append(("Batch Endpoint", "⚠️  WARNING", "Unexpected response format"))
                    return False
            elif response.status_code == 401:
                self.results.append(("Batch Endpoint", "⚠️  AUTH REQUIRED", "Need authentication token"))
                return False
            else:
                self.results.append(("Batch Endpoint", "❌ FAIL", f"Status: {response.status_code}: {response.text}"))
                return False
        except Exception as e:
            self.results.append(("Batch Endpoint", "❌ ERROR", str(e)))
            return False

    async def test_playground(self) -> bool:
        """Test playground endpoint."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/langserve/chat/playground",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                content = response.text
                if "NexusAI Chat - LangServe Playground" in content:
                    self.results.append(("Playground Endpoint", "✅ PASS", "HTML page returned"))
                    return True
                else:
                    self.results.append(("Playground Endpoint", "⚠️  WARNING", "Unexpected content"))
                    return False
            else:
                self.results.append(("Playground Endpoint", "❌ FAIL", f"Status: {response.status_code}"))
                return False
        except Exception as e:
            self.results.append(("Playground Endpoint", "❌ ERROR", str(e)))
            return False

    def print_results(self):
        """Print test results in a formatted table."""
        if HAS_RICH:
            table = Table(title="LangServe Test Results", show_header=True, header_style="bold magenta")
            table.add_column("Test", style="cyan", no_wrap=True)
            table.add_column("Status", justify="center")
            table.add_column("Details", style="green")

            for test_name, status, details in self.results:
                if isinstance(details, dict):
                    details_str = json.dumps(details, indent=2)[:100] + "..." if len(str(details)) > 100 else json.dumps(details, indent=2)
                else:
                    details_str = str(details)[:100]
                table.add_row(test_name, status, details_str)

            console.print(table)
        else:
            # Fallback to basic print
            print("\n" + "=" * 80)
            print("LangServe Test Results")
            print("=" * 80)
            for test_name, status, details in self.results:
                if isinstance(details, dict):
                    details_str = json.dumps(details, indent=2)[:100] + "..." if len(str(details)) > 100 else json.dumps(details, indent=2)
                else:
                    details_str = str(details)[:100]
                print(f"{test_name:30} {status:20} {details_str}")
            print("=" * 80)

    async def run_all_tests(self):
        """Run all tests."""
        if HAS_RICH:
            console.print(Panel.fit("[bold cyan]LangServe Integration Tests[/bold cyan]", border_style="cyan"))
            console.print(f"Testing: {self.base_url}\n")
        else:
            print("\n" + "=" * 80)
            print("LangServe Integration Tests")
            print("=" * 80)
            print(f"Testing: {self.base_url}\n")

        # Run tests
        await self.test_health()
        await self.test_info()
        await self.test_playground()
        await self.test_invoke()
        await self.test_stream()
        await self.test_batch()

        # Print results
        self.print_results()

        # Summary
        passed = sum(1 for _, status, _ in self.results if "✅" in status)
        total = len(self.results)
        auth_required = sum(1 for _, status, _ in self.results if "AUTH REQUIRED" in status)

        if HAS_RICH:
            console.print(f"\n[bold]Summary:[/bold] {passed}/{total} tests passed")
            if auth_required > 0:
                console.print(f"[yellow]Note:[/yellow] {auth_required} tests require authentication. Provide a token with --token option.")
        else:
            print(f"\nSummary: {passed}/{total} tests passed")
            if auth_required > 0:
                print(f"Note: {auth_required} tests require authentication. Provide a token with --token option.")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test LangServe API endpoints")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--token",
        help="Authentication token (optional, for testing authenticated endpoints)",
    )
    parser.add_argument(
        "--test",
        choices=["health", "info", "invoke", "stream", "batch", "playground", "all"],
        default="all",
        help="Which test to run (default: all)",
    )

    args = parser.parse_args()

    async with LangServeTester(base_url=args.url, token=args.token) as tester:
        if args.test == "all":
            await tester.run_all_tests()
        elif args.test == "health":
            await tester.test_health()
            tester.print_results()
        elif args.test == "info":
            await tester.test_info()
            tester.print_results()
        elif args.test == "invoke":
            await tester.test_invoke()
            tester.print_results()
        elif args.test == "stream":
            await tester.test_stream()
            tester.print_results()
        elif args.test == "batch":
            await tester.test_batch()
            tester.print_results()
        elif args.test == "playground":
            await tester.test_playground()
            tester.print_results()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if HAS_RICH:
            console.print("\n[yellow]Tests interrupted by user[/yellow]")
        else:
            print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        if HAS_RICH:
            console.print(f"\n[red]Error:[/red] {e}")
        else:
            print(f"\nError: {e}")
        sys.exit(1)
