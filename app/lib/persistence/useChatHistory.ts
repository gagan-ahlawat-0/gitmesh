import { useLoaderData, useNavigate, useSearchParams } from '@remix-run/react';
import { useState, useEffect, useCallback } from 'react';
import { atom } from 'nanostores';
import { generateId, type JSONValue, type Message } from 'ai';
import { toast } from 'react-toastify';
import { workbenchStore } from '~/lib/stores/workbench';
import { logStore } from '~/lib/stores/logs'; // Import logStore
import {
  getMessages,
  getNextId,
  getUrlId,
  openDatabase,
  setMessages,
  duplicateChat,
  createChatFromMessages,
  getSnapshot,
  setSnapshot,
  type IChatMetadata,
} from './db';
import type { FileMap } from '~/lib/stores/files';
import type { Snapshot } from './types';
import { webcontainer } from '~/lib/webcontainer';
import { detectProjectCommands, createCommandActionsString } from '~/utils/projectCommands';
import type { ContextAnnotation } from '~/types/context';

export interface ChatHistoryItem {
  id: string;
  urlId?: string;
  description?: string;
  messages: Message[];
  timestamp: string;
  metadata?: IChatMetadata;
}

const persistenceEnabled = !import.meta.env.VITE_DISABLE_PERSISTENCE;

// Database will be initialized client-side only
export let db: IDBDatabase | undefined = undefined;

