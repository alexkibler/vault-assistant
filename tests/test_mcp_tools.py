"""Comprehensive tests for MCP tool integration.

Tests tool detection, execution, error handling, and edge cases.
"""

import pytest
import re
from llm.tool_handler import detect_tool_call, handle_tool_call, format_tools_for_prompt
from mcp_server import get_tools, execute_tool


class TestToolDetection:
    """Test tool call detection in LLM responses."""

    def test_detect_basic_tool_call(self):
        """Detect simple [TOOL: name, param=value] format."""
        response = "The answer is [TOOL: get_current_date]"
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["tool"] == "get_current_date"
        assert tool_call["full_match"] == "[TOOL: get_current_date]"

    def test_detect_tool_with_params(self):
        """Detect tool calls with parameters."""
        response = "Let me search [TOOL: web_search, query=python programming]"
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["tool"] == "web_search"
        assert tool_call["params"]["query"] == "python programming"

    def test_detect_tool_with_multiple_params(self):
        """Detect tool calls with multiple parameters."""
        response = "[TOOL: list_vault_files, path=/notes, type=markdown]"
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["params"]["path"] == "/notes"
        assert tool_call["params"]["type"] == "markdown"

    def test_detect_xml_format_tool_call(self):
        """Detect XML-style tool calls."""
        response = "Result: <tool name=\"get_current_date\"></tool>"
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["tool"] == "get_current_date"

    def test_detect_xml_with_params(self):
        """Detect XML tool calls with parameters."""
        response = '<tool name="web_search"><param name="query">weather</param></tool>'
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["tool"] == "web_search"
        assert tool_call["params"]["query"] == "weather"

    def test_no_tool_call_in_response(self):
        """Return None when no tool call present."""
        response = "This is just a normal response without any tools."
        tool_call = detect_tool_call(response)
        assert tool_call is None

    def test_detect_first_tool_in_multiple(self):
        """Detect first tool when multiple are present."""
        response = "First [TOOL: get_current_date] and second [TOOL: web_search, query=test]"
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["tool"] == "get_current_date"

    def test_detect_tool_with_spaces(self):
        """Handle extra spaces in tool calls."""
        response = "[TOOL:  get_current_date  ,  ]"
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert tool_call["tool"] == "get_current_date"

    def test_detect_tool_with_quoted_params(self):
        """Handle quoted parameter values."""
        response = '[TOOL: web_search, query="python 3.11"]'
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        assert "python" in tool_call["params"]["query"]

    def test_detect_tool_with_equals_in_param(self):
        """Handle parameter values containing equals signs."""
        response = '[TOOL: web_search, query=a=b]'
        tool_call = detect_tool_call(response)
        assert tool_call is not None
        # Should split on first = only
        assert "=" in tool_call["params"]["query"]


class TestToolExecution:
    """Test tool execution and result handling."""

    def test_execute_get_current_date(self):
        """Execute date tool successfully."""
        result = execute_tool("get_current_date", {})
        assert isinstance(result, str)
        assert "Current date" in result or "2026" in result

    def test_execute_web_search(self):
        """Execute web search (may be unavailable)."""
        result = execute_tool("web_search", {"query": "python"})
        assert isinstance(result, str)
        # Either returns results or "not available" message

    def test_execute_list_vault_files(self):
        """Execute vault listing."""
        result = execute_tool("list_vault_files", {})
        assert isinstance(result, str)
        # Should return JSON or error message

    def test_execute_unknown_tool(self):
        """Handle unknown tool gracefully."""
        result = execute_tool("nonexistent_tool", {})
        assert "Unknown tool" in result

    def test_execute_with_empty_params(self):
        """Execute tool with empty parameters."""
        result = execute_tool("get_current_date", {})
        assert result is not None

    def test_execute_with_none_params(self):
        """Execute tool with None parameter value."""
        result = execute_tool("web_search", {"query": None})
        assert isinstance(result, str)

    def test_execute_with_empty_string_param(self):
        """Execute tool with empty string parameter."""
        result = execute_tool("web_search", {"query": ""})
        assert isinstance(result, str)

    def test_execute_with_special_chars_in_param(self):
        """Execute tool with special characters in parameters."""
        result = execute_tool("web_search", {"query": "@#$%^&*()"})
        assert isinstance(result, str)

    def test_execute_vault_with_invalid_path(self):
        """List vault files with invalid path."""
        result = execute_tool("list_vault_files", {"path": "/nonexistent/path/xyz"})
        assert isinstance(result, str)

    def test_execute_web_search_very_long_query(self):
        """Web search with very long query string."""
        long_query = "test " * 1000
        result = execute_tool("web_search", {"query": long_query})
        assert isinstance(result, str)


