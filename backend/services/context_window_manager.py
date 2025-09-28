"""
Context Window Manager for handling context limits and optimization.
Implements intelligent context truncation and summarization.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
import re

from models.api.session_models import (
    ChatSession, SessionMessage, SessionContext, FileContext
)

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """Context window configuration and state."""
    max_tokens: int
    current_tokens: int
    max_messages: int
    current_messages: int
    max_files: int
    current_files: int
    truncation_strategy: str  # 'oldest_first', 'importance_based', 'sliding_window'
    summarization_enabled: bool = True
    preserve_system_messages: bool = True


@dataclass
class ContextOptimization:
    """Context optimization result."""
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    messages_removed: int
    files_removed: int
    summary_created: bool
    optimization_strategy: str
    timestamp: datetime


class ContextWindowManager:
    """Manages chat context windows with intelligent truncation and optimization."""
    
    def __init__(self):
        # Default context window settings
        self.default_max_tokens = 50000
        self.default_max_messages = 100
        self.default_max_files = 20
        self.token_estimation_ratio = 4  # Rough estimation: 1 token ≈ 4 characters
        
        # Context optimization settings
        self.min_context_tokens = 5000  # Minimum tokens to keep
        self.summary_trigger_ratio = 0.8  # Trigger summarization at 80% capacity
        self.importance_keywords = [
            'error', 'bug', 'fix', 'issue', 'problem', 'solution',
            'implement', 'create', 'add', 'remove', 'update', 'modify',
            'function', 'class', 'method', 'variable', 'import', 'export'
        ]
    
    def create_context_window(
        self,
        max_tokens: int = None,
        max_messages: int = None,
        max_files: int = None,
        truncation_strategy: str = "sliding_window"
    ) -> ContextWindow:
        """Create a new context window configuration."""
        return ContextWindow(
            max_tokens=max_tokens or self.default_max_tokens,
            current_tokens=0,
            max_messages=max_messages or self.default_max_messages,
            current_messages=0,
            max_files=max_files or self.default_max_files,
            current_files=0,
            truncation_strategy=truncation_strategy,
            summarization_enabled=True,
            preserve_system_messages=True
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0
        return len(text) // self.token_estimation_ratio
    
    def estimate_message_tokens(self, message: SessionMessage) -> int:
        """Estimate tokens for a message including metadata."""
        base_tokens = self.estimate_tokens(message.content)
        
        # Add tokens for metadata
        if message.files_referenced:
            base_tokens += len(message.files_referenced) * 10  # Rough estimate for file references
        
        if message.code_snippets:
            for snippet in message.code_snippets:
                if isinstance(snippet, dict) and 'code' in snippet:
                    base_tokens += self.estimate_tokens(snippet['code'])
        
        return base_tokens
    
    def estimate_file_tokens(self, file_context: FileContext) -> int:
        """Estimate tokens for a file context."""
        return self.estimate_tokens(file_context.content)
    
    def calculate_context_usage(
        self,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Dict[str, int]:
        """Calculate current context usage."""
        message_tokens = sum(self.estimate_message_tokens(msg) for msg in messages)
        file_tokens = sum(self.estimate_file_tokens(fc) for fc in file_contexts)
        total_tokens = message_tokens + file_tokens
        
        return {
            'total_tokens': total_tokens,
            'message_tokens': message_tokens,
            'file_tokens': file_tokens,
            'message_count': len(messages),
            'file_count': len(file_contexts)
        }
    
    def check_context_limits(
        self,
        context_window: ContextWindow,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Dict[str, Any]:
        """Check if context exceeds limits."""
        usage = self.calculate_context_usage(messages, file_contexts)
        
        exceeds_tokens = usage['total_tokens'] > context_window.max_tokens
        exceeds_messages = usage['message_count'] > context_window.max_messages
        exceeds_files = usage['file_count'] > context_window.max_files
        
        needs_optimization = (
            exceeds_tokens or exceeds_messages or exceeds_files or
            usage['total_tokens'] > (context_window.max_tokens * self.summary_trigger_ratio)
        )
        
        return {
            'exceeds_limits': exceeds_tokens or exceeds_messages or exceeds_files,
            'needs_optimization': needs_optimization,
            'usage': usage,
            'limits': {
                'max_tokens': context_window.max_tokens,
                'max_messages': context_window.max_messages,
                'max_files': context_window.max_files
            },
            'utilization': {
                'tokens': usage['total_tokens'] / context_window.max_tokens,
                'messages': usage['message_count'] / context_window.max_messages,
                'files': usage['file_count'] / context_window.max_files
            }
        }
    
    def calculate_message_importance(self, message: SessionMessage) -> float:
        """Calculate importance score for a message."""
        importance = 0.0
        content_lower = message.content.lower()
        
        # System messages are always important
        if message.role == 'system':
            return 1.0
        
        # Recent messages are more important
        age_hours = (datetime.now() - message.timestamp).total_seconds() / 3600
        recency_score = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
        importance += recency_score * 0.3
        
        # Messages with keywords are more important
        keyword_count = sum(1 for keyword in self.importance_keywords if keyword in content_lower)
        keyword_score = min(1.0, keyword_count / 5)  # Max score at 5 keywords
        importance += keyword_score * 0.3
        
        # Messages with code snippets are important
        if message.code_snippets:
            importance += 0.2
        
        # Messages with file references are important
        if message.files_referenced:
            importance += 0.2
        
        # Longer messages might be more important
        length_score = min(1.0, len(message.content) / 1000)  # Max score at 1000 chars
        importance += length_score * 0.1
        
        return min(1.0, importance)
    
    def calculate_file_importance(self, file_context: FileContext) -> float:
        """Calculate importance score for a file context."""
        importance = 0.0
        
        # Recently accessed files are more important
        age_hours = (datetime.now() - file_context.last_accessed).total_seconds() / 3600
        recency_score = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
        importance += recency_score * 0.4
        
        # Files with certain extensions are more important
        important_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']
        if any(file_context.path.endswith(ext) for ext in important_extensions):
            importance += 0.3
        
        # Main/index files are important
        main_patterns = ['main', 'index', 'app', '__init__', 'setup']
        filename = file_context.path.lower()
        if any(pattern in filename for pattern in main_patterns):
            importance += 0.2
        
        # Smaller files might be more focused and important
        if file_context.size < 5000:  # Less than 5KB
            importance += 0.1
        
        return min(1.0, importance)
    
    def optimize_context_sliding_window(
        self,
        context_window: ContextWindow,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Tuple[List[SessionMessage], List[FileContext], ContextOptimization]:
        """Optimize context using sliding window strategy."""
        original_usage = self.calculate_context_usage(messages, file_contexts)
        
        # Keep system messages and recent messages
        optimized_messages = []
        system_messages = [msg for msg in messages if msg.role == 'system']
        user_assistant_messages = [msg for msg in messages if msg.role != 'system']
        
        # Always keep system messages
        optimized_messages.extend(system_messages)
        
        # Keep recent messages within token limit
        remaining_tokens = context_window.max_tokens - sum(
            self.estimate_message_tokens(msg) for msg in system_messages
        )
        
        # Sort by timestamp (newest first)
        user_assistant_messages.sort(key=lambda x: x.timestamp, reverse=True)
        
        for message in user_assistant_messages:
            message_tokens = self.estimate_message_tokens(message)
            if remaining_tokens >= message_tokens and len(optimized_messages) < context_window.max_messages:
                optimized_messages.append(message)
                remaining_tokens -= message_tokens
            else:
                break
        
        # Optimize file contexts (keep most recently accessed)
        optimized_files = sorted(
            file_contexts,
            key=lambda x: x.last_accessed,
            reverse=True
        )[:context_window.max_files]
        
        # Remove files that exceed token limit
        file_tokens = 0
        final_files = []
        for file_ctx in optimized_files:
            tokens = self.estimate_file_tokens(file_ctx)
            if file_tokens + tokens <= remaining_tokens:
                final_files.append(file_ctx)
                file_tokens += tokens
            else:
                break
        
        # Sort messages back to chronological order
        optimized_messages.sort(key=lambda x: x.timestamp)
        
        final_usage = self.calculate_context_usage(optimized_messages, final_files)
        
        optimization = ContextOptimization(
            original_tokens=original_usage['total_tokens'],
            optimized_tokens=final_usage['total_tokens'],
            tokens_saved=original_usage['total_tokens'] - final_usage['total_tokens'],
            messages_removed=len(messages) - len(optimized_messages),
            files_removed=len(file_contexts) - len(final_files),
            summary_created=False,
            optimization_strategy='sliding_window',
            timestamp=datetime.now()
        )
        
        return optimized_messages, final_files, optimization
    
    def optimize_context_importance_based(
        self,
        context_window: ContextWindow,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Tuple[List[SessionMessage], List[FileContext], ContextOptimization]:
        """Optimize context using importance-based strategy."""
        original_usage = self.calculate_context_usage(messages, file_contexts)
        
        # Calculate importance scores
        message_scores = [
            (msg, self.calculate_message_importance(msg))
            for msg in messages
        ]
        file_scores = [
            (fc, self.calculate_file_importance(fc))
            for fc in file_contexts
        ]
        
        # Sort by importance (highest first)
        message_scores.sort(key=lambda x: x[1], reverse=True)
        file_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select messages within limits
        optimized_messages = []
        remaining_tokens = context_window.max_tokens
        
        for message, score in message_scores:
            if len(optimized_messages) >= context_window.max_messages:
                break
            
            message_tokens = self.estimate_message_tokens(message)
            if remaining_tokens >= message_tokens:
                optimized_messages.append(message)
                remaining_tokens -= message_tokens
        
        # Select files within limits
        optimized_files = []
        for file_ctx, score in file_scores:
            if len(optimized_files) >= context_window.max_files:
                break
            
            file_tokens = self.estimate_file_tokens(file_ctx)
            if remaining_tokens >= file_tokens:
                optimized_files.append(file_ctx)
                remaining_tokens -= file_tokens
        
        # Sort messages back to chronological order
        optimized_messages.sort(key=lambda x: x.timestamp)
        
        final_usage = self.calculate_context_usage(optimized_messages, optimized_files)
        
        optimization = ContextOptimization(
            original_tokens=original_usage['total_tokens'],
            optimized_tokens=final_usage['total_tokens'],
            tokens_saved=original_usage['total_tokens'] - final_usage['total_tokens'],
            messages_removed=len(messages) - len(optimized_messages),
            files_removed=len(file_contexts) - len(optimized_files),
            summary_created=False,
            optimization_strategy='importance_based',
            timestamp=datetime.now()
        )
        
        return optimized_messages, optimized_files, optimization
    
    def create_conversation_summary(
        self,
        messages: List[SessionMessage],
        max_summary_tokens: int = 500
    ) -> str:
        """Create a summary of conversation messages."""
        if not messages:
            return ""
        
        # Group messages by conversation turns
        conversation_turns = []
        current_turn = []
        
        for message in messages:
            if message.role == 'system':
                continue
            
            if message.role == 'user' and current_turn:
                conversation_turns.append(current_turn)
                current_turn = [message]
            else:
                current_turn.append(message)
        
        if current_turn:
            conversation_turns.append(current_turn)
        
        # Create summary points
        summary_points = []
        
        for turn in conversation_turns[-10:]:  # Last 10 turns
            user_msg = next((msg for msg in turn if msg.role == 'user'), None)
            assistant_msg = next((msg for msg in turn if msg.role == 'assistant'), None)
            
            if user_msg and assistant_msg:
                # Extract key topics
                user_content = user_msg.content[:200]  # First 200 chars
                assistant_content = assistant_msg.content[:200]
                
                # Look for key actions or topics
                key_topics = []
                for keyword in self.importance_keywords:
                    if keyword in user_content.lower() or keyword in assistant_content.lower():
                        key_topics.append(keyword)
                
                if key_topics:
                    summary_points.append(f"Discussed: {', '.join(key_topics[:3])}")
                elif user_msg.files_referenced:
                    files = ', '.join(user_msg.files_referenced[:2])
                    summary_points.append(f"Worked on files: {files}")
        
        # Create final summary
        if summary_points:
            summary = "Previous conversation summary:\n" + "\n".join(f"- {point}" for point in summary_points[-5:])
        else:
            summary = "Previous conversation covered general development topics."
        
        # Ensure summary doesn't exceed token limit
        while self.estimate_tokens(summary) > max_summary_tokens and summary_points:
            summary_points.pop(0)
            summary = "Previous conversation summary:\n" + "\n".join(f"- {point}" for point in summary_points)
        
        return summary
    
    def optimize_context_with_summarization(
        self,
        context_window: ContextWindow,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Tuple[List[SessionMessage], List[FileContext], ContextOptimization]:
        """Optimize context with summarization of old messages."""
        original_usage = self.calculate_context_usage(messages, file_contexts)
        
        if not context_window.summarization_enabled:
            return self.optimize_context_sliding_window(context_window, messages, file_contexts)
        
        # Separate system messages and conversation messages
        system_messages = [msg for msg in messages if msg.role == 'system']
        conversation_messages = [msg for msg in messages if msg.role != 'system']
        
        # Keep recent messages (last 20% or minimum 10)
        keep_count = max(10, int(len(conversation_messages) * 0.2))
        recent_messages = conversation_messages[-keep_count:]
        old_messages = conversation_messages[:-keep_count]
        
        optimized_messages = system_messages.copy()
        
        # Create summary of old messages if they exist
        summary_created = False
        if old_messages:
            summary = self.create_conversation_summary(old_messages)
            if summary:
                summary_message = SessionMessage(
                    message_id=f"summary_{datetime.now().isoformat()}",
                    session_id=messages[0].session_id if messages else "unknown",
                    role="system",
                    content=summary,
                    timestamp=old_messages[0].timestamp if old_messages else datetime.now()
                )
                optimized_messages.append(summary_message)
                summary_created = True
        
        # Add recent messages
        optimized_messages.extend(recent_messages)
        
        # Optimize files using sliding window
        remaining_tokens = context_window.max_tokens - sum(
            self.estimate_message_tokens(msg) for msg in optimized_messages
        )
        
        optimized_files = sorted(
            file_contexts,
            key=lambda x: x.last_accessed,
            reverse=True
        )[:context_window.max_files]
        
        # Remove files that exceed token limit
        file_tokens = 0
        final_files = []
        for file_ctx in optimized_files:
            tokens = self.estimate_file_tokens(file_ctx)
            if file_tokens + tokens <= remaining_tokens:
                final_files.append(file_ctx)
                file_tokens += tokens
        
        final_usage = self.calculate_context_usage(optimized_messages, final_files)
        
        optimization = ContextOptimization(
            original_tokens=original_usage['total_tokens'],
            optimized_tokens=final_usage['total_tokens'],
            tokens_saved=original_usage['total_tokens'] - final_usage['total_tokens'],
            messages_removed=len(messages) - len(optimized_messages),
            files_removed=len(file_contexts) - len(final_files),
            summary_created=summary_created,
            optimization_strategy='summarization',
            timestamp=datetime.now()
        )
        
        return optimized_messages, final_files, optimization
    
    def optimize_context(
        self,
        context_window: ContextWindow,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Tuple[List[SessionMessage], List[FileContext], ContextOptimization]:
        """Optimize context using the configured strategy."""
        strategy = context_window.truncation_strategy
        
        if strategy == "sliding_window":
            return self.optimize_context_sliding_window(context_window, messages, file_contexts)
        elif strategy == "importance_based":
            return self.optimize_context_importance_based(context_window, messages, file_contexts)
        elif strategy == "oldest_first":
            return self.optimize_context_sliding_window(context_window, messages, file_contexts)
        else:
            # Default to summarization
            return self.optimize_context_with_summarization(context_window, messages, file_contexts)
    
    def get_context_recommendations(
        self,
        context_window: ContextWindow,
        messages: List[SessionMessage],
        file_contexts: List[FileContext]
    ) -> Dict[str, Any]:
        """Get recommendations for context optimization."""
        limits_check = self.check_context_limits(context_window, messages, file_contexts)
        
        recommendations = {
            'needs_optimization': limits_check['needs_optimization'],
            'current_usage': limits_check['usage'],
            'utilization': limits_check['utilization'],
            'suggestions': []
        }
        
        if limits_check['utilization']['tokens'] > 0.8:
            recommendations['suggestions'].append({
                'type': 'token_optimization',
                'message': 'Context is approaching token limit. Consider summarization.',
                'priority': 'high'
            })
        
        if limits_check['utilization']['messages'] > 0.8:
            recommendations['suggestions'].append({
                'type': 'message_optimization',
                'message': 'Too many messages in context. Consider removing older messages.',
                'priority': 'medium'
            })
        
        if limits_check['utilization']['files'] > 0.8:
            recommendations['suggestions'].append({
                'type': 'file_optimization',
                'message': 'Too many files in context. Consider removing unused files.',
                'priority': 'medium'
            })
        
        # Suggest strategy based on usage patterns
        if len(messages) > 50:
            recommendations['suggestions'].append({
                'type': 'strategy_suggestion',
                'message': 'Consider using summarization strategy for long conversations.',
                'priority': 'low'
            })
        
        return recommendations


# Global instance
context_window_manager = ContextWindowManager()