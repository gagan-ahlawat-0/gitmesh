import type { ITheme } from '@xterm/xterm';

const style = getComputedStyle(document.documentElement);
const cssVar = (token: string) => style.getPropertyValue(token) || undefined;

export function getTerminalTheme(overrides?: ITheme): ITheme {
  return {
    cursor: cssVar('--gitmesh-elements-terminal-cursorColor'),
    cursorAccent: cssVar('--gitmesh-elements-terminal-cursorColorAccent'),
    foreground: cssVar('--gitmesh-elements-terminal-textColor'),
    background: cssVar('--gitmesh-elements-terminal-backgroundColor'),
    selectionBackground: cssVar('--gitmesh-elements-terminal-selection-backgroundColor'),
    selectionForeground: cssVar('--gitmesh-elements-terminal-selection-textColor'),
    selectionInactiveBackground: cssVar('--gitmesh-elements-terminal-selection-backgroundColorInactive'),

    // ansi escape code colors
    black: cssVar('--gitmesh-elements-terminal-color-black'),
    red: cssVar('--gitmesh-elements-terminal-color-red'),
    green: cssVar('--gitmesh-elements-terminal-color-green'),
    yellow: cssVar('--gitmesh-elements-terminal-color-yellow'),
    blue: cssVar('--gitmesh-elements-terminal-color-blue'),
    magenta: cssVar('--gitmesh-elements-terminal-color-magenta'),
    cyan: cssVar('--gitmesh-elements-terminal-color-cyan'),
    white: cssVar('--gitmesh-elements-terminal-color-white'),
    brightBlack: cssVar('--gitmesh-elements-terminal-color-brightBlack'),
    brightRed: cssVar('--gitmesh-elements-terminal-color-brightRed'),
    brightGreen: cssVar('--gitmesh-elements-terminal-color-brightGreen'),
    brightYellow: cssVar('--gitmesh-elements-terminal-color-brightYellow'),
    brightBlue: cssVar('--gitmesh-elements-terminal-color-brightBlue'),
    brightMagenta: cssVar('--gitmesh-elements-terminal-color-brightMagenta'),
    brightCyan: cssVar('--gitmesh-elements-terminal-color-brightCyan'),
    brightWhite: cssVar('--gitmesh-elements-terminal-color-brightWhite'),

    ...overrides,
  };
}
