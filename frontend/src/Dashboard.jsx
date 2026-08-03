import { useState, useRef, useEffect, useCallback } from "react"
import ReactMarkdown from "react-markdown"

function useWindowWidth() {
  const [w, setW] = useState(window.innerWidth)
  useEffect(() => {
    const h = () => setW(window.innerWidth)
    window.addEventListener("resize", h)
    return () => window.removeEventListener("resize", h)
  }, [])
  return w
}

// ── Markdown renderer ───────────────────────────────────────────
const MD = {
  p:      ({children}) => <p style={{margin:"0 0 8px",lineHeight:1.7}}>{children}</p>,
  strong: ({children}) => <strong style={{color:"#08365c",fontWeight:700}}>{children}</strong>,
  em:     ({children}) => <em style={{color:"#12405f",fontStyle:"italic"}}>{children}</em>,
  h1:     ({children}) => <div style={{fontSize:16,fontWeight:700,color:"#0369a1",margin:"10px 0 5px",borderBottom:"1px solid #cfe0f0",paddingBottom:3}}>{children}</div>,
  h2:     ({children}) => <div style={{fontSize:15,fontWeight:700,color:"#0369a1",margin:"8px 0 4px"}}>{children}</div>,
  h3:     ({children}) => <div style={{fontSize:14,fontWeight:700,color:"#0a5c8a",margin:"6px 0 3px"}}>{children}</div>,
  ul:     ({children}) => <ul style={{margin:"4px 0",paddingLeft:18}}>{children}</ul>,
  ol:     ({children}) => <ol style={{margin:"4px 0",paddingLeft:18}}>{children}</ol>,
  li:     ({children}) => <li style={{margin:"3px 0",color:"#1c4a6b"}}>{children}</li>,
  code:   ({inline,children}) => inline
    ? <code style={{background:"#cfe0f0",border:"1px solid #bdd6ea",borderRadius:3,padding:"1px 6px",fontSize:12,color:"#08365c",fontFamily:"inherit"}}>{children}</code>
    : <pre style={{background:"#e9f1fa",border:"1px solid #cfe0f0",borderRadius:5,padding:"10px 12px",margin:"6px 0",overflowX:"auto",fontSize:12,color:"#12405f",fontFamily:"inherit",lineHeight:1.6}}><code>{children}</code></pre>,
  blockquote: ({children}) => <blockquote style={{borderLeft:"2px solid #8fb6d8",margin:"6px 0",paddingLeft:12,color:"#35759b"}}>{children}</blockquote>,
  hr:     () => <hr style={{border:"none",borderTop:"1px solid #cfe0f0",margin:"8px 0"}}/>,
  a:      ({href,children}) => <a href={href} target="_blank" rel="noreferrer" style={{color:"#2b7ba8",textDecoration:"underline"}}>{children}</a>,
  table:  ({children}) => <table style={{borderCollapse:"collapse",width:"100%",margin:"6px 0",fontSize:13}}>{children}</table>,
  th:     ({children}) => <th style={{padding:"5px 10px",background:"#cfe0f0",color:"#0369a1",textAlign:"left",borderBottom:"1px solid #bdd6ea"}}>{children}</th>,
  td:     ({children}) => <td style={{padding:"4px 10px",borderBottom:"1px solid #dce9f6",color:"#1c4a6b"}}>{children}</td>,
}

function ChatBubble({msg}) {
  const isUser = msg.role === "user"
  return (
    <div style={{marginBottom:10}}>
      <div style={{fontSize:14,lineHeight:1.75,padding:"10px 14px",borderRadius:6,
        background:isUser?"#cfe0f0":"#eaf2fb",
        border:`1px solid ${isUser?"#8fb6d8":"#d5e5f4"}`,
        color:isUser?"#12405f":"#1c4a6b",wordBreak:"break-word"}}>
        {isUser&&<div style={{fontSize:10,fontWeight:700,color:"#7398ac",letterSpacing:"0.1em",marginBottom:4}}>YOU</div>}
        {isUser
          ? <span style={{whiteSpace:"pre-wrap"}}>{msg.text}</span>
          : <ReactMarkdown components={MD}>{msg.text}</ReactMarkdown>
        }
      </div>
    </div>
  )
}