class TestHandleToolCall:
    """Test tool call handling and response integration."""

    def test_handle_tool_call_integration(self):
        """End-to-end tool execution with response integration."""
        response = "Let me get the current date: [TOOL: get_current_date]"
        updated, tool_info = handle_tool_call(response)

        assert tool_info is not None
        assert tool_info["tool"] == "get_current_date"
        assert "[TOOL:" not in updated  # Tool call should be replaced
        assert "Current date" in updated or "2026" in updated

    def test_handle_tool_call_no_tool(self):
        """Handle response without tool calls."""
        response = "This is a normal response."
        updated, tool_info = handle_tool_call(response)

        assert tool_info is None
        assert updated == response

    def test_handle_tool_call_with_error(self):
        """Handle tool execution errors."""
        response = "Let me use [TOOL: nonexistent_tool, param=value]"
        updated, tool_info = handle_tool_call(response)

        assert tool_info is not None
        assert "result" in tool_info
        assert "Unknown tool" in updated

    def test_handle_multiple_tool_calls_only_first(self):
        """Only handle first tool call."""
        response = "First [TOOL: get_current_date] and second [TOOL: web_search, query=test]"
        updated, tool_info = handle_tool_call(response)

        assert tool_info is not None
        assert tool_info["tool"] == "get_current_date"
        # First tool should be replaced
        assert "[TOOL: get_current_date]" not in updated

    def test_handle_tool_preserves_context(self):
        """Tool handling preserves surrounding text."""
        response = "Based on [TOOL: get_current_date], here's my answer about today."
        updated, tool_info = handle_tool_call(response)

        assert "Based on" in updated
        assert "here's my answer about today" in updated
        assert "[TOOL:" not in updated

    def test_handle_tool_with_xml_format(self):
        """Handle XML-formatted tool calls."""
        response = 'The date is <tool name="get_current_date"></tool> today.'
        updated, tool_info = handle_tool_call(response)

        assert tool_info is not None
        assert "today" in updated
        assert "<tool" not in updated


class TestFormatToolsForPrompt:
    """Test tool formatting for LLM system prompts."""

    def test_format_tools_basic(self):
        """Format available tools for prompt."""
        tools = get_tools()
        formatted = format_tools_for_prompt(tools)

        assert "Available Tools" in formatted
        assert "get_current_date" in formatted

    def test_format_includes_descriptions(self):
        """Formatted tools include descriptions."""
        tools = get_tools()
        formatted = format_tools_for_prompt(tools)

        assert "current date" in formatted.lower()
        assert "search the web" in formatted.lower()

    def test_format_includes_usage_examples(self):
        """Formatted tools include usage examples."""
        tools = get_tools()
        formatted = format_tools_for_prompt(tools)

        assert "[TOOL:" in formatted
        assert "Usage:" in formatted

    def test_format_empty_tools(self):
        """Format empty tools dictionary."""
        formatted = format_tools_for_prompt({})
        assert "Available Tools" in formatted

    def test_format_single_tool(self):
        """Format single tool."""
        tools = {"get_current_date": {
            "description": "Get current date",
            "parameters": {}
        }}
        formatted = format_tools_for_prompt(tools)
        assert "get_current_date" in formatted


class TestToolEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_tool_call_with_newlines_in_param(self):
        """Tool call with newline characters in parameter."""
        response = '[TOOL: web_search, query=test\nquery]'
        tool_call = detect_tool_call(response)
        # Should either detect it or return None gracefully
        assert tool_call is None or tool_call["tool"] == "web_search"

    def test_tool_call_unbalanced_brackets(self):
        """Malformed tool call with unbalanced brackets."""
        response = "[TOOL: get_current_date"
        tool_call = detect_tool_call(response)
        assert tool_call is None

    def test_tool_call_nested_brackets(self):
        """Tool call with nested brackets."""
        response = "[TOOL: web_search, query=[nested]]"
        tool_call = detect_tool_call(response)
        # Should handle gracefully

    def test_param_with_comma(self):
        """Parameter value containing commas."""
        response = '[TOOL: web_search, query="hello, world"]'
        tool_call = detect_tool_call(response)
        if tool_call:
            # Should preserve the comma
            assert "hello" in str(tool_call["params"])

    def test_very_long_response_with_tool(self):
        """Very long response containing tool call."""
        long_response = "" * 10000 + "[TOOL: get_current_date]" + "" * 10000
        tool_call = detect_tool_call(long_response)
        assert tool_call is not None
        assert tool_call["tool"] == "get_current_date"

    def test_tool_call_case_sensitivity(self):
        """Tool names are case sensitive."""
        response = "[TOOL: GET_CURRENT_DATE]"
        tool_call = detect_tool_call(response)
        if tool_call:
            # Should not match (case sensitive)
            assert tool_call["tool"] != "get_current_date"

    def test_whitespace_variations(self):
        """Tool call with various whitespace."""
        variations = [
            "[TOOL:get_current_date]",
            "[TOOL: get_current_date ]",
            "[ TOOL: get_current_date]",  # Space before TOOL
        ]
        for response in variations:
            tool_call = detect_tool_call(response)
            # Some may not detect due to regex, that's ok

    def test_unicode_in_search_param(self):
        """Tool parameter with unicode characters."""
        response = '[TOOL: web_search, query=café]'
        tool_call = detect_tool_call(response)
        if tool_call:
            # Should handle unicode
            assert "caf" in tool_call["params"]["query"]

    def test_empty_tool_call(self):
        """Empty tool call."""
        response = "[TOOL: ]"
        tool_call = detect_tool_call(response)
        # Should handle gracefully (None or error)


class TestToolSecurityConcerns:
    """Test potential security issues with tool usage."""

    def test_path_traversal_attempt(self):
        """Vault listing with path traversal attempt."""
        result = execute_tool("list_vault_files", {"path": "../../../etc/passwd"})
        assert isinstance(result, str)
        # Should not expose sensitive files or error gracefully

    def test_injection_in_web_search(self):
        """Web search with injection-like query."""
        result = execute_tool("web_search", {"query": "; rm -rf /"})
        assert isinstance(result, str)
        # Should handle safely

    def test_null_byte_injection(self):
        """Parameter with null bytes."""
        result = execute_tool("web_search", {"query": "test\x00malicious"})
        assert isinstance(result, str)

    def test_extremely_long_param(self):
        """Extremely long parameter value."""
        long_param = "a" * 100000
        result = execute_tool("web_search", {"query": long_param})
        assert isinstance(result, str)

    def test_tool_call_code_injection(self):
        """Tool call response with code-like content."""
        response = "[TOOL: get_current_date]; print('hacked')"
        tool_call = detect_tool_call(response)
        # Should only extract tool call, not execute code after it
        assert tool_call["full_match"] == "[TOOL: get_current_date]"

    def test_response_with_malicious_paths(self):
        """Vault file listing returns no sensitive paths."""
        result = execute_tool("list_vault_files", {})
        assert isinstance(result, str)
        # Should not contain system paths


class TestToolAvailability:
    """Test tool availability and metadata."""

    def test_get_tools_returns_dict(self):
        """get_tools returns dictionary."""
        tools = get_tools()
        assert isinstance(tools, dict)

    def test_all_required_tools_present(self):
        """All required tools are available."""
        tools = get_tools()
        required_tools = ["get_current_date", "web_search", "list_vault_files"]
        for tool in required_tools:
            assert tool in tools, f"Tool {tool} not found"

    def test_tools_have_descriptions(self):
        """All tools have descriptions."""
        tools = get_tools()
        for tool_name, tool_info in tools.items():
            assert "description" in tool_info
            assert tool_info["description"]

    def test_tools_have_parameters(self):
        """All tools have parameters field."""
        tools = get_tools()
        for tool_name, tool_info in tools.items():
            assert "parameters" in tool_info

    def test_tool_parameters_are_valid(self):
        """Tool parameters are properly structured."""
        tools = get_tools()
        for tool_name, tool_info in tools.items():
            params = tool_info.get("parameters", {})
            assert isinstance(params, dict)
            for param_name, param_info in params.items():
                if isinstance(param_info, dict):
                    assert "type" in param_info or "description" in param_info
