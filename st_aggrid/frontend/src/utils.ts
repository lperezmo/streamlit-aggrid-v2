// stole from https://github.com/andfanilo/streamlit-echarts/blob/master/streamlit_echarts/frontend/src/utils.js Thanks andfanilo
function mapObject(obj: Record<string, any>, fn: (val: any) => any, keysToIgnore: string[]): Record<string, any> {
    let keysToMap = Object.keys(obj)
    return keysToMap.reduce((res: Record<string, any>, key: string) => {
        if (!keysToIgnore.includes(key)) {
            res[key] = fn(obj[key]);
            return res
        }
        res[key] = obj[key];
        return res

    }, {})
}

function deepMap(obj: any, fn: (val: any) => any, keysToIgnore: string[] = []): any {
    const deepMapper = (val: any) =>
        val !== null && typeof val === "object" ? deepMap(val, fn) : fn(val)
    if (Array.isArray(obj)) {
        return obj.map(deepMapper)
    }
    if (typeof obj === "object") {
        return mapObject(obj, deepMapper, keysToIgnore)
    }
    return obj
}

export { deepMap }