function ChatPanel({ chat, mobile }) {
  const { chatMsgs: msgs, setChatMsgs: setMsgs, chatInput: input, setChatInput: setInput, chatLoading: loading, setChatLoading: setLoading } = chat
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({behavior:"smooth"}) }, [msgs])

  const send = async () => {
    const txt = input.trim(); if (!txt || loading) return
    setInput(""); setLoading(true)
    const next = [...msgs, {role:"user", text:txt}]
    setMsgs(next)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/agent/chat`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({messages: next.slice(-12).map(m=>({role:m.role,text:m.text}))}),
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.detail||res.statusText) }
      const d = await res.json()
      setMsgs(m=>[...m,{role:"assistant",text:d.reply}])
    } catch(err) {
      setMsgs(m=>[...m,{role:"assistant",text:`Error: ${err.message}`}])
    }
    setLoading(false)
  }

  return (
    <div style={{width:mobile?"100%":360,flexShrink:0,display:"flex",flexDirection:"column",
      borderLeft:mobile?"none":"1px solid #cfe0f0",borderTop:mobile?"1px solid #cfe0f0":"none",
      background:"#f7fbff",height:mobile?360:"auto"}}>
      {/* Header */}
      <div style={{padding:"10px 18px",borderBottom:"1px solid #cfe0f0",flexShrink:0,display:"flex",alignItems:"center",justifyContent:"space-between"}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:8,height:8,borderRadius:"50%",background:"#0369a1",boxShadow:"0 0 0 3px rgba(3,105,161,0.16)"}}/>
          <div>
            <div style={{fontSize:15,fontWeight:800,letterSpacing:"0.08em",color:"#0369a1"}}>震度 SHINDO</div>
            <div style={{fontSize:10,color:"#7398ac",letterSpacing:"0.12em",marginTop:1}}>SEISMIC INTELLIGENCE AGENT</div>
          </div>
        </div>
      </div>
      {/* Messages */}
      <div style={{flex:1,overflowY:"auto",padding:"14px"}}>
        {msgs.map((m,i)=><ChatBubble key={i} msg={m}/>)}
        {loading&&<div style={{padding:"10px 14px",background:"#eaf2fb",border:"1px solid #d5e5f4",borderRadius:6,color:"#8aa6b8",fontSize:13}}>
          <span>analyzing </span>
          {[0,1,2].map(i=><span key={i} style={{display:"inline-block",width:4,height:4,borderRadius:"50%",background:"#0369a1",margin:"0 2px",animation:`bounce 1.2s ${i*0.2}s infinite`}}/>)}
        </div>}
        <div ref={endRef}/>
      </div>
      {/* Input */}
      <div style={{padding:"10px 14px 14px",borderTop:"1px solid #cfe0f0",flexShrink:0}}>
        <div style={{display:"flex",gap:6,alignItems:"flex-end"}}>
          <textarea value={input} onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}}}
            placeholder="Ask about fault zones, nuclear risk, historical events…"
            rows={2}
            style={{flex:1,background:"#eaf2fb",border:"1px solid #bdd6ea",borderRadius:6,
              padding:"8px 10px",color:"#12405f",fontSize:14,fontFamily:"inherit",
              resize:"none",outline:"none",lineHeight:1.5}}/>
          <button onClick={send} disabled={!input.trim()||loading}
            style={{height:50,padding:"0 14px",background:input.trim()&&!loading?"#8fb6d8":"#eaf2fb",
              border:"1px solid #8fb6d8",borderRadius:6,
              color:input.trim()&&!loading?"#0369a1":"#b3c6d3",
              cursor:input.trim()&&!loading?"pointer":"default",
              fontSize:18,fontFamily:"inherit",transition:"all 0.2s"}}>›</button>
        </div>
        <div style={{fontSize:10,color:"#9db4c4",marginTop:5}}>Enter to send · Shift+Enter for newline</div>
      </div>
    </div>
  )
}

// ── Sample EDA data (representative of Japan seismic dataset) ──
const MAG_DIST = [
  {bin:"4.0–4.4",count:1842,pct:38},
  {bin:"4.5–4.9",count:1204,pct:25},
  {bin:"5.0–5.4",count:761, pct:16},
  {bin:"5.5–5.9",count:432, pct:9},
  {bin:"6.0–6.4",count:234, pct:5},
  {bin:"6.5–6.9",count:124, pct:3},
  {bin:"7.0–7.4",count:76,  pct:2},
  {bin:"7.5+",   count:47,  pct:1},
]
const DEPTH_DIST = [
  {bin:"0–10",  count:412, pct:9, label:"Crustal"},
  {bin:"10–30", count:1680,pct:35,label:"Crustal"},
  {bin:"30–70", count:1320,pct:27,label:"Transition"},
  {bin:"70–150",count:890, pct:18,label:"Intraslab"},
  {bin:"150–300",count:380,pct:8, label:"Deep"},
  {bin:"300+",  count:138, pct:3, label:"Deep"},
]
const FAULT_RISK = [
  {name:"Japan Trench",     type:"subduction",  events:1240,deaths:22000,maxMag:9.1,col:"#d93d2b"},
  {name:"Nankai Trough",    type:"subduction",  events:380, deaths:8800, maxMag:8.4,col:"#cc7000"},
  {name:"Sagami Trough",    type:"subduction",  events:210, deaths:99000,maxMag:7.9,col:"#d8478f"},
  {name:"Median Tectonic",  type:"strike_slip", events:180, deaths:6500, maxMag:7.2,col:"#8b3fd6"},
  {name:"Itoigawa-Shizuoka",type:"strike_slip", events:95,  deaths:2400, maxMag:7.1,col:"#2b7fd4"},
  {name:"Noto System",      type:"reverse",     events:64,  deaths:245,  maxMag:7.6,col:"#17a05e"},
]
const TOP_PREFS = [
  {name:"Miyagi",   score:94,quakes:890,tsunamis:12,npp:2},
  {name:"Iwate",    score:87,quakes:720,tsunamis:10,npp:1},
  {name:"Fukushima",score:85,quakes:680,tsunamis:8, npp:2},
  {name:"Shizuoka", score:82,quakes:310,tsunamis:3, npp:1},
  {name:"Tokyo",    score:78,quakes:440,tsunamis:4, npp:0},
  {name:"Aichi",    score:74,quakes:280,tsunamis:3, npp:1},
  {name:"Kochi",    score:71,quakes:190,tsunamis:7, npp:0},
  {name:"Mie",      score:68,quakes:175,tsunamis:6, npp:0},
]
const DECADE_DATA = [
  {decade:"1900s",quakes:28,tsunamis:4,deaths:82000},
  {decade:"1910s",quakes:34,tsunamis:3,deaths:107000},
  {decade:"1920s",quakes:41,tsunamis:5,deaths:142000},
  {decade:"1930s",quakes:38,tsunamis:3,deaths:3100},
  {decade:"1940s",quakes:52,tsunamis:6,deaths:1900},
  {decade:"1950s",quakes:67,tsunamis:4,deaths:1200},
  {decade:"1960s",quakes:81,tsunamis:5,deaths:280},
  {decade:"1970s",quakes:94,tsunamis:3,deaths:116},
  {decade:"1980s",quakes:112,tsunamis:4,deaths:104},
  {decade:"1990s",quakes:189,tsunamis:7,deaths:6437},
  {decade:"2000s",quakes:241,tsunamis:5,deaths:1540},
  {decade:"2010s",quakes:312,tsunamis:9,deaths:22000},
  {decade:"2020s",quakes:198,tsunamis:4,deaths:310},
]

// ── Cypher queries ──────────────────────────────────────────────
const QUERIES = [
  {
    id:1, title:"Cascade Trace — 2011 Tohoku",
    desc:"Follow a full disaster chain: fault zone → earthquake → tsunami → prefecture → nuclear facility.",
    cypher:`MATCH path =
    (fz:FaultZone)<-[:ORIGINATED_ON]-(eq:Earthquake)
    -[:TRIGGERED]->(t:Tsunami)
    -[:INUNDATED]->(pf:Prefecture)
    <-[:LOCATED_IN]-(nf:NuclearFacility)
WHERE eq.magnitude >= 8.5
RETURN fz.name, eq.magnitude, t.max_height_m,
       pf.name, nf.name, nf.status
ORDER BY eq.magnitude DESC`,
    tags:["cascade","tsunami","nuclear"],
  },
  {
    id:2, title:"Compounded Risk Corridors",
    desc:"Prefectures on subduction faults with a nuclear plant and Pacific coast exposure.",
    cypher:`MATCH (fz:FaultZone)-[:UNDERLIES]->(pf:Prefecture)
      <-[:CONTAINS]-(nf:NuclearFacility)
WHERE fz.type = 'subduction'
  AND pf.coast IN ['pacific', 'both']
RETURN pf.name, fz.name, nf.name, nf.status,
       fz.predicted_max_mag
ORDER BY fz.predicted_max_mag DESC`,
    tags:["risk","subduction","nuclear"],
  },
  {
    id:3, title:"Historical Analog Finder",
    desc:"Find past M7.5+ subduction events to use as analogs for Nankai Trough scenarios.",
    cypher:`MATCH (eq:Earthquake)-[:ORIGINATED_ON]->(fz:FaultZone)
WHERE fz.type = 'subduction'
  AND eq.magnitude >= 7.5
  AND eq.depth_km BETWEEN 10 AND 60
WITH eq, fz
MATCH (eq)-[:STRUCK]->(pf:Prefecture)
OPTIONAL MATCH (eq)-[:TRIGGERED]->(t:Tsunami)
RETURN eq.time, eq.magnitude, fz.name,
       pf.name, eq.deaths, t.max_height_m
ORDER BY eq.magnitude DESC
LIMIT 20`,
    tags:["analog","historical","subduction"],
  },
  {
    id:4, title:"Nuclear Proximity Risk",
    desc:"Every M6.5+ earthquake that struck within 50km of a nuclear plant.",
    cypher:`MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility)
