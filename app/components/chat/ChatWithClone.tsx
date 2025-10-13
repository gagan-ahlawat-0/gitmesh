import { useEffect, useState } from 'react';
import { useSearchParams } from '@remix-run/react';
import { ClientOnly } from 'remix-utils/client-only';
import { BaseChat } from '~/components/chat/BaseChat';
import { Chat } from '~/components/chat/Chat.client';
import { LoadingOverlay } from '~/components/ui/LoadingOverlay';
import { useGit } from '~/lib/hooks/useGit';
import { useChatHistory } from '~/lib/persistence';
import { toast } from 'react-toastify';
import ignore from 'ignore';
import type { Message } from 'ai';
import { detectProjectCommands, createCommandsMessage, escapegitmeshTags } from '~/utils/projectCommands';
import { generateId } from '~/utils/fileUtils';
import { useCloneContext } from '~/lib/contexts/CloneContext';
import { webcontainer } from '~/lib/webcontainer';
import { RepoStatus } from './RepoStatus';
import { useStore } from '@nanostores/react';
import { chatStore } from '~/lib/stores/chat';

const IGNORE_PATTERNS = [
  'node_modules/**',
  '.git/**',
  '.github/**',
  '.vscode/**',
  'dist/**',
  'build/**',
  '.next/**',
  'coverage/**',
  '.cache/**',
  '.idea/**',
  '**/*.log',
  '**/.DS_Store',
  '**/npm-debug.log*',
  '**/yarn-debug.log*',
  '**/yarn-error.log*',
  '**/*lock.json',
  '**/*lock.yaml',
];

const ig = ignore().add(IGNORE_PATTERNS);
const MAX_FILE_SIZE = 100 * 1024; // 100KB limit per file
const MAX_TOTAL_SIZE = 500 * 1024; // 500KB total limit

async function readExistingWorkspace(): Promise<{
  workdir: string;
  data: Record<string, { data: any; encoding?: string }>;
}> {
  try {
    const container = await webcontainer;
    const workdir = container.workdir;
    const data: Record<string, { data: any; encoding?: string }> = {};

    // Read files recursively from the workspace
    const readDirectory = async (dirPath: string = '') => {
      try {
        const entries = await container.fs.readdir(dirPath, { withFileTypes: true });

        for (const entry of entries) {
          const fullPath = dirPath ? `${dirPath}/${entry.name}` : entry.name;

          // Skip ignored paths
          if (ig.ignores(fullPath)) {
            continue;
          }

          if (entry.isDirectory()) {
            await readDirectory(fullPath);
          } else if (entry.isFile()) {
            try {
              // Only read text files
              if (
                fullPath.match(
                  /\.(txt|md|astro|mjs|js|jsx|ts|tsx|json|html|css|scss|less|yml|yaml|xml|svg|vue|svelte)$/i,
                )
              ) {
                const content = await container.fs.readFile(fullPath, 'utf8');
                data[fullPath] = { data: content, encoding: 'utf8' };
              }
            } catch (error) {
              console.warn(`Failed to read file ${fullPath}:`, error);
            }
          }
        }
      } catch (error) {
        console.warn(`Failed to read directory ${dirPath}:`, error);
      }
    };

    await readDirectory();

    return { workdir, data };
  } catch (error) {
    console.error('Failed to read existing workspace:', error);
    throw error;
  }
}

