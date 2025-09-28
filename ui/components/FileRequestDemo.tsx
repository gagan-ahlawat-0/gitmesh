/**
 * File Request Demo Component
 * 
 * Demonstrates the file request feature with mock AI responses
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { FileRequestPanel, FileRequest } from './chat/FileRequestPanel';
import { Bot, Send, FileText } from 'lucide-react';
import { toast } from 'sonner';

const MOCK_AI_RESPONSES = [
  {
    trigger: "show me the main file",
    response: "I'd be happy to help you understand the main functionality. Please add `app.py` to the chat so I can examine the main application file.",
    fileRequests: [
      {
        path: "app.py",
        reason: "Main application file requested to understand core functionality",
        branch: "main",
        auto_add: false
      }
    ]
  },
  {
    trigger: "explain the api structure",
    response: "To explain the API structure, I need to see the API files. Please add `api/routes.py` to the chat so I can analyze the routing structure.",
    fileRequests: [
      {
        path: "api/routes.py",
        reason: "API routes file needed to explain the API structure",
        branch: "main",
        auto_add: false
      }
    ]
  },
  {
    trigger: "help with configuration",
    response: "I can help with configuration. Let me examine the config files. Please add `config.json` and `settings.py` to the chat.",
    fileRequests: [
      {
        path: "config.json",
        reason: "Configuration file needed to understand current settings",
        branch: "main",
        auto_add: false
      },
      {
        path: "settings.py",
        reason: "Settings module needed to explain configuration options",
        branch: "main",
        auto_add: false
      }
    ]
  },
  {
    trigger: "analyze the database models",
    response: "To analyze the database models, I need to see the model definitions. Please add `models/user.py` to the chat.",
    fileRequests: [
      {
        path: "models/user.py",
        reason: "User model file requested for database analysis",
        branch: "main",
        auto_add: true // This one will be auto-suggested
      }
    ]
  }
];

export const FileRequestDemo: React.FC = () => {
  const [userInput, setUserInput] = useState('');
  const [conversation, setConversation] = useState<Array<{
    type: 'user' | 'ai';
    content: string;
    timestamp: Date;
  }>>([]);
  const [fileRequests, setFileRequests] = useState<FileRequest[]>([]);
  const [approvedFiles, setApprovedFiles] = useState<string[]>([]);

  const handleSendMessage = () => {
    if (!userInput.trim()) return;

    const userMessage = {
      type: 'user' as const,
      content: userInput,
      timestamp: new Date()
    };

    setConversation(prev => [...prev, userMessage]);

    // Find matching AI response
    const matchingResponse = MOCK_AI_RESPONSES.find(response => 
      userInput.toLowerCase().includes(response.trigger.toLowerCase())
    );

    if (matchingResponse) {
      // Add AI response
      const aiMessage = {
        type: 'ai' as const,
        content: matchingResponse.response,
        timestamp: new Date()
      };

      setTimeout(() => {
        setConversation(prev => [...prev, aiMessage]);
        
        // Add file requests
        const newRequests = matchingResponse.fileRequests.map(req => ({
          ...req,
          metadata: { demo: true }
        }));
        
        setFileRequests(prev => [...prev, ...newRequests]);
        
        toast.info(`AI requested ${newRequests.length} file(s)`, {
          description: 'Check the file request panel above the chat'
        });
      }, 1000);
    } else {
      // Generic response
      const aiMessage = {
        type: 'ai' as const,
        content: "I understand your request. To provide better assistance, I might need to examine specific files from your repository. Try asking about 'main file', 'api structure', 'configuration', or 'database models' to see file requests in action.",
        timestamp: new Date()
      };

      setTimeout(() => {
        setConversation(prev => [...prev, aiMessage]);
      }, 1000);
    }

    setUserInput('');
  };

  const handleApproveFile = async (filePath: string, branch: string) => {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setApprovedFiles(prev => [...prev, filePath]);
    setFileRequests(prev => prev.filter(req => req.path !== filePath));
    
    toast.success(`Added ${filePath} to context`);
  };

  const handleRejectFile = (filePath: string) => {
    setFileRequests(prev => prev.filter(req => req.path !== filePath));
    toast.info(`Rejected ${filePath}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            File Request Feature Demo
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            This demo shows how AI can request specific files and display them with approve/reject buttons.
            Try asking about: "main file", "api structure", "configuration", or "database models"
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Approved Files Display */}
            {approvedFiles.length > 0 && (
              <div className="p-3 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-800">
                <h4 className="text-sm font-medium text-green-800 dark:text-green-200 mb-2">
                  Files in Context ({approvedFiles.length})
                </h4>
                <div className="flex flex-wrap gap-1">
                  {approvedFiles.map(file => (
                    <Badge key={file} variant="secondary" className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                      {file}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* File Request Panel */}
            {fileRequests.length > 0 && (
              <FileRequestPanel
                fileRequests={fileRequests}
                onApproveFile={handleApproveFile}
                onRejectFile={handleRejectFile}
              />
            )}

            {/* Chat Messages */}
            <div className="space-y-3 min-h-[200px] max-h-[400px] overflow-y-auto border rounded-lg p-4">
              {conversation.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Start a conversation to see file requests in action</p>
                  <p className="text-xs mt-1">Try: "show me the main file" or "help with configuration"</p>
                </div>
              ) : (
                conversation.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex gap-3 ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-3 ${
                        msg.type === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {msg.type === 'user' ? (
                          <span className="text-xs font-medium">You</span>
                        ) : (
                          <>
                            <Bot className="w-3 h-3" />
                            <span className="text-xs font-medium">AI Assistant</span>
                          </>
                        )}
                        <span className="text-xs opacity-70">
                          {msg.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm">{msg.content}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Input Area */}
            <div className="flex gap-2">
              <Textarea
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about files you'd like to see... (e.g., 'show me the main file')"
                className="flex-1 min-h-[44px] max-h-[120px] resize-none"
                rows={1}
              />
              <Button
                onClick={handleSendMessage}
                disabled={!userInput.trim()}
                size="sm"
                className="h-[44px] px-4"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-muted-foreground">Quick examples:</span>
              {MOCK_AI_RESPONSES.map((response, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => setUserInput(response.trigger)}
                  className="text-xs h-6"
                >
                  {response.trigger}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};