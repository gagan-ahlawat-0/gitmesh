import React, { useState, useEffect } from 'react';
import { Bug, AlertCircle, CheckCircle2, Clock, GitBranch, ChevronDown, ChevronUp, ExternalLink, MessageSquare } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { apiService } from '@/lib/api';
import type { Issue, IssueComment } from './contribution-data';

interface BranchIssueTableProps {
  issues: Issue[];
  branch: string;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'open': return 'bg-red-100 text-red-800 border-red-200';
    case 'in_progress': return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'resolved': return 'bg-green-100 text-green-800 border-green-200';
    default: return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'open': return <AlertCircle size={14} />;
    case 'in_progress': return <Clock size={14} />;
    case 'resolved': return <CheckCircle2 size={14} />;
    default: return <Bug size={14} />;
  }
};

const BranchIssueTable = ({ issues, branch }: BranchIssueTableProps) => {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, IssueComment[]>>({});
  const [loadingComments, setLoadingComments] = useState<Record<string, boolean>>({});

  const fetchComments = async (issueNumber: number, issueId: string) => {
    if (comments[issueId] || loadingComments[issueId]) return;
    
    setLoadingComments(prev => ({ ...prev, [issueId]: true }));
    
    try {
      // Extract owner and repo from the current context
      // For now, we'll use a placeholder - in a real app, you'd get this from context
      const owner = 'RAWx18'; // This should come from repository context
      const repo = 'Beetle';   // This should come from repository context
      
      const response = await apiService.getIssueComments(owner, repo, issueNumber);
      
      if (response.data && response.data.comments) {
        setComments(prev => ({ ...prev, [issueId]: response.data.comments }));
      }
    } catch (error) {
      console.error('Error fetching comments:', error);
    } finally {
      setLoadingComments(prev => ({ ...prev, [issueId]: false }));
    }
  };

  const handleExpand = (issueId: string, issueNumber?: number) => {
    if (expanded === issueId) {
      setExpanded(null);
    } else {
      setExpanded(issueId);
      if (issueNumber && !comments[issueId]) {
        fetchComments(issueNumber, issueId);
      }
    }
  };

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <Bug size={48} className="mb-4" />
        <p>No issues found for {branch} branch</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto">
      <div className="overflow-x-auto">
        <Table className="w-full text-base mb-8">
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"></TableHead>
              <TableHead className="w-2/5">Issue</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Assignee</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
          {issues.map((issue) => {
            const isOpen = expanded === issue.id;
            return (
              <React.Fragment key={issue.id}>
                <TableRow className="hover:bg-muted/40 border-b border-muted-foreground/10 transition-all group">
                  <TableCell className="align-top">
                    <button
                      className={`rounded-full p-2 bg-muted-foreground/10 hover:bg-primary/20 transition-colors flex items-center justify-center text-primary text-lg`}
                      style={{ minWidth: 40, minHeight: 40 }}
                      onClick={() => handleExpand(issue.id, issue.number)}
                      aria-label={isOpen ? 'Collapse details' : 'Expand details'}
                    >
                      {isOpen ? <ChevronUp size={22} /> : <ChevronDown size={22} />}
                    </button>
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex items-start gap-2">
                      <div className="mt-1">{getStatusIcon(issue.status)}</div>
                      <div>
                        {issue.githubUrl ? (
                          <a 
                            href={issue.githubUrl} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="font-semibold text-lg leading-tight break-words max-w-xl text-blue-600 hover:text-blue-800 hover:underline cursor-pointer flex items-center gap-1"
                          >
                            {issue.title}
                            <ExternalLink size={14} className="text-blue-500" />
                          </a>
                        ) : (
                          <div className="font-semibold text-lg leading-tight break-words max-w-xl">{issue.title}</div>
                        )}
                        <div className="text-xs text-muted-foreground">
                          {issue.number ? `#${issue.number}` : `#${issue.id}`}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="align-top">
                    <Badge className={getStatusColor(issue.status) + ' px-4 py-2 text-base rounded-lg font-semibold'}>{issue.status.replace('_', ' ')}</Badge>
                  </TableCell>
                  <TableCell className="align-top">
                    {issue.assignee ? (
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="text-base">{issue.assignee.slice(0, 2).toUpperCase()}</AvatarFallback>
                        </Avatar>
                        <a 
                          href={`https://github.com/${issue.assignee}`} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-base font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer flex items-center gap-1"
                        >
                          {issue.assignee}
                          <ExternalLink size={12} className="text-blue-500" />
                        </a>
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-base">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell className="align-top">
                    <Badge variant={issue.priority === 'high' ? 'destructive' : issue.priority === 'medium' ? 'default' : 'secondary'} className="px-4 py-2 text-base rounded-lg font-semibold">{issue.priority}</Badge>
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex items-center gap-2 text-base text-muted-foreground">
                      <Clock size={16} />
                      {issue.createdAt}
                    </div>
                  </TableCell>
                </TableRow>
                {isOpen && (
                  <TableRow className="bg-muted/30">
                    <TableCell colSpan={6} className="py-4">
                      <div className="flex flex-wrap gap-8">
                        <div>
                          <div className="font-semibold mb-1">Labels</div>
                          <div className="flex flex-wrap gap-2">
                            {issue.labels.map((label, idx) => (
                              <Badge key={idx} variant="secondary" className="text-sm px-3 py-1 rounded-lg">{label}</Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div className="font-semibold mb-1">Linked PRs</div>
                          {issue.linkedPRs.length > 0 ? (
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <GitBranch size={14} />
                              {issue.linkedPRs.length} PR(s)
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-sm">None</span>
                          )}
                        </div>
                        <div className="flex-1 min-w-[200px]">
                          <div className="font-semibold mb-1">Description</div>
                          <div className="text-sm text-muted-foreground break-words whitespace-pre-line">{issue.description}</div>
                        </div>
                      </div>
                      
                      {/* Comments Section */}
                      <div className="mt-6 border-t border-muted-foreground/20 pt-4">
                        <div className="flex items-center gap-2 mb-3">
                          <MessageSquare size={16} className="text-muted-foreground" />
                          <span className="font-semibold">Comments ({issue.discussions})</span>
                        </div>
                        
                        {loadingComments[issue.id] ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                            Loading comments...
                          </div>
                        ) : comments[issue.id] && comments[issue.id].length > 0 ? (
                          <div className="space-y-4">
                            {comments[issue.id].map((comment) => (
                              <div key={comment.id} className="bg-muted/30 rounded-lg p-4 border border-muted-foreground/10">
                                <div className="flex items-start gap-3">
                                  <Avatar className="h-8 w-8">
                                    <AvatarFallback className="text-sm">
                                      {comment.user.login.slice(0, 2).toUpperCase()}
                                    </AvatarFallback>
                                  </Avatar>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2">
                                      <a 
                                        href={`https://github.com/${comment.user.login}`} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer flex items-center gap-1"
                                      >
                                        {comment.user.login}
                                        <ExternalLink size={10} className="text-blue-500" />
                                      </a>
                                      <span className="text-xs text-muted-foreground">
                                        {new Date(comment.created_at).toLocaleDateString()}
                                      </span>
                                    </div>
                                    <div className="text-sm text-muted-foreground break-words whitespace-pre-line">
                                      {comment.body}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm text-muted-foreground">
                            No comments yet. Be the first to comment!
                          </div>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            );
          })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default BranchIssueTable;
