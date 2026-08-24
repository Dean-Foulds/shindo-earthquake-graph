import { useState, useEffect } from "react"
import Shindo from "./shindo_live"
import Dashboard from "./Dashboard"
import Login from "./Login"
import { useI18n, LanguageToggle } from "./i18n"
import { MONO } from "./fonts"

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
  const { t } = useI18n()
  const [session, setSession] = useState(loadSession)
  const [view, setView] = useState("shindo")
  // `initial: true` marks the untouched greeting so switching language can
  // re-render it — a real conversation is left in the language it happened in.
  const [chatMsgs,    setChatMsgs]    = useState(() => [{role:"assistant", text:t("chat.greeting"), initial:true}])
  const [chatInput,   setChatInput]   = useState("")
  const [chatLoading, setChatLoading] = useState(false)

  // `t` is memoised on `lang`, so this fires exactly once per language change.
  useEffect(() => {
    setChatMsgs(msgs =>
      msgs.some(m => m.initial)
        ? msgs.map(m => (m.initial ? {...m, text: t("chat.greeting")} : m))
        : msgs
    )
  }, [t])

  const signIn = s => {
    localStorage.setItem(STORE, JSON.stringify(s))
    setSession(s)
  }

  // Called when the API rejects our token, so an expired session can't strand the
  // user on a screen where every request 401s.
  const signOut = () => {
    localStorage.removeItem(STORE)
    setSession(null)
    setChatMsgs([{role:"assistant", text:t("chat.greeting"), initial:true}])
  }

  if (!session) return <Login onSignedIn={signIn} />

  const chat = { chatMsgs, setChatMsgs, chatInput, setChatInput, chatLoading, setChatLoading }
  const auth = { token: session.token, email: session.email, signOut }

  if (view === "dashboard")
    return <Dashboard onBack={() => setView("shindo")} chat={chat} auth={auth} />

  return (
    <div style={{ position: "relative" }}>
      <Shindo chat={chat} auth={auth} />
      <div style={{position:"fixed",bottom:16,right:16,zIndex:100,display:"flex",gap:6,alignItems:"center"}}>
        <LanguageToggle compact />
        <button
          onClick={signOut}
          title={session.email}
          style={{
            background: "#f7fbff", border: "1px solid #bdd6ea",
            color: "#557f9e", padding: "6px 12px", borderRadius: 6,
            fontSize: 11, cursor: "pointer", fontFamily: MONO,
            letterSpacing: "0.08em",
          }}
        >
          {t("nav.signOut")}
        </button>
        <button
          onClick={() => setView("dashboard")}
          style={{
            background: "#f7fbff", border: "1px solid #8fb6d8",
            color: "#0369a1", padding: "6px 14px", borderRadius: 6,
            fontSize: 11, cursor: "pointer", fontFamily: MONO,
            letterSpacing: "0.08em", boxShadow: "0 1px 4px rgba(30,90,150,0.12)",
          }}
        >
          {t("nav.dashboard")}
        </button>
      </div>
    </div>
  )
}
