import { useState } from "react"
import Shindo from "./shindo_live"
import Dashboard from "./Dashboard"

const INIT_MSGS = [{role:"assistant", text:"Hello — I'm 震度 (Shindo), your seismic risk assistant.\n\nClick anywhere on Japan to run a simulation, then ask me anything about the event, fault zones, or historical precedents."}]

export default function App() {
  const [view, setView] = useState("shindo")
  const [chatMsgs,    setChatMsgs]    = useState(INIT_MSGS)
  const [chatInput,   setChatInput]   = useState("")
  const [chatLoading, setChatLoading] = useState(false)

  const chat = { chatMsgs, setChatMsgs, chatInput, setChatInput, chatLoading, setChatLoading }

  if (view === "dashboard") return <Dashboard onBack={() => setView("shindo")} chat={chat} />

  return (
    <div style={{ position: "relative" }}>
      <Shindo chat={chat} />
      <button
        onClick={() => setView("dashboard")}
        style={{
          position: "fixed", bottom: 16, right: 16, zIndex: 100,
          background: "#000b1a", border: "1px solid #003366",
          color: "#00e5ff", padding: "6px 14px", borderRadius: 6,
          fontSize: 11, cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
          letterSpacing: "0.08em", boxShadow: "0 0 16px rgba(0,100,200,0.2)",
        }}
      >
        DATA DASHBOARD →
      </button>
    </div>
  )
}
