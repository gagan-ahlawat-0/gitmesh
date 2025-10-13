import { globSync } from 'fast-glob';
import fs from 'node:fs/promises';
import { basename } from 'node:path';
import { defineConfig, presetIcons, presetUno, transformerDirectives } from 'unocss';

const iconPaths = globSync('./icons/*.svg');

const collectionName = 'gitmesh';

const customIconCollection = iconPaths.reduce(
  (acc, iconPath) => {
    const [iconName] = basename(iconPath).split('.');

    acc[collectionName] ??= {};
    acc[collectionName][iconName] = async () => fs.readFile(iconPath, 'utf8');

    return acc;
  },
  {} as Record<string, Record<string, () => Promise<string>>>,
);

const BASE_COLORS = {
  white: '#FFFFFF',
  gray: {
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#E5E5E5',
    300: '#D4D4D4',
    400: '#A3A3A3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
    950: '#0A0A0A',
  },
  accent: {
    50: '#F8F5FF',
    100: '#F0EBFF',
    200: '#E1D6FF',
    300: '#CEBEFF',
    400: '#B69EFF',
    500: '#9C7DFF',
    600: '#8A5FFF',
    700: '#7645E8',
    800: '#6234BB',
    900: '#502D93',
    950: '#2D1959',
  },
  green: {
    50: '#F0FDF4',
    100: '#DCFCE7',
    200: '#BBF7D0',
    300: '#86EFAC',
    400: '#4ADE80',
    500: '#22C55E',
    600: '#16A34A',
    700: '#15803D',
    800: '#166534',
    900: '#14532D',
    950: '#052E16',
  },
  orange: {
    50: '#FFFAEB',
    100: '#FEEFC7',
    200: '#FEDF89',
    300: '#FEC84B',
    400: '#FDB022',
    500: '#F79009',
    600: '#DC6803',
    700: '#B54708',
    800: '#93370D',
    900: '#792E0D',
  },
  red: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    200: '#FECACA',
    300: '#FCA5A5',
    400: '#F87171',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C',
    800: '#991B1B',
    900: '#7F1D1D',
    950: '#450A0A',
  },
  blue: {
    50: '#EFF6FF',
    100: '#DBEAFE',
    200: '#BFDBFE',
    300: '#93C5FD',
    400: '#60A5FA',
    500: '#3B82F6',
    600: '#2563EB',
    700: '#1D4ED8',
    800: '#1E40AF',
    900: '#1E3A8A',
    950: '#172554',
  },
};

const COLOR_PRIMITIVES = {
  ...BASE_COLORS,
  alpha: {
    white: generateAlphaPalette(BASE_COLORS.white),
    gray: generateAlphaPalette(BASE_COLORS.gray[900]),
    red: generateAlphaPalette(BASE_COLORS.red[500]),
    blue: generateAlphaPalette(BASE_COLORS.blue[500]),
    accent: generateAlphaPalette(BASE_COLORS.accent[500]),
  },
};

