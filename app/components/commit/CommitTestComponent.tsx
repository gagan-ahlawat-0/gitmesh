import React, { useState } from 'react';
import { workbenchStore } from '~/lib/stores/workbench';
import { useCommit, useModifiedFiles } from '~/lib/hooks';

/**
 * Test component to demonstrate AI commit functionality
 * This component simulates file modifications and shows how the AI can suggest commits
 */
export const CommitTestComponent: React.FC = () => {
  const [testFiles, setTestFiles] = useState<string[]>([]);
  const { handleCommitToGitHub, handleCommitToGitLab } = useCommit();
  const { count: modifiedFilesCount } = useModifiedFiles();

  const addTestFile = () => {
    const fileName = `test-file-${Date.now()}.ts`;
    const content = `// Test file created at ${new Date().toISOString()}\nexport const testFunction = () => {\n  console.log('Hello from test file!');\n};`;

    // Add file to workbench store using the correct method
    const files = workbenchStore.files.get();
    files[fileName] = {
      type: 'file',
      content,
      isBinary: false,
    };
    workbenchStore.files.set(files);

    // File will automatically be tracked as modified by FilesStore
    setTestFiles((prev) => [...prev, fileName]);
  };

  const clearTestFiles = () => {
    testFiles.forEach((fileName) => {
      // Remove files from the workbench
      const files = workbenchStore.files.get();
      delete files[fileName];
      workbenchStore.files.set(files);
    });
    setTestFiles([]);
  };

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
      <h3 className="text-lg font-semibold mb-4">AI Commit Functionality Test</h3>

      <div className="space-y-4">
        <div className="flex gap-2">
          <button onClick={addTestFile} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            Add Test File
          </button>
          <button onClick={clearTestFiles} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">
            Clear Test Files
          </button>
        </div>

        <div className="text-sm text-gray-600">
          Modified Files Count: <span className="font-semibold">{modifiedFilesCount}</span>
        </div>

        {testFiles.length > 0 && (
          <div className="text-sm">
            <div className="font-semibold mb-2">Test Files Created:</div>
            <ul className="list-disc list-inside space-y-1">
              {testFiles.map((file) => (
                <li key={file} className="text-gray-700">
                  {file}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="border-t pt-4">
          <h4 className="font-semibold mb-2">AI Commit Actions Available:</h4>
          <div className="flex gap-2">
            <button
              onClick={handleCommitToGitHub}
              disabled={modifiedFilesCount === 0}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Test GitHub Commit
            </button>
            <button
              onClick={handleCommitToGitLab}
              disabled={modifiedFilesCount === 0}
              className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Test GitLab Commit
            </button>
          </div>
        </div>

        <div className="text-xs text-gray-500 bg-blue-50 p-3 rounded">
          <strong>How it works:</strong>
          <ol className="list-decimal list-inside mt-2 space-y-1">
            <li>Click "Add Test File" to simulate file modifications</li>
            <li>The AI will now be aware of modified files in the system prompt</li>
            <li>When you chat with the AI, it will suggest commit actions</li>
            <li>Click the AI's commit buttons to open the commit dialogs</li>
            <li>Use the test commit buttons above to verify the dialogs work</li>
          </ol>
        </div>
      </div>
    </div>
  );
};
