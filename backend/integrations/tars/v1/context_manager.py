"""
TARS v1 Progressive Context Manager
==================================

Manages context loading and optimization for better AI responses:
- Progressive context loading (summary → details)
- Smart context filtering and prioritization
- Context window optimization
- Hierarchical information structure
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ContextItem:
    """Represents a piece of context with metadata."""
    content: str
    priority: float  # 0.0 to 1.0
    context_type: str  # 'summary', 'detail', 'code', 'documentation', etc.
    source: str
    token_estimate: int
    relevance_score: float = 0.0


@dataclass
class ContextLevel:
    """Represents a level in the progressive context hierarchy."""
    level_name: str
    description: str
    items: List[ContextItem]
    token_limit: int
    min_items: int = 1
    max_items: int = 10


class ProgressiveContextManager:
    """
    Manages progressive context loading for better AI responses.
    
    Uses a hierarchical approach:
    1. High-level summaries (always included)
    2. Medium-detail explanations (included if space allows)
    3. Detailed code/documentation (included only if highly relevant)
    """
    
    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens
        self.reserved_tokens = int(max_context_tokens * 0.3)  # Reserve 30% for response
        self.available_tokens = max_context_tokens - self.reserved_tokens
        
        # Define progressive levels
        self.context_levels = [
            ContextLevel(
                level_name="summary",
                description="High-level summaries and overviews",
                items=[],
                token_limit=int(self.available_tokens * 0.4),  # 40% for summaries
                min_items=1,
                max_items=5
            ),
            ContextLevel(
                level_name="details",
                description="Medium-detail explanations and key information",
                items=[],
                token_limit=int(self.available_tokens * 0.4),  # 40% for details
                min_items=0,
                max_items=8
            ),
            ContextLevel(
                level_name="specifics",
                description="Detailed code, documentation, and specific examples",
                items=[],
                token_limit=int(self.available_tokens * 0.2),  # 20% for specifics
                min_items=0,
                max_items=3
            )
        ]
    
    def add_context_item(
        self,
        content: str,
        context_type: str,
        source: str,
        priority: float = 0.5,
        level: str = "details"
    ) -> None:
        """Add a context item to the appropriate level."""
        try:
            # Estimate tokens
            token_estimate = len(content.split()) * 1.3
            
            # Create context item
            item = ContextItem(
                content=content,
                priority=priority,
                context_type=context_type,
                source=source,
                token_estimate=int(token_estimate)
            )
            
            # Add to appropriate level
            for context_level in self.context_levels:
                if context_level.level_name == level:
                    context_level.items.append(item)
                    break
                    
        except Exception as e:
            logger.warning(f"Error adding context item: {e}")
    
    def add_repository_context(self, repo_content: str, repository_id: str) -> None:
        """Add repository context with progressive detail levels."""
        try:
            lines = repo_content.split('\n')
            
            # Level 1: High-level summary
            file_count = len([l for l in lines if l.startswith('File: ')])
            languages = set()
            key_files = []
            
            for line in lines[:50]:
                if 'File: ' in line:
                    file_path = line.replace('File: ', '').strip()
                    if file_path:
                        ext = Path(file_path).suffix
                        if ext:
                            languages.add(ext)
                        
                        # Identify key files
                        if any(key in file_path.lower() for key in ['main', 'index', 'app', 'readme', 'config']):
                            key_files.append(file_path)
            
            summary = f"Repository: {repository_id}\n"
            summary += f"Files: {file_count}\n"
            summary += f"Languages: {', '.join(sorted(languages)) if languages else 'Unknown'}\n"
            summary += f"Key Files: {', '.join(key_files[:5])}"
            
            self.add_context_item(
                content=summary,
                context_type="repository_summary",
                source=repository_id,
                priority=0.9,
                level="summary"
            )
            
            # Level 2: Code structure details
            code_elements = []
            current_file = None
            
            for line in lines[:200]:
                if line.startswith('File: '):
                    current_file = line.replace('File: ', '').strip()
                elif any(pattern in line for pattern in ['def ', 'class ', 'function ', 'import ', 'interface ']):
                    if current_file:
                        code_elements.append(f"{current_file}: {line.strip()}")
                    
                    if len(code_elements) >= 15:
                        break
            
            if code_elements:
                details = "Code Structure:\n" + '\n'.join(code_elements[:10])
                self.add_context_item(
                    content=details,
                    context_type="code_structure",
                    source=repository_id,
                    priority=0.7,
                    level="details"
                )
            
            # Level 3: Specific code snippets (only if highly relevant)
            code_snippets = []
            current_snippet = []
            in_code_block = False
            
            for line in lines[:500]:
                if any(pattern in line for pattern in ['def ', 'class ', 'function ']):
                    if current_snippet:
                        code_snippets.append('\n'.join(current_snippet))
                        current_snippet = []
                    current_snippet.append(line)
                    in_code_block = True
                elif in_code_block and line.strip():
                    current_snippet.append(line)
                    if len(current_snippet) >= 8:  # Limit snippet size
                        code_snippets.append('\n'.join(current_snippet))
                        current_snippet = []
                        in_code_block = False
                elif in_code_block and not line.strip():
                    if current_snippet:
                        code_snippets.append('\n'.join(current_snippet))
                        current_snippet = []
                    in_code_block = False
                    
                if len(code_snippets) >= 3:
                    break
            
            if current_snippet:
                code_snippets.append('\n'.join(current_snippet))
            
            for i, snippet in enumerate(code_snippets[:2]):
                self.add_context_item(
                    content=f"Code Example {i+1}:\n{snippet}",
                    context_type="code_snippet",
                    source=repository_id,
                    priority=0.5,
                    level="specifics"
                )
                
        except Exception as e:
            logger.warning(f"Error adding repository context: {e}")
    
    def calculate_relevance_scores(self, query: str) -> None:
        """Calculate relevance scores for all context items based on query."""
        try:
            query_words = set(query.lower().split())
            
            for level in self.context_levels:
                for item in level.items:
                    item.relevance_score = self._calculate_item_relevance(item, query_words)
                    
        except Exception as e:
            logger.warning(f"Error calculating relevance scores: {e}")
    
    def _calculate_item_relevance(self, item: ContextItem, query_words: set) -> float:
        """Calculate relevance score for a specific item."""
        content_words = set(item.content.lower().split())
        
        # Base relevance from word overlap
        if query_words:
            overlap = len(query_words.intersection(content_words))
            relevance = overlap / len(query_words)
        else:
            relevance = item.priority
        
        # Boost based on context type
        type_boosts = {
            'repository_summary': 0.2,
            'code_structure': 0.15,
            'code_snippet': 0.1,
            'documentation': 0.15,
            'error_handling': 0.1
        }
        
        relevance += type_boosts.get(item.context_type, 0.0)
        
        # Boost based on priority
        relevance = (relevance + item.priority) / 2
        
        return min(relevance, 1.0)
    
    def build_progressive_context(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """Build progressive context string with optimization metrics."""
        try:
            # Calculate relevance scores
            self.calculate_relevance_scores(query)
            
            # Sort items within each level by relevance and priority
            for level in self.context_levels:
                level.items.sort(key=lambda x: (x.relevance_score + x.priority) / 2, reverse=True)
            
            context_parts = [f"User Query: {query}\n"]
            total_tokens = len(query.split()) * 1.3
            items_included = {"summary": 0, "details": 0, "specifics": 0}
            
            # Progressive inclusion by level
            for level in self.context_levels:
                level_tokens = 0
                level_items = 0
                
                context_parts.append(f"\n📋 {level.description.title()}:")
                
                for item in level.items:
                    # Check if we can include this item
                    if (level_tokens + item.token_estimate <= level.token_limit and
                        total_tokens + item.token_estimate <= self.available_tokens and
                        level_items < level.max_items):
                        
                        context_parts.append(f"• {item.content}")
                        level_tokens += item.token_estimate
                        total_tokens += item.token_estimate
                        level_items += 1
                        items_included[level.level_name] += 1
                    
                    # Stop if we've reached minimum items for this level
                    if level_items >= level.min_items and total_tokens > self.available_tokens * 0.8:
                        break
                
                if level_items == 0 and level.min_items > 0:
                    context_parts.append("• (No relevant information available)")
            
            # Add optimization summary
            context_parts.append(f"\n📊 Context Optimization:")
            context_parts.append(f"• Tokens Used: {int(total_tokens)} / {self.available_tokens}")
            context_parts.append(f"• Utilization: {(total_tokens / self.available_tokens) * 100:.1f}%")
            context_parts.append(f"• Items Included: {sum(items_included.values())}")
            
            context_parts.append("\n💡 Please provide a comprehensive response based on the above progressive context.")
            
            context_string = '\n'.join(context_parts)
            
            # Metrics for debugging
            metrics = {
                "total_tokens": int(total_tokens),
                "available_tokens": self.available_tokens,
                "utilization_percent": (total_tokens / self.available_tokens) * 100,
                "items_included": items_included,
                "levels_used": len([l for l in self.context_levels if any(i.relevance_score > 0 for i in l.items)])
            }
            
            return context_string, metrics
            
        except Exception as e:
            logger.error(f"Error building progressive context: {e}")
            return f"User Query: {query}\n\nError building context: {str(e)}", {}
    
    def clear(self) -> None:
        """Clear all context items."""
        for level in self.context_levels:
            level.items.clear()
