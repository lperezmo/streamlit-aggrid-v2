import React, { useState, useRef, useEffect } from "react"

interface AiToolkitBarProps {
  onSubmit: (query: string) => void
  onReset: () => void
  status: string | null // null | "processing" | "success" | "error"
  explanation: string
  prompt: string
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    padding: "8px 0",
    fontFamily: "-apple-system, 'system-ui', sans-serif",
    fontSize: "13px",
  },
  controlsRow: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  },
  form: {
    display: "flex",
    flex: 1,
  },
  input: {
    flex: 1,
    height: "34px",
    padding: "5px 12px",
    fontSize: "13px",
    border: "1px solid var(--ag-border-color, #d0d5dd)",
    borderRight: "none",
    borderRadius: "6px 0 0 6px",
    backgroundColor: "var(--ag-background-color, #fff)",
    color: "var(--ag-foreground-color, #101828)",
    outline: "none",
    fontFamily: "inherit",
  },
  submitBtn: {
    height: "34px",
    padding: "0 14px",
    fontSize: "14px",
    cursor: "pointer",
    border: "1px solid var(--ag-border-color, #d0d5dd)",
    borderRadius: "0 6px 6px 0",
    backgroundColor: "var(--ag-background-color, #fff)",
    color: "var(--ag-foreground-color, #101828)",
    transition: "background-color 0.15s",
  },
  resetBtn: {
    height: "34px",
    padding: "0 14px",
    fontSize: "13px",
    cursor: "pointer",
    border: "1px solid var(--ag-border-color, #d0d5dd)",
    borderRadius: "6px",
    backgroundColor: "var(--ag-background-color, #fff)",
    color: "var(--ag-foreground-color, #101828)",
    whiteSpace: "nowrap" as const,
    transition: "background-color 0.15s",
  },
  responseRow: {
    display: "flex",
    gap: "16px",
    minHeight: "28px",
    alignItems: "flex-start",
  },
  statusBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "4px 12px",
    fontSize: "12px",
    borderRadius: "4px",
    fontFamily: "SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    whiteSpace: "nowrap" as const,
  },
  responsePanel: {
    flex: 1,
    padding: "6px 10px",
    borderRadius: "6px",
    border: "1px dashed var(--ag-border-color, #d0d5dd)",
    fontSize: "12px",
    lineHeight: "1.5",
    minHeight: "28px",
  },
  label: {
    display: "block",
    fontSize: "11px",
    opacity: 0.5,
    marginBottom: "2px",
  },
  msgBlock: {
    padding: "4px 6px",
    borderRadius: "4px",
    backgroundColor: "color-mix(in srgb, var(--ag-foreground-color, #101828) 3%, transparent)",
    border: "1px solid color-mix(in srgb, var(--ag-foreground-color, #101828) 10%, transparent)",
    marginBottom: "6px",
    fontSize: "12px",
  },
}

const statusStyles: Record<string, React.CSSProperties> = {
  processing: {
    backgroundColor: "color-mix(in srgb, var(--ag-foreground-color, #101828) 5%, transparent)",
    color: "var(--ag-foreground-color, #101828)",
    border: "1px solid color-mix(in srgb, var(--ag-foreground-color, #101828) 15%, transparent)",
  },
  success: {
    backgroundColor: "color-mix(in srgb, #0759c2 8%, transparent)",
    color: "#0759c2",
    border: "1px solid color-mix(in srgb, #0759c2 20%, transparent)",
  },
  error: {
    backgroundColor: "color-mix(in srgb, #dc0505 8%, transparent)",
    color: "#dc0505",
    border: "1px solid color-mix(in srgb, #dc0505 20%, transparent)",
  },
}

const statusText: Record<string, string> = {
  processing: "Processing request with OpenAI. LLM may take up to 30s to respond.",
  success: "Request processed successfully!",
  error: "Error processing request",
}

const statusIcon: Record<string, string> = {
  processing: "\u29D6",
  success: "\u2713",
  error: "\u2717",
}

const AiToolkitBar: React.FC<AiToolkitBarProps> = ({
  onSubmit,
  onReset,
  status,
  explanation,
  prompt,
}) => {
  const [inputValue, setInputValue] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const isProcessing = status === "processing"

  useEffect(() => {
    if (status === "success" || status === "error") {
      setInputValue("")
    }
  }, [status])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const query = inputValue.trim()
    if (query && !isProcessing) {
      onSubmit(query)
    }
  }

  return (
    <div style={styles.wrapper}>
      {/* Input row */}
      <div style={styles.controlsRow}>
        <form style={styles.form} onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder='Your prompt e.g. "hide age column"'
            disabled={isProcessing}
            style={{
              ...styles.input,
              opacity: isProcessing ? 0.6 : 1,
            }}
          />
          <button
            type="submit"
            disabled={isProcessing || !inputValue.trim()}
            style={{
              ...styles.submitBtn,
              opacity: isProcessing || !inputValue.trim() ? 0.5 : 1,
            }}
          >
            &rarr;
          </button>
        </form>
        <button
          onClick={onReset}
          disabled={isProcessing}
          style={{
            ...styles.resetBtn,
            opacity: isProcessing ? 0.5 : 1,
          }}
        >
          Reset Grid
        </button>
      </div>

      {/* Status + response row */}
      {(status || prompt || explanation) && (
        <div style={styles.responseRow}>
          {/* Status badge */}
          <div style={{ flex: "0 0 auto" }}>
            {status && (
              <code
                style={{
                  ...styles.statusBadge,
                  ...(statusStyles[status] || {}),
                }}
              >
                {statusText[status] || status}
                <b>{statusIcon[status] || ""}</b>
              </code>
            )}
          </div>

          {/* Response panel */}
          {(prompt || explanation) && (
            <div style={styles.responsePanel}>
              {prompt && (
                <>
                  <span style={styles.label}>Prompt</span>
                  <div style={styles.msgBlock}>
                    <em>{prompt}</em>
                  </div>
                </>
              )}
              {explanation && (
                <>
                  <span style={{ ...styles.label, textAlign: "right" }}>
                    Response
                  </span>
                  <div style={{ ...styles.msgBlock, marginBottom: 0 }}>
                    {explanation}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default AiToolkitBar
