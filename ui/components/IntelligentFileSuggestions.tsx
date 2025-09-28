/**
 * Intelligent File Suggestions Component
 * 
 * Displays intelligent file suggestions with auto-addition capabilities
 * and provides a UI for users to manually add suggested files.
 */

import React, { useState, useCallback } from 'react';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from '@/components/ui/tooltip';
import { 
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Plus,
  ChevronDown,
  ChevronRight,
  Sparkles,
  FileText,
  Settings,
  BookOpen,
  TestTube,
  Hammer,
  Folder,
  Zap,
  Clock,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { 
  useIntelligentSuggestions, 
  useSuggestionUI,
  SuggestedFile 
} from '@/hooks/useIntelligentSuggestions';
import { toast } from 'sonner';

interface IntelligentFileSuggestionsProps {
  sessionId: string;
  currentFiles: string[];
  onFileAdd: (filePath: string, branch: string) => void;
  className?: string;
}

const FileTypeIcon = ({ fileType }: { fileType: string }) => {
  const icons = {
    source_code: FileText,
    config: Settings,
    documentation: BookOpen,
    test: TestTube,
    build: Hammer,
    other: Folder
  };
  
  const Icon = icons[fileType as keyof typeof icons] || Folder;
  return <Icon className="w-4 h-4" />;
};

const RelevanceIndicator = ({ score }: { score: number }) => {
  const getColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    if (score >= 0.4) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getLabel = (score: number) => {
    if (score >= 0.8) return 'High';
    if (score >= 0.6) return 'Medium';
    if (score >= 0.4) return 'Low';
    return 'Very Low';
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        <div className={cn("w-2 h-2 rounded-full", getColor(score))} />
        <span className="text-xs text-muted-foreground">
          {getLabel(score)}
        </span>
      </div>
      <span className="text-xs font-mono text-muted-foreground">
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
};

const SuggestionCard = ({ 
  suggestion, 
  onAdd, 
  isExpanded, 
  onToggle,
  onFeedback 
}: {
  suggestion: SuggestedFile;
  onAdd: () => void;
  isExpanded: boolean;
  onToggle: () => void;
  onFeedback: (accepted: boolean) => void;
}) => {
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async () => {
    setIsAdding(true);
    try {
      await onAdd();
      onFeedback(true);
      toast.success(`Added ${suggestion.path.split('/').pop()} to context`);
    } catch (error) {
      toast.error('Failed to add file');
      onFeedback(false);
    } finally {
      setIsAdding(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <Card className={cn(
      "transition-all duration-200 hover:shadow-md",
      suggestion.auto_add && "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="flex items-center gap-2 mt-1">
              <FileTypeIcon fileType={suggestion.file_type} />
              {suggestion.auto_add && (
                <Zap className="w-3 h-3 text-green-600" />
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <CardTitle className="text-sm font-medium truncate">
                  {suggestion.path.split('/').pop()}
                </CardTitle>
                {suggestion.auto_add && (
                  <Badge variant="secondary" className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    Auto-added
                  </Badge>
                )}
              </div>
              
              <CardDescription className="text-xs truncate">
                {suggestion.path}
              </CardDescription>
              
              <div className="flex items-center gap-4 mt-2">
                <RelevanceIndicator score={suggestion.relevance_score} />
                <span className="text-xs text-muted-foreground">
                  {formatFileSize(suggestion.size_bytes)}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-1">
            {!suggestion.auto_add && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleAdd}
                      disabled={isAdding}
                      className="h-8 w-8 p-0"
                    >
                      <Plus className="w-3 h-3" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Add to context
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            
            <Collapsible open={isExpanded} onOpenChange={onToggle}>
              <CollapsibleTrigger asChild>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 w-8 p-0"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3" />
                  ) : (
                    <ChevronRight className="w-3 h-3" />
                  )}
                </Button>
              </CollapsibleTrigger>
            </Collapsible>
          </div>
        </div>
      </CardHeader>
      
      <Collapsible open={isExpanded} onOpenChange={onToggle}>
        <CollapsibleContent>
          <CardContent className="pt-0">
            <div className="space-y-3">
              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-1">
                  Why this file?
                </h4>
                <p className="text-sm">{suggestion.reason}</p>
              </div>
              
              {suggestion.content_preview && (
                <div>
                  <h4 className="text-xs font-medium text-muted-foreground mb-1">
                    Preview
                  </h4>
                  <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                    {suggestion.content_preview}
                  </pre>
                </div>
              )}
              
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Branch: {suggestion.branch}</span>
                {suggestion.last_modified && (
                  <span>Modified: {new Date(suggestion.last_modified).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

export const IntelligentFileSuggestions: React.FC<IntelligentFileSuggestionsProps> = ({
  sessionId,
  currentFiles,
  onFileAdd,
  className
}) => {
  const {
    suggestions,
    isLoading,
    autoAddedFiles,
    stats,
    submitFeedback,
    clearSuggestions
  } = useIntelligentSuggestions({
    enableAutoSuggestions: true,
    showNotifications: true,
    maxAutoAddFiles: 3
  });

  const {
    expandedSuggestions,
    toggleSuggestion
  } = useSuggestionUI();

  const handleFileAdd = useCallback(async (suggestion: SuggestedFile) => {
    try {
      await onFileAdd(suggestion.path, suggestion.branch);
    } catch (error) {
      throw error;
    }
  }, [onFileAdd]);

  const handleFeedback = useCallback(async (
    suggestion: SuggestedFile, 
    accepted: boolean
  ) => {
    await submitFeedback(
      suggestion.path,
      accepted,
      suggestion.relevance_score,
      sessionId
    );
  }, [submitFeedback, sessionId]);

  // Group suggestions by relevance
  const groupedSuggestions = {
    high: suggestions.filter(s => s.relevance_score >= 0.7),
    medium: suggestions.filter(s => s.relevance_score >= 0.4 && s.relevance_score < 0.7),
    low: suggestions.filter(s => s.relevance_score < 0.4)
  };

  if (!suggestions.length && !isLoading) {
    return null;
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Smart File Suggestions</h3>
          {isLoading && (
            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        
        {suggestions.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            onClick={clearSuggestions}
            className="text-xs"
          >
            Clear
          </Button>
        )}
      </div>

      {/* Auto-added files notification */}
      {autoAddedFiles.length > 0 && (
        <Card className="border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-green-800 dark:text-green-200">
                  Files automatically added
                </h4>
                <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                  {autoAddedFiles.length} highly relevant files were added to your context:
                </p>
                <ul className="text-sm text-green-700 dark:text-green-300 mt-2 space-y-1">
                  {autoAddedFiles.map(file => (
                    <li key={file} className="flex items-center gap-2">
                      <div className="w-1 h-1 bg-green-600 rounded-full" />
                      {file.split('/').pop()}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Statistics */}
      {stats && (
        <Card>
          <CardContent className="pt-4">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {stats.total_suggestions}
                </div>
                <div className="text-xs text-muted-foreground">
                  Total Suggestions
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {stats.auto_added_files}
                </div>
                <div className="text-xs text-muted-foreground">
                  Auto-added Files
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">
                  {(stats.average_relevance_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-muted-foreground">
                  Avg. Relevance
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* High relevance suggestions */}
      {groupedSuggestions.high.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-600" />
            <h4 className="text-sm font-medium">High Relevance</h4>
            <Badge variant="secondary" className="text-xs">
              {groupedSuggestions.high.length}
            </Badge>
          </div>
          
          <div className="space-y-2">
            {groupedSuggestions.high.map(suggestion => (
              <SuggestionCard
                key={suggestion.path}
                suggestion={suggestion}
                onAdd={() => handleFileAdd(suggestion)}
                isExpanded={expandedSuggestions.has(suggestion.path)}
                onToggle={() => toggleSuggestion(suggestion.path)}
                onFeedback={(accepted) => handleFeedback(suggestion, accepted)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Medium relevance suggestions */}
      {groupedSuggestions.medium.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-yellow-600" />
            <h4 className="text-sm font-medium">Medium Relevance</h4>
            <Badge variant="secondary" className="text-xs">
              {groupedSuggestions.medium.length}
            </Badge>
          </div>
          
          <div className="space-y-2">
            {groupedSuggestions.medium.map(suggestion => (
              <SuggestionCard
                key={suggestion.path}
                suggestion={suggestion}
                onAdd={() => handleFileAdd(suggestion)}
                isExpanded={expandedSuggestions.has(suggestion.path)}
                onToggle={() => toggleSuggestion(suggestion.path)}
                onFeedback={(accepted) => handleFeedback(suggestion, accepted)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Low relevance suggestions (collapsed by default) */}
      {groupedSuggestions.low.length > 0 && (
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between p-2 h-auto">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">Lower Relevance</span>
                <Badge variant="secondary" className="text-xs">
                  {groupedSuggestions.low.length}
                </Badge>
              </div>
              <ChevronDown className="w-4 h-4" />
            </Button>
          </CollapsibleTrigger>
          
          <CollapsibleContent className="space-y-2 mt-2">
            {groupedSuggestions.low.map(suggestion => (
              <SuggestionCard
                key={suggestion.path}
                suggestion={suggestion}
                onAdd={() => handleFileAdd(suggestion)}
                isExpanded={expandedSuggestions.has(suggestion.path)}
                onToggle={() => toggleSuggestion(suggestion.path)}
                onFeedback={(accepted) => handleFeedback(suggestion, accepted)}
              />
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Loading state */}
      {isLoading && suggestions.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-muted-foreground">
                Analyzing repository for relevant files...
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};