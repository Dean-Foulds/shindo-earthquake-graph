import { useState } from "react"
import Shindo from "./shindo_live"
import Dashboard from "./Dashboard"
import Login from "./Login"

const INIT_MSGS = [{role:"assistant", text:"Hello — I'm 震度 (Shindo), your seismic risk assistant.\n\nClick anywhere on Japan to run a simulation, then ask me anything about the event, fault zones, or historical precedents."}]

const STORE = "shindo.session"

function loadSession() {
  try {
    const raw = localStorage.getItem(STORE)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export default function App() {
  const [session, setSession] = useState(loadSession)
  const [view, setView] = useState("shindo")
  const [chatMsgs,    setChatMsgs]    = useState(INIT_MSGS)
  const [chatInput,   setChatInput]   = useState("")
  const [chatLoading, setChatLoading] = useState(false)

  const signIn = s => {
    localStorage.setItem(STORE, JSON.stringify(s))
    setSession(s)
  }

  // Called when the API rejects our token, so an expired session can't strand the
  // user on a screen where every request 401s.
  const signOut = () => {
    localStorage.removeItem(STORE)
    setSession(null)
    setChatMsgs(INIT_MSGS)
  }

  if (!session) return <Login onSignedIn={signIn} />

  const chat = { chatMsgs, setChatMsgs, chatInput, setChatInput, chatLoading, setChatLoading }
  const auth = { token: session.token, email: session.email, signOut }

  if (view === "dashboard")
    return <Dashboard onBack={() => setView("shindo")} chat={chat} auth={auth} />

  return (
    <div style={{ position: "relative" }}>
      <Shindo chat={chat} auth={auth} />
      <div style={{position:"fixed",bottom:16,right:16,zIndex:100,display:"flex",gap:6}}>
        <button
          onClick={signOut}
          title={session.email}
          style={{
            background: "#f7fbff", border: "1px solid #bdd6ea",
            color: "#557f9e", padding: "6px 12px", borderRadius: 6,
            fontSize: 11, cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
            letterSpacing: "0.08em",
          }}
        >
          SIGN OUT
        </button>
        <button
          onClick={() => setView("dashboard")}
          style={{
            background: "#f7fbff", border: "1px solid #8fb6d8",
            color: "#0369a1", padding: "6px 14px", borderRadius: 6,
            fontSize: 11, cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
            letterSpacing: "0.08em", boxShadow: "0 1px 4px rgba(30,90,150,0.12)",
          }}
        >
          DATA DASHBOARD →
        </button>
      </div>
    </div>
  )
}
