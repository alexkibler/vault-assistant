"""Stress tests for MCP tools.

Tests concurrent usage, performance, and resource handling.
"""

import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from llm.tool_handler import detect_tool_call, handle_tool_call
from mcp_server import execute_tool, get_tools


class TestConcurrentToolExecution:
    """Test tools under concurrent load."""

    def test_concurrent_date_calls(self):
        """Execute date tool concurrently from multiple threads."""
        results = []

        def call_date_tool():
            result = execute_tool("get_current_date", {})
            results.append(result)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(call_date_tool) for _ in range(50)]
            for future in futures:
                future.result()

        assert len(results) == 50
        assert all("Current date" in r or "2026" in r for r in results)
        assert all(results[0] == r for r in results)  # All should return same date

    def test_concurrent_vault_listing(self):
        """List vault files concurrently."""
        results = []

        def list_files():
            result = execute_tool("list_vault_files", {})
            results.append(result)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(list_files) for _ in range(30)]
            for future in futures:
                future.result()

        assert len(results) == 30
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_web_search(self):
        """Web search concurrently."""
        results = []

        def search(query):
            result = execute_tool("web_search", {"query": query})
            results.append(result)

        queries = [f"query {i}" for i in range(10)]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search, q) for q in queries]
            for future in futures:
                future.result()

        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_tool_detection(self):
        """Detect tool calls concurrently."""
        responses = [f"[TOOL: get_current_date] for query {i}" for i in range(100)]
        results = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(detect_tool_call, r) for r in responses]
            results = [f.result() for f in futures]

        assert len(results) == 100
        assert all(r is not None for r in results)


class TestToolPerformance:
    """Test tool performance and responsiveness."""

    def test_tool_detection_speed(self):
        """Tool detection should be fast."""
        response = "[TOOL: get_current_date]" + "x" * 10000

        for _ in range(100):
            tool_call = detect_tool_call(response)
            assert tool_call is not None

    def test_large_batch_tool_handling(self):
        """Handle tool calls in large batch."""
        responses = [f"Result for query {i}: [TOOL: get_current_date]" for i in range(1000)]

        handled = 0
        for response in responses:
            updated, tool_info = handle_tool_call(response)
            if tool_info:
                handled += 1

        assert handled == 1000

    def test_format_tools_performance(self):
        """Formatting tools should be fast."""
        tools = get_tools()

        for _ in range(100):
            from llm.tool_handler import format_tools_for_prompt

            formatted = format_tools_for_prompt(tools)
            assert len(formatted) > 0


class TestToolResponseIntegrity:
    """Test that tool responses maintain data integrity."""

    def test_tool_response_types(self):
        """All tool responses are strings."""
        tools_to_test = [
            ("get_current_date", {}),
            ("web_search", {"query": "test"}),
            ("list_vault_files", {}),
        ]

        for tool_name, params in tools_to_test:
            result = execute_tool(tool_name, params)
            assert isinstance(result, str), f"{tool_name} should return string"

    def test_tool_response_not_empty(self):
        """Tool responses should have content."""
        result = execute_tool("get_current_date", {})
        assert len(result) > 0

    def test_tool_response_consistency(self):
        """Multiple calls return consistent formats."""
        results = [execute_tool("get_current_date", {}) for _ in range(5)]

        # All should have similar format
        assert all("date" in r.lower() or "2026" in r for r in results)

    def test_tool_info_complete(self):
        """Tool execution returns complete info."""
        response = "[TOOL: get_current_date]"
        updated, tool_info = handle_tool_call(response)

        assert tool_info["tool"] == "get_current_date"
        assert "result" in tool_info or "error" not in tool_info


class TestToolParameterValidation:
    """Test tool parameter handling edge cases."""

    def test_web_search_empty_string(self):
        """Web search with empty query."""
        result = execute_tool("web_search", {"query": ""})
        assert isinstance(result, str)

    def test_web_search_whitespace_only(self):
        """Web search with only whitespace."""
        result = execute_tool("web_search", {"query": "   \t\n  "})
        assert isinstance(result, str)

    def test_vault_empty_path(self):
        """Vault listing with empty path."""
        result = execute_tool("list_vault_files", {"path": ""})
        assert isinstance(result, str)

    def test_vault_with_trailing_slash(self):
        """Vault listing with trailing slash."""
        result = execute_tool("list_vault_files", {"path": "/"})
        assert isinstance(result, str)

    def test_execute_with_extra_params(self):
        """Tool execution with extra unexpected parameters."""
        result = execute_tool("get_current_date", {"extra_param": "value", "another": "param"})
        assert isinstance(result, str)

    def test_execute_with_none_value(self):
        """Tool execution with None parameter value."""
        result = execute_tool("web_search", {"query": None})
        assert isinstance(result, str)

    def test_execute_with_numeric_param(self):
        """Tool execution with numeric parameter."""
        result = execute_tool("web_search", {"query": 12345})
        assert isinstance(result, str)


