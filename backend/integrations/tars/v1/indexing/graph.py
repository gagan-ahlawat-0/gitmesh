"""
TARS v1 Graph-Based Code Intelligence
=====================================

Advanced graph indexing for code relationships, dependencies,
and semantic connections with comprehensive performance tracking.
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
import networkx as nx

# AI framework imports
from ai.memory.supabase_db import SupabaseMemory

logger = logging.getLogger(__name__)


@dataclass
class GraphConfig:
    """Configuration for graph-based indexing."""
    # Graph storage
    enable_persistent_storage: bool = True
    use_supabase_backend: bool = True
    graph_collection: str = "tars-code-graph"
    
    # Graph construction
    max_graph_size: int = 100000  # nodes
    max_edge_weight: float = 1.0
    min_edge_weight: float = 0.1
    
    # Relationship detection
    enable_ast_relationships: bool = True
    enable_semantic_relationships: bool = True
    enable_dependency_tracking: bool = True
    enable_call_graph: bool = True
    
    # Performance
    batch_size: int = 1000
    max_concurrent_operations: int = 8
    enable_caching: bool = True
    cache_size: int = 5000
    
    # Analysis settings
    max_path_length: int = 6
    community_detection: bool = True
    centrality_analysis: bool = True


@dataclass
class GraphStats:
    """Graph performance and structure statistics."""
    total_nodes: int = 0
    total_edges: int = 0
    graph_build_time: float = 0.0
    total_queries: int = 0
    query_time: float = 0.0
    avg_query_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Graph structure metrics
    avg_degree: float = 0.0
    clustering_coefficient: float = 0.0
    connected_components: int = 0
    graph_density: float = 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total_requests, 1)


@dataclass
class GraphNode:
    """Represents a node in the code graph."""
    id: str
    node_type: str  # function, class, variable, file, module, etc.
    name: str
    content: Optional[str] = None
    file_path: Optional[str] = None
    language: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "content": self.content,
            "file_path": self.file_path,
            "language": self.language,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "metadata": self.metadata
        }


@dataclass
class GraphEdge:
    """Represents an edge in the code graph."""
    source_id: str
    target_id: str
    relationship_type: str  # calls, imports, inherits, contains, etc.
    weight: float = 1.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "weight": self.weight,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class GraphCache:
    """High-performance graph query cache."""
    
    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = deque()
        self.query_counts = defaultdict(int)
    
    def _make_key(self, query_type: str, **kwargs) -> str:
        """Create cache key from query parameters."""
        params = sorted(kwargs.items())
        return f"{query_type}:{hash(str(params))}"
    
    def get(self, query_type: str, **kwargs) -> Optional[Any]:
        """Get cached query result."""
        key = self._make_key(query_type, **kwargs)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            self.query_counts[key] += 1
            return self.cache[key]
        
        return None
    
    def put(self, result: Any, query_type: str, **kwargs):
        """Store query result in cache."""
        key = self._make_key(query_type, **kwargs)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.popleft()
            del self.cache[oldest_key]
            del self.query_counts[oldest_key]
        
        # Store result
        self.cache[key] = result
        
        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        self.query_counts[key] += 1
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.access_order.clear()
        self.query_counts.clear()
    
    @property
    def size(self) -> int:
        return len(self.cache)


class GraphIntelligenceEngine:
    """Advanced graph-based code intelligence engine."""
    
    def __init__(self, config: Optional[GraphConfig] = None):
        self.config = config or GraphConfig()
        self.stats = GraphStats()
        
        # Initialize graph storage
        self.graph = nx.MultiDiGraph()  # Allows multiple edges between nodes
        self.supabase_client = None
        
        # Initialize cache
        self.cache = GraphCache(self.config.cache_size) if self.config.enable_caching else None
        
        # Node and edge mappings for fast lookup
        self.node_index = {}  # node_id -> GraphNode
        self.edge_index = {}  # edge_id -> GraphEdge
        
        # Analysis results cache
        self.analysis_cache = {}
        
        # Query history
        self.query_history = []
    
    async def initialize(self):
        """Initialize graph intelligence engine."""
        logger.info("Initializing Graph Intelligence Engine...")
        
        try:
            # Initialize Supabase backend if enabled
            if self.config.use_supabase_backend:
                await self._init_supabase_backend()
            
            # Create graph schema tables
            await self._create_graph_tables()
            
            logger.info("Graph intelligence engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize graph engine: {e}")
            raise
    
    async def _init_supabase_backend(self):
        """Initialize Supabase backend for persistent graph storage."""
        try:
            supabase_config = {
                'supabase_url': os.getenv('SUPABASE_URL'),
                'supabase_key': os.getenv('SUPABASE_ANON_KEY'),
                'supabase_service_key': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
                'pg_host': os.getenv('POSTGRES_HOST'),
                'pg_port': os.getenv('POSTGRES_PORT', '5432'),
                'pg_db': os.getenv('POSTGRES_DB', 'postgres'),
                'pg_user': os.getenv('POSTGRES_USER'),
                'pg_password': os.getenv('POSTGRES_PASSWORD'),
                'pg_ssl': os.getenv('POSTGRES_SSL', 'require')
            }
            
            self.supabase_client = SupabaseMemory(config=supabase_config, verbose=0)
            logger.info("Supabase backend initialized for graph storage")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase backend: {e}")
            raise
    
    async def _create_graph_tables(self):
        """Create tables for persistent graph storage."""
        if not self.supabase_client:
            return
        
        try:
            with self.supabase_client.conn.cursor() as cursor:
                # Create graph nodes table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT,
                    file_path TEXT,
                    language TEXT,
                    line_start INTEGER,
                    line_end INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                
                # Create graph edges table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    weight FLOAT DEFAULT 1.0,
                    confidence FLOAT DEFAULT 1.0,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    FOREIGN KEY (source_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES graph_nodes(id) ON DELETE CASCADE
                );
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_file ON graph_nodes(file_path);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_language ON graph_nodes(language);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(relationship_type);")
                
                self.supabase_client.conn.commit()
                logger.info("Graph tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating graph tables: {e}")
            self.supabase_client.conn.rollback()
            raise
    
    async def add_node(self, node: GraphNode) -> str:
        """Add a node to the graph."""
        try:
            # Add to NetworkX graph
            self.graph.add_node(
                node.id,
                node_type=node.node_type,
                name=node.name,
                content=node.content,
                file_path=node.file_path,
                language=node.language,
                line_start=node.line_start,
                line_end=node.line_end,
                **node.metadata
            )
            
            # Store in index
            self.node_index[node.id] = node
            
            # Persist to database if enabled
            if self.config.enable_persistent_storage and self.supabase_client:
                await self._persist_node(node)
            
            # Update statistics
            self.stats.total_nodes += 1
            
            return node.id
            
        except Exception as e:
            logger.error(f"Error adding node {node.id}: {e}")
            raise
    
    async def add_edge(self, edge: GraphEdge) -> str:
        """Add an edge to the graph."""
        try:
            # Ensure both nodes exist
            if edge.source_id not in self.node_index or edge.target_id not in self.node_index:
                raise ValueError(f"Source or target node not found: {edge.source_id} -> {edge.target_id}")
            
            # Add to NetworkX graph
            edge_id = f"{edge.source_id}_{edge.target_id}_{edge.relationship_type}"
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                key=edge.relationship_type,
                relationship_type=edge.relationship_type,
                weight=edge.weight,
                confidence=edge.confidence,
                **edge.metadata
            )
            
            # Store in index
            self.edge_index[edge_id] = edge
            
            # Persist to database if enabled
            if self.config.enable_persistent_storage and self.supabase_client:
                await self._persist_edge(edge)
            
            # Update statistics
            self.stats.total_edges += 1
            
            return edge_id
            
        except Exception as e:
            logger.error(f"Error adding edge {edge.source_id} -> {edge.target_id}: {e}")
            raise
    
    async def _persist_node(self, node: GraphNode):
        """Persist node to database."""
        try:
            with self.supabase_client.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO graph_nodes 
                    (id, node_type, name, content, file_path, language, line_start, line_end, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        node_type = EXCLUDED.node_type,
                        name = EXCLUDED.name,
                        content = EXCLUDED.content,
                        file_path = EXCLUDED.file_path,
                        language = EXCLUDED.language,
                        line_start = EXCLUDED.line_start,
                        line_end = EXCLUDED.line_end,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        node.id, node.node_type, node.name, node.content,
                        node.file_path, node.language, node.line_start, node.line_end,
                        json.dumps(node.metadata)
                    )
                )
                self.supabase_client.conn.commit()
                
        except Exception as e:
            logger.error(f"Error persisting node {node.id}: {e}")
            self.supabase_client.conn.rollback()
    
    async def _persist_edge(self, edge: GraphEdge):
        """Persist edge to database."""
        try:
            with self.supabase_client.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO graph_edges 
                    (source_id, target_id, relationship_type, weight, confidence, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        edge.source_id, edge.target_id, edge.relationship_type,
                        edge.weight, edge.confidence, json.dumps(edge.metadata)
                    )
                )
                self.supabase_client.conn.commit()
                
        except Exception as e:
            logger.error(f"Error persisting edge {edge.source_id} -> {edge.target_id}: {e}")
            self.supabase_client.conn.rollback()
    
    async def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        relationship_types: Optional[List[str]] = None
    ) -> Optional[List[str]]:
        """Find shortest path between two nodes."""
        cache_key = f"shortest_path_{source_id}_{target_id}_{relationship_types}"
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get("shortest_path", source=source_id, target=target_id, types=relationship_types)
            if cached_result is not None:
                self.stats.cache_hits += 1
                return cached_result
        
        self.stats.cache_misses += 1
        
        try:
            start_time = time.time()
            
            # Create filtered graph if relationship types specified
            if relationship_types:
                filtered_graph = self._filter_graph_by_edge_types(relationship_types)
            else:
                filtered_graph = self.graph
            
            # Find shortest path
            try:
                path = nx.shortest_path(filtered_graph, source_id, target_id)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                path = None
            
            # Update statistics
            query_time = time.time() - start_time
            self.stats.total_queries += 1
            self.stats.query_time += query_time
            self.stats.avg_query_time = self.stats.query_time / self.stats.total_queries
            
            # Cache result
            if self.cache:
                self.cache.put(path, "shortest_path", source=source_id, target=target_id, types=relationship_types)
            
            # Record query
            self._record_query("shortest_path", query_time, {"source": source_id, "target": target_id})
            
            return path
            
        except Exception as e:
            logger.error(f"Error finding shortest path: {e}")
            return None
    
    async def find_connected_components(
        self,
        node_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None
    ) -> List[List[str]]:
        """Find connected components in the graph."""
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get("connected_components", node_types=node_types, rel_types=relationship_types)
            if cached_result is not None:
                self.stats.cache_hits += 1
                return cached_result
        
        self.stats.cache_misses += 1
        
        try:
            start_time = time.time()
            
            # Create filtered graph
            filtered_graph = self._filter_graph(node_types, relationship_types)
            
            # Convert to undirected for connected components
            undirected_graph = filtered_graph.to_undirected()
            
            # Find connected components
            components = list(nx.connected_components(undirected_graph))
            component_lists = [list(component) for component in components]
            
            # Update statistics
            query_time = time.time() - start_time
            self.stats.total_queries += 1
            self.stats.query_time += query_time
            self.stats.avg_query_time = self.stats.query_time / self.stats.total_queries
            self.stats.connected_components = len(components)
            
            # Cache result
            if self.cache:
                self.cache.put(component_lists, "connected_components", node_types=node_types, rel_types=relationship_types)
            
            # Record query
            self._record_query("connected_components", query_time, {"node_types": node_types, "rel_types": relationship_types})
            
            return component_lists
            
        except Exception as e:
            logger.error(f"Error finding connected components: {e}")
            return []
    
    async def find_neighbors(
        self,
        node_id: str,
        relationship_types: Optional[List[str]] = None,
        max_distance: int = 1,
        direction: str = "both"  # "in", "out", "both"
    ) -> List[GraphNode]:
        """Find neighboring nodes within specified distance."""
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(
                "neighbors", 
                node_id=node_id, 
                rel_types=relationship_types, 
                distance=max_distance,
                direction=direction
            )
            if cached_result is not None:
                self.stats.cache_hits += 1
                return cached_result
        
        self.stats.cache_misses += 1
        
        try:
            start_time = time.time()
            
            # Create filtered graph
            if relationship_types:
                filtered_graph = self._filter_graph_by_edge_types(relationship_types)
            else:
                filtered_graph = self.graph
            
            # Find neighbors at specified distance
            neighbors = set()
            
            for distance in range(1, max_distance + 1):
                if direction in ["out", "both"]:
                    # Outgoing edges (successors)
                    current_neighbors = set()
                    for node in neighbors if distance > 1 else {node_id}:
                        if node in filtered_graph:
                            current_neighbors.update(filtered_graph.successors(node))
                    neighbors.update(current_neighbors)
                
                if direction in ["in", "both"]:
                    # Incoming edges (predecessors)
                    current_neighbors = set()
                    for node in neighbors if distance > 1 else {node_id}:
                        if node in filtered_graph:
                            current_neighbors.update(filtered_graph.predecessors(node))
                    neighbors.update(current_neighbors)
            
            # Remove the original node
            neighbors.discard(node_id)
            
            # Convert to GraphNode objects
            neighbor_nodes = [self.node_index[node_id] for node_id in neighbors if node_id in self.node_index]
            
            # Update statistics
            query_time = time.time() - start_time
            self.stats.total_queries += 1
            self.stats.query_time += query_time
            self.stats.avg_query_time = self.stats.query_time / self.stats.total_queries
            
            # Cache result
            if self.cache:
                self.cache.put(
                    neighbor_nodes, 
                    "neighbors", 
                    node_id=node_id, 
                    rel_types=relationship_types, 
                    distance=max_distance,
                    direction=direction
                )
            
            # Record query
            self._record_query("find_neighbors", query_time, {
                "node_id": node_id, 
                "distance": max_distance,
                "neighbors_found": len(neighbor_nodes)
            })
            
            return neighbor_nodes
            
        except Exception as e:
            logger.error(f"Error finding neighbors for {node_id}: {e}")
            return []
    
    async def analyze_centrality(self, centrality_type: str = "betweenness") -> Dict[str, float]:
        """Analyze node centrality in the graph."""
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get("centrality", centrality_type=centrality_type)
            if cached_result is not None:
                self.stats.cache_hits += 1
                return cached_result
        
        self.stats.cache_misses += 1
        
        try:
            start_time = time.time()
            
            # Calculate centrality based on type
            if centrality_type == "betweenness":
                centrality = nx.betweenness_centrality(self.graph)
            elif centrality_type == "closeness":
                centrality = nx.closeness_centrality(self.graph)
            elif centrality_type == "degree":
                centrality = nx.degree_centrality(self.graph)
            elif centrality_type == "pagerank":
                centrality = nx.pagerank(self.graph)
            elif centrality_type == "eigenvector":
                try:
                    centrality = nx.eigenvector_centrality(self.graph, max_iter=1000)
                except nx.PowerIterationFailedConvergence:
                    logger.warning("Eigenvector centrality failed to converge, using degree centrality")
                    centrality = nx.degree_centrality(self.graph)
            else:
                raise ValueError(f"Unsupported centrality type: {centrality_type}")
            
            # Update statistics
            query_time = time.time() - start_time
            self.stats.total_queries += 1
            self.stats.query_time += query_time
            self.stats.avg_query_time = self.stats.query_time / self.stats.total_queries
            
            # Cache result
            if self.cache:
                self.cache.put(centrality, "centrality", centrality_type=centrality_type)
            
            # Record query
            self._record_query("analyze_centrality", query_time, {"centrality_type": centrality_type})
            
            return centrality
            
        except Exception as e:
            logger.error(f"Error analyzing centrality: {e}")
            return {}
    
    def _filter_graph(self, node_types: Optional[List[str]] = None, relationship_types: Optional[List[str]] = None) -> nx.MultiDiGraph:
        """Filter graph by node types and relationship types."""
        filtered_graph = self.graph.copy()
        
        # Filter by node types
        if node_types:
            nodes_to_remove = [
                node for node, data in filtered_graph.nodes(data=True)
                if data.get('node_type') not in node_types
            ]
            filtered_graph.remove_nodes_from(nodes_to_remove)
        
        # Filter by relationship types
        if relationship_types:
            edges_to_remove = [
                (u, v, key) for u, v, key, data in filtered_graph.edges(data=True, keys=True)
                if data.get('relationship_type') not in relationship_types
            ]
            filtered_graph.remove_edges_from(edges_to_remove)
        
        return filtered_graph
    
    def _filter_graph_by_edge_types(self, relationship_types: List[str]) -> nx.MultiDiGraph:
        """Filter graph to include only specified edge types."""
        filtered_graph = nx.MultiDiGraph()
        
        # Add all nodes
        filtered_graph.add_nodes_from(self.graph.nodes(data=True))
        
        # Add only edges with specified relationship types
        for u, v, key, data in self.graph.edges(data=True, keys=True):
            if data.get('relationship_type') in relationship_types:
                filtered_graph.add_edge(u, v, key=key, **data)
        
        return filtered_graph
    
    def _record_query(self, query_type: str, query_time: float, params: Dict[str, Any]):
        """Record query for analytics."""
        query_record = {
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "query_time": query_time,
            "params": params
        }
        
        self.query_history.append(query_record)
        
        # Keep only recent queries (last 1000)
        if len(self.query_history) > 1000:
            self.query_history = self.query_history[-1000:]
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics."""
        try:
            # Calculate graph metrics if not cached
            if self.graph.number_of_nodes() > 0:
                if self.stats.avg_degree == 0:
                    total_degree = sum(dict(self.graph.degree()).values())
                    self.stats.avg_degree = total_degree / self.graph.number_of_nodes()
                
                if self.stats.graph_density == 0:
                    self.stats.graph_density = nx.density(self.graph)
                
                if self.stats.clustering_coefficient == 0:
                    # Use undirected graph for clustering coefficient
                    undirected = self.graph.to_undirected()
                    self.stats.clustering_coefficient = nx.average_clustering(undirected)
            
            return {
                "structure": {
                    "total_nodes": self.stats.total_nodes,
                    "total_edges": self.stats.total_edges,
                    "avg_degree": f"{self.stats.avg_degree:.2f}",
                    "graph_density": f"{self.stats.graph_density:.4f}",
                    "clustering_coefficient": f"{self.stats.clustering_coefficient:.4f}",
                    "connected_components": self.stats.connected_components
                },
                "performance": {
                    "total_queries": self.stats.total_queries,
                    "total_query_time": f"{self.stats.query_time:.2f}s",
                    "avg_query_time": f"{self.stats.avg_query_time:.4f}s",
                    "graph_build_time": f"{self.stats.graph_build_time:.2f}s"
                },
                "caching": {
                    "cache_enabled": self.config.enable_caching,
                    "cache_size": self.cache.size if self.cache else 0,
                    "cache_hit_rate": f"{self.stats.cache_hit_rate:.1%}",
                    "cache_hits": self.stats.cache_hits,
                    "cache_misses": self.stats.cache_misses
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {}
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent query history."""
        return self.query_history[-limit:] if self.query_history else []
    
    def clear_cache(self):
        """Clear graph cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Graph cache cleared")
    
    def reset_stats(self):
        """Reset graph statistics."""
        self.stats = GraphStats()
        self.query_history.clear()
        self.analysis_cache.clear()
        logger.info("Graph statistics reset")


class CodeRelationshipExtractor:
    """Extract code relationships for graph construction."""
    
    def __init__(self, graph_engine: GraphIntelligenceEngine):
        self.graph_engine = graph_engine
        
        # Language-specific extractors
        self.extractors = {
            "python": self._extract_python_relationships,
            "javascript": self._extract_javascript_relationships,
            "typescript": self._extract_typescript_relationships,
            "java": self._extract_java_relationships,
            "cpp": self._extract_cpp_relationships,
            "c": self._extract_cpp_relationships,
        }
    
    async def extract_relationships(
        self,
        file_path: str,
        content: str,
        language: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract nodes and edges from source code."""
        
        extractor = self.extractors.get(language.lower())
        if extractor:
            return await extractor(file_path, content)
        else:
            # Generic extraction for unknown languages
            return await self._extract_generic_relationships(file_path, content, language)
    
    async def _extract_python_relationships(
        self,
        file_path: str,
        content: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract Python-specific relationships."""
        nodes = []
        edges = []
        
        try:
            import ast
            
            # Parse Python AST
            tree = ast.parse(content, filename=file_path)
            
            # Extract classes, functions, imports
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_node = GraphNode(
                        id=f"{file_path}:{node.name}:{node.lineno}",
                        node_type="function",
                        name=node.name,
                        content=ast.unparse(node) if hasattr(ast, 'unparse') else "",
                        file_path=file_path,
                        language="python",
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        metadata={
                            "args": [arg.arg for arg in node.args.args],
                            "decorators": [ast.unparse(dec) if hasattr(ast, 'unparse') else str(dec) for dec in node.decorator_list],
                            "is_async": isinstance(node, ast.AsyncFunctionDef)
                        }
                    )
                    nodes.append(func_node)
                
                elif isinstance(node, ast.ClassDef):
                    class_node = GraphNode(
                        id=f"{file_path}:{node.name}:{node.lineno}",
                        node_type="class",
                        name=node.name,
                        content=ast.unparse(node) if hasattr(ast, 'unparse') else "",
                        file_path=file_path,
                        language="python",
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        metadata={
                            "bases": [ast.unparse(base) if hasattr(ast, 'unparse') else str(base) for base in node.bases],
                            "decorators": [ast.unparse(dec) if hasattr(ast, 'unparse') else str(dec) for dec in node.decorator_list]
                        }
                    )
                    nodes.append(class_node)
                    
                    # Add inheritance relationships
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            edge = GraphEdge(
                                source_id=class_node.id,
                                target_id=f"class:{base.id}",  # Generic reference
                                relationship_type="inherits",
                                weight=1.0,
                                confidence=0.9
                            )
                            edges.append(edge)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Handle import relationships
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_node = GraphNode(
                                id=f"import:{alias.name}",
                                node_type="module",
                                name=alias.name,
                                file_path=file_path,
                                language="python",
                                line_start=node.lineno,
                                metadata={"import_type": "import"}
                            )
                            nodes.append(import_node)
                            
                            # Add dependency edge
                            file_node_id = f"file:{file_path}"
                            edge = GraphEdge(
                                source_id=file_node_id,
                                target_id=import_node.id,
                                relationship_type="imports",
                                weight=1.0,
                                confidence=1.0
                            )
                            edges.append(edge)
            
            return nodes, edges
            
        except Exception as e:
            logger.error(f"Error extracting Python relationships: {e}")
            return await self._extract_generic_relationships(file_path, content, "python")
    
    async def _extract_javascript_relationships(
        self,
        file_path: str,
        content: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract JavaScript-specific relationships."""
        # This is a simplified implementation
        # In production, you'd use a proper JavaScript AST parser
        nodes = []
        edges = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Extract function declarations
            if line.startswith('function ') or 'function(' in line:
                func_match = line.split('function')[1].split('(')[0].strip()
                if func_match:
                    func_node = GraphNode(
                        id=f"{file_path}:{func_match}:{i}",
                        node_type="function",
                        name=func_match,
                        content=line,
                        file_path=file_path,
                        language="javascript",
                        line_start=i,
                        metadata={"declaration_type": "function"}
                    )
                    nodes.append(func_node)
            
            # Extract class declarations
            elif line.startswith('class '):
                class_match = line.split('class')[1].split(' ')[1].split('{')[0].strip()
                if class_match:
                    class_node = GraphNode(
                        id=f"{file_path}:{class_match}:{i}",
                        node_type="class",
                        name=class_match,
                        content=line,
                        file_path=file_path,
                        language="javascript",
                        line_start=i,
                        metadata={"declaration_type": "class"}
                    )
                    nodes.append(class_node)
            
            # Extract imports/requires
            elif 'import ' in line or 'require(' in line:
                import_node = GraphNode(
                    id=f"{file_path}:import:{i}",
                    node_type="import",
                    name=line.split('from')[-1].strip().replace("'", "").replace('"', '') if 'from' in line else line,
                    content=line,
                    file_path=file_path,
                    language="javascript",
                    line_start=i,
                    metadata={"import_statement": line}
                )
                nodes.append(import_node)
        
        return nodes, edges
    
    async def _extract_typescript_relationships(
        self,
        file_path: str,
        content: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract TypeScript-specific relationships (similar to JavaScript)."""
        return await self._extract_javascript_relationships(file_path, content)
    
    async def _extract_java_relationships(
        self,
        file_path: str,
        content: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract Java-specific relationships."""
        # Simplified Java extraction
        nodes = []
        edges = []
        
        lines = content.split('\n')
        current_class = None
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Extract class declarations
            if line.startswith('public class ') or line.startswith('class '):
                class_match = line.split('class')[1].split(' ')[1].split('{')[0].strip()
                if class_match:
                    class_node = GraphNode(
                        id=f"{file_path}:{class_match}:{i}",
                        node_type="class",
                        name=class_match,
                        content=line,
                        file_path=file_path,
                        language="java",
                        line_start=i
                    )
                    nodes.append(class_node)
                    current_class = class_match
            
            # Extract method declarations
            elif ('public ' in line or 'private ' in line or 'protected ' in line) and '(' in line and ')' in line:
                method_parts = line.split('(')[0].split()
                if len(method_parts) >= 2:
                    method_name = method_parts[-1]
                    method_node = GraphNode(
                        id=f"{file_path}:{method_name}:{i}",
                        node_type="method",
                        name=method_name,
                        content=line,
                        file_path=file_path,
                        language="java",
                        line_start=i,
                        metadata={"class": current_class}
                    )
                    nodes.append(method_node)
                    
                    # Add contains relationship with class
                    if current_class:
                        edge = GraphEdge(
                            source_id=f"{file_path}:{current_class}",
                            target_id=method_node.id,
                            relationship_type="contains",
                            weight=1.0
                        )
                        edges.append(edge)
            
            # Extract imports
            elif line.startswith('import '):
                import_statement = line.replace('import ', '').replace(';', '').strip()
                import_node = GraphNode(
                    id=f"import:{import_statement}",
                    node_type="import",
                    name=import_statement,
                    content=line,
                    file_path=file_path,
                    language="java",
                    line_start=i
                )
                nodes.append(import_node)
        
        return nodes, edges
    
    async def _extract_cpp_relationships(
        self,
        file_path: str,
        content: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract C/C++-specific relationships."""
        # Simplified C++ extraction
        nodes = []
        edges = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Extract function declarations
            if (('(' in line and ')' in line and 
                 not line.startswith('//') and 
                 not line.startswith('/*') and
                 not line.startswith('#')) and
                ('int ' in line or 'void ' in line or 'double ' in line or 'float ' in line or 'char ' in line)):
                
                # Simple function extraction
                func_parts = line.split('(')[0].split()
                if len(func_parts) >= 2:
                    func_name = func_parts[-1]
                    func_node = GraphNode(
                        id=f"{file_path}:{func_name}:{i}",
                        node_type="function",
                        name=func_name,
                        content=line,
                        file_path=file_path,
                        language="cpp",
                        line_start=i
                    )
                    nodes.append(func_node)
            
            # Extract class declarations
            elif line.startswith('class ') and '{' in line:
                class_name = line.split('class')[1].split('{')[0].strip()
                if class_name:
                    class_node = GraphNode(
                        id=f"{file_path}:{class_name}:{i}",
                        node_type="class",
                        name=class_name,
                        content=line,
                        file_path=file_path,
                        language="cpp",
                        line_start=i
                    )
                    nodes.append(class_node)
            
            # Extract includes
            elif line.startswith('#include'):
                include_statement = line.replace('#include', '').strip().replace('<', '').replace('>', '').replace('"', '')
                include_node = GraphNode(
                    id=f"include:{include_statement}",
                    node_type="include",
                    name=include_statement,
                    content=line,
                    file_path=file_path,
                    language="cpp",
                    line_start=i
                )
                nodes.append(include_node)
        
        return nodes, edges
    
    async def _extract_generic_relationships(
        self,
        file_path: str,
        content: str,
        language: str
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Generic relationship extraction for unknown languages."""
        nodes = []
        edges = []
        
        # Create a file node
        file_node = GraphNode(
            id=f"file:{file_path}",
            node_type="file",
            name=os.path.basename(file_path),
            content=content[:1000],  # First 1000 chars
            file_path=file_path,
            language=language,
            metadata={"size": len(content), "lines": len(content.split('\n'))}
        )
        nodes.append(file_node)
        
        return nodes, edges
