"""
Model Context Protocol (MCP) integration for GitMesh Agents.

This package provides classes and utilities for connecting to MCP servers
using different transport methods (stdio, SSE, etc.).
"""
from .mcp import MCP

__all__ = ["MCP"]
