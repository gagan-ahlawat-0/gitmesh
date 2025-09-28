"use client";

import { FileRequestDemo } from '@/components/FileRequestDemo';

export default function FileRequestDemoPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold mb-2">AI File Request Feature</h1>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            This demo showcases how the AI can intelligently request specific files from your repository 
            and display them with approve/reject buttons for user control.
          </p>
          
          <div className="mt-4 p-4 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-800">
            <h3 className="font-semibold text-green-800 dark:text-green-200 mb-2">✅ Feature Status: Implemented</h3>
            <p className="text-sm text-green-700 dark:text-green-300">
              The file request feature is now fully implemented! When you chat with the AI in the main application,
              it will automatically detect when it needs specific files and show approval buttons.
            </p>
          </div>
        </div>
        
        <FileRequestDemo />
        
        <div className="mt-8 max-w-4xl mx-auto">
          <div className="bg-muted/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-3">How it works in the real application:</h2>
            <ol className="list-decimal list-inside space-y-2 text-sm">
              <li>When you ask the AI about specific functionality, it analyzes your request</li>
              <li>The backend response processor detects file requests using regex patterns</li>
              <li>File requests appear above the chat with + (approve) and × (reject) buttons</li>
              <li>You can approve individual files or use "Add All" / "Reject All" for bulk actions</li>
              <li>Approved files are fetched from your repository and added to the chat context</li>
              <li>The AI can then provide more accurate and detailed responses based on the actual code</li>
            </ol>
            
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950/20 rounded border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                <strong>Privacy & Security:</strong> Files are only added to your chat context with your explicit approval. 
                You maintain full control over what information the AI can access.
              </p>
            </div>
            
            <div className="mt-4 p-3 bg-purple-50 dark:bg-purple-950/20 rounded border border-purple-200 dark:border-purple-800">
              <p className="text-sm text-purple-800 dark:text-purple-200">
                <strong>Technical Implementation:</strong> The feature uses regex patterns to detect file requests in AI responses,
                creates interactive UI elements, and integrates with the repository service to fetch file contents.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}