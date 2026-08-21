import { themeQuartz,
    themeAlpine,
    themeBalham,
    themeMaterial,
    Theme,
    colorSchemeLight,
    colorSchemeLightWarm,
    colorSchemeLightCold,
    colorSchemeDark,
    colorSchemeDarkWarm,
    colorSchemeDarkBlue,
    iconSetQuartz,
    iconSetQuartzLight,
    iconSetQuartzBold,
    iconSetAlpine,
    iconSetMaterial,
    iconSetQuartzRegular,
    Part,
} from 'ag-grid-community';

import isEmpty from 'lodash/isEmpty'

import { STREAMLIT_THEME_VARS } from './streamlitThemeVars'


// In CCv2, Streamlit injects --st-* CSS custom properties on the component's
// parentElement (or its shadow host). We must read from that element, not from
// document.documentElement.
interface StreamlitThemeFromCSS {
    primaryColor: string
    textColor: string
    backgroundColor: string
    secondaryBackgroundColor: string
    font: string
    base: 'light' | 'dark'
}

/**
 * The element whose computed style carries the --st-* properties.
 *
 * With isolate_styles=False (what _compat.py always registers) this is the
 * component's own parentElement. The `host` hop keeps this working if style
 * isolation is ever turned on, where parentElement is a ShadowRoot and has no
 * computed style of its own. document.documentElement is a last resort that
 * resolves nothing useful: Streamlit declares these properties on the element
 * container, never on :root, so reading the root returns empty strings and
 * every lookup below silently takes its fallback.
 */
function resolveThemeHost(el?: Element | ShadowRoot | null): Element {
    return (el as ShadowRoot | null)?.host ?? (el as Element | null) ?? document.documentElement
}

function parseColorChannels(color: string): [number, number, number] | null {
    const value = color.trim()

    // getComputedStyle hands back rgb()/rgba() for anything it resolved itself,
    // such as the document background read below.
    const rgb = value.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i)
    if (rgb) {
        return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])]
    }

    const hex = value.startsWith('#') ? value.slice(1) : ''
    const full = hex.length === 3 ? hex.split('').map(c => c + c).join('') : hex
    if (!/^[0-9a-f]{6}$/i.test(full)) {
        return null
    }
    return [
        parseInt(full.slice(0, 2), 16),
        parseInt(full.slice(2, 4), 16),
        parseInt(full.slice(4, 6), 16),
    ]
}

function isDarkColor(color: string): boolean {
    const channels = parseColorChannels(color)
    if (!channels) {
        return false
    }
    const toLinear = (v: number) => {
        const c = v / 255
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    }
    const [r, g, b] = channels
    const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b)
    return luminance < 0.4
}

/**
 * Streamlit's background color, which is also what decides light vs dark.
 *
 * An absent --st-background-color means the read landed outside the app subtree
 * or on a Streamlit that does not publish the property. Assuming light there
 * puts a white grid on a dark page, so fall back to what the page actually
 * renders before falling back to a guess.
 */