WHERE eq.magnitude >= 6.5
MATCH (eq)-[:ORIGINATED_ON]->(fz:FaultZone)
RETURN eq.time, eq.magnitude, eq.depth_km,
       nf.name, nf.status, fz.name
ORDER BY eq.magnitude DESC`,
    tags:["nuclear","proximity","risk"],
  },
  {
    id:5, title:"Decade Pattern Analysis",
    desc:"Which decades saw the most seismic activity and tsunami events?",
    cypher:`MATCH (eq:Earthquake)-[:IN_DECADE]->(d:Decade)
OPTIONAL MATCH (eq)-[:TRIGGERED]->(t:Tsunami)
RETURN d.label,
       count(eq)                    AS total_quakes,
       round(avg(eq.magnitude), 2)  AS avg_magnitude,
       max(eq.magnitude)            AS max_magnitude,
       count(t)                     AS tsunamis,
       sum(COALESCE(eq.deaths, 0))  AS known_deaths
ORDER BY d.year`,
    tags:["temporal","trends","tsunami"],
  },
  {
    id:6, title:"Fault Zone Lethality Ranking",
    desc:"Rank fault zones by total documented deaths and predicted future maximum.",
    cypher:`MATCH (eq:Earthquake)-[:ORIGINATED_ON]->(fz:FaultZone)
WHERE eq.deaths IS NOT NULL
RETURN fz.name, fz.type,
       count(eq)          AS major_events,
       sum(eq.deaths)     AS total_deaths,
       max(eq.magnitude)  AS max_magnitude,
       fz.predicted_max_mag
ORDER BY total_deaths DESC`,
    tags:["lethality","faults","ranking"],
  },
  {
    id:7, title:"Hamaoka Nuclear Risk",
    desc:"All historical quakes within 50km of Hamaoka — the plant above the Nankai Trough.",
    cypher:`MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility {id: 'hamaoka'})
MATCH (eq)-[:ORIGINATED_ON]->(fz:FaultZone)
RETURN eq.time, eq.magnitude, eq.depth_km,
       fz.name, eq.tsunami AS tsunami_flagged
ORDER BY eq.magnitude DESC`,
    tags:["hamaoka","nankai","nuclear"],
  },
  {
    id:8, title:"Prefecture Composite Risk Index",
    desc:"Score each prefecture across four dimensions: quake count, tsunami exposure, NPP proximity, subduction fault coverage.",
    cypher:`MATCH (eq:Earthquake)-[:STRUCK]->(pf:Prefecture)
