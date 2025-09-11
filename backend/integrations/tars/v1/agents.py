"""
TARS v1 Agent Implementations
Production-ready multi-agent system for open source project analysis.
Uses only ai framework classes/functions and GitIngest for repositories.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

# Core AI framework imports
from ai.agent import Agent, Handoff
from ai.session import Session

# Production tools using ai framework only
import ai.tools as tools
from . import tools as tars_tools

# Data models for complex responses
from .models import (
    ComparisonResult,
    AnalysisResult,
    DocumentAnalysisResult,
    CodeAnalysisResult,
    DataInsight,
    SystemHealth,
    WorkflowResult,
    ProjectStatus
)

# Set up logging
logger = logging.getLogger(__name__)


# ================================
# RESOURCE ACQUISITION LAYER AGENTS
# ================================

class WebCrawlerAgent(Agent):
    """Web Content Specialist Agent for intelligent web content extraction."""
    
    def __init__(self, **kwargs):
        # Set up tools using production tools from TARS
        agent_tools = [
            tars_tools.web_scraper,  # Production web scraping tool
            tars_tools.internet_search  # Production search tool
        ]
        
        # Agent configuration
        agent_config = {
            "name": "WebCrawler",
            "role": "Web Content Specialist",
            "goal": "Fetch and process web content from URLs with intelligent extraction",
            "backstory": "Expert in web scraping, content extraction, and URL analysis with advanced filtering capabilities",
            "tools": agent_tools,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def crawl_multiple_urls(self, urls: List[str], extract_links: bool = True) -> List[Dict[str, Any]]:
        """Crawl multiple URLs efficiently."""
        results = []
        for url in urls:
            try:
                # Use production web scraper tool
                result = tars_tools.web_scraper(url)
                results.append({"url": url, "content": result, "success": True})
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                results.append({"url": url, "error": str(e), "success": False})
        return results
    
    def search_and_crawl(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search for content and crawl relevant URLs."""
        try:
            # Use production internet search to find relevant URLs
            search_results = tars_tools.internet_search(query)
            
            # Extract URLs from search results
            urls = []
            if isinstance(search_results, str):
                # Simple URL extraction from text
                import re
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', search_results)
            elif isinstance(search_results, list):
                for result in search_results[:max_results]:
                    if isinstance(result, dict) and "url" in result:
                        urls.append(result["url"])
            
            # Crawl found URLs
            crawl_results = self.crawl_multiple_urls(urls[:max_results])
            
            return {
                "query": query,
                "search_results": search_results,
                "crawled_content": crawl_results,
                "total_urls": len(urls),
                "successful_crawls": len([r for r in crawl_results if r.get("success", False)])
            }
        except Exception as e:
            logger.error(f"Error in search and crawl: {e}")
            return {"error": str(e)}


