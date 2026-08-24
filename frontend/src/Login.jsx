import { useState } from "react"
import { useI18n, LanguageToggle } from "./i18n"
import { MONO } from "./fonts"

const API = import.meta.env.VITE_API_URL

const FIELD = {
  width:"100%", background:"#ffffff", border:"1px solid #bdd6ea", borderRadius:6,
  padding:"9px 11px", color:"#12405f", fontSize:14, fontFamily:"inherit",
  outline:"none", marginTop:4,
}
const LABEL = {
  fontSize:10, color:"#4a7fa1", letterSpacing:"0.1em", fontWeight:700,
}

export default function Login({ onSignedIn }) {
  const { t, lang } = useI18n()
  const [mode,     setMode]     = useState("signup")
  const [email,    setEmail]    = useState("")
  const [password, setPassword] = useState("")
  const [busy,     setBusy]     = useState(false)
  const [error,    setError]    = useState(null)

  const isSignup = mode === "signup"

  const submit = async e => {
    e.preventDefault()
    if (busy) return
    setError(null)

    // Mirrors the backend's min_length=10 so the failure is immediate, not a round trip.
    if (isSignup && password.length < 10) {
      setError(t("login.passwordTooShort"))
      return
    }

    setBusy(true)
    try {
      const res = await fetch(`${API}/auth/${isSignup ? "signup" : "login"}`, {
        method:"POST",
        headers:{"Content-Type":"application/json","Accept-Language":lang},
        body: JSON.stringify({ email, password }),
      })
      const d = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(d?.detail || res.statusText)
      onSignedIn(d)
    } catch (err) {
      setError(
        err.message === "Failed to fetch" ? t("login.unreachable") : err.message
      )
    }
    setBusy(false)
  }

  return (
    <div style={{minHeight:"100vh",background:"#eef5fc",display:"flex",
      alignItems:"center",justifyContent:"center",padding:20,
      fontFamily:MONO}}>
      <div style={{width:"100%",maxWidth:380}}>

        <div style={{display:"flex",justifyContent:"flex-end",marginBottom:10}}>
          <LanguageToggle/>
        </div>

        <div style={{textAlign:"center",marginBottom:22}}>
          <div style={{fontSize:34,fontWeight:700,color:"#0369a1",letterSpacing:"0.04em"}}>震度</div>
          <div style={{fontSize:13,color:"#0a5c8a",letterSpacing:"0.16em",fontWeight:700,marginTop:2}}>
            SHINDO
          </div>
          <div style={{fontSize:11,color:"#648ba4",letterSpacing:"0.08em",marginTop:6}}>
            {t("login.tagline")}
          </div>
        </div>

        <form onSubmit={submit} style={{background:"#f7fbff",border:"1px solid #cfe0f0",
          borderRadius:8,padding:"20px 22px"}}>

          <div style={{display:"flex",gap:4,marginBottom:18}}>
            {[["signup",t("login.signup")],["login",t("login.signin")]].map(([m,label])=>(
              <button key={m} type="button" onClick={()=>{setMode(m);setError(null)}}
                style={{flex:1,padding:"7px 0",fontSize:11,letterSpacing:"0.08em",
                  fontWeight:700,cursor:"pointer",borderRadius:5,fontFamily:"inherit",
                  background:mode===m?"#cfe0f0":"transparent",
                  border:`1px solid ${mode===m?"#8fb6d8":"transparent"}`,
                  color:mode===m?"#0369a1":"#7398ac"}}>
                {label}
              </button>
            ))}
          </div>

          <label style={{display:"block",marginBottom:12}}>
            <span style={LABEL}>{t("login.email")}</span>
            <input type="email" value={email} required autoComplete="username"
              onChange={e=>setEmail(e.target.value)} style={FIELD}/>
          </label>

          <label style={{display:"block",marginBottom:6}}>
            <span style={LABEL}>{t("login.password")}</span>
            <input type="password" value={password} required
              autoComplete={isSignup ? "new-password" : "current-password"}
              onChange={e=>setPassword(e.target.value)} style={FIELD}/>
          </label>

          {isSignup && (
            <div style={{fontSize:10,color:"#8aa6b8",marginBottom:12}}>
              {t("login.passwordHint")}
            </div>
          )}

          {error && (
            <div role="alert" style={{fontSize:11,color:"#c2003f",background:"#fdf0f2",
              border:"1px solid #e8b4bd",borderRadius:5,padding:"7px 10px",marginBottom:12}}>
              {error}
            </div>
          )}

          <button type="submit" disabled={busy}
            style={{width:"100%",padding:"10px 0",marginTop:6,fontSize:12,
              letterSpacing:"0.1em",fontWeight:700,borderRadius:6,fontFamily:"inherit",
              cursor:busy?"default":"pointer",
              background:busy?"#dce9f6":"#0369a1",
              border:"1px solid #0369a1",
              color:busy?"#8aa6b8":"#ffffff"}}>
            {busy ? "…" : isSignup ? t("login.createAccount") : t("login.signin")}
          </button>
        </form>

        <div style={{fontSize:10,color:"#8aa6b8",textAlign:"center",marginTop:14,lineHeight:1.7}}>
          {t("login.note")}
        </div>
      </div>
    </div>
  )
}
