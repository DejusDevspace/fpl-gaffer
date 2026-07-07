import asyncio
from typing import Dict, Any, List, Optional
from fpl_gaffer.tools.loader import TOOLS, AsyncFPLTool
from fpl_gaffer.core.exceptions import ToolExecutionError

class AsyncToolExecutor:
    """Custom tool executor for async FPL tools within the workflow."""

    def __init__(self):
        self.tools: Dict[str, Any] = {t.name: t for t in TOOLS}

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a specific tool by name."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self.tools[tool_name]
        return await tool._arun(**kwargs)

    async def execute_multiple_tools(self, tool_calls: List[Dict[str, Any]]) -> Any:
        """Execute multiple tools concurrently."""
        results = {}

        # Create tasks for concurrent execution
        tasks = []
        for tc in tool_calls:
            tool_name = tc.get("name")
            tool_args = tc.get("arguments", {})

            if tool_name in self.tools:
                task = self.execute_tool(tool_name, **tool_args)
                tasks.append((tool_name, task))

        tool_names = [tool_name for tool_name, _ in tasks]
        tool_results = await asyncio.gather(
            *(task for _, task in tasks),
            return_exceptions=True
        )

        for index, (tool_name, result) in enumerate(zip(tool_names, tool_results)):
            if isinstance(result, Exception):
                raise ToolExecutionError(
                    f"Error executing tool '{tool_name}': {result}"
                ) from result

            result_key = tool_name
            if result_key in results:
                result_key = f"{tool_name}_{index}"

            results[result_key] = result

        return results

    # Utility functions
    def get_tool_by_name(self, tool_name: str) -> Optional[AsyncFPLTool]:
        """Get a specific tool by name."""
        return self.tools.get(tool_name)

    def list_available_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.tools.keys())
