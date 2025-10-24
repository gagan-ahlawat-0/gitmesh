import { memo, useMemo } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import type { BundledLanguage } from 'shiki';
import { createScopedLogger } from '~/utils/logger';
import { rehypePlugins, remarkPlugins, allowedHTMLElements } from '~/utils/markdown';
import { Artifact, openArtifactInWorkbench } from './Artifact';
import { CodeBlock } from './CodeBlock';
import type { Message } from 'ai';
import styles from './Markdown.module.scss';
import ThoughtBox from './ThoughtBox';
import type { ProviderInfo } from '~/types/model';

const logger = createScopedLogger('MarkdownComponent');

interface MarkdownProps {
  children: string;
  html?: boolean;
  limitedMarkdown?: boolean;
  append?: (message: Message) => void;
  chatMode?: 'discuss' | 'build';
  setChatMode?: (mode: 'discuss' | 'build') => void;
  model?: string;
  provider?: ProviderInfo;
}

export const Markdown = memo(
  ({ children, html = false, limitedMarkdown = false, append, setChatMode, model, provider }: MarkdownProps) => {
    logger.trace('Render');

    const components = useMemo(() => {
      return {
        div: ({ className, children, node, ...props }) => {
          const dataProps = node?.properties as Record<string, unknown>;

          if (className?.includes('__gitmeshArtifact__')) {
            const messageId = node?.properties.dataMessageId as string;
            const artifactId = node?.properties.dataArtifactId as string;

            if (!messageId) {
              logger.error(`Invalid message id ${messageId}`);
            }

            if (!artifactId) {
              logger.error(`Invalid artifact id ${artifactId}`);
            }

            return <Artifact messageId={messageId} artifactId={artifactId} />;
          }

          if (className?.includes('__gitmeshSelectedElement__')) {
            const messageId = node?.properties.dataMessageId as string;
            const elementDataAttr = node?.properties.dataElement as string;

            // Parse the element data if it exists
            let elementData: any = null;

            if (elementDataAttr) {
              try {
                elementData = JSON.parse(elementDataAttr);
              } catch (e) {
                console.error('Failed to parse element data:', e);
              }
            }

            if (!messageId) {
              logger.error(`Invalid message id ${messageId}`);
            }

            return (
              <div className="bg-gitmesh-elements-background-depth-3 border border-gitmesh-elements-borderColor rounded-lg p-3 my-2">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono bg-gitmesh-elements-background-depth-1 px-2 py-1 rounded text-gitmesh-elements-textTer">
                    {elementData?.tagName}
                  </span>
                  {elementData?.className && (
                    <span className="text-xs text-gitmesh-elements-textSecondary">.{elementData.className}</span>
                  )}
                </div>
                <code className="block text-sm !text-gitmesh-elements-textSecondary !bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor p-2 rounded">
                  {elementData?.displayText}
                </code>
              </div>
            );
          }

          if (className?.includes('__gitmeshThought__')) {
            return <ThoughtBox title="Thought process">{children}</ThoughtBox>;
          }

          if (className?.includes('__gitmeshQuickAction__') || dataProps?.dataGitmeshQuickAction) {
            return <div className="flex items-center gap-2 flex-wrap mt-3.5">{children}</div>;
          }

          return (
            <div className={className} {...props}>
              {children}
            </div>
          );
        },
        pre: (props) => {
          const { children, node, ...rest } = props;

          const [firstChild] = node?.children ?? [];

          if (
            firstChild &&
            firstChild.type === 'element' &&
            firstChild.tagName === 'code' &&
            firstChild.children[0].type === 'text'
          ) {
            const { className, ...rest } = firstChild.properties;
            const [, language = 'plaintext'] = /language-(\w+)/.exec(String(className) || '') ?? [];

            return <CodeBlock code={firstChild.children[0].value} language={language as BundledLanguage} {...rest} />;
          }

          return <pre {...rest}>{children}</pre>;
        },
        button: ({ node, children, ...props }) => {
          const dataProps = node?.properties as Record<string, unknown>;

          if (
            dataProps?.class?.toString().includes('__gitmeshQuickAction__') ||
            dataProps?.dataGitmeshQuickAction === 'true'
          ) {
            const type = dataProps['data-type'] || dataProps.dataType;
            const message = dataProps['data-message'] || dataProps.dataMessage;
            const path = dataProps['data-path'] || dataProps.dataPath;
            const href = dataProps['data-href'] || dataProps.dataHref;

            const iconClassMap: Record<string, string> = {
              file: 'i-ph:file',
              message: 'i-ph:chats',
              implement: 'i-ph:code',
              link: 'i-ph:link',
              commit: 'i-ph:git-commit',
            };

            const safeType = typeof type === 'string' ? type : '';
            const iconClass = iconClassMap[safeType] ?? 'i-ph:question';

            return (
              <button
                className="rounded-md justify-center px-3 py-1.5 text-xs bg-gitmesh-elements-item-backgroundAccent text-gitmesh-elements-item-contentAccent opacity-90 hover:opacity-100 flex items-center gap-2 cursor-pointer"
                data-type={type}
                data-message={message}
                data-path={path}
                data-href={href}
                onClick={() => {
                  if (type === 'file') {
                    openArtifactInWorkbench(path);
                  } else if (type === 'message' && append) {
                    append({
                      id: `quick-action-message-${Date.now()}`,
                      content: [
                        {
                          type: 'text',
                          text: `[Model: ${model}]\n\n[Provider: ${provider?.name}]\n\n${message}`,
                        },
                      ] as any,
                      role: 'user',
                    });
                    console.log('Message appended:', message);
                  } else if (type === 'implement' && append && setChatMode) {
                    // Don't automatically switch to build mode - let user decide
                    append({
                      id: `quick-action-implement-${Date.now()}`,
                      content: [
                        {
                          type: 'text',
                          text: `[Model: ${model}]\n\n[Provider: ${provider?.name}]\n\n${message}`,
                        },
                      ] as any,
                      role: 'user',
                    });
                  } else if (type === 'commit' && append) {
                    // Trigger commit dialog directly instead of just appending message
                    if (typeof window !== 'undefined' && (window as any).gitmeshCommitAction) {
                      // Extract provider from message (GitHub or GitLab)
                      const messageStr = String(message);
                      const isGitHub = messageStr.toLowerCase().includes('github');
                      const isGitLab = messageStr.toLowerCase().includes('gitlab');

                      if (isGitHub) {
                        (window as any).gitmeshCommitAction('github');
                      } else if (isGitLab) {
                        (window as any).gitmeshCommitAction('gitlab');
                      } else {
                        // Default to GitHub if not specified
                        (window as any).gitmeshCommitAction('github');
                      }
                    } else {
                      // Fallback: append message if commit action not available
                      append({
                        id: `quick-action-commit-${Date.now()}`,
                        content: [
                          {
                            type: 'text',
                            text: `[Model: ${model}]\n\n[Provider: ${provider?.name}]\n\n${message}`,
                          },
                        ] as any,
                        role: 'user',
                      });
                    }

                    console.log('Commit action triggered:', message);
                  } else if (type === 'link' && typeof href === 'string') {
                    try {
                      const url = new URL(href, window.location.origin);
                      window.open(url.toString(), '_blank', 'noopener,noreferrer');
                    } catch (error) {
                      console.error('Invalid URL:', href, error);
                    }
                  }
                }}
              >
                <div className={`text-lg ${iconClass}`} />
                {children}
              </button>
            );
          }

          return <button {...props}>{children}</button>;
        },
      } satisfies Components;
    }, []);

    return (
      <ReactMarkdown
        allowedElements={allowedHTMLElements}
        className={styles.MarkdownContent}
        components={components}
        remarkPlugins={remarkPlugins(limitedMarkdown)}
        rehypePlugins={rehypePlugins(html)}
      >
        {stripCodeFenceFromArtifact(children)}
      </ReactMarkdown>
    );
  },
);

