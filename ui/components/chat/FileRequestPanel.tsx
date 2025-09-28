/**
 * File Request Panel Component
 * 
 * Displays AI-requested files with approve/reject buttons
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
  Plus,
  X,
  FileText,
  Bot,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

export interface FileRequest {
  path: string;
  reason: string;
  branch?: string;
  auto_add?: boolean;
  pattern_matched?: string;
  metadata?: Record<string, any>;
}

interface FileRequestPanelProps {
  fileRequests: FileRequest[];
  onApproveFile: (filePath: string, branch: string) => Promise<void>;
  onRejectFile: (filePath: string) => void;
  className?: string;
}

interface FileRequestItemProps {
  request: FileRequest;
  onApprove: () => Promise<void>;
  onReject: () => void;
}

const FileRequestItem: React.FC<FileRequestItemProps> = ({
  request,
  onApprove,
  onReject
}) => {
  const [status, setStatus] = useState<'pending' | 'approving' | 'approved' | 'rejected'>('pending');
  const [error, setError] = useState<string | null>(null);

  const handleApprove = useCallback(async () => {
    if (status !== 'pending') return;
    
    setStatus('approving');
    setError(null);
    
    try {
      await onApprove();
      setStatus('approved');
      toast.success(`Added ${request.path.split('/').pop()} to context`);
    } catch (err: any) {
      setStatus('pending');
      setError(err.message || 'Failed to add file');
      toast.error(`Failed to add ${request.path.split('/').pop()}`);
    }
  }, [status, onApprove, request.path]);

  const handleReject = useCallback(() => {
    if (status !== 'pending') return;
    
    setStatus('rejected');
    onReject();
    toast.info(`Rejected ${request.path.split('/').pop()}`);
  }, [status, onReject, request.path]);

  const getFileIcon = () => {
    const extension = request.path.split('.').pop()?.toLowerCase();
    const iconClass = "w-4 h-4";
    
    switch (extension) {
      case 'py':
        return <FileText className={cn(iconClass, "text-blue-600")} />;
      case 'js':
      case 'jsx':
        return <FileText className={cn(iconClass, "text-yellow-500")} />;
      case 'ts':
      case 'tsx':
        return <FileText className={cn(iconClass, "text-blue-500")} />;
      case 'json':
        return <FileText className={cn(iconClass, "text-green-500")} />;
      case 'md':
        return <FileText className={cn(iconClass, "text-purple-500")} />;
      case 'css':
      case 'scss':
        return <FileText className={cn(iconClass, "text-pink-500")} />;
      case 'html':
        return <FileText className={cn(iconClass, "text-orange-500")} />;
      default:
        return <FileText className={cn(iconClass, "text-gray-500")} />;
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'approving':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'rejected':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const fileName = request.path.split('/').pop() || request.path;
  const filePath = request.path.includes('/') ? request.path.split('/').slice(0, -1).join('/') + '/' : '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={cn(
        "border rounded-lg p-3 transition-all duration-200",
        status === 'approved' && "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20",
        status === 'rejected' && "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20",
        status === 'pending' && "border-border hover:border-primary/50"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="flex items-center gap-2 mt-0.5">
            {getFileIcon()}
            {getStatusIcon()}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm truncate">
                {fileName}
              </span>
              {request.auto_add && (
                <Badge variant="secondary" className="text-xs">
                  Auto-suggested
                </Badge>
              )}
            </div>
            
            {filePath && (
              <p className="text-xs text-muted-foreground truncate mb-1">
                {filePath}
              </p>
            )}
            
            <p className="text-xs text-muted-foreground">
              {request.reason}
            </p>
            
            {error && (
              <div className="flex items-center gap-1 mt-1 text-xs text-red-600">
                <AlertCircle className="w-3 h-3" />
                <span>{error}</span>
              </div>
            )}
          </div>
        </div>
        
        {status === 'pending' && (
          <div className="flex items-center gap-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleApprove}
                    className="h-8 w-8 p-0 hover:bg-green-50 hover:border-green-300"
                  >
                    <Plus className="w-3 h-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Add to context
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReject}
                    className="h-8 w-8 p-0 hover:bg-red-50 hover:border-red-300"
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Reject
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export const FileRequestPanel: React.FC<FileRequestPanelProps> = ({
  fileRequests,
  onApproveFile,
  onRejectFile,
  className
}) => {
  const [rejectedFiles, setRejectedFiles] = useState<Set<string>>(new Set());

  const handleApproveFile = useCallback(async (filePath: string, branch: string = 'main') => {
    await onApproveFile(filePath, branch);
  }, [onApproveFile]);

  const handleRejectFile = useCallback((filePath: string) => {
    setRejectedFiles(prev => new Set([...prev, filePath]));
    onRejectFile(filePath);
  }, [onRejectFile]);

  // Filter out rejected files
  const visibleRequests = fileRequests.filter(request => !rejectedFiles.has(request.path));

  if (visibleRequests.length === 0) {
    return null;
  }

  return (
    <Card className={cn("mb-4", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-600" />
          <CardTitle className="text-base">AI File Requests</CardTitle>
          <Badge variant="secondary" className="text-xs">
            {visibleRequests.length}
          </Badge>
        </div>
        <CardDescription className="text-sm">
          The AI has requested access to these files to better assist you
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-2">
        <AnimatePresence>
          {visibleRequests.map((request) => (
            <FileRequestItem
              key={request.path}
              request={request}
              onApprove={() => handleApproveFile(request.path, request.branch)}
              onReject={() => handleRejectFile(request.path)}
            />
          ))}
        </AnimatePresence>
        
        {visibleRequests.length > 1 && (
          <div className="flex items-center justify-between pt-2 border-t">
            <span className="text-xs text-muted-foreground">
              {visibleRequests.length} files requested
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  visibleRequests.forEach(request => {
                    handleApproveFile(request.path, request.branch);
                  });
                }}
                className="text-xs h-7"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add All
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  visibleRequests.forEach(request => {
                    handleRejectFile(request.path);
                  });
                }}
                className="text-xs h-7"
              >
                <X className="w-3 h-3 mr-1" />
                Reject All
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};