function ChatWithCloneInner() {
  const [searchParams] = useSearchParams();
  const { ready: gitReady, gitClone } = useGit();
  const { ready: historyReady } = useChatHistory();
  const { addClonedMessages } = useCloneContext();
  const [isCloning, setIsCloning] = useState(false);
  const [hasProcessedClone, setHasProcessedClone] = useState(false);
  const chat = useStore(chatStore);

  const cloneUrl = searchParams.get('clone');
  const repoName = searchParams.get('repo');
  const fromHub = searchParams.get('from') === 'hub';

  useEffect(() => {
    const processClone = async () => {
      // Only auto-clone if we have a clone URL and we're coming from the hub
      if (!cloneUrl || hasProcessedClone || !gitReady || !historyReady || isCloning || !fromHub) {
        return;
      }

      setHasProcessedClone(true);
      setIsCloning(true);

      try {
        let workdir: string;
        let data: Record<string, { data: any; encoding?: string }>;

        try {
          const result = await gitClone(cloneUrl);
          workdir = result.workdir;
          data = result.data;
        } catch (error) {
          // If cloning fails due to existing files, try to read the existing workspace
          const errorMessage = error instanceof Error ? error.message : String(error);

          if (errorMessage.includes('would be overwritten') || errorMessage.includes('already exists')) {
            console.log('Repository already exists in workspace, reading existing files...');
            toast.info('Repository already cloned, loading existing files...');

            // Read existing files from the workspace
            const result = await readExistingWorkspace();
            workdir = result.workdir;
            data = result.data;
          } else {
            throw error; // Re-throw other errors
          }
        }

        if (addClonedMessages) {
          const filePaths = Object.keys(data).filter((filePath) => !ig.ignores(filePath));
          const textDecoder = new TextDecoder('utf-8');

          let totalSize = 0;
          const skippedFiles: string[] = [];
          const fileContents = [];

          for (const filePath of filePaths) {
            const { data: content, encoding } = data[filePath];

            // Skip binary files
            if (
              content instanceof Uint8Array &&
              !filePath.match(
                /\.(txt|md|astro|mjs|js|jsx|ts|tsx|json|html|css|scss|less|yml|yaml|xml|svg|vue|svelte)$/i,
              )
            ) {
              skippedFiles.push(filePath);
              continue;
            }

            try {
              const textContent =
                encoding === 'utf8' ? content : content instanceof Uint8Array ? textDecoder.decode(content) : '';

              if (!textContent || typeof textContent !== 'string') {
                continue;
              }

              // Check file size
              const fileSize = new TextEncoder().encode(textContent).length;

              if (fileSize > MAX_FILE_SIZE) {
                skippedFiles.push(`${filePath} (too large: ${Math.round(fileSize / 1024)}KB)`);
                continue;
              }

              // Check total size
              if (totalSize + fileSize > MAX_TOTAL_SIZE) {
                skippedFiles.push(`${filePath} (would exceed total size limit)`);
                continue;
              }

              totalSize += fileSize;
              fileContents.push({
                path: filePath,
                content: textContent,
              });
            } catch (e: any) {
              skippedFiles.push(`${filePath} (error: ${e.message})`);
            }
          }

          const commands = await detectProjectCommands(fileContents);
          const commandsMessage = createCommandsMessage(commands);

          const filesMessage: Message = {
            role: 'assistant',
            content: `Cloning the repo ${cloneUrl} into ${workdir}
${
  skippedFiles.length > 0
    ? `\nSkipped files (${skippedFiles.length}):
${skippedFiles.map((f) => `- ${f}`).join('\n')}`
    : ''
}

<gitmeshArtifact id="imported-files" title="Git Cloned Files" type="bundled">
${fileContents
  .map(
    (file) =>
      `<gitmeshAction type="file" filePath="${file.path}">
${escapegitmeshTags(typeof file.content === 'string' ? file.content : '')}
</gitmeshAction>`,
  )
  .join('\n')}
</gitmeshArtifact>`,
            id: generateId(),
            createdAt: new Date(),
          };

          const messages = [filesMessage];

          if (commandsMessage) {
            messages.push(commandsMessage);
          }

          addClonedMessages(messages);
        }

        const repoDisplayName = repoName || cloneUrl.split('/').slice(-1)[0];
        toast.success(`Repository "${repoDisplayName}" cloned successfully!`);
      } catch (error) {
        console.error('Error during import:', error);
        toast.error('Failed to clone repository');
        setHasProcessedClone(false); // Allow retry
      } finally {
        setIsCloning(false);
      }
    };

    processClone();
  }, [cloneUrl, fromHub, gitReady, historyReady, hasProcessedClone, isCloning, gitClone, addClonedMessages]);

  return (
    <>
      {/* Only show standalone RepoStatus when chat hasn't started */}
      {!chat.started && <RepoStatus />}
      <ClientOnly
        fallback={
          <div className="loading-chat">
            <BaseChat />
          </div>
        }
      >
        {() => <Chat />}
      </ClientOnly>
      {isCloning && <LoadingOverlay message="Cloning repository..." />}
    </>
  );
}

export function ChatWithClone() {
  return <ChatWithCloneInner />;
}