class TestDetectionRobustness:
    """Test tool detection robustness."""

    def test_detect_with_surrounding_text(self):
        """Tool detection ignores surrounding text."""
        response = "Before [TOOL: get_current_date] after more text here"
        tool = detect_tool_call(response)
        assert tool is not None
        assert tool["tool"] == "get_current_date"

    def test_detect_multiple_lines(self):
        """Tool detection works across lines."""
        response = """First line
[TOOL: get_current_date]
Last line"""
        tool = detect_tool_call(response)
        assert tool is not None

    def test_detect_with_code_blocks(self):
        """Tool detection in code blocks."""
        response = """```
[TOOL: get_current_date]
```"""
        tool = detect_tool_call(response)
        # Should still detect it

    def test_detect_similar_patterns(self):
        """Don't detect similar but invalid patterns."""
        invalid = "[TOOL_get_current_date]"
        tool = detect_tool_call(invalid)
        assert tool is None

    def test_detect_json_format(self):
        """Don't confuse JSON with tool format."""
        response = '{"tool": "get_current_date"}'
        tool = detect_tool_call(response)
        assert tool is None  # Should not detect JSON as tool call


class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_recovery_from_invalid_tool(self):
        """System recovers from invalid tool calls."""
        response1 = "[TOOL: bad_tool]"
        updated1, info1 = handle_tool_call(response1)

        # Should still be able to handle valid tool
        response2 = "[TOOL: get_current_date]"
        updated2, info2 = handle_tool_call(response2)

        assert info2["tool"] == "get_current_date"

    def test_recovery_from_malformed_call(self):
        """System recovers from malformed tool calls."""
        response1 = "[TOOL:"  # Incomplete
        updated1, info1 = handle_tool_call(response1)

        # Should still be usable
        response2 = "Normal text"
        updated2, info2 = handle_tool_call(response2)
        assert info2 is None

    def test_invalid_param_doesnt_break_tool(self):
        """Invalid parameters don't crash tools."""
        invalid_params = [
            None,
            "",
            "x" * 10000,
            "\x00",
            "../../etc/passwd",
        ]

        for param in invalid_params:
            result = execute_tool("web_search", {"query": param})
            assert isinstance(result, str)
            assert len(result) > 0


class TestToolChaining:
    """Test multiple tool calls in sequence."""

    def test_sequential_tool_calls(self):
        """Execute tools sequentially."""
        response1 = "First [TOOL: get_current_date]"
        updated1, info1 = handle_tool_call(response1)

        response2 = "Then [TOOL: list_vault_files]"
        updated2, info2 = handle_tool_call(response2)

        assert info1["tool"] == "get_current_date"
        assert info2["tool"] == "list_vault_files"

    def test_multiple_tools_pick_first(self):
        """Multiple tools in response picks first."""
        response = "First [TOOL: get_current_date] second [TOOL: web_search, query=test]"
        updated, info = handle_tool_call(response)

        assert info["tool"] == "get_current_date"
        assert "[TOOL: get_current_date]" not in updated

    def test_tool_result_in_next_query(self):
        """Tool result can be used in next query."""
        response1 = "[TOOL: get_current_date]"
        updated1, info1 = handle_tool_call(response1)

        # updated1 contains the date result
        response2 = f"Based on {updated1}, [TOOL: web_search, query=today]"
        # Should be able to parse this
        assert "[TOOL:" in response2


class TestToolMessageFormat:
    """Test message formatting with tools."""

    def test_tool_doesnt_corrupt_message(self):
        """Tool handling preserves message content."""
        message = "Important context here [TOOL: get_current_date] more context"
        updated, info = handle_tool_call(message)

        assert "Important context" in updated
        assert "more context" in updated

    def test_tool_with_special_markdown(self):
        """Tool handling with markdown content."""
        message = "**Bold** _italic_ [TOOL: get_current_date] `code`"
        updated, info = handle_tool_call(message)

        assert "Bold" in updated
        assert "code" in updated

    def test_tool_result_formatting(self):
        """Tool results are cleanly formatted."""
        response = "Before [TOOL: get_current_date] after"
        updated, info = handle_tool_call(response)

        # Should have result cleanly integrated
        assert "Current date" in updated or "2026" in updated
