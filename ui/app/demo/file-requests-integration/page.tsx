"use client";

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { FileRequestPanel, FileRequest } from '@/components/chat/FileRequestPanel';
import { toast } from 'sonner';

export default function FileRequestsIntegrationDemo() {
  const [fileRequests, setFileRequests] = useState<FileRequest[]>([]);
  const [sessionId] = useState('demo_session_' + Date.now());
  const [isLoading, setIsLoading] = useState(false);

  // Simulate AI response with file requests
  const simulateAIResponse = async () => {
    setIsLoading(true);
    
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Create mock file requests
    const mockRequests: FileRequest[] = [
      {
        id: 'req_1',
        path: 'src/components/ChatInterface.tsx',
        reason: 'I need to see the chat interface component to understand how messages are displayed',
        branch: 'main',
        auto_add: false,
        metadata: {
          confidence: 0.9,
          pattern_matched: 'add_to_chat'
        }
      },
      {
        id: 'req_2',
        path: 'backend/api/v1/routes/chat.py',
        reason: 'I need to examine the chat API to understand the message processing flow',
        branch: 'main',
        auto_add: false,
        metadata: {
          confidence: 0.8,
          pattern_matched: 'show_me_file'
        }
      },
      {
        id: 'req_3',
        path: 'config/settings.py',
        reason: 'I need to check the configuration settings to understand the system setup',
        branch: 'main',
        auto_add: false,
        metadata: {
          confidence: 0.7,
          pattern_matched: 'need_to_see'
        }
      }
    ];
    
    setFileRequests(mockRequests);
    setIsLoading(false);
    
    toast.success(`Generated ${mockRequests.length} file requests from AI response`);
  };

  // Handle file approval
  const handleApproveFile = async (filePath: string, branch: string = 'main') => {
    try {
      console.log(`Approving file: ${filePath} (branch: ${branch})`);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Remove from requests
      setFileRequests(prev => prev.filter(req => req.path !== filePath));
      
      toast.success(`Added ${filePath} to context`);
    } catch (error) {
      console.error('Error approving file:', error);
      toast.error('Failed to approve file');
    }
  };

  // Handle file rejection
  const handleRejectFile = async (filePath: string) => {
    try {
      console.log(`Rejecting file: ${filePath}`);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Remove from requests
      setFileRequests(prev => prev.filter(req => req.path !== filePath));
      
      toast.success(`Rejected ${filePath}`);
    } catch (error) {
      console.error('Error rejecting file:', error);
      toast.error('Failed to reject file');
    }
  };

  // Clear all requests
  const clearAllRequests = () => {
    setFileRequests([]);
    toast.info('Cleared all file requests');
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">File Request Integration Demo</h1>
          <p className="text-muted-foreground">
            Test the complete file request flow from AI response to user approval
          </p>
        </div>

        {/* Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Demo Controls</CardTitle>
            <CardDescription>
              Simulate AI responses and test file request functionality
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <Button 
                onClick={simulateAIResponse}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? 'Processing...' : 'Simulate AI Response with File Requests'}
              </Button>
              
              <Button 
                variant="outline" 
                onClick={clearAllRequests}
                disabled={fileRequests.length === 0}
              >
                Clear All Requests
              </Button>
            </div>
            
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <Badge variant="secondary">Session: {sessionId}</Badge>
              <Badge variant="outline">{fileRequests.length} pending requests</Badge>
            </div>
          </CardContent>
        </Card>

        <Separator />

        {/* File Request Panel */}
        {fileRequests.length > 0 ? (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Pending File Requests</h2>
            <FileRequestPanel
              fileRequests={fileRequests}
              repositoryName="demo/repository"
              onApproveFile={handleApproveFile}
              onRejectFile={handleRejectFile}
            />
          </div>
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <div className="space-y-2">
                <p className="text-muted-foreground">No file requests pending</p>
                <p className="text-sm text-muted-foreground">
                  Click "Simulate AI Response" to generate file requests
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Integration Status */}
        <Card>
          <CardHeader>
            <CardTitle>Integration Status</CardTitle>
            <CardDescription>
              Current status of the file request integration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center space-y-2">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                  <span className="text-green-600 font-bold">✓</span>
                </div>
                <h3 className="font-medium">Response Processing</h3>
                <p className="text-sm text-muted-foreground">
                  AI responses are processed to extract file requests
                </p>
              </div>
              
              <div className="text-center space-y-2">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                  <span className="text-green-600 font-bold">✓</span>
                </div>
                <h3 className="font-medium">File Request Storage</h3>
                <p className="text-sm text-muted-foreground">
                  File requests are stored and can be retrieved
                </p>
              </div>
              
              <div className="text-center space-y-2">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                  <span className="text-green-600 font-bold">✓</span>
                </div>
                <h3 className="font-medium">User Interface</h3>
                <p className="text-sm text-muted-foreground">
                  Users can approve or reject file requests
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Technical Details */}
        <Card>
          <CardHeader>
            <CardTitle>Technical Implementation</CardTitle>
            <CardDescription>
              How the file request feature works
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div>
                <h4 className="font-medium">1. Response Processing</h4>
                <p className="text-sm text-muted-foreground">
                  AI responses are analyzed using regex patterns to detect file requests
                </p>
              </div>
              
              <div>
                <h4 className="font-medium">2. Entity Creation</h4>
                <p className="text-sm text-muted-foreground">
                  File request entities are created and stored in Redis with session context
                </p>
              </div>
              
              <div>
                <h4 className="font-medium">3. UI Display</h4>
                <p className="text-sm text-muted-foreground">
                  File requests are displayed as interactive panels with approve/reject buttons
                </p>
              </div>
              
              <div>
                <h4 className="font-medium">4. User Action</h4>
                <p className="text-sm text-muted-foreground">
                  User decisions are processed via API endpoints and file context is updated
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}