function resolveBackgroundColor(styles: CSSStyleDeclaration): string {
    const fromTheme = styles.getPropertyValue('--st-background-color').trim()
    if (fromTheme) {
        return fromTheme
    }

    const bodyBackground = getComputedStyle(document.body).backgroundColor
    if (bodyBackground && bodyBackground !== 'transparent' && bodyBackground !== 'rgba(0, 0, 0, 0)') {
        return bodyBackground
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? '#0e1117' : '#ffffff'
}

/**
 * The values behind every --st-* property the recipes read, plus the resolved
 * background, joined.
 *
 * The recipes bake their colors into an AG Grid theme at parse time, and a
 * Streamlit appearance change rewrites these properties without touching the
 * `theme` argument the app passed. Comparing this string across renders is
 * what tells the grid the palette it was built with has gone stale.
 *
 * The resolved background is part of the signature even when it equals the raw
 * --st-background-color: when that property is absent, resolveBackgroundColor
 * falls back to document.body and then to prefers-color-scheme, and an OS
 * appearance flip changes those while every --st-* value stays empty. Without
 * this term such a flip would leave the signature constant ("||||" plus a
 * stale background) and the grid would keep its old palette.
 */
export function streamlitThemeSignature(el?: Element | ShadowRoot | null): string {
    const styles = getComputedStyle(resolveThemeHost(el))
    return STREAMLIT_THEME_VARS
        .map(name => styles.getPropertyValue(name).trim())
        .concat(resolveBackgroundColor(styles))
        .join('|')
}

function getStreamlitThemeFromCSS(el?: Element | ShadowRoot | null): StreamlitThemeFromCSS {
    const styles = getComputedStyle(resolveThemeHost(el))
    const backgroundColor = resolveBackgroundColor(styles)
    const isDark = isDarkColor(backgroundColor)
    return {
        primaryColor: styles.getPropertyValue('--st-primary-color').trim() || '#ff4b4b',
        // The remaining fallbacks follow the resolved appearance. A light
        // default on a dark background is how the unset case turns into black
        // text on a near-black grid.
        textColor: styles.getPropertyValue('--st-text-color').trim() || (isDark ? '#fafafa' : '#262730'),
        backgroundColor,
        secondaryBackgroundColor: styles.getPropertyValue('--st-secondary-background-color').trim() || (isDark ? '#262730' : '#f0f2f6'),
        font: styles.getPropertyValue('--st-font').trim() || 'Source Sans, sans-serif',
        base: isDark ? 'dark' : 'light',
    }
}

type stAggridThemeOptions = {
    themeName: string,
    base: string,
    params: { [key: string]: any }
    parts: string[],
}

class ThemeParser {
    private baseMapper : { [key: string] : Theme} = {
        quartz: themeQuartz,
        alpine: themeAlpine,
        balham: themeBalham,
        material: themeMaterial,
    }

    private partsMapper : { [key: string ] : Part }= {
        colorSchemeLight: colorSchemeLight,
        colorSchemeLightWarm: colorSchemeLightWarm,
        colorSchemeLightCold: colorSchemeLightCold,
        colorSchemeDark: colorSchemeDark,
        colorSchemeDarkWarm: colorSchemeDarkWarm,
        colorSchemeDarkBlue: colorSchemeDarkBlue,
        iconSetQuartz: iconSetQuartz({strokeWidth: 1.5}),
        iconSetQuartzLight: iconSetQuartzLight,
        iconSetQuartzBold: iconSetQuartzBold,
        iconSetAlpine: iconSetAlpine,
        iconSetMaterial: iconSetMaterial,
        iconSetQuartzRegular: iconSetQuartzRegular
    }

    private streamlitFontFamily(streamlitTheme: StreamlitThemeFromCSS): string[] {
        // streamlitTheme.font is a full computed/normalized stack, e.g. '"Source Sans", sans-serif'.
        // getComputedStyle / --st-font wrap multi-word families in quotes; strip them so AG Grid
        // (which re-quotes any family containing spaces) does not emit doubled quotes like ""Source Sans"".
        // The grid renders inline in the same document where Streamlit already loaded the face, so we
        // reference the family directly and do not force a googleFont fetch.
        const stack = (streamlitTheme.font || "Source Sans, sans-serif")
            .split(",")
            .map(s => s.trim().replace(/^['"]+|['"]+$/g, ""))
            .filter(Boolean)
        return stack.length ? stack : ["sans-serif"]
    }

    streamlitRecipe(el?: Element | ShadowRoot | null): Theme{
        const streamlitTheme = getStreamlitThemeFromCSS(el)
        let theme : Theme = this.baseMapper['balham']

        theme = theme.withParams({
            accentColor: streamlitTheme.primaryColor,
            fontFamily: this.streamlitFontFamily(streamlitTheme),
            foregroundColor: streamlitTheme.textColor,
            backgroundColor: streamlitTheme.backgroundColor
        }).withPart(iconSetQuartzLight)
        .withPart(this.partsMapper.iconSetQuartzRegular)
        if (streamlitTheme.base === 'dark'){
            theme = theme.withPart(colorSchemeDark)
        }

        return theme
    }

    quartzRecipe(el?: Element | ShadowRoot | null) {
        const streamlitTheme = getStreamlitThemeFromCSS(el)
        let theme: Theme = themeQuartz.withParams({fontFamily: this.streamlitFontFamily(streamlitTheme)})
        if (streamlitTheme.base === 'dark') theme = theme.withPart(colorSchemeDark)
        return theme
    }

    alpineRecipe(el?: Element | ShadowRoot | null) {
        const streamlitTheme = getStreamlitThemeFromCSS(el)
        let theme: Theme = themeAlpine.withParams({fontFamily: this.streamlitFontFamily(streamlitTheme)})
        if (streamlitTheme.base === 'dark') theme = theme.withPart(colorSchemeDark)
        return theme
    }

    balhamRecipe(el?: Element | ShadowRoot | null) {
        const streamlitTheme = getStreamlitThemeFromCSS(el)
        let theme: Theme = themeBalham.withParams({fontFamily: this.streamlitFontFamily(streamlitTheme)})
        if (streamlitTheme.base === 'dark') theme = theme.withPart(colorSchemeDark)
        return theme
    }

    materialRecipe(el?: Element | ShadowRoot | null) {
        const streamlitTheme = getStreamlitThemeFromCSS(el)
        if (streamlitTheme.base === 'dark') {
            return themeMaterial
                .withParams({
                    fontFamily: this.streamlitFontFamily(streamlitTheme),
                    headerTextColor: streamlitTheme.textColor,
                })
                .withPart(colorSchemeDark)
        }
        return themeMaterial.withParams({fontFamily: this.streamlitFontFamily(streamlitTheme)})
    }

    customRecipe(gridOptionsTheme: stAggridThemeOptions) : Theme {
        const {base, params, parts} = gridOptionsTheme

        // A custom theme built without an explicit base still has to render.
        let theme: Theme = this.baseMapper[base] ?? this.baseMapper['quartz']

        if (! isEmpty(params)){
            theme = theme.withParams(params)
        }

        if (! isEmpty(parts)){
            theme = parts.reduce((acc, partName) => {const part =  this.partsMapper[partName];  return acc.withPart(part)}, theme)
    
        }
      
        return theme
    }


    parse(gridOptionsTheme: stAggridThemeOptions, el?: Element | ShadowRoot | null) : Theme {
        const { themeName } = gridOptionsTheme;

        const recipeMapper: { [key: string]: () => Theme } = {
            streamlit: () => this.streamlitRecipe(el),
            quartz: () => this.quartzRecipe(el),
            alpine: () => this.alpineRecipe(el),
            balham: () => this.balhamRecipe(el),
            material: () => this.materialRecipe(el),
            custom: () => this.customRecipe(gridOptionsTheme)
        };

        const recipe = recipeMapper[themeName] || (() => themeBalham);
        return recipe();
    }
}


export {ThemeParser}