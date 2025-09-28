"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { useRepository } from '@/contexts/RepositoryContext';
import { useChat } from '@/contexts/ChatContext';
import { useBranch } from '@/contexts/BranchContext';
import { RateLimitError } from '@/lib/chat-api';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { RealTimeStatusIndicator } from './RealTimeStatusIndicator';
import {
  Send,
  Bot,
  User,
  Loader2,
  AlertCircle,
  CheckCircle,
  Copy,
  Clock,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { ModelSelector } from './ModelSelector';
import { RepositorySelector } from './RepositorySelector';
import { ContextPanel } from './ContextPanel';
import { RepositorySizeErrorDialog } from './RepositorySizeErrorDialog';
// Removed problematic imports that don't exist
import { ChatMessage } from '@/lib/chat-api';
import { useIntelligentSuggestions } from '@/hooks/useIntelligentSuggestions';
import { FileRequestPanel, FileRequest } from './FileRequestPanel';

interface ChatInterfaceProps {
  className?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ className }) => {
  const { user, isAuthenticated, token } = useAuth();
  const { repository } = useRepository();
  const { selectedBranch } = useBranch();
  const {
    state,
    getActiveSession,
    sendMessageWithRetry,
    createSession,
    getMessageStatus,
    setRepositorySizeError
  } = useChat();

  // Local state
  const [message, setMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [isExpanded, setIsExpanded] = useState(false);
  const [showContextPanel, setShowContextPanel] = useState(true);
  const [showMetrics, setShowMetrics] = useState(false);
  const [fileRequests, setFileRequests] = useState<FileRequest[]>([]);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Get active session
  const activeSession = getActiveSession();

  // Intelligent suggestions hook
  const { triggerAutoSuggestions } = useIntelligentSuggestions({
    enableAutoSuggestions: true,
    showNotifications: true,
    maxAutoAddFiles: 3
  });

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [activeSession?.messages, scrollToBottom]);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [message, adjustTextareaHeight]);

  // Fetch file requests for the active session
  const fetchFileRequests = useCallback(async () => {
    if (!activeSession?.id || !isAuthenticated || !token) return;

    try {
      const response = await fetch(`/api/v1/file-requests/session/${activeSession.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const requests = await response.json();
        setFileRequests(requests);
      } else {
        console.warn('Failed to fetch file requests:', response.statusText);
      }
    } catch (error) {
      console.warn('Error fetching file requests:', error);
    }
  }, [activeSession?.id, isAuthenticated, token]);

  // Fetch file requests when session changes
  useEffect(() => {
    fetchFileRequests();
  }, [fetchFileRequests]);

  // Removed problematic functions that depend on missing components

  // Handle file request approval
  const handleApproveFile = useCallback(async (filePath: string, branch: string = 'main') => {
    if (!repository?.name || !activeSession?.id || !token) {
      toast.error('No repository, session, or authentication token available');
      return;
    }

    try {
      const response = await fetch('/api/v1/file-requests/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          file_path: filePath,
          repository_name: repository.name,
          branch: branch,
          session_id: activeSession.id
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to approve file: ${response.status}`);
      }

      const result = await response.json().catch(() => null);

      if (result && result.success) {
        // Remove the approved file from the requests list
        setFileRequests(prev => prev.filter(req => req.path !== filePath));

        // Refresh file requests from API to ensure consistency
        await fetchFileRequests();

        // File approved and added to context
        toast.success(`Added ${filePath} to context`);
      } else {
        const errorMessage = result?.error || 'Failed to approve file - invalid response';
        throw new Error(errorMessage);
      }

    } catch (error: any) {
      console.warn('Error approving file:', error);
      throw error;
    }
  }, [repository?.name, activeSession?.id, token, fetchFileRequests]);

  // Handle file request rejection
  const handleRejectFile = useCallback(async (filePath: string) => {
    if (!activeSession?.id || !token) {
      return;
    }

    try {
      const response = await fetch('/api/v1/file-requests/reject', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          file_path: filePath,
          session_id: activeSession.id,
          reason: 'User rejected'
        })
      });

      if (response.ok) {
        // Remove the rejected file from the requests list
        setFileRequests(prev => prev.filter(req => req.path !== filePath));

        // Refresh file requests from API to ensure consistency
        await fetchFileRequests();

        toast.success(`Rejected ${filePath}`);
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.error || `Failed to reject file: ${response.status}`;
        toast.error(errorMessage);
      }

    } catch (error) {
      console.warn('Error rejecting file:', error);
    }
  }, [activeSession?.id, token, fetchFileRequests]);

  // Handle message submission
  const handleSendMessage = useCallback(async () => {
    if (!message.trim() || !activeSession || state.loadingStates.chat) {
      return;
    }

    if (!isAuthenticated) {
      toast.error('Please sign in to send messages');
      return;
    }

    const messageText = message.trim();
    setMessage('');

    try {
      const response = await sendMessageWithRetry(activeSession.id, messageText, 3, {
        model: selectedModel,
        context: {
          files: state.selectedFiles
        }
      });

      // Check if the AI response contains file requests
      const assistantMessage = response?.assistantMessage || response;
      const metadata = assistantMessage?.metadata || response?.metadata;

      if (metadata?.requested_files && metadata.requested_files.length > 0) {
        const requests: FileRequest[] = metadata.requested_files.map((req: any) => ({
          path: req.path,
          reason: req.reason,
          branch: req.branch || 'main',
          auto_add: req.auto_add || false,
          pattern_matched: req.pattern_matched,
          metadata: req
        }));

        setFileRequests(prev => [...prev, ...requests]);

        // Show notification
        toast.info(`AI requested ${requests.length} file(s)`, {
          description: 'Check below the AI response for approval buttons',
          duration: 5000
        });
      } else if (metadata?.interactive_elements && metadata.interactive_elements.length > 0) {
        // Convert interactive elements to file requests if they are file_request type
        const fileRequestElements = metadata.interactive_elements.filter((elem: any) => elem.element_type === 'file_request');
        if (fileRequestElements.length > 0) {
          const requests: FileRequest[] = fileRequestElements.map((elem: any) => ({
            path: elem.value || elem.metadata?.file_path,
            reason: elem.metadata?.reason || elem.label,
            branch: elem.metadata?.branch || 'main',
            auto_add: elem.metadata?.auto_add || false,
            pattern_matched: elem.metadata?.pattern_matched,
            metadata: elem.metadata
          }));

          setFileRequests(prev => [...prev, ...requests]);

          // Show notification
          toast.info(`AI requested ${requests.length} file(s)`, {
            description: 'Check below the AI response for approval buttons',
            duration: 5000
          });
        }
      }

      // Trigger intelligent file suggestions based on the user's message
      if (repository?.name && activeSession?.id) {
        const conversationHistory = activeSession.messages
          .slice(-5) // Last 5 messages
          .map(msg => msg.content);

        const currentFiles = state.selectedFiles.map(f => f.path);

        triggerAutoSuggestions(
          messageText,
          activeSession.id,
          conversationHistory,
          currentFiles
        );
      }
    } catch (error: any) {
      console.warn('Failed to send message:', error);

      // Handle rate limit errors specifically
      if (error instanceof RateLimitError || error?.name === 'RateLimitError' || error?.message?.includes('Rate limit exceeded')) {
        // Rate limit error is already handled by the ChatAPI and events are emitted
        // Just show a user-friendly message
        toast.error('Rate limit exceeded. Please wait before sending another message.');
        console.warn('Rate limit error handled gracefully in ChatInterface');
        return; // Don't re-throw the error
      }

      // Handle authentication errors
      if (error?.message?.includes('No authentication token')) {
        toast.error('Please log in to send messages.');
        return;
      }

      // Handle network errors
      if (error?.message?.includes('fetch') || error?.message?.includes('Network')) {
        toast.error('Network error. Please check your connection and try again.');
        return;
      }

      // Handle other errors
      const errorMessage = error?.message || 'Unknown error occurred';
      toast.error(`Failed to send message: ${errorMessage}`);

      // Don't re-throw the error to prevent unhandled runtime errors
      console.warn('Message sending failed, but error was handled gracefully');
    }
  }, [message, activeSession, state.loadingStates.chat, state.selectedFiles, isAuthenticated, sendMessageWithRetry, selectedModel, repository?.name, triggerAutoSuggestions]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // Copy message content
  const handleCopyMessage = useCallback((content: string) => {
    navigator.clipboard.writeText(content);
    toast.success('Message copied to clipboard');
  }, []);

  // Create initial session if none exists
  useEffect(() => {
    if (!activeSession && repository && isAuthenticated && !state.loadingStates.sessions) {
      createSession(`Chat with ${repository.name}`);
    }
  }, [activeSession, repository, isAuthenticated, state.loadingStates.sessions, createSession]);

  if (!isAuthenticated) {
    return (
      <div className={cn("flex items-center justify-center h-full", className)}>
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
            <Bot size={24} className="text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-2">Sign in to start chatting</h3>
            <p className="text-muted-foreground">
              Connect your GitHub account to chat with your repositories
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!repository) {
    return (
      <div className={cn("flex items-center justify-center h-full", className)}>
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
            <FileText size={24} className="text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-2">Select a repository</h3>
            <p className="text-muted-foreground">
              Choose a repository to start chatting with your codebase
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex h-full bg-background", className)}>
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-card/50">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Bot size={20} className="text-primary" />
              <h2 className="font-semibold">
                {activeSession?.title || 'New Chat'}
              </h2>
            </div>
            {activeSession && activeSession.messages && (
              <Badge variant="outline" className="text-xs">
                {activeSession.messages.length} messages
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Model Selector */}
            {/* <ModelSelector
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
            /> */}

            {/* Repository Selector */}
            <RepositorySelector />

            <Separator orientation="vertical" className="h-6" />

            {/* Metrics toggle removed - component doesn't exist */}

            {/* Context Panel Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowContextPanel(!showContextPanel)}
              className="flex items-center gap-2"
            >
              {showContextPanel ? (
                <span className="text-lg font-bold">&gt;</span>
              ) : (
                <span className="text-lg font-bold">&lt;</span>
              )}
            </Button>
          </div>
        </div>

        {/* Messages Area */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-6 max-w-4xl mx-auto">
            {/* File Request Panel moved to individual messages */}

            {/* Performance metrics components removed - don't exist */}
            {!activeSession?.messages || activeSession.messages.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Bot size={24} className="text-primary" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
                <p className="text-muted-foreground mb-4">
                  Ask questions about your code, request explanations, or get help with development tasks.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setMessage("Explain the main functionality of this repository")}
                  >
                    Explain this repo
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setMessage("What are the main components and their relationships?")}
                  >
                    Show architecture
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setMessage("Help me understand the codebase structure")}
                  >
                    Code structure
                  </Button>
                </div>
              </div>
            ) : (
              <AnimatePresence>
                {activeSession.messages.map((msg) => (
                  <div key={msg.id}>
                    <ChatMessageComponent
                      message={msg}
                      onCopy={handleCopyMessage}
                      messageStatus={getMessageStatus(msg.id)}
                    />

                    {/* Show file request panel after assistant messages that have file requests */}
                    {msg.type === 'assistant' && msg.metadata?.requested_files && msg.metadata.requested_files.length > 0 && (
                      <div className="mt-4">
                        <FileRequestPanel
                          fileRequests={msg.metadata.requested_files.map((req: any) => ({
                            id: `${msg.id}_${req.path}`,
                            path: req.path,
                            reason: req.reason,
                            branch: req.branch || 'main',
                            auto_add: req.auto_add || false,
                            metadata: req.metadata || {}
                          }))}
                          repositoryName={repository?.name || 'unknown'}
                          onApproveFile={handleApproveFile}
                          onRejectFile={handleRejectFile}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </AnimatePresence>
            )}

            {/* Loading indicator */}
            {state.loadingStates.chat && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-3"
              >
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                  <Bot size={16} />
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <RealTimeStatusIndicator
                    sessionId={activeSession?.id}
                    userId={user?.id}
                    className="flex items-center gap-2"
                  />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>



        {/* Message Input */}
        <div className="p-4 border-t border-border bg-card/50">
          <div className="max-w-4xl mx-auto">
            {/* Context Files Preview */}
            {state.selectedFiles.length > 0 && (
              <div className="mb-3 p-2 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <FileText size={14} />
                  <span>Context files ({state.selectedFiles.length})</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {state.selectedFiles.slice(0, 3).map((file, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {file.path.split('/').pop()}
                    </Badge>
                  ))}
                  {state.selectedFiles.length > 3 && (
                    <Badge variant="secondary" className="text-xs">
                      +{state.selectedFiles.length - 3} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Textarea
                  ref={textareaRef}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    state.selectedFiles.length > 0
                      ? "Ask about your selected files..."
                      : "Ask about your repository..."
                  }
                  className="min-h-[44px] max-h-[120px] resize-none pr-12"
                  disabled={state.loadingStates.chat}
                />
                <div className="absolute right-2 bottom-2 text-xs text-muted-foreground">
                  {message.length}/4000
                </div>
              </div>
              <Button
                onClick={handleSendMessage}
                disabled={!message.trim() || state.loadingStates.chat}
                size="sm"
                className="h-[44px] px-4"
              >
                {state.loadingStates.chat ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </Button>
            </div>

            <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <div className="flex items-center gap-4">
                <span>Press Enter to send, Shift+Enter for new line</span>
                {selectedModel && (
                  <span>Model: {selectedModel}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {repository && (
                  <span>{repository.name}/{selectedBranch}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Context Panel */}
      {showContextPanel && (
        <div className="w-80 border-l border-border bg-card/30">
          <ContextPanel />
        </div>
      )}

      {/* Repository Size Error Dialog */}
      <RepositorySizeErrorDialog
        isOpen={!!state.repositorySizeError}
        onClose={() => setRepositorySizeError(null)}
        repositoryName={state.repositorySizeError?.repositoryName}
        repositorySize={state.repositorySizeError?.repositorySize}
        maxSize={state.repositorySizeError?.maxSize}
        onUpgrade={() => {
          // Handle upgrade logic here
          window.open('/pricing', '_blank');
        }}
      />
    </div>
  );
};

// Chat Message Component
interface ChatMessageComponentProps {
  message: ChatMessage;
  onCopy: (content: string) => void;
  messageStatus?: {
    id: string;
    status: 'sending' | 'sent' | 'failed' | 'retrying';
    retryCount: number;
    error?: string;
  } | null;
}

const ChatMessageComponent: React.FC<ChatMessageComponentProps> = ({
  message,
  onCopy,
  messageStatus
}) => {
  const isUser = message.type === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex gap-4",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div className={cn(
        "flex gap-3 max-w-[80%] min-w-0",
        isUser && "flex-row-reverse"
      )}>
        {/* Avatar */}
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        )}>
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>

        {/* Message Content */}
        <div className={cn(
          "rounded-lg p-4 relative group min-w-0 break-words overflow-hidden",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}>
          {/* Message Header */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">
                {isUser ? 'You' : 'Assistant'}
              </span>
              {message.model && (
                <Badge
                  variant={isUser ? "secondary" : "outline"}
                  className="text-xs px-1 py-0 h-4"
                >
                  {message.model}
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs opacity-70">
              <Clock size={12} />
              <span>
                {new Date(message.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>

              {/* Message Status */}
              {messageStatus && (
                <MessageStatusIndicator {...messageStatus} />
              )}

              {/* Copy Button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onCopy(message.content)}
                className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0"
              >
                <Copy size={12} />
              </Button>
            </div>
          </div>

          {/* Message Content */}
          <div className="prose prose-sm max-w-none dark:prose-invert overflow-hidden chat-message-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={getMarkdownComponents()}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Files Referenced */}
          {message.files && message.files.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/20">
              <div className="text-xs text-muted-foreground mb-1">
                Referenced files:
              </div>
              <div className="flex flex-wrap gap-1">
                {message.files.map((file, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {file.split('/').pop()}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// Removed MessageContentRenderer - used missing SearchAnimation component

// Markdown components configuration
const getMarkdownComponents = () => ({
  h1: ({ children }: any) => <h1 className="text-xl font-bold mb-2 break-words">{children}</h1>,
  h2: ({ children }: any) => <h2 className="text-lg font-semibold mb-2 break-words">{children}</h2>,
  h3: ({ children }: any) => <h3 className="text-base font-medium mb-1 break-words">{children}</h3>,
  p: ({ children }: any) => <p className="mb-2 leading-relaxed break-words">{children}</p>,
  ul: ({ children }: any) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
  code: ({ children, className }: any) => {
    const isInline = !className;
    return isInline ? (
      <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono break-all">
        {children}
      </code>
    ) : (
      <code className={className}>{children}</code>
    );
  },
  pre: ({ children }: any) => (
    <pre className="bg-muted p-3 rounded-lg overflow-x-auto text-sm max-w-full whitespace-pre-wrap">
      {children}
    </pre>
  ),
});

// Message Status Indicator Component
const MessageStatusIndicator: React.FC<{
  status: 'sending' | 'sent' | 'failed' | 'retrying';
  retryCount?: number;
  error?: string;
}> = ({ status, retryCount = 0, error }) => {
  switch (status) {
    case 'sending':
      return (
        <div className="flex items-center gap-1 text-xs">
          <Loader2 size={10} className="animate-spin" />
          <span>Sending...</span>
        </div>
      );
    case 'retrying':
      return (
        <div className="flex items-center gap-1 text-xs text-amber-600">
          <Loader2 size={10} className="animate-spin" />
          <span>Retrying ({retryCount}/3)...</span>
        </div>
      );
    case 'failed':
      return (
        <div className="flex items-center gap-1 text-xs text-red-500" title={error}>
          <AlertCircle size={10} />
          <span>Failed</span>
        </div>
      );
    case 'sent':
      return (
        <div className="flex items-center gap-1 text-xs text-green-600">
          <CheckCircle size={10} />
          <span>Sent</span>
        </div>
      );
    default:
      return null;
  }
};