WITH pf, count(eq) AS qc, max(eq.magnitude) AS mm
OPTIONAL MATCH (t:Tsunami)-[:INUNDATED]->(pf)
WITH pf, qc, mm, count(t) AS tc
OPTIONAL MATCH (pf)-[:CONTAINS]->(nf:NuclearFacility)
WITH pf, qc, mm, tc, count(nf) AS nc
OPTIONAL MATCH (fz:FaultZone {type:'subduction'})-[:UNDERLIES]->(pf)
RETURN pf.name, qc, mm, tc, nc, count(fz) AS sz,
       (qc + tc*10 + nc*5 + count(fz)*8) AS composite_risk
ORDER BY composite_risk DESC LIMIT 15`,
    tags:["composite","risk","index"],
  },
  {
    id:9, title:"Graph Schema Check",
    desc:"Verify node counts and relationship types loaded correctly in Neo4j Aura.",
    cypher:`MATCH (n)
RETURN labels(n)[0] AS node_type, count(n) AS count
UNION ALL
MATCH ()-[r]->()
RETURN type(r) AS node_type, count(r) AS count
ORDER BY count DESC`,
    tags:["schema","debug","meta"],
  },
]

// ── Tiny chart components ───────────────────────────────────────
function BarChart({data, valueKey, labelKey, colorFn, maxVal}) {
  const max = maxVal || Math.max(...data.map(d=>d[valueKey]))
  return (
    <div style={{display:"flex",flexDirection:"column",gap:7}}>
      {data.map((d,i)=>(
        <div key={i} style={{display:"flex",alignItems:"center",gap:8}}>
          <div style={{width:80,fontSize:12,color:"#1d6d95",textAlign:"right",flexShrink:0,fontWeight:600}}>{d[labelKey]}</div>
          <div style={{flex:1,height:16,background:"#eaf2fb",borderRadius:2,overflow:"hidden",position:"relative"}}>
            <div style={{
              height:"100%",borderRadius:2,transition:"width 0.6s ease",
              width:`${(d[valueKey]/max)*100}%`,
              background:colorFn?colorFn(d,i):"#2b7ba8",
              boxShadow:`0 0 6px ${colorFn?colorFn(d,i):"#2b7ba8"}44`,
            }}/>
          </div>
          <div style={{width:52,fontSize:12,color:"#0369a1",textAlign:"right",flexShrink:0,fontWeight:600}}>{d[valueKey].toLocaleString()}</div>
        </div>
      ))}
    </div>
  )
}

function StatCard({label,value,sub,color="#0369a1"}) {
  return (
    <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 18px",flex:1,minWidth:130}}>
      <div style={{fontSize:11,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:6,fontWeight:600}}>{label}</div>
      <div style={{fontSize:32,fontWeight:700,color,lineHeight:1}}>{value}</div>
      {sub&&<div style={{fontSize:12,color:"#648ba4",marginTop:6,fontWeight:500}}>{sub}</div>}
    </div>
  )
}

function QueryCard({q}) {
  const [open,setOpen] = useState(false)
  const [copied,setCopied] = useState(false)
  const copy = () => { navigator.clipboard.writeText(q.cypher); setCopied(true); setTimeout(()=>setCopied(false),1600) }
  return (
    <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,marginBottom:12,overflow:"hidden"}}>
      <div style={{padding:"14px 16px",cursor:"pointer",display:"flex",justifyContent:"space-between",alignItems:"center"}}
        onClick={()=>setOpen(o=>!o)}>
        <div>
          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:5}}>
            <span style={{fontSize:11,color:"#7398ac",fontWeight:700}}>#{q.id}</span>
            <span style={{fontSize:14,color:"#0a5c8a",fontWeight:700}}>{q.title}</span>
          </div>
          <div style={{display:"flex",gap:5}}>
            {q.tags.map(t=>(
              <span key={t} style={{fontSize:10,padding:"2px 7px",background:"#cfe0f0",borderRadius:3,color:"#4a7fa1",letterSpacing:"0.05em"}}>{t}</span>
            ))}
          </div>
        </div>
        <span style={{fontSize:14,color:"#7398ac",flexShrink:0}}>{open?"▲":"▼"}</span>
      </div>
      {open&&<div style={{borderTop:"1px solid #cfe0f0"}}>
        <div style={{padding:"12px 16px",fontSize:12,color:"#35759b",lineHeight:1.7}}>{q.desc}</div>
        <div style={{position:"relative"}}>
          <pre style={{margin:0,padding:"14px 16px",background:"#e9f1fa",
            color:"#12405f",fontSize:12,lineHeight:1.8,overflowX:"auto",
            fontFamily:"'IBM Plex Mono',monospace",borderTop:"1px solid #dce9f6"}}>
            {q.cypher.split("\n").map((line,i)=>{
              const hl = line
                .replace(/(MATCH|WHERE|RETURN|ORDER BY|WITH|LIMIT|OPTIONAL|UNION ALL|AS|AND|IN|NOT)/g, '<k>$1</k>')
                .replace(/(:\w+)/g, '<t>$1</t>')
                .replace(/('[\w_]+')/g, '<s>$1</s>')
                .replace(/(\/\/.*)/g,'<c>$1</c>')
              return <span key={i} dangerouslySetInnerHTML={{__html:hl+"\n"}}/>
            })}
          </pre>
          <button onClick={copy} style={{position:"absolute",top:10,right:10,background:"#cfe0f0",border:"1px solid #8fb6d8",
            color:copied?"#0d9b57":"#1d6d95",padding:"4px 10px",borderRadius:4,fontSize:11,cursor:"pointer",fontFamily:"inherit"}}>
            {copied?"✓ copied":"copy"}
          </button>
        </div>
      </div>}
    </div>
  )
}

// ── OVERDUE GAUGE ───────────────────────────────────────────────
function OverdueGauge({score}) {
  const clamped = Math.min(score ?? 0, 5)
  const angle = (clamped / 5) * 180
  const color = clamped < 0.8 ? "#0f9e5c" : clamped < 1.5 ? "#a37800" : clamped < 2.5 ? "#cc7000" : "#d63000"
  const rad = (angle - 180) * (Math.PI / 180)
  const cx = 60, cy = 54, r = 44
  const nx = cx + r * Math.cos(rad)
  const ny = cy + r * Math.sin(rad)
  return (
    <svg width={120} height={62} viewBox="0 0 120 62">
      <path d={`M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}`} fill="none" stroke="#cfe0f0" strokeWidth={10} strokeLinecap="round"/>
      <path d={`M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}`} fill="none" stroke={color} strokeWidth={10}
        strokeLinecap="round" strokeDasharray={`${(clamped/5)*139} 139`} opacity={0.35}/>
      <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={color} strokeWidth={2.5} strokeLinecap="round"/>
      <circle cx={cx} cy={cy} r={4} fill={color} opacity={0.8}/>
      <text x={cx-r+2} y={cy+14} fontSize={8} fill="#9db4c4">0</text>
      <text x={cx+r-8} y={cy+14} fontSize={8} fill="#9db4c4">5×</text>
      <text x={cx} y={cy+14} textAnchor="middle" fontSize={8} fill="#9db4c4">1×</text>
      <text x={cx} y={cy-r-6} textAnchor="middle" fontSize={9} fontWeight="700" fill={color}>{score != null ? score.toFixed(2)+"×" : "—"}</text>
    </svg>
  )
}

// ── RISK ANALYSIS TAB ───────────────────────────────────────────
function RiskTab({data, loading, error}) {
  const TYPE_COL = {subduction:"#d93d2b", strike_slip:"#8b3fd6", crustal:"#a37800", reverse:"#0a7fb8", intraslab:"#2b7fd4"}
  return (
    <div>
      {/* Disclaimer — always visible */}
      <div style={{border:"1px solid #e0d090",background:"#fdf8e8",borderRadius:6,padding:"12px 16px",marginBottom:20,fontSize:12,color:"#8a6d1f",lineHeight:1.8}}>
        <span style={{fontWeight:700,color:"#a37800",letterSpacing:"0.06em"}}>STATISTICAL ANALYSIS — NOT PREDICTION</span>
        {"  "}These figures represent historical recurrence rates derived from 75 years of seismic records.
        Earthquake timing is inherently unpredictable. A ratio above 1.0× indicates a fault zone has exceeded its
        historical average recurrence interval — this does not imply imminent occurrence.
      </div>

      {loading&&<div style={{color:"#8aa6b8",fontSize:13,padding:20}}>Loading recurrence data from graph…</div>}
      {error&&<div style={{color:"#d84315",fontSize:13,padding:20}}>Could not load risk data: {error}</div>}

      {data&&<>
        {/* Summary ranking */}
        <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px",marginBottom:16}}>
          <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:12,fontWeight:700}}>HISTORICAL OVERDUE RATIO — RANKED</div>
          <div style={{fontSize:11,color:"#8ba7b9",marginBottom:10}}>
            Based on {data.data_range?.total_events?.toLocaleString()} events · {data.data_range?.from_year}–{data.data_range?.to_year}
          </div>
          {data.ranked_by_overdue?.map((r,i)=>{
            const score = r.overdue_score
            const col = score < 0.8 ? "#0f9e5c" : score < 1.5 ? "#a37800" : score < 2.5 ? "#cc7000" : "#d63000"
            return (
              <div key={r.fault_id} style={{display:"flex",alignItems:"center",gap:10,marginBottom:6}}>
                <div style={{width:16,fontSize:10,color:"#9db4c4",textAlign:"right"}}>{i+1}.</div>
                <div style={{flex:1,fontSize:12,color:"#0a5c8a",fontWeight:600}}>{r.fault_name}</div>
                <div style={{fontSize:11,color:col,fontWeight:700}}>{r.display_label}</div>
              </div>
            )
          })}
        </div>

        {/* Per-fault cards */}
        {data.fault_zones?.map(fz=>(
          <div key={fz.fault_id} style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px",marginBottom:12}}>
            {/* Header */}
            <div style={{display:"flex",alignItems:"flex-start",justifyContent:"space-between",marginBottom:12}}>
              <div>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:4}}>
                  <span style={{fontSize:14,fontWeight:700,color:"#0a5c8a"}}>{fz.fault_name}</span>
                  <span style={{fontSize:9,padding:"2px 7px",borderRadius:3,
                    background:"#dce9f6",border:`1px solid ${TYPE_COL[fz.fault_type]||"#9db4c4"}`,
                    color:TYPE_COL[fz.fault_type]||"#9db4c4",letterSpacing:"0.06em",fontWeight:700}}>
                    {fz.fault_type}
                  </span>
                </div>
                <div style={{fontSize:11,color:"#7398ac"}}>
                  Predicted max: <span style={{color:"#cc7000",fontWeight:700}}>M{fz.predicted_max_mag}</span>
                  {fz.last_major_year&&<> · Last major: <span style={{color:"#35759b"}}>{fz.last_major_year}</span></>}
                  {" · "}<span style={{color:"#8aa6b8"}}>{fz.total_events?.toLocaleString()} total events</span>
                </div>
              </div>
              {/* Gauge for best tier */}
              {(()=>{
                const best = ["m8","m7","m6"].map(k=>fz.tiers?.[k]).find(t=>t?.overdue_score!=null)
                return best ? <OverdueGauge score={best.overdue_score}/> : null
              })()}
            </div>

            {/* Tier table */}
            <div style={{overflowX:"auto"}}><div style={{display:"grid",gridTemplateColumns:"auto 1fr 1fr 1fr 1fr 1fr",gap:0,fontSize:11,minWidth:380}}>
              {["TIER","EVENTS","AVG INTERVAL","LAST EVENT","YRS SINCE","OVERDUE RATIO"].map(h=>(
                <div key={h} style={{padding:"5px 8px",color:"#5f88a6",borderBottom:"1px solid #c9dcee",fontWeight:700,letterSpacing:"0.06em",fontSize:10}}>{h}</div>
              ))}
              {["m6","m7","m8"].map(tier=>{
                const t = fz.tiers?.[tier]
                if (!t) return null
                const score = t.overdue_score
                const col = score == null ? "#9db4c4" : score < 0.8 ? "#0f9e5c" : score < 1.5 ? "#a37800" : score < 2.5 ? "#cc7000" : "#d63000"
                return [
                  <div key={`${tier}-l`} style={{padding:"5px 8px",color:"#1d6d95",borderBottom:"1px solid #dce9f6",fontWeight:700}}>
                    {tier.toUpperCase().replace("M","M")}+
                  </div>,
                  <div key={`${tier}-ec`} style={{padding:"5px 8px",color:"#35759b",borderBottom:"1px solid #dce9f6"}}>
                    {t.event_count}
                    {t.sample_size_warning&&<span style={{fontSize:9,padding:"1px 4px",background:"#fdf1e3",border:"1px solid #e8c9a0",borderRadius:3,color:"#a35f00",marginLeft:5}}>low n</span>}
                  </div>,
                  <div key={`${tier}-ar`} style={{padding:"5px 8px",color:"#4a7fa1",borderBottom:"1px solid #dce9f6"}}>
                    {t.avg_recurrence_years != null ? `${t.avg_recurrence_years} yr` : "—"}
                  </div>,
                  <div key={`${tier}-le`} style={{padding:"5px 8px",color:"#4a7fa1",borderBottom:"1px solid #dce9f6"}}>
                    {t.last_event_year ?? "—"}
                  </div>,
                  <div key={`${tier}-ys`} style={{padding:"5px 8px",color:"#4a7fa1",borderBottom:"1px solid #dce9f6"}}>
                    {t.years_since_last != null ? `${t.years_since_last} yr` : "—"}
                  </div>,
                  <div key={`${tier}-os`} style={{padding:"5px 8px",borderBottom:"1px solid #dce9f6",fontWeight:700,color:col}}>
                    {score != null ? `${score.toFixed(2)}×` : "—"}
                  </div>,
                ]
              })}
            </div></div>
          </div>
        ))}
      </>}
    </div>
  )
}

// ── MAIN DASHBOARD ──────────────────────────────────────────────
export default function Dashboard({onBack, chat}) {
  const width = useWindowWidth()
  const isMobile = width < 768
  const [activeTab,setActiveTab] = useState("eda")
  const [riskData,setRiskData] = useState(null)
  const [riskLoading,setRiskLoading] = useState(false)
  const [riskError,setRiskError] = useState(null)

  const selectTab = (t) => {
    setActiveTab(t)
    if (t === "risk" && !riskData && !riskLoading) {
      setRiskLoading(true)
      fetch(`${import.meta.env.VITE_API_URL}/analysis/predict`)
        .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
        .then(d => { setRiskData(d); setRiskLoading(false) })
        .catch(e => { setRiskError(e.message); setRiskLoading(false) })
    }
  }

  const col2 = isMobile ? "1fr" : "1fr 1fr"

  return (
    <div style={{height:"100vh",background:"#eef5fc",fontFamily:"'IBM Plex Mono',monospace",color:"#2b7ba8",display:"flex",flexDirection:"column"}}>
      {/* Nav */}
      <div style={{borderBottom:"1px solid #cfe0f0",background:"#f7fbff",padding:isMobile?"0 12px":"0 24px",
        display:"flex",alignItems:"center",gap:isMobile?8:16,height:50,flexShrink:0,flexWrap:"wrap",minHeight:50}}>
        <button onClick={onBack} style={{background:"none",border:"1px solid #bdd6ea",borderRadius:5,
          color:"#35759b",fontSize:11,padding:"5px 10px",cursor:"pointer",fontFamily:"inherit",letterSpacing:"0.06em",flexShrink:0}}>
          ← SHINDO
        </button>
        {!isMobile&&<div style={{fontSize:14,fontWeight:700,color:"#0369a1",letterSpacing:"0.08em"}}>
          DATA ANALYSIS DASHBOARD
        </div>}
        <div style={{marginLeft:"auto",display:"flex",gap:isMobile?2:4,flexShrink:0}}>
          {[["eda",isMobile?"EDA":"EDA CHARTS"],["risk",isMobile?"RISK":"RISK ANALYSIS"],["cypher",isMobile?"CYPHER":"CYPHER QUERIES"]].map(([t,label])=>(
            <button key={t} onClick={()=>selectTab(t)}
              style={{background:activeTab===t?"#cfe0f0":"none",border:"1px solid",
                borderColor:activeTab===t?"#8fb6d8":"transparent",borderRadius:5,
                color:activeTab===t?"#0369a1":"#8aa6b8",fontSize:isMobile?10:11,padding:isMobile?"5px 8px":"5px 14px",
                cursor:"pointer",fontFamily:"inherit",letterSpacing:"0.05em"}}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Body: charts + chat */}
      <div style={{flex:1,display:"flex",flexDirection:isMobile?"column":"row",overflow:"hidden"}}>
      <div style={{flex:1,overflowY:"auto",padding:isMobile?"12px":"24px"}}>

        {/* ── EDA TAB ─────────────────────────────────────────── */}
        {activeTab==="eda"&&<>
          {/* KPI strip */}
          <div style={{display:"flex",gap:10,marginBottom:24,flexWrap:"wrap"}}>
            <StatCard label="TOTAL EVENTS (M4+)" value="4,720" sub="1900 – 2024" color="#0369a1"/>
            <StatCard label="DEADLIEST EVENT"    value="M9.1"  sub="Tohoku 2011 · 22k deaths" color="#d84315"/>
            <StatCard label="ACTIVE FAULT ZONES" value="7"     sub="monitored in graph" color="#a37800"/>
            <StatCard label="NUCLEAR FACILITIES" value="15"    sub="tracked in graph" color="#0f9e5c"/>
            <StatCard label="AVG ANNUAL M6+"     value="18.4"  sub="past 50 years" color="#8b3fd6"/>
          </div>

          <div style={{display:"grid",gridTemplateColumns:col2,gap:16,marginBottom:16}}>
            {/* Magnitude distribution */}
            <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px"}}>
              <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:14,fontWeight:700}}>MAGNITUDE DISTRIBUTION</div>
              <BarChart data={MAG_DIST} valueKey="count" labelKey="bin"
                colorFn={(d,i)=>{
                  const cols=["#648ba4","#5b859f","#4a7fa1","#cc7000","#d16000","#d94a00","#d63000","#b0001c"]
                  return cols[i]||"#2b7ba8"
                }}/>
              <div style={{fontSize:12,color:"#648ba4",marginTop:12,lineHeight:1.7}}>
                38% of events M4.0–4.4. Each magnitude step is ~31.6× more energy.
              </div>
            </div>

            {/* Depth distribution */}
            <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px"}}>
              <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:14,fontWeight:700}}>DEPTH DISTRIBUTION (km)</div>
              <BarChart data={DEPTH_DIST} valueKey="count" labelKey="bin"
                colorFn={(d)=>{
                  if(d.label==="Crustal") return "#cc7000"
                  if(d.label==="Transition") return "#a37800"
                  return "#2b7ba8"
                }}/>
              <div style={{fontSize:12,color:"#648ba4",marginTop:12,lineHeight:1.7}}>
                35% shallow crustal (10–30km) — highest surface shaking. Deep intraslab events less destructive but broader reach.
              </div>
            </div>
          </div>

          <div style={{display:"grid",gridTemplateColumns:col2,gap:16,marginBottom:16}}>
            {/* Decade trend */}
            <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px"}}>
              <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:14,fontWeight:700}}>EVENTS PER DECADE (M4+)</div>
              <div style={{display:"flex",alignItems:"flex-end",gap:3,height:100}}>
                {DECADE_DATA.map((d,i)=>{
                  const maxQ=Math.max(...DECADE_DATA.map(x=>x.quakes))
                  const h=`${Math.round((d.quakes/maxQ)*90)}px`
                  return (
                    <div key={i} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:2}}>
                      <div style={{width:"100%",height:h,background:d.tsunamis>=7?"#d84315":"#2b7ba8",borderRadius:"2px 2px 0 0",
                        boxShadow:`0 0 6px ${d.tsunamis>=7?"#d84315":"#2b7ba8"}44`,
                        transition:"height 0.6s ease",position:"relative"}}>
                        {d.tsunamis>=5&&<div style={{position:"absolute",bottom:"100%",left:"50%",transform:"translateX(-50%)",
                          fontSize:7,color:"#c05f38",whiteSpace:"nowrap"}}>{d.tsunamis}ts</div>}
                      </div>
                      <div style={{fontSize:6,color:"#9db4c4",transform:"rotate(-45deg)",transformOrigin:"top center",
                        marginTop:4,whiteSpace:"nowrap"}}>{d.decade.slice(0,4)}s</div>
                    </div>
                  )
                })}
              </div>
              <div style={{fontSize:12,color:"#648ba4",marginTop:18,lineHeight:1.7}}>
                Increasing trend due to improved seismic network coverage (not actual increase). Red bars = high tsunami years.
              </div>
            </div>

            {/* Fault lethality */}
            <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px"}}>
              <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:14,fontWeight:700}}>FAULT ZONE TOTAL DEATHS</div>
              <BarChart data={FAULT_RISK} valueKey="deaths" labelKey="name"
                colorFn={(d)=>d.col} maxVal={150000}/>
              <div style={{fontSize:12,color:"#648ba4",marginTop:12,lineHeight:1.7}}>
                Sagami Trough leads due to 1923 Great Kanto (99,000 deaths). Japan Trench second: 2011 Tohoku (22,000).
              </div>
            </div>
          </div>

          {/* Prefecture risk table */}
          <div style={{background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8,padding:"14px 16px"}}>
            <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.1em",marginBottom:14,fontWeight:700}}>PREFECTURE COMPOSITE RISK INDEX (top 8)</div>
            <div style={{overflowX:"auto"}}><div style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr 1fr 1fr",gap:0,minWidth:420}}>
              {["PREFECTURE","RISK SCORE","QUAKES","TSUNAMIS","NPP","RISK BAR"].map(h=>(
                <div key={h} style={{fontSize:11,color:"#4a7fa1",padding:"6px 10px",borderBottom:"1px solid #c9dcee",letterSpacing:"0.07em",fontWeight:700}}>{h}</div>
              ))}
              {TOP_PREFS.map((p,i)=>{
                const barW=`${p.score}%`
                const col=p.score>85?"#d84315":p.score>75?"#cc7000":"#2b7ba8"
                return [
                  <div key={`n${i}`} style={{fontSize:12,color:"#0a5c8a",padding:"7px 10px",borderBottom:"1px solid #dce9f6",fontWeight:600}}>{p.name}</div>,
                  <div key={`s${i}`} style={{fontSize:12,color:col,padding:"7px 10px",borderBottom:"1px solid #dce9f6",fontWeight:700}}>{p.score}</div>,
                  <div key={`q${i}`} style={{fontSize:12,color:"#35759b",padding:"7px 10px",borderBottom:"1px solid #dce9f6"}}>{p.quakes}</div>,
                  <div key={`t${i}`} style={{fontSize:12,color:"#1d6d95",padding:"7px 10px",borderBottom:"1px solid #dce9f6"}}>{p.tsunamis}</div>,
                  <div key={`np${i}`} style={{fontSize:12,color:p.npp>0?"#c96b1a":"#8ba7b9",padding:"7px 10px",borderBottom:"1px solid #dce9f6"}}>{p.npp}</div>,
                  <div key={`b${i}`} style={{padding:"7px 10px",borderBottom:"1px solid #dce9f6",display:"flex",alignItems:"center"}}>
                    <div style={{height:10,width:barW,background:col,borderRadius:2,boxShadow:`0 0 4px ${col}44`,transition:"width 0.6s"}}/>
                  </div>,
                ]
              })}
            </div>
            </div>
            <div style={{fontSize:12,color:"#648ba4",marginTop:12}}>
              Score = quake_count + tsunami_count×10 + npp_count×5 + subduction_zones×8
            </div>
          </div>
        </>}

        {/* ── RISK ANALYSIS TAB ───────────────────────────────── */}
        {activeTab==="risk"&&<RiskTab data={riskData} loading={riskLoading} error={riskError}/>}

        {/* ── CYPHER TAB ──────────────────────────────────────── */}
        {activeTab==="cypher"&&<>
          <div style={{marginBottom:20,padding:"16px 20px",background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8}}>
            <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.08em",marginBottom:10,fontWeight:700}}>HOW TO USE</div>
            <div style={{fontSize:13,color:"#35759b",lineHeight:1.8}}>
              Open <span style={{color:"#0a5c8a"}}>Neo4j Aura Console</span> → your database → <span style={{color:"#0a5c8a"}}>Query</span> tab.
              Paste any query below and run it. Queries use the SHINDO graph schema:<br/>
              <span style={{color:"#0369a1"}}>Earthquake</span> · <span style={{color:"#0369a1"}}>FaultZone</span> · <span style={{color:"#0369a1"}}>Tsunami</span> · <span style={{color:"#0369a1"}}>Prefecture</span> · <span style={{color:"#0369a1"}}>NuclearFacility</span> · <span style={{color:"#0369a1"}}>Decade</span>
            </div>
          </div>

          {/* schema diagram */}
          <div style={{marginBottom:20,padding:"16px 20px",background:"#f7fbff",border:"1px solid #cfe0f0",borderRadius:8}}>
            <div style={{fontSize:12,color:"#4a7fa1",letterSpacing:"0.08em",marginBottom:14,fontWeight:700}}>GRAPH SCHEMA</div>
            <div style={{fontSize:12,fontFamily:"inherit",lineHeight:2.4,color:"#4a7fa1"}}>
              <div><span style={{color:"#8b3fd6"}}>(FaultZone)</span> <span style={{color:"#93a9bb"}}>←[:ORIGINATED_ON]—</span> <span style={{color:"#d84315"}}>(Earthquake)</span> <span style={{color:"#93a9bb"}}>—[:TRIGGERED]→</span> <span style={{color:"#1f8ad4"}}>(Tsunami)</span> <span style={{color:"#93a9bb"}}>—[:INUNDATED]→</span> <span style={{color:"#0f9e5c"}}>(Prefecture)</span></div>
              <div><span style={{color:"#d84315"}}>(Earthquake)</span> <span style={{color:"#93a9bb"}}>—[:STRUCK]→</span> <span style={{color:"#0f9e5c"}}>(Prefecture)</span> <span style={{color:"#93a9bb"}}>—[:CONTAINS]→</span> <span style={{color:"#a37800"}}>(NuclearFacility)</span></div>
              <div><span style={{color:"#d84315"}}>(Earthquake)</span> <span style={{color:"#93a9bb"}}>—[:WITHIN_50KM_OF]→</span> <span style={{color:"#a37800"}}>(NuclearFacility)</span></div>
              <div><span style={{color:"#d84315"}}>(Earthquake)</span> <span style={{color:"#93a9bb"}}>—[:IN_DECADE]→</span> <span style={{color:"#0369a1"}}>(Decade)</span></div>
              <div><span style={{color:"#8b3fd6"}}>(FaultZone)</span> <span style={{color:"#93a9bb"}}>—[:UNDERLIES]→</span> <span style={{color:"#0f9e5c"}}>(Prefecture)</span></div>
            </div>
          </div>

          {QUERIES.map(q=><QueryCard key={q.id} q={q}/>)}
        </>}
      </div>{/* end scrollable content */}

      <ChatPanel chat={chat} mobile={isMobile}/>
      </div>{/* end body */}

      <style>{`
        pre k { color: #8b3fd6; font-weight: 700; }
        pre t { color: #0f9e5c; }
        pre s { color: #a37800; }
        pre c { color: #8aa6b8; font-style: italic; }
        @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #eef5fc; }
        ::-webkit-scrollbar-thumb { background: #cfe0f0; border-radius: 2px; }
      `}</style>
    </div>
  )
}
