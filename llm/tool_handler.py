"""
Handle tool calls from Ollama responses.
Provides tool execution and result formatting back to the LLM.
"""

import re
import json
from typing import Optional
from mcp_server import get_tools, execute_tool as exec_tool


def detect_tool_call(response: str) -> Optional[dict]:
    """
    Detect if the LLM response contains a tool call.
    Looks for patterns like: [TOOL: tool_name, param1=value1, param2=value2]
    Or: <tool name="tool_name"><param name="param1">value1</param></tool>
    """
    # Pattern 1: [TOOL: name, params]
    pattern1 = r"\[TOOL:\s*(\w+),?\s*(.*?)\]"
    match = re.search(pattern1, response)
    if match:
        tool_name = match.group(1)
        params_str = match.group(2)
        params = {}
        for param in params_str.split(","):
            if "=" in param:
                key, val = param.split("=", 1)
                params[key.strip()] = val.strip().strip("\"'")
        return {"tool": tool_name, "params": params, "full_match": match.group(0)}

    # Pattern 2: <tool> tags
    pattern2 = r'<tool name="(\w+)">(.*?)</tool>'
    match = re.search(pattern2, response)
    if match:
        tool_name = match.group(1)
        params_str = match.group(2)
        params = {}
        param_pattern = r'<param name="(\w+)">([^<]+)</param>'
        for param_match in re.finditer(param_pattern, params_str):
            params[param_match.group(1)] = param_match.group(2)
        return {"tool": tool_name, "params": params, "full_match": match.group(0)}

    return None


def handle_tool_call(response: str) -> tuple[str, Optional[dict]]:
    """
    Check if response contains a tool call, execute it, and return updated response.
    Returns: (response_with_tool_result, tool_info)
    """
    tool_call = detect_tool_call(response)
    if not tool_call:
        return response, None

    tool_name = tool_call["tool"]
    params = tool_call["params"]

    try:
        result = exec_tool(tool_name, params)
        # Replace tool call with clean result
        updated_response = response.replace(tool_call["full_match"], result)
        return updated_response, {"tool": tool_name, "params": params, "result": result}
    except Exception as e:
        error_msg = f"Error using {tool_name}: {str(e)}"
        updated_response = response.replace(tool_call["full_match"], error_msg)
        return updated_response, {"tool": tool_name, "params": params, "error": str(e)}


def format_tools_for_prompt(tools: dict) -> str:
    """Format available tools as context for the LLM prompt."""
    prompt = "\n=== Available Tools ===\n"
    for tool_name, tool_info in tools.items():
        prompt += f"\n[TOOL: {tool_name}]\n"
        prompt += f"Description: {tool_info.get('description', 'N/A')}\n"
        if tool_info.get("parameters"):
            prompt += "Parameters:\n"
            for param_name, param_info in tool_info["parameters"].items():
                prompt += f"  - {param_name}: {param_info.get('description', 'N/A')}\n"
        prompt += "Usage: [TOOL: {}, {}={}]\n".format(
            tool_name, ", ".join(tool_info.get("parameters", {}).keys()) or "no params", "value"
        )
    prompt += "\n======================\n"
    return prompt
