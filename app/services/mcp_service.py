"""
MCP (Model Context Protocol) Server Integration Service

This service handles the integration with MCP servers using langchain-mcp-adapters
"""
import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.runners import StreamableHTTPRunner
from langchain_mcp_adapters.platforms import Platform

from app.core.config import settings


class MCPService:
    """Service for managing MCP server connections and tool discovery"""

    def __init__(self):
        """Initialize the MCP service"""
        # Cache of MCP runners by server URL
        self.runners: Dict[str, StreamableHTTPRunner] = {}
        
    def get_runner(self, server_url: str) -> StreamableHTTPRunner:
        """
        Get or create an MCP runner for the specified server URL
        
        Args:
            server_url: The MCP server URL
            
        Returns:
            A StreamableHTTPRunner instance for the MCP server
        """
        if server_url not in self.runners:
            # Create a new runner
            self.runners[server_url] = StreamableHTTPRunner(
                url=server_url,
                platform=Platform.OPENAI,
            )
        return self.runners[server_url]
    
    def get_tools(self, server_url: str) -> List[BaseTool]:
        """
        Get available tools from an MCP server
        
        Args:
            server_url: The MCP server URL
            
        Returns:
            A list of LangChain BaseTool instances
        """
        runner = self.get_runner(server_url)
        try:
            return runner.tools
        except Exception as e:
            raise ValueError(f"Failed to get tools from MCP server {server_url}: {e}")
    
    def describe_tools(self, server_url: str) -> List[Dict[str, Any]]:
        """
        Get descriptions of available tools from an MCP server
        
        Args:
            server_url: The MCP server URL
            
        Returns:
            A list of tool descriptions with name, description, and parameters
        """
        tools = self.get_tools(server_url)
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": self._get_tool_parameters(tool),
            }
            for tool in tools
        ]
    
    def _get_tool_parameters(self, tool: BaseTool) -> Dict[str, Any]:
        """Extract parameter information from a tool schema"""
        if not hasattr(tool, "args_schema"):
            return {}
        
        schema = tool.args_schema.schema()
        if "properties" not in schema:
            return {}
        
        return schema["properties"]
    
    def get_test_server(self) -> StreamableHTTPRunner:
        """
        Get the test MCP server runner
        
        Returns:
            A StreamableHTTPRunner for the test MCP server
        """
        return self.get_runner(settings.mcp_test_server_url)


# Create a singleton instance
mcp_service = MCPService()