export const chatId = atom<string | undefined>(undefined);
export const description = atom<string | undefined>(undefined);
export const chatMetadata = atom<IChatMetadata | undefined>(undefined);
export function useChatHistory() {
  const navigate = useNavigate();
  const loaderData = useLoaderData<{ id?: string; mixedId?: string; baseRoute?: boolean }>();
  // Try to get ID from either the 'id' field or 'mixedId' field
  const mixedId = loaderData?.mixedId || loaderData?.id;
  const [searchParams] = useSearchParams();

  // Add stack trace to see which component is calling this
  const stack = new Error().stack?.split('\n')[2]?.trim() || 'unknown';

  console.log('🔍 useChatHistory initialized:', {
    mixedId,
    loaderData: JSON.stringify(loaderData),
    loaderDataKeys: Object.keys(loaderData || {}),
    currentPath: window.location.pathname,
    href: window.location.href,
    calledFrom: stack,
  });

  const [archivedMessages, setArchivedMessages] = useState<Message[]>([]);
  const [initialMessages, setInitialMessages] = useState<Message[]>([]);
  const [ready, setReady] = useState<boolean>(false);
  const [urlId, setUrlId] = useState<string | undefined>();
  const [database, setDatabase] = useState<IDBDatabase | undefined>(db);
  const [dbInitialized, setDbInitialized] = useState<boolean>(false);

  // Initialize database on client-side only
  useEffect(() => {
    console.log('🔍 Database initialization effect triggered:', {
      isClient: typeof window !== 'undefined',
      persistenceEnabled,
    });

    if (typeof window !== 'undefined' && persistenceEnabled) {
      console.log('🔄 Starting database initialization...');
      openDatabase()
        .then((initDb) => {
          console.log('📊 Database initialization result:', { success: !!initDb });
          db = initDb; // Update the global variable too
          setDatabase(initDb);
          setDbInitialized(true);

          if (!initDb) {
            const error = new Error('Chat persistence is unavailable');
            logStore.logError('Database initialization failed', error);
            toast.error('Chat persistence is unavailable');
          } else {
            console.log('✅ Database initialized successfully');
          }
        })
        .catch((error) => {
          console.error('❌ Failed to initialize database:', error);
          logStore.logError('Database initialization failed', error);
          toast.error('Chat persistence is unavailable');
          setDatabase(undefined);
          setDbInitialized(true);
        });
    } else if (!persistenceEnabled) {
      console.log('⚠️ Persistence is disabled');
      setDbInitialized(true);
    }
  }, []);

  useEffect(() => {
    // Wait for database initialization to complete
    if (!dbInitialized) {
      return;
    }

    // If no database and no mixedId, we're ready
    if (!database && !mixedId) {
      setReady(true);
      return;
    }

    // If no database but we have mixedId, we can't load the chat
    if (!database && mixedId) {
      setReady(true);
      return;
    }

    if (mixedId && database) {
      console.log('🔍 Loading chat messages for ID:', mixedId);
      Promise.all([
        getMessages(database, mixedId),
        getSnapshot(database, mixedId), // Fetch snapshot from DB
      ])
        .then(async ([storedMessages, snapshot]) => {
          console.log('📝 getMessages result:', {
            storedMessages: storedMessages
              ? {
                  id: storedMessages.id,
                  messagesLength: storedMessages.messages.length,
                  description: storedMessages.description,
                  urlId: storedMessages.urlId,
                }
              : null,
            snapshot: snapshot
              ? { chatIndex: snapshot.chatIndex, filesCount: Object.keys(snapshot.files || {}).length }
              : null,
          });

          if (storedMessages && storedMessages.messages.length > 0) {
            /*
             * const snapshotStr = localStorage.getItem(`snapshot:${mixedId}`); // Remove localStorage usage
             * const snapshot: Snapshot = snapshotStr ? JSON.parse(snapshotStr) : { chatIndex: 0, files: {} }; // Use snapshot from DB
             */
            const validSnapshot = snapshot || { chatIndex: '', files: {} }; // Ensure snapshot is not undefined
            const summary = validSnapshot.summary;

            const rewindId = searchParams.get('rewindTo');
            let startingIdx = -1;
            const endingIdx = rewindId
              ? storedMessages.messages.findIndex((m) => m.id === rewindId) + 1
              : storedMessages.messages.length;
            const snapshotIndex = storedMessages.messages.findIndex((m) => m.id === validSnapshot.chatIndex);

            if (snapshotIndex >= 0 && snapshotIndex < endingIdx) {
              startingIdx = snapshotIndex;
            }

            if (snapshotIndex > 0 && storedMessages.messages[snapshotIndex].id == rewindId) {
              startingIdx = -1;
            }

            let filteredMessages = storedMessages.messages.slice(startingIdx + 1, endingIdx);
            let archivedMessages: Message[] = [];

            if (startingIdx >= 0) {
              archivedMessages = storedMessages.messages.slice(0, startingIdx + 1);
            }

            setArchivedMessages(archivedMessages);

            if (startingIdx > 0) {
              const files = Object.entries(validSnapshot?.files || {})
                .map(([key, value]) => {
                  if (value?.type !== 'file') {
                    return null;
                  }

                  return {
                    content: value.content,
                    path: key,
                  };
                })
                .filter((x): x is { content: string; path: string } => !!x); // Type assertion
              const projectCommands = await detectProjectCommands(files);

              // Call the modified function to get only the command actions string
              const commandActionsString = createCommandActionsString(projectCommands);

              filteredMessages = [
                {
                  id: generateId(),
                  role: 'user',
                  content: `Restore project from snapshot`, // Removed newline
                  annotations: ['no-store', 'hidden'],
                },
                {
                  id: storedMessages.messages[snapshotIndex].id,
                  role: 'assistant',

                  // Combine followup message and the artifact with files and command actions
                  content: `gitmesh Restored your chat from a snapshot. You can revert this message to load the full chat history.
                  <gitmeshArtifact id="restored-project-setup" title="Restored Project & Setup" type="bundled">
                  ${Object.entries(snapshot?.files || {})
                    .map(([key, value]) => {
                      if (value?.type === 'file') {
                        return `
                      <gitmeshAction type="file" filePath="${key}">
${value.content}
                      </gitmeshAction>
                      `;
                      } else {
                        return ``;
                      }
                    })
                    .join('\n')}
                  ${commandActionsString} 
                  </gitmeshArtifact>
                  `, // Added commandActionsString, followupMessage, updated id and title
                  annotations: [
                    'no-store',
                    ...(summary
                      ? [
                          {
                            chatId: storedMessages.messages[snapshotIndex].id,
                            type: 'chatSummary',
                            summary,
                          } satisfies ContextAnnotation,
                        ]
                      : []),
                  ],
                },

                // Remove the separate user and assistant messages for commands
                /*
                 *...(commands !== null // This block is no longer needed
                 *  ? [ ... ]
                 *  : []),
                 */
                ...filteredMessages,
              ];
              restoreSnapshot(mixedId);
            }

            console.log('✅ Setting initial messages:', {
              filteredMessagesLength: filteredMessages.length,
              archivedMessagesLength: archivedMessages.length,
              chatId: storedMessages.id,
              urlId: storedMessages.urlId,
              description: storedMessages.description,
            });

            setInitialMessages(filteredMessages);

            setUrlId(storedMessages.urlId);
            description.set(storedMessages.description);
            chatId.set(storedMessages.id);
            chatMetadata.set(storedMessages.metadata);

            // Restore repository context from metadata if available
            if (
              storedMessages.metadata?.cloneUrl &&
              storedMessages.metadata?.repoName &&
              storedMessages.metadata?.repoFullName &&
              storedMessages.metadata?.repoProvider
            ) {
              // Trigger repository context restoration via custom event
              const repoEvent = new CustomEvent('restore-repo-context', {
                detail: {
                  cloneUrl: storedMessages.metadata.cloneUrl,
                  repoName: storedMessages.metadata.repoName,
                  repoFullName: storedMessages.metadata.repoFullName,
                  provider: storedMessages.metadata.repoProvider,
                },
              });
              window.dispatchEvent(repoEvent);
            }
          } else {
            console.log('❌ No messages found, navigating to home');
            navigate('/', { replace: true });
          }

          setReady(true);
        })
        .catch((error) => {
          console.error('❌ Error loading chat:', error);

          logStore.logError('Failed to load chat messages or snapshot', error); // Updated error message
          toast.error('Failed to load chat: ' + error.message); // More specific error
          setReady(true);
        });
    } else {
      // Handle case where there is no mixedId (e.g., new chat)
      setReady(true);
    }
  }, [mixedId, database, navigate, searchParams, dbInitialized]); // Updated to use database and dbInitialized

  const takeSnapshot = useCallback(
    async (chatIdx: string, files: FileMap, _chatId?: string | undefined, chatSummary?: string) => {
      const id = chatId.get();

      if (!id || !database) {
        return;
      }

      const snapshot: Snapshot = {
        chatIndex: chatIdx,
        files,
        summary: chatSummary,
      };

      // localStorage.setItem(`snapshot:${id}`, JSON.stringify(snapshot)); // Remove localStorage usage
      try {
        await setSnapshot(database, id, snapshot);
      } catch (error) {
        console.error('Failed to save snapshot:', error);
        toast.error('Failed to save chat snapshot.');
      }
    },
    [database],
  );

  const restoreSnapshot = useCallback(async (id: string, snapshot?: Snapshot) => {
    // const snapshotStr = localStorage.getItem(`snapshot:${id}`); // Remove localStorage usage
    const container = await webcontainer;

    const validSnapshot = snapshot || { chatIndex: '', files: {} };

    if (!validSnapshot?.files) {
      return;
    }

    Object.entries(validSnapshot.files).forEach(async ([key, value]) => {
      if (key.startsWith(container.workdir)) {
        key = key.replace(container.workdir, '');
      }

      if (value?.type === 'folder') {
        await container.fs.mkdir(key, { recursive: true });
      }
    });
    Object.entries(validSnapshot.files).forEach(async ([key, value]) => {
      if (value?.type === 'file') {
        if (key.startsWith(container.workdir)) {
          key = key.replace(container.workdir, '');
        }

        await container.fs.writeFile(key, value.content, { encoding: value.isBinary ? undefined : 'utf8' });
      } else {
      }
    });

    // workbenchStore.files.setKey(snapshot?.files)
  }, []);

  return {
    ready: !mixedId || ready,
    initialMessages,
    updateChatMestaData: async (metadata: IChatMetadata) => {
      const id = chatId.get();

      if (!database || !id) {
        return;
      }

      try {
        await setMessages(database, id, initialMessages, urlId, description.get(), undefined, metadata);
        chatMetadata.set(metadata);
      } catch (error) {
        toast.error('Failed to update chat metadata');
        console.error(error);
      }
    },
    storeMessageHistory: async (messages: Message[]) => {
      console.log('🔍 storeMessageHistory called with:', {
        databaseExists: !!database,
        messagesLength: messages.length,
        persistenceEnabled,
      });

      if (!database || messages.length === 0) {
        console.log('❌ storeMessageHistory early return:', { database: !!database, messagesLength: messages.length });
        return;
      }

      const { firstArtifact } = workbenchStore;
      messages = messages.filter((m) => !m.annotations?.includes('no-store'));

      let _urlId = urlId;

      if (!urlId && firstArtifact?.id) {
        const urlId = await getUrlId(database, firstArtifact.id);
        _urlId = urlId;
        navigateChat(urlId);
        setUrlId(urlId);
      }

      let chatSummary: string | undefined = undefined;
      const lastMessage = messages[messages.length - 1];

      if (lastMessage.role === 'assistant') {
        const annotations = lastMessage.annotations as JSONValue[];
        const filteredAnnotations = (annotations?.filter(
          (annotation: JSONValue) =>
            annotation && typeof annotation === 'object' && Object.keys(annotation).includes('type'),
        ) || []) as { type: string; value: any } & { [key: string]: any }[];

        if (filteredAnnotations.find((annotation) => annotation.type === 'chatSummary')) {
          chatSummary = filteredAnnotations.find((annotation) => annotation.type === 'chatSummary')?.summary;
        }
      }

      takeSnapshot(messages[messages.length - 1].id, workbenchStore.files.get(), _urlId, chatSummary);

      if (!description.get() && firstArtifact?.title) {
        description.set(firstArtifact?.title);
      }

      // Ensure chatId.get() is used here as well
      if (initialMessages.length === 0 && !chatId.get()) {
        const nextId = await getNextId(database);

        chatId.set(nextId);

        if (!urlId) {
          navigateChat(nextId);
        }
      }

      // Ensure chatId.get() is used for the final setMessages call
      const finalChatId = chatId.get();

      if (!finalChatId) {
        console.error('Cannot save messages, chat ID is not set.');
        toast.error('Failed to save chat messages: Chat ID missing.');

        return;
      }

      console.log('💾 Saving messages to database:', {
        finalChatId,
        totalMessages: [...archivedMessages, ...messages].length,
        urlId,
        description: description.get(),
      });

      try {
        await setMessages(
          database,
          finalChatId, // Use the potentially updated chatId
          [...archivedMessages, ...messages],
          urlId,
          description.get(),
          undefined,
          chatMetadata.get(),
        );
        console.log('✅ Messages saved successfully');
      } catch (error) {
        console.error('❌ Failed to save messages:', error);
        toast.error('Failed to save chat messages');
        throw error;
      }
    },
    duplicateCurrentChat: async (listItemId: string) => {
      if (!database || (!mixedId && !listItemId)) {
        return;
      }

      try {
        const newId = await duplicateChat(database, mixedId || listItemId);
        navigate(`/chat/${newId}`);
        toast.success('Chat duplicated successfully');
      } catch (error) {
        toast.error('Failed to duplicate chat');
        console.log(error);
      }
    },
    importChat: async (description: string, messages: Message[], metadata?: IChatMetadata) => {
      if (!database) {
        return;
      }

      try {
        const newId = await createChatFromMessages(database, description, messages, metadata);
        window.location.href = `/chat/${newId}`;
        toast.success('Chat imported successfully');
      } catch (error) {
        if (error instanceof Error) {
          toast.error('Failed to import chat: ' + error.message);
        } else {
          toast.error('Failed to import chat');
        }
      }
    },
    exportChat: async (id = urlId) => {
      if (!database || !id) {
        return;
      }

      const chat = await getMessages(database, id);

      if (!chat) {
        toast.error('Chat not found');
        return;
      }

      const chatData = {
        messages: chat.messages,
        description: chat.description,
        exportDate: new Date().toISOString(),
      };

      const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-${new Date().toISOString()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  };
}

function navigateChat(nextId: string) {
  /**
   * FIXME: Using the intended navigate function causes a rerender for <Chat /> that breaks the app.
   *
   * `navigate(`/chat/${nextId}`, { replace: true });`
   */
  const url = new URL(window.location.href);
  url.pathname = `/chat/${nextId}`;

  window.history.replaceState({}, '', url);
}
