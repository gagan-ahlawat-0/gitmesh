/**
 * Intelligent File Suggestions Hook
 * 
 * Provides intelligent file suggestions based on user queries and automatically
 * adds relevant files to the chat context.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRepository } from '@/contexts/RepositoryContext';
import { toast } from 'sonner';

export interface SuggestedFile {
  path: string;
  branch: string;
  relevance_score: number;
  reason: string;
  file_type: string;
  size_bytes: number;
  content_preview?: string;
  auto_add: boolean;
  last_modified?: string;
}

export interface SuggestionRequest {
  user_query: string;
  repository_name: string;
  branch?: string;
  session_id: string;
  conversation_history?: string[];
  current_files?: string[];
  max_suggestions?: number;
  auto_add_threshold?: number;
}

export interface SuggestionResponse {
  success: boolean;
  suggestions: SuggestedFile[];
  auto_added_files: string[];
  total_suggestions: number;
  processing_time_ms: number;
  message: string;
}

export interface SuggestionStats {
  total_suggestions: number;
  auto_added_files: number;
  user_accepted_suggestions: number;
  last_suggestion_time?: string;
  most_suggested_file_types: Record<string, number>;
  average_relevance_score: number;
}

interface UseIntelligentSuggestionsOptions {
  enableAutoSuggestions?: boolean;
  autoSuggestionDelay?: number; // ms to wait before triggering suggestions
  showNotifications?: boolean;
  maxAutoAddFiles?: number;
}

const DEFAULT_OPTIONS: UseIntelligentSuggestionsOptions = {
  enableAutoSuggestions: true,
  autoSuggestionDelay: 2000, // 2 seconds
  showNotifications: true,
  maxAutoAddFiles: 3
};

export function useIntelligentSuggestions(
  options: UseIntelligentSuggestionsOptions = {}
) {
  const { user } = useAuth();
  const { repository } = useRepository();
  const finalOptions = { ...DEFAULT_OPTIONS, ...options };
  
  // State
  const [suggestions, setSuggestions] = useState<SuggestedFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState<string>('');
  const [stats, setStats] = useState<SuggestionStats | null>(null);
  const [autoAddedFiles, setAutoAddedFiles] = useState<string[]>([]);
  
  // Refs for managing timeouts and preventing duplicate requests
  const suggestionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastRequestRef = useRef<string>('');
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Get file suggestions from the API
   */
  const getSuggestions = useCallback(async (
    request: SuggestionRequest
  ): Promise<SuggestionResponse | null> => {
    if (!user?.id) {
      console.warn('No user ID available for suggestions');
      return null;
    }

    // Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    try {
      setIsLoading(true);
      
      const response = await fetch('/api/v1/intelligent-suggestions/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...request,
          max_suggestions: request.max_suggestions || 10,
          auto_add_threshold: request.auto_add_threshold || 0.8
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`Suggestions request failed: ${response.status}`);
      }

      const result: SuggestionResponse = await response.json();
      
      if (result.success) {
        setSuggestions(result.suggestions);
        setAutoAddedFiles(result.auto_added_files);
        setLastQuery(request.user_query);
        
        // Show notification for auto-added files
        if (finalOptions.showNotifications && result.auto_added_files.length > 0) {
          toast.success(
            `Auto-added ${result.auto_added_files.length} relevant files`,
            {
              description: result.auto_added_files.join(', '),
              duration: 5000,
            }
          );
        }
        
        // Show notification for manual suggestions
        if (finalOptions.showNotifications && result.suggestions.length > result.auto_added_files.length) {
          const manualSuggestions = result.suggestions.length - result.auto_added_files.length;
          toast.info(
            `Found ${manualSuggestions} additional relevant files`,
            {
              description: 'Click the + button next to files to add them',
              duration: 3000,
            }
          );
        }
      }
      
      return result;

    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Suggestion request was cancelled');
        return null;
      }
      
      console.error('Error getting suggestions:', error);
      
      if (finalOptions.showNotifications) {
        toast.error('Failed to get file suggestions');
      }
      
      return null;
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [user?.id, finalOptions.showNotifications]);

  /**
   * Automatically trigger suggestions based on user query
   */
  const triggerAutoSuggestions = useCallback((
    query: string,
    sessionId: string,
    conversationHistory: string[] = [],
    currentFiles: string[] = []
  ) => {
    if (!finalOptions.enableAutoSuggestions || !repository?.name || !user?.id) {
      return;
    }

    // Clear existing timeout
    if (suggestionTimeoutRef.current) {
      clearTimeout(suggestionTimeoutRef.current);
    }

    // Don't trigger for very short queries or duplicate queries
    if (query.length < 10 || query === lastRequestRef.current) {
      return;
    }

    lastRequestRef.current = query;

    // Set timeout to trigger suggestions
    suggestionTimeoutRef.current = setTimeout(() => {
      const request: SuggestionRequest = {
        user_query: query,
        repository_name: repository.name,
        branch: repository.default_branch || 'main',
        session_id: sessionId,
        conversation_history: conversationHistory.slice(-5), // Last 5 messages
        current_files: currentFiles,
        max_suggestions: 8,
        auto_add_threshold: 0.75
      };

      getSuggestions(request);
    }, finalOptions.autoSuggestionDelay);
  }, [
    finalOptions.enableAutoSuggestions,
    finalOptions.autoSuggestionDelay,
    repository,
    user?.id,
    getSuggestions
  ]);

  /**
   * Submit feedback on suggestion quality
   */
  const submitFeedback = useCallback(async (
    filePath: string,
    accepted: boolean,
    relevanceScore: number,
    sessionId: string
  ): Promise<boolean> => {
    if (!user?.id) {
      return false;
    }

    try {
      const response = await fetch('/api/v1/intelligent-suggestions/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_path: filePath,
          accepted: accepted,
          relevance_score: relevanceScore,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`Feedback submission failed: ${response.status}`);
      }

      const result = await response.json();
      return result.success;

    } catch (error) {
      console.error('Error submitting feedback:', error);
      return false;
    }
  }, [user?.id]);

  /**
   * Get suggestion statistics
   */
  const getStats = useCallback(async (): Promise<SuggestionStats | null> => {
    if (!user?.id) {
      return null;
    }

    try {
      const response = await fetch('/api/v1/intelligent-suggestions/stats');
      
      if (!response.ok) {
        throw new Error(`Stats request failed: ${response.status}`);
      }

      const result: SuggestionStats = await response.json();
      setStats(result);
      return result;

    } catch (error) {
      console.error('Error getting suggestion stats:', error);
      return null;
    }
  }, [user?.id]);

  /**
   * Clear current suggestions
   */
  const clearSuggestions = useCallback(() => {
    setSuggestions([]);
    setAutoAddedFiles([]);
    setLastQuery('');
    
    // Cancel any pending requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Clear timeout
    if (suggestionTimeoutRef.current) {
      clearTimeout(suggestionTimeoutRef.current);
    }
  }, []);

  /**
   * Manual file exploration
   */
  const exploreRepository = useCallback(async (
    repositoryName: string,
    branch: string = 'main',
    filePattern: string = ''
  ) => {
    if (!user?.id) {
      return null;
    }

    try {
      setIsLoading(true);
      
      const params = new URLSearchParams({
        repository_name: repositoryName,
        branch: branch,
        file_pattern: filePattern
      });

      const response = await fetch(`/api/v1/intelligent-suggestions/manual-suggest?${params}`);
      
      if (!response.ok) {
        throw new Error(`Exploration request failed: ${response.status}`);
      }

      const result = await response.json();
      
      if (finalOptions.showNotifications && result.success) {
        toast.info(
          `Found ${result.total_files} files for exploration`,
          {
            description: `Organized by ${Object.keys(result.suggestions_by_type).length} file types`,
            duration: 4000,
          }
        );
      }
      
      return result;

    } catch (error) {
      console.error('Error exploring repository:', error);
      
      if (finalOptions.showNotifications) {
        toast.error('Failed to explore repository');
      }
      
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, finalOptions.showNotifications]);

  /**
   * Get file type icon/color
   */
  const getFileTypeInfo = useCallback((fileType: string) => {
    const typeInfo = {
      source_code: { icon: '📄', color: '#3b82f6', label: 'Source Code' },
      config: { icon: '⚙️', color: '#8b5cf6', label: 'Configuration' },
      documentation: { icon: '📚', color: '#10b981', label: 'Documentation' },
      test: { icon: '🧪', color: '#f59e0b', label: 'Test' },
      build: { icon: '🔨', color: '#ef4444', label: 'Build' },
      other: { icon: '📁', color: '#6b7280', label: 'Other' }
    };

    return typeInfo[fileType as keyof typeof typeInfo] || typeInfo.other;
  }, []);

  // Load stats on mount
  useEffect(() => {
    if (user?.id) {
      getStats();
    }
  }, [user?.id, getStats]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (suggestionTimeoutRef.current) {
        clearTimeout(suggestionTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    // State
    suggestions,
    isLoading,
    lastQuery,
    stats,
    autoAddedFiles,
    
    // Actions
    getSuggestions,
    triggerAutoSuggestions,
    submitFeedback,
    getStats,
    clearSuggestions,
    exploreRepository,
    
    // Utilities
    getFileTypeInfo,
    
    // Configuration
    options: finalOptions
  };
}

/**
 * Hook for managing suggestion UI state
 */
export function useSuggestionUI() {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState<SuggestedFile | null>(null);
  const [expandedSuggestions, setExpandedSuggestions] = useState<Set<string>>(new Set());

  const toggleSuggestion = useCallback((filePath: string) => {
    setExpandedSuggestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(filePath)) {
        newSet.delete(filePath);
      } else {
        newSet.add(filePath);
      }
      return newSet;
    });
  }, []);

  const selectSuggestion = useCallback((suggestion: SuggestedFile | null) => {
    setSelectedSuggestion(suggestion);
  }, []);

  return {
    showSuggestions,
    setShowSuggestions,
    selectedSuggestion,
    selectSuggestion,
    expandedSuggestions,
    toggleSuggestion
  };
}