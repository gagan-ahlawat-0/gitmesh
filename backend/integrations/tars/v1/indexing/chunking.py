"""
TARS v1 Advanced Chunking Strategies
====================================

Enhanced chunking strategies built on ai framework's Chunking class:
- Leverages Chonkie library for advanced chunking
- Multiple chunking strategies (token, sentence, semantic, etc.)
- Production-ready performance optimization
- Quality scoring and analysis
"""

import time
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass

# Import ai framework chunking
from ai.knowledge.chunking import Chunking

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Enhanced metadata for code chunks with ai framework integration."""
    chunk_id: str
    chunk_type: str  # token, sentence, semantic, etc.
    start_line: int = 0
    end_line: int = 0
    language: str = "unknown"
    importance_score: float = 0.5
    context_level: int = 0  # 0=finest, 1=medium, 2=coarse
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = None
    semantic_tags: List[str] = None
    token_count: int = 0
    chonkie_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.child_chunk_ids is None:
            self.child_chunk_ids = []
        if self.semantic_tags is None:
            self.semantic_tags = []
        if self.chonkie_metadata is None:
            self.chonkie_metadata = {}


@dataclass
class ChunkingResult:
    """Enhanced chunking result with performance metrics and quality scores."""
    chunks: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    performance: Dict[str, float]
    quality_score: float
    ai_chunker_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.ai_chunker_info is None:
            self.ai_chunker_info = {}


class EnhancedChunker:
    """Enhanced chunker built on ai framework's Chunking class."""
    
    def __init__(
        self,
        chunker_type: str = 'token',
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        embedding_model: Optional[str] = None,
        **kwargs
    ):
        """Initialize enhanced chunker."""
        # Initialize the ai framework chunker
        chunker_kwargs = {
            'chunker_type': chunker_type,
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
        
        if embedding_model:
            chunker_kwargs['embedding_model'] = embedding_model
            
        # Add any additional kwargs
        chunker_kwargs.update(kwargs)
        
        self.ai_chunker = Chunking(**chunker_kwargs)
        self.chunker_type = chunker_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        
        logger.info(f"AI chunker initialized: {self.ai_chunker}")
        logger.info(f"Initialized EnhancedChunker with type '{chunker_type}' and size {chunk_size}")
        
    def chunk(self, content: str, file_path: Union[str, Path]) -> ChunkingResult:
        """
        Initialize enhanced chunker using ai framework.
        
        Args:
            chunker_type: Type of chunker ('token', 'sentence', 'semantic', 'sdpm', 'late', 'recursive')
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks 
            tokenizer: Tokenizer for token-based chunking
            embedding_model: Model for semantic chunking
            max_chunk_size: Maximum chunk size limit
            **kwargs: Additional parameters for specific chunkers
        """
        self.chunker_type = chunker_type
        self.chunk_size = min(chunk_size, max_chunk_size)
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer
        self.embedding_model = embedding_model
        self.max_chunk_size = max_chunk_size
        self.kwargs = kwargs
        
        # Initialize ai framework Chunking
        self._init_ai_chunker()
        
        logger.info(f"Initialized EnhancedChunker with type '{chunker_type}' and size {chunk_size}")
    
    def _init_ai_chunker(self):
        """Initialize the ai framework Chunking instance."""
        try:
            chunker_params = {
                'chunker_type': self.chunker_type,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
                'tokenizer_or_token_counter': self.tokenizer,
                **self.kwargs
            }
            
            # Add embedding model for semantic chunkers
            if self.chunker_type in ['semantic', 'sdpm', 'late'] and self.embedding_model:
                chunker_params['embedding_model'] = self.embedding_model
            
            self.ai_chunker = Chunking(**chunker_params)
            
            logger.info(f"AI chunker initialized: {self.ai_chunker}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ai chunker: {e}")
            # Fallback to basic token chunker
            self.ai_chunker = Chunking(
                chunker_type='token',
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
    
    def chunk(self, content: str, file_path: Path) -> ChunkingResult:
        """Chunk content using ai framework chunking with enhancements."""
        start_time = time.time()
        
        try:
            # Use ai framework chunking
            chonkie_chunks = self.ai_chunker.chunk(content)
            
            # Convert to enhanced chunks with metadata
            enhanced_chunks = self._enhance_chunks(chonkie_chunks, content, file_path)
            
            # Calculate quality metrics
            quality_score = self._calculate_quality_score(enhanced_chunks, content)
            
            # Performance metrics
            processing_time = time.time() - start_time
            
            result = ChunkingResult(
                chunks=enhanced_chunks,
                metadata={
                    'chunking_strategy': f'ai_framework_{self.chunker_type}',
                    'ai_chunker_type': self.chunker_type,
                    'chunk_size': self.chunk_size,
                    'chunk_overlap': self.chunk_overlap,
                    'total_chunks': len(enhanced_chunks),
                    'file_path': str(file_path),
                    'language': self._detect_language(file_path)
                },
                performance={
                    'processing_time': processing_time,
                    'chunks_per_second': len(enhanced_chunks) / processing_time if processing_time > 0 else 0,
                    'characters_per_second': len(content) / processing_time if processing_time > 0 else 0,
                    'avg_chunk_size': sum(len(chunk['content']) for chunk in enhanced_chunks) / len(enhanced_chunks) if enhanced_chunks else 0
                },
                quality_score=quality_score,
                ai_chunker_info={
                    'chunker_class': self.ai_chunker.__class__.__name__,
                    'chunker_params': {
                        'chunker_type': self.chunker_type,
                        'chunk_size': self.chunk_size,
                        'chunk_overlap': self.chunk_overlap
                    }
                }
            )
            
            logger.info(f"Chunking completed: {len(enhanced_chunks)} chunks, quality: {quality_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            # Return fallback result
            return self._fallback_chunk(content, file_path, start_time)
    
    def _enhance_chunks(self, chonkie_chunks, content: str, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Enhance Chonkie chunks with additional metadata and analysis."""
        # Ensure file_path is a Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        enhanced_chunks = []
        language = self._detect_language(file_path)
        
        for i, chunk in enumerate(chonkie_chunks):
            # Extract chunk content and metadata
            if hasattr(chunk, 'text'):
                chunk_content = chunk.text
                chonkie_meta = {
                    'start_index': getattr(chunk, 'start_index', 0),
                    'end_index': getattr(chunk, 'end_index', len(chunk_content)),
                    'token_count': getattr(chunk, 'token_count', len(chunk_content.split()))
                }
            else:
                # Handle different chunk formats
                chunk_content = str(chunk)
                chonkie_meta = {'token_count': len(chunk_content.split())}
            
            # Create enhanced metadata
            chunk_id = f"{file_path.stem}_{self.chunker_type}_{i:04d}"
            
            # Analyze chunk content
            importance_score = self._calculate_chunk_importance(chunk_content, language)
            semantic_tags = self._extract_semantic_tags(chunk_content, language)
            chunk_type = self._identify_chunk_type(chunk_content, language)
            
            # Calculate line numbers (approximate)
            lines_before = content[:content.find(chunk_content)].count('\n') if chunk_content in content else 0
            lines_in_chunk = chunk_content.count('\n')
            
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                chunk_type=f"{self.chunker_type}_{chunk_type}",
                start_line=lines_before,
                end_line=lines_before + lines_in_chunk,
                language=language,
                importance_score=importance_score,
                context_level=0,  # Could be enhanced based on chunker type
                semantic_tags=semantic_tags,
                token_count=chonkie_meta.get('token_count', 0),
                chonkie_metadata=chonkie_meta
            )
            
            enhanced_chunk = {
                'content': chunk_content,
                'metadata': metadata,
                'chunk_info': {
                    'length': len(chunk_content),
                    'word_count': len(chunk_content.split()),
                    'line_count': chunk_content.count('\n') + 1,
                    'complexity_score': self._calculate_complexity(chunk_content, language)
                }
            }
            
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def _detect_language(self, file_path: Union[str, Path]) -> str:
        """Detect programming language from file extension."""
        # Ensure file_path is a Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }
        
        return extension_map.get(file_path.suffix.lower(), 'text')
    
    def _calculate_chunk_importance(self, content: str, language: str) -> float:
        """Calculate importance score for a chunk based on content analysis."""
        importance = 0.5  # Base importance
        content_lower = content.lower().strip()
        
        # Language-specific importance patterns
        if language == 'python':
            patterns = {
                'class ': 0.3,
                'def ': 0.25,
                'import ': 0.1,
                'from ': 0.1,
                'async def ': 0.3,
                '@': 0.15,  # decorators
                'raise ': 0.2,
                'except ': 0.15,
                '__init__': 0.25,
                '__main__': 0.2
            }
        elif language in ['javascript', 'typescript']:
            patterns = {
                'function ': 0.25,
                'class ': 0.3,
                'export ': 0.2,
                'import ': 0.1,
                'async ': 0.2,
                'const ': 0.1,
                'interface ': 0.25,
                'type ': 0.2
            }
        else:
            patterns = {
                'function': 0.2,
                'class': 0.25,
                'import': 0.1,
                'struct': 0.2,
                'enum': 0.15
            }
        
        # Apply pattern-based scoring
        for pattern, score in patterns.items():
            if pattern in content_lower:
                importance += score
        
        # Content quality factors
        lines = content.count('\n') + 1
        words = len(content.split())
        
        # Prefer medium-sized chunks
        if 10 <= lines <= 50 and 50 <= words <= 500:
            importance += 0.1
        elif lines < 5 or words < 20:
            importance -= 0.2
        
        # Check for documentation
        if '"""' in content or '/*' in content or content.count('#') > 3:
            importance += 0.1
        
        return min(max(importance, 0.1), 1.0)
    
    def _extract_semantic_tags(self, content: str, language: str) -> List[str]:
        """Extract semantic tags from chunk content."""
        tags = []
        content_lower = content.lower()
        
        # Programming constructs
        if 'class ' in content_lower:
            tags.append('class_definition')
        if 'def ' in content_lower or 'function ' in content_lower:
            tags.append('function_definition')
        if 'import ' in content_lower or 'from ' in content_lower or 'export ' in content_lower:
            tags.append('imports')
        if '"""' in content or '/*' in content or content.count('#') > 2:
            tags.append('documentation')
        if 'test' in content_lower or 'assert' in content_lower:
            tags.append('testing')
        if 'async' in content_lower:
            tags.append('asynchronous')
        if 'exception' in content_lower or 'error' in content_lower or 'try:' in content_lower:
            tags.append('error_handling')
        
        # Design patterns (simplified detection)
        patterns = ['singleton', 'factory', 'observer', 'decorator', 'adapter', 'strategy']
        for pattern in patterns:
            if pattern in content_lower:
                tags.append(f'pattern_{pattern}')
        
        return tags
    
    def _identify_chunk_type(self, content: str, language: str) -> str:
        """Identify the primary type of content in the chunk."""
        content_lower = content.lower().strip()
        
        if content_lower.startswith('class '):
            return 'class_definition'
        elif content_lower.startswith('def ') or content_lower.startswith('function '):
            return 'function_definition'
        elif 'import ' in content_lower or 'from ' in content_lower:
            return 'imports'
        elif content_lower.startswith('"""') or content_lower.startswith('/*'):
            return 'documentation'
        elif content.strip().startswith('#') or content.strip().startswith('//'):
            return 'comments'
        elif 'test' in content_lower and ('def test' in content_lower or 'function test' in content_lower):
            return 'test_code'
        elif 'config' in content_lower or 'settings' in content_lower:
            return 'configuration'
        else:
            return 'code_block'
    
    def _calculate_complexity(self, content: str, language: str) -> float:
        """Calculate code complexity score for a chunk."""
        complexity = 0.0
        
        # Cyclomatic complexity indicators
        complexity_keywords = ['if', 'elif', 'else', 'while', 'for', 'try', 'except', 'finally', 'with']
        for keyword in complexity_keywords:
            complexity += content.lower().count(keyword) * 0.1
        
        # Nesting indicators
        if language == 'python':
            lines = content.split('\n')
            max_indent = 0
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    max_indent = max(max_indent, indent)
            complexity += max_indent * 0.05
        
        # Function/method count
        if language == 'python':
            complexity += content.count('def ') * 0.15
        elif language in ['javascript', 'typescript']:
            complexity += content.count('function ') * 0.15
        
        return min(complexity, 2.0)  # Cap at 2.0
    
    def _calculate_quality_score(self, chunks: List[Dict], original_content: str) -> float:
        """Calculate overall quality score for the chunking result."""
        if not chunks:
            return 0.0
        
        scores = []
        
        # Size consistency
        sizes = [len(chunk['content']) for chunk in chunks]
        avg_size = sum(sizes) / len(sizes)
        size_variance = sum((size - avg_size) ** 2 for size in sizes) / len(sizes)
        size_consistency = max(0, 1 - (size_variance ** 0.5) / avg_size) if avg_size > 0 else 0
        scores.append(size_consistency)
        
        # Content coverage
        total_chunk_content = ''.join(chunk['content'] for chunk in chunks)
        coverage = len(total_chunk_content) / len(original_content) if original_content else 0
        scores.append(min(coverage, 1.0))
        
        # Average chunk importance
        avg_importance = sum(chunk['metadata'].importance_score for chunk in chunks) / len(chunks)
        scores.append(avg_importance)
        
        # Semantic coherence (simplified)
        semantic_score = sum(len(chunk['metadata'].semantic_tags) for chunk in chunks) / len(chunks) / 5
        scores.append(min(semantic_score, 1.0))
        
        return sum(scores) / len(scores)
    
    def _fallback_chunk(self, content: str, file_path: Union[str, Path], start_time: float) -> ChunkingResult:
        """Fallback chunking when ai framework chunking fails."""
        logger.warning("Using fallback chunking due to ai framework failure")
        
        # Ensure file_path is a Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        # Simple text chunking as fallback
        words = content.split()
        chunk_size_words = max(self.chunk_size // 4, 100)  # Approximate words per chunk
        
        chunks = []
        for i in range(0, len(words), chunk_size_words):
            chunk_words = words[i:i + chunk_size_words]
            chunk_content = ' '.join(chunk_words)
            
            metadata = ChunkMetadata(
                chunk_id=f"{file_path.stem}_fallback_{i}",
                chunk_type="fallback_text",
                language=self._detect_language(file_path),
                importance_score=0.5,
                token_count=len(chunk_words),
                chonkie_metadata={'fallback': True}
            )
            
            chunk = {
                'content': chunk_content,
                'metadata': metadata,
                'chunk_info': {
                    'length': len(chunk_content),
                    'word_count': len(chunk_words),
                    'line_count': chunk_content.count('\n') + 1,
                    'complexity_score': 0.0
                }
            }
            
            chunks.append(chunk)
        
        processing_time = time.time() - start_time
        
        return ChunkingResult(
            chunks=chunks,
            metadata={
                'chunking_strategy': 'fallback_text',
                'ai_chunker_type': 'fallback',
                'total_chunks': len(chunks),
                'file_path': str(file_path),
                'language': self._detect_language(file_path)
            },
            performance={
                'processing_time': processing_time,
                'chunks_per_second': len(chunks) / processing_time if processing_time > 0 else 0
            },
            quality_score=0.3,  # Lower quality for fallback
            ai_chunker_info={'fallback': True}
        )


class HierarchicalChunker:
    """Hierarchical chunking using multiple ai framework chunkers."""
    
    def __init__(
        self,
        chunk_sizes: List[int] = None,
        chunker_types: List[str] = None,
        overlap_ratio: float = 0.25,
        embedding_model: Optional[str] = None,
        tokenizer: str = "gpt2"
    ):
        """
        Initialize hierarchical chunker with multiple levels.
        
        Args:
            chunk_sizes: Sizes for each hierarchical level
            chunker_types: Types of chunkers for each level 
            overlap_ratio: Overlap between chunks
            embedding_model: Model for semantic chunkers
            tokenizer: Tokenizer for token-based chunkers
        """
        self.chunk_sizes = chunk_sizes or [512, 1024, 2048]
        self.chunker_types = chunker_types or ['token', 'sentence', 'semantic']
        self.overlap_ratio = overlap_ratio
        self.embedding_model = embedding_model
        self.tokenizer = tokenizer
        
        # Ensure we have matching numbers of sizes and types
        if len(self.chunk_sizes) != len(self.chunker_types):
            # Repeat the last type if needed
            while len(self.chunker_types) < len(self.chunk_sizes):
                self.chunker_types.append(self.chunker_types[-1])
        
        # Initialize chunkers for each level
        self.chunkers = self._init_level_chunkers()
        
        logger.info(f"HierarchicalChunker initialized with {len(self.chunk_sizes)} levels")
    
    def _init_level_chunkers(self) -> List[EnhancedChunker]:
        """Initialize chunkers for each hierarchical level."""
        chunkers = []
        
        for i, (size, chunker_type) in enumerate(zip(self.chunk_sizes, self.chunker_types)):
            chunker = EnhancedChunker(
                chunker_type=chunker_type,
                chunk_size=size,
                chunk_overlap=int(size * self.overlap_ratio),
                tokenizer=self.tokenizer,
                embedding_model=self.embedding_model if chunker_type in ['semantic', 'sdpm', 'late'] else None
            )
            chunkers.append(chunker)
            
            logger.info(f"Level {i}: {chunker_type} chunker with size {size}")
        
        return chunkers
    
    def chunk(self, content: str, file_path: Path) -> ChunkingResult:
        """Create hierarchical chunks at multiple levels."""
        start_time = time.time()
        all_chunks = []
        level_results = []
        
        # Create chunks at each level
        for level, chunker in enumerate(self.chunkers):
            try:
                level_result = chunker.chunk(content, file_path)
                
                # Add level information to chunks
                for chunk in level_result.chunks:
                    chunk['metadata'].context_level = level
                    chunk['level_info'] = {
                        'level': level,
                        'chunker_type': self.chunker_types[level],
                        'chunk_size': self.chunk_sizes[level],
                        'total_in_level': len(level_result.chunks)
                    }
                
                all_chunks.extend(level_result.chunks)
                level_results.append(level_result)
                
            except Exception as e:
                logger.error(f"Level {level} chunking failed: {e}")
                continue
        
        # Establish hierarchical relationships
        self._establish_hierarchy(all_chunks)
        
        # Calculate combined metrics
        processing_time = time.time() - start_time
        quality_score = self._calculate_hierarchical_quality(level_results, all_chunks)
        
        return ChunkingResult(
            chunks=all_chunks,
            metadata={
                'chunking_strategy': 'hierarchical_ai_framework',
                'levels': len(self.chunkers),
                'chunk_sizes': self.chunk_sizes,
                'chunker_types': self.chunker_types,
                'total_chunks': len(all_chunks),
                'chunks_per_level': [len(result.chunks) for result in level_results]
            },
            performance={
                'processing_time': processing_time,
                'chunks_per_second': len(all_chunks) / processing_time if processing_time > 0 else 0,
                'level_performance': [result.performance for result in level_results]
            },
            quality_score=quality_score,
            ai_chunker_info={
                'hierarchical': True,
                'level_results': [result.ai_chunker_info for result in level_results]
            }
        )
    
    def _establish_hierarchy(self, chunks: List[Dict]):
        """Establish parent-child relationships between hierarchical levels."""
        # Group chunks by level
        levels = {}
        for chunk in chunks:
            level = chunk['metadata'].context_level
            if level not in levels:
                levels[level] = []
            levels[level].append(chunk)
        
        # Sort levels (finest to coarsest)
        sorted_levels = sorted(levels.keys())
        
        # Link adjacent levels
        for i in range(len(sorted_levels) - 1):
            child_level = sorted_levels[i]      # Finer level
            parent_level = sorted_levels[i + 1] # Coarser level
            
            self._link_levels(levels[parent_level], levels[child_level])
    
    def _link_levels(self, parent_chunks: List[Dict], child_chunks: List[Dict]):
        """Link parent chunks to their child chunks based on content overlap."""
        for parent in parent_chunks:
            parent_content = parent['content'].lower()
            
            for child in child_chunks:
                child_content = child['content'].lower()
                
                # Check if child content is contained in or overlaps with parent
                overlap_ratio = self._calculate_content_overlap(parent_content, child_content)
                
                if overlap_ratio > 0.3:  # At least 30% overlap
                    parent['metadata'].child_chunk_ids.append(child['metadata'].chunk_id)
                    child['metadata'].parent_chunk_id = parent['metadata'].chunk_id
    
    def _calculate_content_overlap(self, parent_content: str, child_content: str) -> float:
        """Calculate content overlap ratio between parent and child chunks."""
        if not child_content or not parent_content:
            return 0.0
        
        # Simple word-based overlap calculation
        parent_words = set(parent_content.split())
        child_words = set(child_content.split())
        
        if not child_words:
            return 0.0
        
        common_words = parent_words & child_words
        overlap_ratio = len(common_words) / len(child_words)
        
        return overlap_ratio
    
    def _calculate_hierarchical_quality(self, level_results: List[ChunkingResult], all_chunks: List[Dict]) -> float:
        """Calculate quality score for hierarchical chunking."""
        if not level_results or not all_chunks:
            return 0.0
        
        # Average quality across levels
        level_qualities = [result.quality_score for result in level_results if result.quality_score > 0]
        avg_level_quality = sum(level_qualities) / len(level_qualities) if level_qualities else 0.0
        
        # Hierarchy coherence (how well levels relate to each other)
        hierarchy_coherence = self._calculate_hierarchy_coherence(all_chunks)
        
        # Coverage consistency across levels
        coverage_consistency = self._calculate_coverage_consistency(level_results)
        
        return (avg_level_quality + hierarchy_coherence + coverage_consistency) / 3
    
    def _calculate_hierarchy_coherence(self, chunks: List[Dict]) -> float:
        """Calculate how coherent the hierarchical relationships are."""
        parent_child_pairs = 0
        valid_relationships = 0
        
        for chunk in chunks:
            if chunk['metadata'].child_chunk_ids:
                parent_child_pairs += len(chunk['metadata'].child_chunk_ids)
                # Check if relationships make sense (simplified)
                valid_relationships += len(chunk['metadata'].child_chunk_ids)
        
        return valid_relationships / parent_child_pairs if parent_child_pairs > 0 else 1.0
    
    def _calculate_coverage_consistency(self, level_results: List[ChunkingResult]) -> float:
        """Calculate consistency of coverage across hierarchical levels."""
        if not level_results:
            return 0.0
        
        # Check if coarser levels have fewer chunks than finer levels
        chunk_counts = [len(result.chunks) for result in level_results]
        
        consistent_hierarchy = True
        for i in range(len(chunk_counts) - 1):
            if chunk_counts[i] < chunk_counts[i + 1]:  # Finer should have more chunks
                consistent_hierarchy = False
                break
        
        return 1.0 if consistent_hierarchy else 0.7


# Utility functions for chunking strategies
def create_adaptive_chunker(
    language: str,
    content_size: int,
    use_case: str = "general"
) -> EnhancedChunker:
    """Create an adaptive chunker optimized for specific language and use case."""
    
    # Language-specific optimizations
    language_configs = {
        'python': {
            'chunker_type': 'semantic',
            'chunk_size': 1024,
            'embedding_model': 'all-MiniLM-L6-v2',
            'chunk_overlap': 128
        },
        'javascript': {
            'chunker_type': 'sentence',
            'chunk_size': 768,
            'chunk_overlap': 100
        },
        'typescript': {
            'chunker_type': 'sentence',
            'chunk_size': 768,
            'chunk_overlap': 100
        },
        'java': {
            'chunker_type': 'token',
            'chunk_size': 1024,
            'chunk_overlap': 128
        },
        'cpp': {
            'chunker_type': 'token',
            'chunk_size': 1024,
            'chunk_overlap': 128
        },
        'markdown': {
            'chunker_type': 'sentence',
            'chunk_size': 512,
            'chunk_overlap': 64
        },
        'text': {
            'chunker_type': 'sentence',
            'chunk_size': 512,
            'chunk_overlap': 64
        }
    }
    
    # Use case optimizations
    use_case_adjustments = {
        'code_search': {
            'chunk_size_multiplier': 0.8,  # Smaller chunks for precise search
            'overlap_multiplier': 1.2
        },
        'documentation': {
            'chunk_size_multiplier': 1.5,  # Larger chunks for context
            'overlap_multiplier': 0.8
        },
        'analysis': {
            'chunk_size_multiplier': 1.2,
            'overlap_multiplier': 1.0
        },
        'embeddings': {
            'chunk_size_multiplier': 1.0,
            'overlap_multiplier': 1.0
        }
    }
    
    # Get base configuration
    config = language_configs.get(language.lower(), language_configs['text']).copy()
    
    # Apply use case adjustments
    if use_case in use_case_adjustments:
        adjustments = use_case_adjustments[use_case]
        config['chunk_size'] = int(config['chunk_size'] * adjustments['chunk_size_multiplier'])
        config['chunk_overlap'] = int(config['chunk_overlap'] * adjustments['overlap_multiplier'])
    
    # Content size adjustments
    if content_size < 1000:  # Small files
        config['chunk_size'] = min(config['chunk_size'], 256)
        config['chunk_overlap'] = min(config['chunk_overlap'], 32)
    elif content_size > 100000:  # Large files
        config['chunk_size'] = min(config['chunk_size'], 2048)
        config['chunk_overlap'] = max(config['chunk_overlap'], 256)
    
    return EnhancedChunker(**config)


def create_multi_strategy_chunker(
    strategies: List[str],
    chunk_sizes: List[int] = None,
    **kwargs
) -> HierarchicalChunker:
    """Create a chunker that uses multiple strategies."""
    
    if chunk_sizes is None:
        # Default sizes for each strategy
        default_sizes = {
            'token': 512,
            'sentence': 1024,
            'semantic': 1536,
            'sdpm': 2048,
            'late': 1024,
            'recursive': 768
        }
        chunk_sizes = [default_sizes.get(strategy, 1024) for strategy in strategies]
    
    return HierarchicalChunker(
        chunk_sizes=chunk_sizes,
        chunker_types=strategies,
        **kwargs
    )


def optimize_chunker_for_search(
    base_chunker: EnhancedChunker,
    search_query_length: int = 100
) -> EnhancedChunker:
    """Optimize chunker configuration for search tasks."""
    
    # Adjust chunk size based on typical query length
    optimal_chunk_size = max(search_query_length * 3, 256)
    optimal_overlap = max(search_query_length // 2, 32)
    
    base_chunker.chunk_size = min(base_chunker.chunk_size, optimal_chunk_size)
    base_chunker.chunk_overlap = min(base_chunker.chunk_overlap, optimal_overlap)
    
    # Reinitialize ai chunker with new parameters
    base_chunker._init_ai_chunker()
    
    return base_chunker


def analyze_chunking_quality(result: ChunkingResult) -> Dict[str, Any]:
    """Analyze the quality of a chunking result."""
    
    chunks = result.chunks
    if not chunks:
        return {'overall_score': 0.0, 'issues': ['No chunks generated']}
    
    analysis = {
        'overall_score': result.quality_score,
        'chunk_count': len(chunks),
        'size_statistics': {},
        'content_analysis': {},
        'recommendations': [],
        'issues': []
    }
    
    # Size statistics
    sizes = [len(chunk['content']) for chunk in chunks]
    analysis['size_statistics'] = {
        'min_size': min(sizes),
        'max_size': max(sizes),
        'avg_size': sum(sizes) / len(sizes),
        'median_size': sorted(sizes)[len(sizes) // 2],
        'size_std': (sum((s - sum(sizes) / len(sizes)) ** 2 for s in sizes) / len(sizes)) ** 0.5
    }
    
    # Content analysis
    importance_scores = [chunk['metadata'].importance_score for chunk in chunks]
    analysis['content_analysis'] = {
        'avg_importance': sum(importance_scores) / len(importance_scores),
        'high_importance_chunks': sum(1 for score in importance_scores if score > 0.7),
        'low_importance_chunks': sum(1 for score in importance_scores if score < 0.3),
        'semantic_tags_count': sum(len(chunk['metadata'].semantic_tags) for chunk in chunks)
    }
    
    # Generate recommendations
    if analysis['size_statistics']['size_std'] > analysis['size_statistics']['avg_size'] * 0.5:
        analysis['recommendations'].append("Consider using a different chunking strategy for more consistent sizes")
    
    if analysis['content_analysis']['low_importance_chunks'] > len(chunks) * 0.3:
        analysis['recommendations'].append("Many chunks have low importance scores - consider adjusting chunk boundaries")
    
    if analysis['size_statistics']['avg_size'] < 100:
        analysis['recommendations'].append("Chunks are very small - consider increasing chunk size")
    elif analysis['size_statistics']['avg_size'] > 3000:
        analysis['recommendations'].append("Chunks are very large - consider decreasing chunk size")
    
    # Identify issues
    if len(chunks) < 3 and len(result.metadata.get('file_content', '')) > 1000:
        analysis['issues'].append("Too few chunks for the content size")
    
    if analysis['content_analysis']['semantic_tags_count'] == 0:
        analysis['issues'].append("No semantic tags extracted - content analysis may be limited")
    
    return analysis


# Export main classes and functions
__all__ = [
    'ChunkMetadata',
    'ChunkingResult', 
    'EnhancedChunker',
    'HierarchicalChunker',
    'create_adaptive_chunker',
    'create_multi_strategy_chunker',
    'optimize_chunker_for_search',
    'analyze_chunking_quality'
]


# Import time module for performance tracking
import time