/**
 * Removes code fence markers (```) surrounding an artifact element while preserving the artifact content.
 * This is necessary because artifacts should not be wrapped in code blocks when rendered for rendering action list.
 *
 * @param content - The markdown content to process
 * @returns The processed content with code fence markers removed around artifacts
 *
 * @example
 * // Removes code fences around artifact
 * const input = "```xml\n<div class='__gitmeshArtifact__'></div>\n```";
 * stripCodeFenceFromArtifact(input);
 * // Returns: "\n<div class='__gitmeshArtifact__'></div>\n"
 *
 * @remarks
 * - Only removes code fences that directly wrap an artifact (marked with __gitmeshArtifact__ class)
 * - Handles code fences with optional language specifications (e.g. ```xml, ```typescript)
 * - Preserves original content if no artifact is found
 * - Safely handles edge cases like empty input or artifacts at start/end of content
 */
export const stripCodeFenceFromArtifact = (content: string) => {
  if (!content || !content.includes('__gitmeshArtifact__')) {
    return content;
  }

  const lines = content.split('\n');
  const artifactLineIndex = lines.findIndex((line) => line.includes('__gitmeshArtifact__'));

  // Return original content if artifact line not found
  if (artifactLineIndex === -1) {
    return content;
  }

  // Check previous line for code fence
  if (artifactLineIndex > 0 && lines[artifactLineIndex - 1]?.trim().match(/^```\w*$/)) {
    lines[artifactLineIndex - 1] = '';
  }

  if (artifactLineIndex < lines.length - 1 && lines[artifactLineIndex + 1]?.trim().match(/^```$/)) {
    lines[artifactLineIndex + 1] = '';
  }

  return lines.join('\n');
};
