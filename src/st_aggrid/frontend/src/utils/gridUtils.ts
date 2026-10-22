type CSSDict = { [key: string]: { [key: string]: string } }

const _injectedCSS = new Set<string>()
const _injectedAssets = new Set<string>()

export function getCSS(styles: CSSDict): string {
  const css = []
  for (const selector in styles) {
    let style = selector + " {"
    for (const prop in styles[selector]) {
      style += prop + ": " + styles[selector][prop] + ";"
    }
    style += "}"
    css.push(style)
  }
  return css.join("\n")
}

export function addCustomCSS(custom_css: CSSDict): void {
  const css = getCSS(custom_css)
  if (_injectedCSS.has(css)) return
  _injectedCSS.add(css)
  const styleSheet = document.createElement("style")
  styleSheet.type = "text/css"
  styleSheet.innerText = css
  document.head.appendChild(styleSheet)
}

export function injectProAssets(jsCode: string, cssCode?: string) {
  const key = (jsCode || "") + "|" + (cssCode || "")
  if (_injectedAssets.has(key)) return
  _injectedAssets.add(key)
  if (jsCode) {
    const script = document.createElement("script")
    script.textContent = jsCode
    document.body.appendChild(script)
  }
  if (cssCode) {
    const style = document.createElement("style")
    style.textContent = cssCode
    document.head.appendChild(style)
  }
}

export function parseJsCodeFromPython(v: string) {
  const JS_PLACEHOLDER = "::JSCODE::"
  const funcReg = new RegExp(`${JS_PLACEHOLDER}(.*?)${JS_PLACEHOLDER}`, "s")
  const match = funcReg.exec(v)
  if (match) {
    const funcStr = match[1]
    return new Function("return " + funcStr)()
  } else {
    return v
  }
}
