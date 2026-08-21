/**
 * Every --st-* property the theme recipes read.
 *
 * streamlitThemeSignature builds the staleness check out of this list, so a
 * property added to a recipe has to be added here too or a change to it will
 * not repaint the grid. test/security.test.mjs guards this by scanning
 * ThemeParser.tsx for --st-* literals and failing on any name missing from
 * this list.
 */
export const STREAMLIT_THEME_VARS = [
    '--st-primary-color',
    '--st-text-color',
    '--st-background-color',
    '--st-secondary-background-color',
    '--st-font',
] as const