export default defineConfig({
  safelist: [...Object.keys(customIconCollection[collectionName] || {}).map((x) => `i-gitmesh:${x}`)],
  shortcuts: {
    'gitmesh-ease-cubic-bezier': 'ease-[cubic-bezier(0.4,0,0.2,1)]',
    'transition-theme': 'transition-[background-color,border-color,color] duration-150 gitmesh-ease-cubic-bezier',
    kdb: 'bg-gitmesh-elements-code-background text-gitmesh-elements-code-text py-1 px-1.5 rounded-md',
    'max-w-chat': 'max-w-[var(--chat-max-width)]',
  },
  rules: [
    /**
     * This shorthand doesn't exist in Tailwind and we overwrite it to avoid
     * any conflicts with minified CSS classes.
     */
    ['b', {}],
  ],
  theme: {
    colors: {
      ...COLOR_PRIMITIVES,
      gitmesh: {
        elements: {
          borderColor: 'var(--gitmesh-elements-borderColor)',
          borderColorActive: 'var(--gitmesh-elements-borderColorActive)',
          background: {
            depth: {
              1: 'var(--gitmesh-elements-bg-depth-1)',
              2: 'var(--gitmesh-elements-bg-depth-2)',
              3: 'var(--gitmesh-elements-bg-depth-3)',
              4: 'var(--gitmesh-elements-bg-depth-4)',
            },
          },
          textPrimary: 'var(--gitmesh-elements-textPrimary)',
          textSecondary: 'var(--gitmesh-elements-textSecondary)',
          textTertiary: 'var(--gitmesh-elements-textTertiary)',
          code: {
            background: 'var(--gitmesh-elements-code-background)',
            text: 'var(--gitmesh-elements-code-text)',
          },
          button: {
            primary: {
              background: 'var(--gitmesh-elements-button-primary-background)',
              backgroundHover: 'var(--gitmesh-elements-button-primary-backgroundHover)',
              text: 'var(--gitmesh-elements-button-primary-text)',
            },
            secondary: {
              background: 'var(--gitmesh-elements-button-secondary-background)',
              backgroundHover: 'var(--gitmesh-elements-button-secondary-backgroundHover)',
              text: 'var(--gitmesh-elements-button-secondary-text)',
            },
            danger: {
              background: 'var(--gitmesh-elements-button-danger-background)',
              backgroundHover: 'var(--gitmesh-elements-button-danger-backgroundHover)',
              text: 'var(--gitmesh-elements-button-danger-text)',
            },
          },
          item: {
            contentDefault: 'var(--gitmesh-elements-item-contentDefault)',
            contentActive: 'var(--gitmesh-elements-item-contentActive)',
            contentAccent: 'var(--gitmesh-elements-item-contentAccent)',
            contentDanger: 'var(--gitmesh-elements-item-contentDanger)',
            backgroundDefault: 'var(--gitmesh-elements-item-backgroundDefault)',
            backgroundActive: 'var(--gitmesh-elements-item-backgroundActive)',
            backgroundAccent: 'var(--gitmesh-elements-item-backgroundAccent)',
            backgroundDanger: 'var(--gitmesh-elements-item-backgroundDanger)',
          },
          actions: {
            background: 'var(--gitmesh-elements-actions-background)',
            code: {
              background: 'var(--gitmesh-elements-actions-code-background)',
            },
          },
          artifacts: {
            background: 'var(--gitmesh-elements-artifacts-background)',
            backgroundHover: 'var(--gitmesh-elements-artifacts-backgroundHover)',
            borderColor: 'var(--gitmesh-elements-artifacts-borderColor)',
            inlineCode: {
              background: 'var(--gitmesh-elements-artifacts-inlineCode-background)',
              text: 'var(--gitmesh-elements-artifacts-inlineCode-text)',
            },
          },
          messages: {
            background: 'var(--gitmesh-elements-messages-background)',
            linkColor: 'var(--gitmesh-elements-messages-linkColor)',
            code: {
              background: 'var(--gitmesh-elements-messages-code-background)',
            },
            inlineCode: {
              background: 'var(--gitmesh-elements-messages-inlineCode-background)',
              text: 'var(--gitmesh-elements-messages-inlineCode-text)',
            },
          },
          icon: {
            success: 'var(--gitmesh-elements-icon-success)',
            error: 'var(--gitmesh-elements-icon-error)',
            primary: 'var(--gitmesh-elements-icon-primary)',
            secondary: 'var(--gitmesh-elements-icon-secondary)',
            tertiary: 'var(--gitmesh-elements-icon-tertiary)',
          },
          preview: {
            addressBar: {
              background: 'var(--gitmesh-elements-preview-addressBar-background)',
              backgroundHover: 'var(--gitmesh-elements-preview-addressBar-backgroundHover)',
              backgroundActive: 'var(--gitmesh-elements-preview-addressBar-backgroundActive)',
              text: 'var(--gitmesh-elements-preview-addressBar-text)',
              textActive: 'var(--gitmesh-elements-preview-addressBar-textActive)',
            },
          },
          terminals: {
            background: 'var(--gitmesh-elements-terminals-background)',
            buttonBackground: 'var(--gitmesh-elements-terminals-buttonBackground)',
          },
          dividerColor: 'var(--gitmesh-elements-dividerColor)',
          loader: {
            background: 'var(--gitmesh-elements-loader-background)',
            progress: 'var(--gitmesh-elements-loader-progress)',
          },
          prompt: {
            background: 'var(--gitmesh-elements-prompt-background)',
          },
          sidebar: {
            dropdownShadow: 'var(--gitmesh-elements-sidebar-dropdownShadow)',
            buttonBackgroundDefault: 'var(--gitmesh-elements-sidebar-buttonBackgroundDefault)',
            buttonBackgroundHover: 'var(--gitmesh-elements-sidebar-buttonBackgroundHover)',
            buttonText: 'var(--gitmesh-elements-sidebar-buttonText)',
          },
          cta: {
            background: 'var(--gitmesh-elements-cta-background)',
            text: 'var(--gitmesh-elements-cta-text)',
          },
        },
      },
    },
  },
  transformers: [transformerDirectives()],
  presets: [
    presetUno({
      dark: {
        light: '[data-theme="light"]',
        dark: '[data-theme="dark"]',
      },
    }),
    presetIcons({
      warn: true,
      collections: {
        ...customIconCollection,
      },
      unit: 'em',
    }),
  ],
});

/**
 * Generates an alpha palette for a given hex color.
 *
 * @param hex - The hex color code (without alpha) to generate the palette from.
 * @returns An object where keys are opacity percentages and values are hex colors with alpha.
 *
 * Example:
 *
 * ```
 * {
 *   '1': '#FFFFFF03',
 *   '2': '#FFFFFF05',
 *   '3': '#FFFFFF08',
 * }
 * ```
 */
function generateAlphaPalette(hex: string) {
  return [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].reduce(
    (acc, opacity) => {
      const alpha = Math.round((opacity / 100) * 255)
        .toString(16)
        .padStart(2, '0');

      acc[opacity] = `${hex}${alpha}`;

      return acc;
    },
    {} as Record<number, string>,
  );
}
