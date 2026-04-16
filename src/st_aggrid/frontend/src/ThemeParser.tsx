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

function hexToLuminance(hex: string): number {
    const c = hex.replace('#', '')
    const r = parseInt(c.substring(0, 2), 16) / 255
    const g = parseInt(c.substring(2, 4), 16) / 255
    const b = parseInt(c.substring(4, 6), 16) / 255
    const toLinear = (v: number) => v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
    return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b)
}

function getStreamlitThemeFromCSS(el?: Element | ShadowRoot | null): StreamlitThemeFromCSS {
    // Walk up to the element that holds --st-* vars
    const target = el ?? document.documentElement
    const styles = getComputedStyle(target as Element)
    const bgColor = styles.getPropertyValue('--st-background-color').trim() || '#ffffff'
    const isDark = bgColor.startsWith('#') && hexToLuminance(bgColor) < 0.4
    return {
        primaryColor: styles.getPropertyValue('--st-primary-color').trim() || '#ff4b4b',
        textColor: styles.getPropertyValue('--st-text-color').trim() || '#262730',
        backgroundColor: bgColor,
        secondaryBackgroundColor: styles.getPropertyValue('--st-secondary-background-color').trim() || '#f0f2f6',
        font: styles.getPropertyValue('--st-font').trim() || 'Source Sans Pro',
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

    private streamlitFontFamily(streamlitTheme: StreamlitThemeFromCSS) {
        const font = streamlitTheme.font?.split(",").at(0)?.trim() || "Source Sans Pro"
        return [font, {googleFont: font}]
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

        let theme: Theme = this.baseMapper[base]

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