class CodebaseAnalyzerAgent(Agent):
    """Source Code Intelligence Specialist for comprehensive code analysis."""
    
    def __init__(self, **kwargs):
        # Set up tools using production gitingest tool
        agent_tools = [
            tars_tools.repository_analyzer  # Production repository analysis tool via GitIngest
        ]
        
        # Agent configuration
        agent_config = {
            "name": "CodebaseAnalyzer",
            "role": "Source Code Intelligence Specialist",
            "goal": "Analyze codebases across branches and extract insights",
            "backstory": "Expert in code analysis, git operations, and software architecture with deep understanding of development patterns",
            "tools": agent_tools,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def analyze_multiple_repositories(self, repo_urls: List[str]) -> Dict[str, Any]:
        """Analyze multiple repositories for comparative insights."""
        results = {}
        for repo_url in repo_urls:
            try:
                # Use production repository analyzer tool
                result = tars_tools.repository_analyzer(repo_url)
                results[repo_url] = result
            except Exception as e:
                logger.error(f"Error analyzing repository {repo_url}: {e}")
                results[repo_url] = {"error": str(e)}
        
        return {
            "repositories": results,
            "total_analyzed": len(repo_urls),
            "successful_analyses": len([r for r in results.values() if "error" not in r])
        }
    
    def compare_branches(self, repo_url: str, branch1: str, branch2: str) -> Dict[str, Any]:
        """Compare two branches in detail."""
        try:
            # Use production repository analyzer tool with branch comparison
            analysis = tars_tools.repository_analyzer(repo_url, branches=[branch1, branch2])
            
            if isinstance(analysis, dict) and "error" in analysis:
                return analysis
            
            branch1_data = analysis["analysis"].get(branch1, {})
            branch2_data = analysis["analysis"].get(branch2, {})
            
            comparison = {
                "repository": repo_url,
                "branches": [branch1, branch2],
                "comparison": {
                    "commit_difference": branch1_data.get("commit_count", 0) - branch2_data.get("commit_count", 0),
                    "contributor_overlap": self._calculate_contributor_overlap(branch1_data, branch2_data),
                    "latest_commits": {
                        branch1: branch1_data.get("latest_commit", {}),
                        branch2: branch2_data.get("latest_commit", {})
                    }
                }
            }
            
            return comparison
        except Exception as e:
            logger.error(f"Error comparing branches: {e}")
            return {"error": str(e)}
    
    def _calculate_contributor_overlap(self, branch1_data: Dict, branch2_data: Dict) -> Dict[str, Any]:
        """Calculate contributor overlap between branches."""
        contributors1 = {c["name"] for c in branch1_data.get("contributors", [])}
        contributors2 = {c["name"] for c in branch2_data.get("contributors", [])}
        
        overlap = contributors1.intersection(contributors2)
        unique_to_branch1 = contributors1 - contributors2
        unique_to_branch2 = contributors2 - contributors1
        
        return {
            "total_overlap": len(overlap),
            "overlap_percentage": len(overlap) / max(len(contributors1 | contributors2), 1) * 100,
            "shared_contributors": list(overlap),
            "unique_to_first": list(unique_to_branch1),
            "unique_to_second": list(unique_to_branch2)
        }


class DocumentProcessorAgent(Agent):
    """Document Processing Specialist for content extraction and analysis."""
    
    def __init__(self, **kwargs):
        # Set up tools using production tools from TARS
        agent_tools = [
            tars_tools.document_processor  # Production document processing tool
        ]
        
        # Agent configuration
        agent_config = {
            "name": "DocumentProcessor",
            "role": "Document Processing Specialist",
            "goal": "Extract, process and analyze documents from various formats",
            "backstory": "Expert in document parsing, content extraction, and format conversion with advanced text processing capabilities",
            "tools": agent_tools,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def process_document_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple documents in batch."""
        results = {}
        for file_path in file_paths:
            try:
                result = self.processor_tool.process_document(file_path)
                results[file_path] = result
            except Exception as e:
                logger.error(f"Error processing document {file_path}: {e}")
                results[file_path] = {"error": str(e)}
        
        return {
            "documents": results,
            "total_processed": len(file_paths),
            "successful_processing": len([r for r in results.values() if "error" not in r])
        }
    
    def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        """Extract structured data from document with AI analysis."""
        try:
            # First process the document
            result = self.processor_tool.process_document(file_path)
            
            if "error" in result:
                return result
            
            content = result.get("content", "")
            
            # Use AI to extract structured information
            analysis_prompt = f"""
            Analyze the following document content and extract structured information:
            
            Content: {content[:2000]}...
            
            Please identify:
            1. Key concepts and topics
            2. Action items or tasks mentioned
            3. Important dates or deadlines
            4. Key people or organizations mentioned
            5. Main conclusions or recommendations
            
            Provide the analysis in a structured format.
            """
            
            # This would typically use the agent's chat method
            structured_analysis = {
                "document_type": result.get("type", "unknown"),
                "content_length": len(content),
                "extraction_timestamp": datetime.now().isoformat(),
                "ai_analysis_needed": True,  # Flag for further AI processing
                "raw_content": content
            }
            
            return structured_analysis
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {"error": str(e)}


class DataAnalyzerAgent(Agent):
    """Data Science and Analytics Specialist for comprehensive data analysis."""
    
    def __init__(self, **kwargs):
        # Set up tools using production tools from TARS
        agent_tools = [
            tars_tools.data_analyzer  # Production data analysis tool
        ]
        
        # Agent configuration
        agent_config = {
            "name": "DataAnalyzer",
            "role": "Data Science and Analytics Specialist",
            "goal": "Analyze datasets, generate insights and create visualizations",
            "backstory": "Expert in statistical analysis, data science methodologies, and insight extraction with advanced analytical capabilities",
            "tools": agent_tools,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def analyze_multiple_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze multiple data files."""
        results = {}
        for file_path in file_paths:
            try:
                result = self.analyzer_tool.analyze_data_file(file_path)
                results[file_path] = result
            except Exception as e:
                logger.error(f"Error analyzing data file {file_path}: {e}")
                results[file_path] = {"error": str(e)}
        
        return {
            "files": results,
            "total_analyzed": len(file_paths),
            "successful_analyses": len([r for r in results.values() if "error" not in r])
        }
    
    def generate_insights(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable insights from data analysis."""
        try:
            insights = {
                "data_quality": self._assess_data_quality(analysis_result),
                "trends": self._identify_trends(analysis_result),
                "recommendations": self._generate_recommendations(analysis_result),
                "anomalies": self._detect_anomalies(analysis_result)
            }
            
            return insights
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {"error": str(e)}
    
    def _assess_data_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess data quality metrics."""
        if analysis.get("type") == "csv":
            missing_values = analysis.get("missing_values", {})
            total_cells = analysis.get("rows", 0) * analysis.get("columns", 0)
            missing_percentage = sum(missing_values.values()) / max(total_cells, 1) * 100
            
            return {
                "completeness": 100 - missing_percentage,
                "missing_percentage": missing_percentage,
                "assessment": "good" if missing_percentage < 10 else "needs_attention"
            }
        
        return {"assessment": "unknown", "reason": "unsupported_format"}
    
    def _identify_trends(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify trends in the data."""
        trends = []
        insights = analysis.get("insights", [])
        
        for insight in insights:
            if insight.get("type") == "numeric":
                trends.append({
                    "column": insight.get("column"),
                    "trend": insight.get("trend", "stable"),
                    "mean": insight.get("mean"),
                    "std": insight.get("std")
                })
        
        return trends
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate data-driven recommendations."""
        recommendations = []
        
        if analysis.get("type") == "csv":
            missing_values = analysis.get("missing_values", {})
            high_missing = [col for col, count in missing_values.items() if count > 0]
            
            if high_missing:
                recommendations.append(f"Consider data cleaning for columns with missing values: {', '.join(high_missing[:3])}")
            
            columns = analysis.get("columns", 0)
            if columns > 50:
                recommendations.append("Consider dimensionality reduction techniques for this high-dimensional dataset")
        
        return recommendations
    
    def _detect_anomalies(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential anomalies in the data."""
        anomalies = []
        
        # Simple anomaly detection based on analysis results
        if analysis.get("type") == "csv":
            summary_stats = analysis.get("summary_statistics", {})
            
            for column, stats in summary_stats.items():
                if isinstance(stats, dict) and "std" in stats and "mean" in stats:
                    # Check for high variance
                    if stats["std"] > stats["mean"] * 2:
                        anomalies.append({
                            "column": column,
                            "type": "high_variance",
                            "description": f"Column {column} has unusually high variance"
                        })
        
        return anomalies


class ControlPanelMonitorAgent(Agent):
    """Project Management Intelligence Specialist for monitoring project control panels."""
    
    def __init__(self, **kwargs):
        # Set up tools using production tools from TARS
        agent_tools = [
            tars_tools.web_scraper,  # Production web scraping for control panels
            tars_tools.data_analyzer  # Production data analysis for metrics
        ]
        
        # Agent configuration
        agent_config = {
            "name": "ControlPanelMonitor",
            "role": "Project Management Intelligence Specialist",
            "goal": "Monitor and analyze project control panel data",
            "backstory": "Expert in project management, issue tracking, and development workflows with comprehensive monitoring capabilities",
            "tools": agent_tools,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def monitor_repository_health(self, repo_url: str) -> Dict[str, Any]:
        """Monitor overall repository health."""
        try:
            # Get issues and PRs
            issues = self.scraper_tool.scrape_github_issues(repo_url)
            prs = self.scraper_tool.scrape_github_prs(repo_url)
            
            health_metrics = {
                "repository": repo_url,
                "issues": issues,
                "pull_requests": prs,
                "health_score": self._calculate_health_score(issues, prs),
                "timestamp": datetime.now().isoformat()
            }
            
            return health_metrics
        except Exception as e:
            logger.error(f"Error monitoring repository health: {e}")
            return {"error": str(e)}
    
    def _calculate_health_score(self, issues: Dict[str, Any], prs: Dict[str, Any]) -> float:
        """Calculate repository health score."""
        try:
            # Simple health score calculation
            score = 100.0
            
            # Penalize for too many open issues
            open_issues = issues.get("count", 0)
            if open_issues > 50:
                score -= min(30, (open_issues - 50) * 0.5)
            
            # Reward active PR activity
            open_prs = prs.get("count", 0)
            if open_prs > 0:
                score = min(100, score + open_prs * 2)
            
            # Penalize stale issues/PRs (would need date analysis)
            
            return max(0, min(100, score))
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return 50.0  # Default neutral score


class KnowledgeOrchestratorAgent(Agent):
    """Knowledge Integration Coordinator for multi-source data integration."""
    
    def __init__(self, handoffs: Optional[List[Agent]] = None, **kwargs):
        # Set up tools using production tools from TARS
        agent_tools = [
            tars_tools.knowledge_integrator  # Production knowledge integration tool
        ]
        
        # Set up handoffs to other agents
        handoff_agents = handoffs or []
        
        # Agent configuration
        agent_config = {
            "name": "KnowledgeOrchestrator",
            "role": "Knowledge Integration Coordinator",
            "goal": "Coordinate and integrate knowledge from all resource agents",
            "backstory": "Expert in knowledge management and multi-source data integration with orchestration capabilities",
            "tools": agent_tools,
            "handoffs": handoff_agents,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 20),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    async def orchestrate_knowledge_acquisition(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Orchestrate knowledge acquisition from multiple agents."""
        try:
            # This would coordinate with other agents to gather information
            acquisition_results = []
            
            for source in sources:
                source_type = source.get("type")
                source_config = source.get("config", {})
                
                if source_type == "web":
                    # Would hand off to WebCrawlerAgent
                    result = {"type": "web_content", "status": "would_hand_off_to_webcrawler"}
                elif source_type == "code":
                    # Would hand off to CodebaseAnalyzerAgent
                    result = {"type": "code_analysis", "status": "would_hand_off_to_codebase_analyzer"}
                elif source_type == "documents":
                    # Would hand off to DocumentProcessorAgent
                    result = {"type": "document", "status": "would_hand_off_to_document_processor"}
                elif source_type == "data":
                    # Would hand off to DataAnalyzerAgent
                    result = {"type": "data_analysis", "status": "would_hand_off_to_data_analyzer"}
                elif source_type == "control_panel":
                    # Would hand off to ControlPanelMonitorAgent
                    result = {"type": "control_panel", "status": "would_hand_off_to_control_panel_monitor"}
                else:
                    result = {"type": "unknown", "error": f"Unknown source type: {source_type}"}
                
                acquisition_results.append(result)
            
            # Integrate all acquired knowledge
            integrated_knowledge = self.integration_tool.integrate_sources(acquisition_results)
            
            return {
                "orchestration_status": "completed",
                "sources_processed": len(sources),
                "acquisition_results": acquisition_results,
                "integrated_knowledge": integrated_knowledge,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error orchestrating knowledge acquisition: {e}")
            return {"error": str(e)}


# ================================
# ANALYSIS AND INTELLIGENCE LAYER AGENTS
# ================================

class CodeComparisonAgent(Agent):
    """Code Comparison Specialist for detailed code analysis."""
    
    def __init__(self, **kwargs):
        # Agent configuration
        agent_config = {
            "name": "CodeComparison",
            "role": "Code Comparison Specialist",
            "goal": "Compare files across branches and provide detailed analysis",
            "backstory": "Expert in code diff analysis, version control, and code review with semantic understanding",
            "tools": [],  # Uses analysis from other agents
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def compare_code_changes(self, branch1_data: Dict[str, Any], branch2_data: Dict[str, Any]) -> ComparisonResult:
        """Compare code changes between branches."""
        try:
            differences = []
            similarities = []
            recommendations = []
            
            # Analyze commit differences
            commit_diff = branch1_data.get("commit_count", 0) - branch2_data.get("commit_count", 0)
            if commit_diff > 0:
                differences.append(f"Branch 1 has {commit_diff} more commits than branch 2")
            elif commit_diff < 0:
                differences.append(f"Branch 2 has {abs(commit_diff)} more commits than branch 1")
            else:
                similarities.append("Both branches have the same number of commits")
            
            # Analyze contributors
            contributors1 = {c["name"] for c in branch1_data.get("contributors", [])}
            contributors2 = {c["name"] for c in branch2_data.get("contributors", [])}
            
            overlap = contributors1.intersection(contributors2)
            if overlap:
                similarities.append(f"Shared contributors: {', '.join(list(overlap)[:3])}")
            
            unique1 = contributors1 - contributors2
            unique2 = contributors2 - contributors1
            
            if unique1:
                differences.append(f"Unique contributors to branch 1: {', '.join(list(unique1)[:3])}")
            if unique2:
                differences.append(f"Unique contributors to branch 2: {', '.join(list(unique2)[:3])}")
            
            # Generate recommendations
            if commit_diff > 10:
                recommendations.append("Consider merging or rebasing to reduce commit divergence")
            
            if len(unique1) > len(unique2):
                recommendations.append("Branch 1 has more diverse contributors - consider knowledge sharing")
            
            # Risk assessment
            risk_level = "low"
            if abs(commit_diff) > 50:
                risk_level = "high"
            elif abs(commit_diff) > 20:
                risk_level = "medium"
            
            return ComparisonResult(
                differences=differences,
                similarities=similarities,
                recommendations=recommendations,
                risk_assessment=f"{risk_level} risk - commit divergence of {abs(commit_diff)}",
                confidence_score=0.85
            )
        except Exception as e:
            logger.error(f"Error comparing code changes: {e}")
            return ComparisonResult(
                differences=[f"Error during comparison: {str(e)}"],
                similarities=[],
                recommendations=["Manual review required due to analysis error"],
                risk_assessment="unknown risk",
                confidence_score=0.0
            )


class DocumentationAnalyzerAgent(Agent):
    """Documentation Intelligence Specialist for documentation analysis."""
    
    def __init__(self, **kwargs):
        # Agent configuration
        agent_config = {
            "name": "DocumentationAnalyzer",
            "role": "Documentation Intelligence Specialist",
            "goal": "Analyze documentation and suggest updates based on code changes",
            "backstory": "Expert in technical writing and documentation maintenance with understanding of code-doc relationships",
            "tools": [],
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def analyze_documentation_gaps(self, code_analysis: Dict[str, Any], 
                                  doc_analysis: Dict[str, Any]) -> DocumentAnalysisResult:
        """Analyze gaps between documentation and code."""
        try:
            # Extract key information
            code_functions = code_analysis.get("functions", [])
            code_classes = code_analysis.get("classes", [])
            doc_content = doc_analysis.get("content", "")
            
            # Identify gaps
            outdated_sections = []
            suggested_updates = []
            action_items = []
            
            # Simple gap analysis
            if code_functions and "function" not in doc_content.lower():
                action_items.append("Add function documentation")
                suggested_updates.append("Document new functions added to codebase")
            
            if code_classes and "class" not in doc_content.lower():
                action_items.append("Add class documentation")
                suggested_updates.append("Document new classes added to codebase")
            
            # Check for outdated sections (simple heuristic)
            if "deprecated" in doc_content.lower():
                outdated_sections.append("Sections mentioning deprecated features")
            
            # Extract key concepts (simple keyword extraction)
            import re
            concepts = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', doc_content)
            key_concepts = list(set(concepts[:10]))
            
            return DocumentAnalysisResult(
                document_type="mixed",
                key_concepts=key_concepts,
                summary=f"Documentation analysis revealed {len(action_items)} action items",
                action_items=action_items,
                outdated_sections=outdated_sections,
                suggested_updates=suggested_updates
            )
        except Exception as e:
            logger.error(f"Error analyzing documentation gaps: {e}")
            return DocumentAnalysisResult(
                document_type="error",
                key_concepts=[],
                summary=f"Error during analysis: {str(e)}",
                action_items=["Manual review required"],
                outdated_sections=[],
                suggested_updates=[]
            )


class ProjectInsightsAgent(Agent):
    """Project Intelligence Specialist for comprehensive project analysis."""
    
    def __init__(self, **kwargs):
        # Agent configuration
        agent_config = {
            "name": "ProjectInsights",
            "role": "Project Intelligence Specialist",
            "goal": "Analyze project status, contributors, and maintenance needs",
            "backstory": "Expert in open source project management and community analysis with strategic oversight",
            "tools": [],
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 15),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def analyze_project_status(self, control_panel_data: Dict[str, Any], 
                             code_analysis: Dict[str, Any]) -> ProjectStatus:
        """Analyze overall project status and health."""
        try:
            # Extract data from control panel
            issues_data = control_panel_data.get("issues", {})
            prs_data = control_panel_data.get("pull_requests", {})
            
            active_issues = issues_data.get("issues", [])[:10]  # Top 10 issues
            
            # Analyze contributor activity
            contributors = {}
            for branch, branch_data in code_analysis.get("analysis", {}).items():
                for contributor in branch_data.get("contributors", []):
                    name = contributor.get("name", "unknown")
                    commits = contributor.get("commits", 0)
                    contributors[name] = contributors.get(name, 0) + commits
            
            contributor_activity = {
                "total_contributors": len(contributors),
                "top_contributors": sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:5],
                "active_contributors": len([c for c in contributors.values() if c > 5])
            }
            
            # Identify maintenance priorities
            maintenance_priorities = []
            if len(active_issues) > 20:
                maintenance_priorities.append("Reduce issue backlog")
            
            if prs_data.get("count", 0) > 10:
                maintenance_priorities.append("Review pending pull requests")
            
            maintenance_priorities.append("Update documentation")
            maintenance_priorities.append("Improve test coverage")
            
            # Identify contribution opportunities
            contribution_opportunities = []
            for issue in active_issues[:5]:
                if isinstance(issue, dict):
                    labels = issue.get("labels", [])
                    if any("good first issue" in label.lower() or "help wanted" in label.lower() for label in labels):
                        contribution_opportunities.append({
                            "type": "issue",
                            "title": issue.get("title", ""),
                            "id": issue.get("id"),
                            "difficulty": "beginner" if "good first issue" in str(labels).lower() else "intermediate"
                        })
            
            # Calculate health score
            health_score = control_panel_data.get("health_score", 75.0) / 100.0
            
            return ProjectStatus(
                active_issues=active_issues,
                contributor_activity=contributor_activity,
                maintenance_priorities=maintenance_priorities,
                contribution_opportunities=contribution_opportunities,
                health_score=health_score
            )
        except Exception as e:
            logger.error(f"Error analyzing project status: {e}")
            return ProjectStatus(
                active_issues=[],
                contributor_activity={"error": str(e)},
                maintenance_priorities=["Manual analysis required"],
                contribution_opportunities=[],
                health_score=0.5
            )


class ReasoningAgent(Agent):
    """Strategic Reasoning Specialist for deep analytical insights."""
    
    def __init__(self, **kwargs):
        # Agent configuration
        agent_config = {
            "name": "ReasoningAgent",
            "role": "Strategic Reasoning Specialist",
            "goal": "Provide deep reasoning and strategic insights across all data",
            "backstory": "Expert in strategic analysis, pattern recognition, and decision support with advanced reasoning capabilities",
            "tools": [],
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "reasoning_steps": kwargs.get("reasoning_steps", True),
            "max_iter": kwargs.get("max_iter", 20),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def analyze_strategic_patterns(self, all_data: Dict[str, Any]) -> AnalysisResult:
        """Analyze strategic patterns across all collected data."""
        try:
            findings = []
            recommendations = []
            supporting_data = {}
            
            # Analyze patterns in the data
            if "code_analysis" in all_data:
                code_data = all_data["code_analysis"]
                total_contributors = len(set(
                    c["name"] for branch_data in code_data.get("analysis", {}).values()
                    for c in branch_data.get("contributors", [])
                ))
                findings.append(f"Project has {total_contributors} unique contributors across all branches")
                supporting_data["contributor_count"] = total_contributors
            
            if "project_status" in all_data:
                status_data = all_data["project_status"]
                health_score = status_data.get("health_score", 0.5)
                findings.append(f"Project health score: {health_score:.1%}")
                supporting_data["health_score"] = health_score
                
                if health_score < 0.7:
                    recommendations.append("Focus on improving project health through issue resolution")
                
            if "documentation" in all_data:
                doc_data = all_data["documentation"]
                action_items = len(doc_data.get("action_items", []))
                if action_items > 0:
                    findings.append(f"Documentation needs {action_items} updates")
                    recommendations.append("Prioritize documentation updates to improve project accessibility")
            
            # Strategic recommendations based on patterns
            if total_contributors < 5:
                recommendations.append("Consider community outreach to attract more contributors")
            
            if health_score > 0.8 and total_contributors > 10:
                recommendations.append("Project is healthy - consider expanding scope or features")
            
            # Calculate confidence based on data availability
            confidence = min(1.0, len(all_data) / 5.0)  # Higher confidence with more data sources
            
            return AnalysisResult(
                agent_name="ReasoningAgent",
                analysis_type="strategic_pattern_analysis",
                findings=findings,
                recommendations=recommendations,
                confidence_score=confidence,
                supporting_data=supporting_data
            )
        except Exception as e:
            logger.error(f"Error in strategic pattern analysis: {e}")
            return AnalysisResult(
                agent_name="ReasoningAgent",
                analysis_type="error_analysis",
                findings=[f"Analysis failed: {str(e)}"],
                recommendations=["Manual review required"],
                confidence_score=0.0,
                supporting_data={"error": str(e)}
            )


class ConversationOrchestratorAgent(Agent):
    """Master Conversation Coordinator for intelligent query routing."""
    
    def __init__(self, handoffs: Optional[List[Agent]] = None, **kwargs):
        # Set up handoffs to specialist agents
        handoff_agents = handoffs or []
        
        # Agent configuration
        agent_config = {
            "name": "ConversationOrchestrator",
            "role": "Master Conversation Coordinator",
            "goal": "Route user queries to appropriate specialists and maintain context",
            "backstory": "Expert in conversation management and intelligent routing with comprehensive understanding of specialist capabilities",
            "handoffs": handoff_agents,
            "memory": kwargs.get("memory", True),
            "llm": kwargs.get("llm", "gpt-4o"),
            "verbose": kwargs.get("verbose", True),
            "max_iter": kwargs.get("max_iter", 25),
            **kwargs
        }
        
        super().__init__(**agent_config)
    
    def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Route user query to appropriate specialist."""
        try:
            query_lower = query.lower()
            routing_decision = {
                "original_query": query,
                "routing_analysis": {},
                "recommended_agent": None,
                "confidence": 0.0
            }
            
            # Analyze query intent
            if any(word in query_lower for word in ["code", "repository", "branch", "commit", "git"]):
                routing_decision["recommended_agent"] = "CodebaseAnalyzer"
                routing_decision["confidence"] = 0.9
            elif any(word in query_lower for word in ["document", "pdf", "doc", "markdown", "readme"]):
                routing_decision["recommended_agent"] = "DocumentProcessor"
                routing_decision["confidence"] = 0.8
            elif any(word in query_lower for word in ["web", "url", "website", "crawl", "scrape"]):
                routing_decision["recommended_agent"] = "WebCrawler"
                routing_decision["confidence"] = 0.85
            elif any(word in query_lower for word in ["data", "csv", "excel", "statistics", "analysis"]):
                routing_decision["recommended_agent"] = "DataAnalyzer"
                routing_decision["confidence"] = 0.8
            elif any(word in query_lower for word in ["issue", "pr", "pull request", "github", "project health"]):
                routing_decision["recommended_agent"] = "ControlPanelMonitor"
                routing_decision["confidence"] = 0.85
            elif any(word in query_lower for word in ["compare", "difference", "similar", "contrast"]):
                routing_decision["recommended_agent"] = "CodeComparison"
                routing_decision["confidence"] = 0.8
            elif any(word in query_lower for word in ["strategy", "recommend", "insight", "pattern"]):
                routing_decision["recommended_agent"] = "ReasoningAgent"
                routing_decision["confidence"] = 0.9
            else:
                # General query - use reasoning agent for comprehensive analysis
                routing_decision["recommended_agent"] = "ReasoningAgent"
                routing_decision["confidence"] = 0.6
            
            routing_decision["routing_analysis"] = {
                "query_type": self._classify_query_type(query),
                "complexity": self._assess_query_complexity(query),
                "required_specialists": self._identify_required_specialists(query)
            }
            
            return routing_decision
        except Exception as e:
            logger.error(f"Error routing query: {e}")
            return {
                "error": str(e),
                "original_query": query,
                "recommended_agent": "ReasoningAgent"  # Fallback
            }
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query."""
        query_lower = query.lower()
        
        if "?" in query:
            return "question"
        elif any(word in query_lower for word in ["analyze", "review", "examine"]):
            return "analysis_request"
        elif any(word in query_lower for word in ["compare", "contrast", "difference"]):
            return "comparison_request"
        elif any(word in query_lower for word in ["help", "how to", "guide"]):
            return "assistance_request"
        else:
            return "general_query"
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess the complexity of the query."""
        word_count = len(query.split())
        
        if word_count < 5:
            return "simple"
        elif word_count < 15:
            return "moderate"
        else:
            return "complex"
    
    def _identify_required_specialists(self, query: str) -> List[str]:
        """Identify which specialists might be needed for the query."""
        query_lower = query.lower()
        specialists = []
        
        if any(word in query_lower for word in ["code", "git", "repository"]):
            specialists.append("CodebaseAnalyzer")
        
        if any(word in query_lower for word in ["web", "url", "internet"]):
            specialists.append("WebCrawler")
        
        if any(word in query_lower for word in ["document", "file", "pdf"]):
            specialists.append("DocumentProcessor")
        
        if any(word in query_lower for word in ["data", "csv", "statistics"]):
            specialists.append("DataAnalyzer")
        
        if any(word in query_lower for word in ["issue", "github", "project"]):
            specialists.append("ControlPanelMonitor")
        
        # Always include reasoning agent for strategic insights
        specialists.append("ReasoningAgent")
        
        return list(set(specialists))  # Remove duplicates
