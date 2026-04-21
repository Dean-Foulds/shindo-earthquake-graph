import { useState, useEffect, useRef, useMemo } from "react"
import * as d3 from "d3"
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

const MD_COMPONENTS = {
  p:      ({children}) => <p style={{margin:"0 0 8px",lineHeight:1.7}}>{children}</p>,
  strong: ({children}) => <strong style={{color:"#00ffff",fontWeight:700}}>{children}</strong>,
  em:     ({children}) => <em style={{color:"#7df9ff",fontStyle:"italic"}}>{children}</em>,
  h1:     ({children}) => <div style={{fontSize:16,fontWeight:700,color:"#00e5ff",margin:"10px 0 5px",borderBottom:"1px solid #001a33",paddingBottom:3}}>{children}</div>,
  h2:     ({children}) => <div style={{fontSize:15,fontWeight:700,color:"#00e5ff",margin:"8px 0 4px"}}>{children}</div>,
  h3:     ({children}) => <div style={{fontSize:14,fontWeight:700,color:"#00ccdd",margin:"6px 0 3px"}}>{children}</div>,
  ul:     ({children}) => <ul style={{margin:"4px 0",paddingLeft:18}}>{children}</ul>,
  ol:     ({children}) => <ol style={{margin:"4px 0",paddingLeft:18}}>{children}</ol>,
  li:     ({children}) => <li style={{margin:"3px 0",color:"#a0e4ff"}}>{children}</li>,
  code:   ({inline,children}) => inline
    ? <code style={{background:"#001a33",border:"1px solid #002244",borderRadius:3,padding:"1px 6px",fontSize:12,color:"#00ffff",fontFamily:"inherit"}}>{children}</code>
    : <pre style={{background:"#00050f",border:"1px solid #001a33",borderRadius:5,padding:"10px 12px",margin:"6px 0",overflowX:"auto",fontSize:12,color:"#7df9ff",fontFamily:"inherit",lineHeight:1.6}}><code>{children}</code></pre>,
  blockquote: ({children}) => <blockquote style={{borderLeft:"2px solid #003366",margin:"6px 0",paddingLeft:12,color:"#0099bb"}}>{children}</blockquote>,
  hr:     () => <hr style={{border:"none",borderTop:"1px solid #001a33",margin:"8px 0"}}/>,
  a:      ({href,children}) => <a href={href} target="_blank" rel="noreferrer" style={{color:"#00b4d8",textDecoration:"underline"}}>{children}</a>,
  table:  ({children}) => <table style={{borderCollapse:"collapse",width:"100%",margin:"6px 0",fontSize:13}}>{children}</table>,
  th:     ({children}) => <th style={{padding:"5px 10px",background:"#001a33",color:"#00e5ff",textAlign:"left",borderBottom:"1px solid #002244"}}>{children}</th>,
  td:     ({children}) => <td style={{padding:"4px 10px",borderBottom:"1px solid #001020",color:"#a0e4ff"}}>{children}</td>,
}

function ChatBubble({msg}) {
  const isUser = msg.role === "user"
  return (
    <div style={{marginBottom:10}}>
      <div style={{fontSize:14,lineHeight:1.75,padding:"10px 14px",borderRadius:6,
        background:isUser?"#001a33":"#000f1f",
        border:`1px solid ${isUser?"#003366":"#001a2e"}`,
        color:isUser?"#7df9ff":"#a0e4ff",wordBreak:"break-word"}}>
        {isUser&&<div style={{fontSize:10,fontWeight:700,color:"#005577",letterSpacing:"0.1em",marginBottom:4}}>YOU</div>}
        {isUser
          ? <span style={{whiteSpace:"pre-wrap"}}>{msg.text}</span>
          : <ReactMarkdown components={MD_COMPONENTS}>{msg.text}</ReactMarkdown>
        }
      </div>
    </div>
  )
}

const MAP_W = 390, MAP_H = 518
const KM_PX = 1040 * Math.PI / 180 / 111.12   // ~0.163 svg-px per km
const API_HEADERS = {
  "Content-Type": "application/json",
  "x-api-key": import.meta.env.VITE_ANTHROPIC_KEY,
  "anthropic-version": "2023-06-01",
  "anthropic-dangerous-direct-browser-access": "true",
}

const makeProj = () => d3.geoMercator().center([135.5,35.5]).scale(1040).translate([MAP_W/2,MAP_H/2])

const POP = {hokkaido:5.2,aomori:1.2,iwate:1.2,miyagi:2.3,akita:1.0,yamagata:1.1,fukushima:1.8,ibaraki:2.9,tochigi:2.0,gunma:2.0,saitama:7.3,chiba:6.3,tokyo:13.9,kanagawa:9.2,niigata:2.2,toyama:1.0,ishikawa:1.1,fukui:0.8,yamanashi:0.8,nagano:2.1,gifu:2.0,shizuoka:3.6,aichi:7.5,mie:1.8,shiga:1.4,kyoto:2.6,osaka:8.8,hyogo:5.5,nara:1.3,wakayama:0.9,tottori:0.6,shimane:0.7,okayama:1.9,hiroshima:2.8,yamaguchi:1.3,tokushima:0.7,kagawa:1.0,ehime:1.4,kochi:0.7,fukuoka:5.1,saga:0.8,nagasaki:1.3,kumamoto:1.8,oita:1.1,miyazaki:1.1,kagoshima:1.6,okinawa:1.5}

const FAULT_LINES = [
  {id:"japan_trench",    name:"Japan Trench",       type:"subduction",  color:"#ff5544", coords:[[35.2,142.2],[36.2,142.5],[37.2,142.8],[38.2,143.3],[39.2,143.8],[40.2,144.2],[41.2,144.5],[42.2,144.6],[43.5,145.0]]},
  {id:"nankai_trough",   name:"Nankai Trough",      type:"subduction",  color:"#ff9922", coords:[[31.0,131.0],[31.5,132.2],[32.0,133.6],[32.4,135.0],[32.8,136.3],[33.2,137.2],[33.5,137.8]]},
  {id:"sagami_trough",   name:"Sagami Trough",      type:"subduction",  color:"#ff66aa", coords:[[33.8,138.5],[34.2,139.2],[34.6,140.0],[35.0,140.7]]},
  {id:"ryukyu_trench",   name:"Ryukyu Trench",      type:"subduction",  color:"#ffcc22", coords:[[30.5,131.0],[29.5,130.0],[28.5,129.0],[27.5,128.2],[26.5,127.4],[25.5,126.6],[24.5,126.0]]},
  {id:"median_tectonic_line",name:"Median Tectonic Line",type:"strike_slip",color:"#cc55ff",coords:[[33.4,130.2],[33.5,131.2],[33.6,132.2],[33.9,133.2],[34.1,134.2],[34.4,135.1],[34.7,135.6],[35.2,136.1],[35.6,136.6],[36.1,137.0]]},
  {id:"itoigawa_shizuoka",name:"Itoigawa-Shizuoka",type:"strike_slip",color:"#44aaff",coords:[[37.2,137.8],[36.7,138.0],[36.2,138.0],[35.7,138.0],[35.2,138.1],[34.9,138.4]]},
  {id:"noto_peninsula",  name:"Noto Fault System",  type:"reverse",     color:"#55ff99", coords:[[36.8,136.7],[37.1,137.0],[37.4,137.3],[37.6,137.5],[37.3,136.7],[37.0,136.5],[36.8,136.7]]},
]

const ISLANDS = {
  honshu:  [[41.4,141.5],[40.8,141.8],[40.2,142.0],[39.6,142.0],[38.9,141.7],[38.3,141.5],[37.8,141.2],[37.2,141.0],[36.5,140.9],[35.7,140.9],[35.2,140.4],[34.9,139.9],[34.8,139.3],[34.6,138.9],[34.5,138.3],[34.5,137.8],[34.6,137.1],[34.7,136.5],[34.6,136.0],[34.4,135.7],[33.8,135.9],[33.4,135.8],[33.7,135.3],[34.1,134.9],[34.5,134.2],[35.0,133.9],[35.4,133.5],[35.6,134.2],[35.5,134.9],[35.1,135.1],[35.4,135.7],[35.8,136.0],[36.3,136.2],[36.9,136.5],[37.5,136.9],[37.7,137.4],[37.9,138.9],[38.5,139.6],[39.4,139.9],[40.2,139.9],[40.7,140.2],[41.4,141.5]],
  hokkaido:[[41.4,140.3],[41.5,141.4],[42.1,142.4],[42.7,143.7],[43.2,145.4],[44.0,145.4],[44.5,145.0],[45.5,142.8],[45.5,141.9],[44.4,142.1],[43.9,141.4],[43.2,140.9],[42.6,140.4],[41.4,140.3]],
  shikoku: [[34.2,132.6],[34.5,133.0],[34.4,134.0],[34.3,134.7],[33.7,134.5],[33.5,133.7],[33.2,132.7],[33.5,132.3],[34.2,132.6]],
  kyushu:  [[33.9,130.9],[34.2,131.2],[34.1,131.6],[33.6,131.9],[33.1,131.7],[32.8,130.9],[32.0,130.6],[31.5,130.2],[31.7,129.8],[32.1,129.6],[32.7,129.7],[33.2,129.6],[33.6,129.9],[33.9,130.5],[33.9,130.9]],
  okinawa: [[26.7,128.2],[26.5,127.8],[26.1,127.7],[25.9,127.6],[26.1,128.0],[26.6,128.4],[26.7,128.2]],
}

const PREFS = [
  {id:"hokkaido",lat:43.06,lon:141.35,name:"Hokkaido",coast:"both"},
  {id:"aomori",lat:40.82,lon:140.74,name:"Aomori",coast:"both"},
  {id:"iwate",lat:39.70,lon:141.15,name:"Iwate",coast:"pacific"},
  {id:"miyagi",lat:38.27,lon:140.87,name:"Miyagi",coast:"pacific"},
  {id:"akita",lat:39.72,lon:140.10,name:"Akita",coast:"sea_of_japan"},
  {id:"yamagata",lat:38.24,lon:140.36,name:"Yamagata",coast:"sea_of_japan"},
  {id:"fukushima",lat:37.75,lon:140.47,name:"Fukushima",coast:"pacific"},
  {id:"ibaraki",lat:36.34,lon:140.45,name:"Ibaraki",coast:"pacific"},
  {id:"tochigi",lat:36.57,lon:139.88,name:"Tochigi",coast:"inland"},
  {id:"gunma",lat:36.39,lon:139.06,name:"Gunma",coast:"inland"},
  {id:"saitama",lat:35.86,lon:139.65,name:"Saitama",coast:"inland"},
  {id:"chiba",lat:35.61,lon:140.12,name:"Chiba",coast:"pacific"},
  {id:"tokyo",lat:35.69,lon:139.69,name:"Tokyo",coast:"pacific"},
  {id:"kanagawa",lat:35.45,lon:139.64,name:"Kanagawa",coast:"pacific"},
  {id:"niigata",lat:37.90,lon:139.02,name:"Niigata",coast:"sea_of_japan"},
  {id:"toyama",lat:36.70,lon:137.21,name:"Toyama",coast:"sea_of_japan"},
  {id:"ishikawa",lat:36.59,lon:136.63,name:"Ishikawa",coast:"sea_of_japan"},
  {id:"fukui",lat:36.06,lon:136.22,name:"Fukui",coast:"sea_of_japan"},
  {id:"yamanashi",lat:35.66,lon:138.57,name:"Yamanashi",coast:"inland"},
  {id:"nagano",lat:36.65,lon:138.19,name:"Nagano",coast:"inland"},
  {id:"gifu",lat:35.39,lon:136.72,name:"Gifu",coast:"inland"},
  {id:"shizuoka",lat:34.98,lon:138.38,name:"Shizuoka",coast:"pacific"},
  {id:"aichi",lat:35.18,lon:137.10,name:"Aichi",coast:"pacific"},
  {id:"mie",lat:34.73,lon:136.51,name:"Mie",coast:"pacific"},
  {id:"shiga",lat:35.00,lon:135.87,name:"Shiga",coast:"inland"},
  {id:"kyoto",lat:35.02,lon:135.76,name:"Kyoto",coast:"sea_of_japan"},
  {id:"osaka",lat:34.69,lon:135.50,name:"Osaka",coast:"pacific"},
  {id:"hyogo",lat:34.69,lon:135.18,name:"Hyogo",coast:"both"},
  {id:"nara",lat:34.69,lon:135.83,name:"Nara",coast:"inland"},
  {id:"wakayama",lat:34.23,lon:135.17,name:"Wakayama",coast:"pacific"},
  {id:"tottori",lat:35.50,lon:134.24,name:"Tottori",coast:"sea_of_japan"},
  {id:"shimane",lat:35.47,lon:133.06,name:"Shimane",coast:"sea_of_japan"},
  {id:"okayama",lat:34.66,lon:133.93,name:"Okayama",coast:"pacific"},
  {id:"hiroshima",lat:34.40,lon:132.46,name:"Hiroshima",coast:"pacific"},
  {id:"yamaguchi",lat:34.19,lon:131.47,name:"Yamaguchi",coast:"both"},
  {id:"tokushima",lat:34.07,lon:134.55,name:"Tokushima",coast:"pacific"},
  {id:"kagawa",lat:34.34,lon:134.04,name:"Kagawa",coast:"pacific"},
  {id:"ehime",lat:33.84,lon:132.77,name:"Ehime",coast:"pacific"},
  {id:"kochi",lat:33.56,lon:133.53,name:"Kochi",coast:"pacific"},
  {id:"fukuoka",lat:33.61,lon:130.42,name:"Fukuoka",coast:"both"},
  {id:"saga",lat:33.25,lon:130.30,name:"Saga",coast:"both"},
  {id:"nagasaki",lat:32.74,lon:129.87,name:"Nagasaki",coast:"both"},
  {id:"kumamoto",lat:32.79,lon:130.74,name:"Kumamoto",coast:"pacific"},
  {id:"oita",lat:33.24,lon:131.61,name:"Oita",coast:"pacific"},
  {id:"miyazaki",lat:31.91,lon:131.42,name:"Miyazaki",coast:"pacific"},
  {id:"kagoshima",lat:31.56,lon:130.56,name:"Kagoshima",coast:"pacific"},
  {id:"okinawa",lat:26.21,lon:127.68,name:"Okinawa",coast:"pacific"},
]

const NUCLEAR = [
  {id:"fukushima_daiichi",name:"Fukushima Daiichi",lat:37.421,lon:141.032,status:"decommissioning"},
  {id:"fukushima_daini",  name:"Fukushima Daini",  lat:37.316,lon:141.025,status:"shutdown"},
  {id:"onagawa",          name:"Onagawa",          lat:38.401,lon:141.498,status:"restarting"},
  {id:"tokai_daini",      name:"Tokai Daini",      lat:36.466,lon:140.607,status:"suspended"},
  {id:"kashiwazaki_kariwa",name:"Kashiwazaki-Kariwa",lat:37.430,lon:138.602,status:"suspended"},
  {id:"shika",            name:"Shika",            lat:37.006,lon:136.689,status:"suspended"},
  {id:"mihama",           name:"Mihama",           lat:35.703,lon:135.994,status:"active"},
  {id:"ohi",              name:"Ohi",              lat:35.540,lon:135.655,status:"active"},
  {id:"takahama",         name:"Takahama",         lat:35.523,lon:135.508,status:"active"},
  {id:"hamaoka",          name:"Hamaoka",          lat:34.624,lon:138.143,status:"suspended"},
  {id:"shimane_npp",      name:"Shimane NPP",      lat:35.535,lon:132.993,status:"restarting"},
  {id:"ikata",            name:"Ikata",            lat:33.493,lon:132.312,status:"active"},
  {id:"genkai",           name:"Genkai",           lat:33.518,lon:129.836,status:"active"},
  {id:"sendai_npp",       name:"Sendai",           lat:31.833,lon:130.194,status:"active"},
  {id:"tomari",           name:"Tomari",           lat:43.046,lon:140.526,status:"suspended"},
]

const IC = ["#c6dbef","#9ecae1","#fdeda5","#fec44f","#fe9929","#d95f0e","#c51b8a","#7a0177","#49006a","#1a0029"]
const SEV = {
  catastrophic: ["#2a0010","#ff2266"],
  major:        ["#1f0800","#ff6600"],
  strong:       ["#161000","#ffcc00"],
  moderate:     ["#001020","#00aaff"],
  minor:        ["#001a08","#00dd55"],
}
const iCol = v => v ? IC[Math.min(Math.floor(v)-1,9)] : null
const cityR = (id, hit) => { const p=POP[id]||1; return hit ? Math.max(6,2.5+Math.sqrt(p)*1.8) : Math.max(1.8,1.2+Math.sqrt(p)*0.75) }
const faultMatch = str => {
  if(!str) return null; const s=str.toLowerCase()
  if(s.includes("nankai"))    return "nankai_trough"
  if(s.includes("japan trench")) return "japan_trench"
  if(s.includes("sagami"))    return "sagami_trough"
  if(s.includes("ryukyu"))    return "ryukyu_trench"
  if(s.includes("median")||s.includes("tectonic")) return "median_tectonic_line"
  if(s.includes("itoigawa")||s.includes("shizuoka")) return "itoigawa_shizuoka"
  if(s.includes("noto"))      return "noto_peninsula"
  return null
}
const islandPath = (proj,coords) => "M "+coords.map(([lt,ln])=>proj([ln,lt]).map(v=>v.toFixed(1)).join(",")).join(" L ")+" Z"

export default function Shindo({ chat }) {
  const width     = useWindowWidth()
  const isMobile  = width < 768
  const [mobileTab, setMobileTab] = useState("map")

  const svgRef    = useRef(null)
  const zoomRef   = useRef(null)
  const proj      = useRef(makeProj())
  const pg        = useRef(d3.geoPath().projection(proj.current))
  const chatEndRef = useRef(null)

  const [jpFeature, setJpFeature] = useState(null)
  const [jpPolys,   setJpPolys]   = useState(null)
  const [mapT,  setMapT]  = useState({x:0,y:0,k:1})
  const [epi,   setEpi]   = useState(null)
  const [wk,    setWk]    = useState(0)
  const [mag,   setMag]   = useState(7.0)
  const [dep,   setDep]   = useState(20)
  const [ana,   setAna]   = useState(null)
  const [loading,setLoading] = useState(false)
  const [showFaults,setShowFaults] = useState(true)
  const { chatMsgs, setChatMsgs, chatInput, setChatInput, chatLoading, setChatLoading } = chat

  useEffect(() => { chatEndRef.current?.scrollIntoView({behavior:"smooth"}) }, [chatMsgs])

  // Precompute projected pref positions
  const prefXY = useMemo(() => PREFS.map(p => { const [x,y]=proj.current([p.lon,p.lat]); return {...p,x,y} }), [])

  // Plexus network links between nearby prefectures
  const plexusLinks = useMemo(() => {
    const links=[]; const T=145
    for(let i=0;i<prefXY.length;i++) for(let j=i+1;j<prefXY.length;j++) {
      const d=Math.hypot(prefXY[i].x-prefXY[j].x, prefXY[i].y-prefXY[j].y)
      if(d<T) links.push({x1:prefXY[i].x,y1:prefXY[i].y,x2:prefXY[j].x,y2:prefXY[j].y,d})
    }
    return links
  }, [prefXY])

  // d3-zoom setup
  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const zoom = d3.zoom().scaleExtent([0.6,10])
      .on("zoom", ({transform:t}) => setMapT({x:t.x,y:t.y,k:t.k}))
    zoomRef.current = zoom
    svg.call(zoom)
    return () => { svg.on(".zoom", null) }
  }, [])

  // Scroll chat to bottom

  // Load Japan topojson
  useEffect(()=>{
    const load = async () => {
      if(!window.topojson){
        await new Promise((res,rej)=>{ const s=document.createElement("script"); s.src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"; s.onload=res; s.onerror=rej; document.head.appendChild(s) })
      }
      const world=await fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json").then(r=>r.json())
      const jp=window.topojson.feature(world,world.objects.countries).features.find(f=>String(f.id)==="392")
      if(!jp) throw new Error()
      setJpFeature(jp)
    }
    load().catch(()=>
      import("https://esm.sh/topojson-client@3").then(topo=>
        fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json").then(r=>r.json()).then(w=>{
          const jp=topo.feature(w,w.objects.countries).features.find(f=>String(f.id)==="392")
          if(jp) setJpFeature(jp); else throw new Error()
        })
      ).catch(()=>setJpPolys(Object.values(ISLANDS).map(c=>islandPath(proj.current,c))))
    )
  },[])

  // ── CORE ANALYSIS ────────────────────────────────────────────
  const runAnalysis = async (lat, lon, currentMag, currentDep) => {
    setLoading(true)
    try{
      const res=await fetch("https://api.anthropic.com/v1/messages",{
        method:"POST", headers:API_HEADERS,
        body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1600,
          system:"You are Shindo, Japan seismic risk AI backed by a Neo4j graph. Return ONLY valid JSON, no markdown.",
          messages:[{role:"user",content:
`Earthquake: ${lat.toFixed(2)}°N ${lon.toFixed(2)}°E M${currentMag.toFixed(1)} depth ${currentDep}km.
Return ONLY JSON:
{"fault_zone":"str","fault_type":"subduction|crustal|intraslab","severity":"minor|moderate|strong|major|catastrophic","affected_prefectures":[{"id":"id","name":"Name","intensity":1-10,"distance_km":number,"shindo":"1-7","risk":"shaking|tsunami|both","tsunami_height_m":number|null}],"tsunami":{"risk":"none|low|moderate|high|extreme","max_height_m":number|null,"warning_min":number|null,"estimated_casualties":number|null},"nuclear_risk":[{"id":"id","name":"Name","distance_km":number,"risk":"none|monitoring|elevated|critical"}],"historical_analogs":[{"name":"str","year":number,"magnitude":number,"deaths":number}],"cascade_chain":["str"],"insight":"str"}
Pref IDs: hokkaido,aomori,iwate,miyagi,akita,yamagata,fukushima,ibaraki,tochigi,gunma,saitama,chiba,tokyo,kanagawa,niigata,toyama,ishikawa,fukui,yamanashi,nagano,gifu,shizuoka,aichi,mie,shiga,kyoto,osaka,hyogo,nara,wakayama,tottori,shimane,okayama,hiroshima,yamaguchi,tokushima,kagawa,ehime,kochi,fukuoka,saga,nagasaki,kumamoto,oita,miyazaki,kagoshima,okinawa
Nuclear IDs: fukushima_daiichi,fukushima_daini,onagawa,tokai_daini,kashiwazaki_kariwa,shika,mihama,ohi,takahama,hamaoka,shimane_npp,ikata,genkai,sendai_npp,tomari
4-8 prefectures. Always include tsunami_height_m for coastal prefs if tsunami risk exists.`}]})
      })
      if(!res.ok){ const e=await res.json().catch(()=>({})); throw new Error(`HTTP ${res.status}: ${e?.error?.message||res.statusText}`) }
      const d=await res.json()
      const t=d.content.filter(c=>c.type==="text").map(c=>c.text).join("").replace(/```[a-z]*\n?|```/g,"").trim()
      setAna(JSON.parse(t))
    }catch(err){
      console.error("[Shindo]", err)
      setAna({fault_zone:err.message,severity:"minor",cascade_chain:["Check API key / console"],affected_prefectures:[],nuclear_risk:[],tsunami:{risk:"none"},historical_analogs:[],insight:err.message})
    }
    setLoading(false)
  }

  // ── MAP CLICK → SIMULATION ───────────────────────────────────
  const onClick = async e => {
    if(loading) return
    const rect=svgRef.current.getBoundingClientRect()
    const sx=(e.clientX-rect.left)*MAP_W/rect.width
    const sy=(e.clientY-rect.top)*MAP_H/rect.height
    const mx=(sx-mapT.x)/mapT.k
    const my=(sy-mapT.y)/mapT.k
    const [lon,lat]=proj.current.invert([mx,my])
    if(lat<23||lat>47||lon<120||lon>150) return
    const [ex,ey]=proj.current([lon,lat])
    setEpi({lat,lon,x:ex,y:ey}); setWk(k=>k+1); setAna(null)
    runAnalysis(lat, lon, mag, dep)
  }

  // ── SLIDER → RE-ANALYSE (debounced 800ms) ───────────────────
  const sliderTimerRef = useRef(null)
  useEffect(() => {
    if (!epi) return
    clearTimeout(sliderTimerRef.current)
    sliderTimerRef.current = setTimeout(() => {
      runAnalysis(epi.lat, epi.lon, mag, dep)
    }, 800)
    return () => clearTimeout(sliderTimerRef.current)
  }, [mag, dep])

  // ── CHAT SEND ────────────────────────────────────────────────
  const sendChat = async () => {
    const txt=chatInput.trim(); if(!txt||chatLoading) return
    setChatInput(""); setChatLoading(true)
    const next=[...chatMsgs,{role:"user",text:txt}]
    setChatMsgs(next)
    const simulation = epi ? {
      lat:epi.lat, lon:epi.lon, mag, depth:dep,
      fault_zone:ana?.fault_zone, severity:ana?.severity,
      affected:ana?.affected_prefectures?.map(p=>p.name)||[],
      tsunami_risk:ana?.tsunami?.risk, cascade:ana?.cascade_chain||[],
    } : null
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/agent/chat`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({messages:next.slice(-12).map(m=>({role:m.role,text:m.text})),simulation}),
      })
      if(!res.ok){const e=await res.json().catch(()=>({}));throw new Error(e?.detail||res.statusText)}
      const d=await res.json()
      setChatMsgs(m=>[...m,{role:"assistant",text:d.reply}])
    } catch(err) {
      setChatMsgs(m=>[...m,{role:"assistant",text:`Error: ${err.message}\n\nIs the backend running? cd backend && uvicorn app.main:app --reload`}])
    }
    setChatLoading(false)
  }

  // ── DERIVED STATE ────────────────────────────────────────────
  const activeFault = faultMatch(ana?.fault_zone)
  const tsunamiOn   = ana?.tsunami?.risk && ana.tsunami.risk!=="none"
  const aSet  = new Set(ana?.affected_prefectures?.map(p=>p.id)||[])
  const tsSet = new Set(ana?.affected_prefectures?.filter(p=>p.risk==="tsunami"||p.risk==="both").map(p=>p.id)||[])
  const nSet  = new Set(ana?.nuclear_risk?.filter(n=>n.risk!=="none").map(n=>n.id)||[])
  const sev   = SEV[ana?.severity]||["#050a14","#00e5ff"]
  const wR    = Math.min(190,18+mag*21)
  const tsR   = Math.min(300,50+mag*30)

  const faultPaths = FAULT_LINES.map(fl=>{
    const pts=fl.coords.map(([lt,ln])=>proj.current([ln,lt]).map(v=>v.toFixed(1)).join(","))
    return {...fl,d:`M ${pts.join(" L ")}`}
  })

  const tStr = `translate(${mapT.x},${mapT.y}) scale(${mapT.k})`

  return (
    <div style={{display:"flex",flexDirection:isMobile?"column":"row",height:"100vh",fontFamily:"'IBM Plex Mono',monospace",background:"#000510",overflow:"hidden"}}>

      {/* ══════════════════════════════════════════════════════════
          MAP COLUMN
      ══════════════════════════════════════════════════════════ */}
      <div style={{
        flex:isMobile?"none":"0 0 640px",
        height:isMobile?(mobileTab==="map"?"calc(100vh - 48px)":"0"):"100%",
        overflow:"hidden",
        display:isMobile&&mobileTab!=="map"?"none":"block",
        background:"#000510",position:"relative",userSelect:"none",
        borderRight:isMobile?"none":"1px solid #001a33",
        borderBottom:isMobile?"1px solid #001a33":"none",
      }}>
        <svg ref={svgRef} width="100%" height="100%" viewBox={`0 0 ${MAP_W} ${MAP_H}`}
          onClick={onClick} style={{display:"block",cursor:"crosshair",height:"100%"}}>
          <defs>
            <filter id="landGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.5" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="nodeGlow" x="-150%" y="-150%" width="400%" height="400%">
              <feGaussianBlur stdDeviation="3" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="nodeGlowHit" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur stdDeviation="6" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="faultGlow" x="-40%" y="-400%" width="180%" height="900%">
              <feGaussianBlur stdDeviation="3" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="epiGlow" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur stdDeviation="8" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
          </defs>

          <rect width={MAP_W} height={MAP_H} fill="#000510"/>
          {Array.from({length:9},(_,i)=><line key={`h${i}`} x1={0} y1={(i+1)*MAP_H/10} x2={MAP_W} y2={(i+1)*MAP_H/10} stroke="#001525" strokeWidth="0.4"/>)}
          {Array.from({length:7},(_,i)=><line key={`v${i}`} x1={(i+1)*MAP_W/8} y1={0} x2={(i+1)*MAP_W/8} y2={MAP_H} stroke="#001525" strokeWidth="0.4"/>)}

          <g transform={tStr}>

            {/* Plexus network lines */}
            {plexusLinks.map((lk,i)=>(
              <line key={i} x1={lk.x1} y1={lk.y1} x2={lk.x2} y2={lk.y2}
                stroke="#00b4d8" strokeWidth="0.4" opacity={Math.max(0.04,0.2-lk.d/145*0.16)}/>
            ))}

            {/* Fault lines */}
            {showFaults&&faultPaths.map(fl=>{
              const act=fl.id===activeFault
              const dash=fl.type==="strike_slip"?"8 4":fl.type==="reverse"?"3 3":undefined
              return (<g key={fl.id}>
                {act&&<path d={fl.d} fill="none" stroke={fl.color} strokeWidth={12} opacity={0.08} filter="url(#faultGlow)"/>}
                {act&&<path d={fl.d} fill="none" stroke={fl.color} strokeWidth={3.5} opacity={0.5} filter="url(#faultGlow)">
                  <animate attributeName="opacity" values="0.3;0.85;0.3" dur="1.6s" repeatCount="indefinite"/>
                </path>}
                <path d={fl.d} fill="none" stroke={fl.color} strokeWidth={act?2.2:0.7} strokeDasharray={dash} opacity={act?1:0.28}/>
              </g>)
            })}

            {/* Japan landmass */}
            {jpFeature&&<g filter="url(#landGlow)">
              <path d={pg.current(jpFeature)} fill="#020d1a" stroke="#00e5ff" strokeWidth="1.2" opacity="0.9"/>
            </g>}
            {!jpFeature&&jpPolys&&jpPolys.map((d,i)=>(
              <g key={i} filter="url(#landGlow)">
                <path d={d} fill="#020d1a" stroke="#00e5ff" strokeWidth="1.2" opacity="0.9"/>
              </g>
            ))}

            {/* ── TREMOR DAMAGE ZONES (intensity rings from epicenter) */}
            {epi&&ana?.affected_prefectures?.length>0&&(
              [...ana.affected_prefectures]
                .filter(ap=>ap.distance_km)
                .sort((a,b)=>(b.distance_km||0)-(a.distance_km||0))
                .map(ap=>{
                  const r=(ap.distance_km||50)*KM_PX
                  const col=iCol(ap.intensity)||"#884400"
                  const op=0.04+(ap.intensity||3)*0.016
                  return (<circle key={`zone-${ap.id}`}
                    cx={epi.x} cy={epi.y} r={r}
                    fill={col} fillOpacity={op}
                    stroke={col} strokeOpacity={0.5} strokeWidth={0.7}/>)
                })
            )}

            {/* ── TSUNAMI INLAND FLOOD ZONES */}
            {epi&&tsunamiOn&&ana?.affected_prefectures
              ?.filter(ap=>(ap.risk==="tsunami"||ap.risk==="both")&&PREFS.find(p=>p.id===ap.id)?.coast!=="inland")
              .map(ap=>{
                const pf=PREFS.find(p=>p.id===ap.id); if(!pf) return null
                const [px,py]=proj.current([pf.lon,pf.lat])
                const angle=Math.atan2(py-epi.y, px-epi.x)
                const h=ap.tsunami_height_m||3
                const ry=Math.min(60,16+h*5)
                const rx=Math.min(35,10+h*2.5)
                const cx=px+Math.cos(angle)*ry*0.45
                const cy=py+Math.sin(angle)*ry*0.45
                const deg=angle*180/Math.PI-90
                return (<g key={`flood-${ap.id}`}>
                  <ellipse cx={cx} cy={cy} rx={rx} ry={ry}
                    fill="#0055cc" fillOpacity={0.32}
                    stroke="#00aaff" strokeOpacity={0.6} strokeWidth={0.8}
                    transform={`rotate(${deg},${cx},${cy})`}/>
                  <ellipse cx={cx} cy={cy} rx={rx*0.55} ry={ry*0.55}
                    fill="#0099ff" fillOpacity={0.18}
                    transform={`rotate(${deg},${cx},${cy})`}/>
                  {ap.tsunami_height_m&&(
                    <text x={px+11} y={py-10} fontSize={9/mapT.k} fill="#00e5ff" fontFamily="inherit" fontWeight="700"
                      style={{textShadow:"0 0 6px #00e5ff"}}>{ap.tsunami_height_m}m</text>
                  )}
                </g>)
              })
            }

            {/* Active plexus highlight lines */}
            {epi&&ana&&prefXY.filter(p=>aSet.has(p.id)).map(p=>(
              <line key={`apl-${p.id}`} x1={p.x} y1={p.y} x2={epi.x} y2={epi.y}
                stroke="#00e5ff" strokeWidth="0.6" opacity="0.2" strokeDasharray="4 5"/>
            ))}

            {/* Prefecture nodes */}
            {prefXY.map(p=>{
              const hit=aSet.has(p.id), tsHit=tsSet.has(p.id)
              const info=ana?.affected_prefectures?.find(a=>a.id===p.id)
              const r=cityR(p.id,hit)
              const col=hit?(tsHit?"#00ffff":(iCol(info?.intensity)||"#00e5ff")):"#00b4d8"
              return (<g key={p.id} filter={hit?"url(#nodeGlowHit)":"url(#nodeGlow)"}>
                <circle cx={p.x} cy={p.y} r={r*2.8} fill={col} opacity={hit?0.12:0.04}/>
                <circle cx={p.x} cy={p.y} r={r*1.1} fill={col} opacity={hit?0.32:0.1}/>
                <circle cx={p.x} cy={p.y} r={hit?r*0.6:r*0.5} fill={hit?"#ffffff":col} opacity={hit?0.95:0.45}/>
              </g>)
            })}

            {/* Nuclear markers */}
            {NUCLEAR.map(n=>{
              const [x,y]=proj.current([n.lon,n.lat])
              const ar=nSet.has(n.id)
              const ri=ana?.nuclear_risk?.find(r=>r.id===n.id)
              const col=ar?(ri?.risk==="critical"?"#ff2020":ri?.risk==="elevated"?"#ff8800":"#ffdd00")
                :(n.status==="active"?"#00cc66":n.status==="restarting"?"#00aaff":"#1a3344")
              return (<g key={n.id}>
                {ar&&[0,1].map(i=>(<circle key={i} cx={x} cy={y} r="5" fill="none" stroke={col} strokeWidth="1.5" opacity="0">
                  <animate attributeName="r" values="5;24" dur="2.2s" begin={`${i*1.1}s`} repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.9;0" dur="2.2s" begin={`${i*1.1}s`} repeatCount="indefinite"/>
                </circle>))}
                <polygon points={`${x},${y-6} ${x+5},${y+4} ${x-5},${y+4}`} fill={col}
                  stroke="rgba(0,200,255,0.15)" strokeWidth="0.5"
                  opacity={(n.status==="shutdown"||n.status==="decommissioning")?0.25:0.9}/>
              </g>)
            })}

            {/* Tsunami propagation pulses */}
            {epi&&tsunamiOn&&ana?.affected_prefectures?.filter(ap=>(ap.risk==="tsunami"||ap.risk==="both")&&PREFS.find(p=>p.id===ap.id)?.coast!=="inland").map(ap=>{
              const pf=PREFS.find(p=>p.id===ap.id); if(!pf) return null
              const [px,py]=proj.current([pf.lon,pf.lat])
              const len=Math.hypot(px-epi.x,py-epi.y), seg=len*0.14
              return (<g key={`tp-${ap.id}`}>
                <line x1={epi.x} y1={epi.y} x2={px} y2={py} stroke="#00b4d8" strokeWidth="0.4" strokeDasharray="4 5" opacity="0.18"/>
                <line x1={epi.x} y1={epi.y} x2={px} y2={py} stroke="#00e5ff" strokeWidth="1.8" strokeDasharray={`${seg} ${len}`} opacity="0.8">
                  <animate attributeName="stroke-dashoffset" from={len+seg} to={-seg} dur="2.2s" repeatCount="indefinite"/>
                </line>
              </g>)
            })}

            {/* Nuclear cascade lines */}
            {epi&&ana?.nuclear_risk?.filter(n=>n.risk!=="none").map(nr=>{
              const pl=NUCLEAR.find(n=>n.id===nr.id); if(!pl) return null
              const [nx,ny]=proj.current([pl.lon,pl.lat])
              return <line key={nr.id} x1={epi.x} y1={epi.y} x2={nx} y2={ny} stroke="#ff4422" strokeWidth="0.9" strokeDasharray="5 3" opacity="0.65"/>
            })}

            {/* Seismic waves */}
            {epi&&[0,1,2].map(i=>(<circle key={`sw${wk}${i}`} cx={epi.x} cy={epi.y} r="4" fill="none" stroke="#ff4422" strokeWidth={2-i*0.5}>
              <animate attributeName="r" from="4" to={wR} dur={`${2.8+i*0.5}s`} begin={`${i*0.9}s`} repeatCount="indefinite"/>
              <animate attributeName="opacity" from="0.9" to="0" dur={`${2.8+i*0.5}s`} begin={`${i*0.9}s`} repeatCount="indefinite"/>
            </circle>))}

            {/* Tsunami waves */}
            {epi&&tsunamiOn&&[0,1,2,3].map(i=>(<circle key={`tw${wk}${i}`} cx={epi.x} cy={epi.y} r="12" fill="none" stroke="#00b4d8" strokeWidth={1.8-i*0.3}>
              <animate attributeName="r" from="12" to={tsR} dur={`${6+i*1.6}s`} begin={`${i*1.6}s`} repeatCount="indefinite"/>
              <animate attributeName="opacity" from="0.7" to="0" dur={`${6+i*1.6}s`} begin={`${i*1.6}s`} repeatCount="indefinite"/>
            </circle>))}

            {/* Destruction flash icons */}
            {epi&&ana?.affected_prefectures?.map(ap=>{
              const pf=PREFS.find(p=>p.id===ap.id); if(!pf) return null
              const [px,py]=proj.current([pf.lon,pf.lat])
              const isShaking=ap.risk==="shaking"||ap.risk==="both"
              const isTS=ap.risk==="tsunami"||ap.risk==="both"
              const severe=(ap.intensity||0)>=7
              const dur=severe?"0.35s":"0.6s"
              return (<g key={`icon-${ap.id}`}>
                {isShaking&&severe&&(<g>
                  <polygon points={`${px},${py-20} ${px+8},${py-7} ${px-8},${py-7}`} fill="#ff3322">
                    <animate attributeName="opacity" values="1;0;1;0;1" dur={dur} repeatCount="indefinite"/>
                  </polygon>
                </g>)}
                {isShaking&&!severe&&(ap.intensity||0)>=5&&(
                  <circle cx={px} cy={py} r={cityR(pf.id,true)+3} fill="none" stroke="#00e5ff" strokeWidth="1.5" opacity="0.5">
                    <animate attributeName="r" values={`${cityR(pf.id,true)+2};${cityR(pf.id,true)+7};${cityR(pf.id,true)+2}`} dur="1s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.5;0.1;0.5" dur="1s" repeatCount="indefinite"/>
                  </circle>
                )}
                {isTS&&[0,1].map(w=>(<path key={w}
                  d={`M${px-9},${py-19+w*5} C${px-6},${py-24+w*5} ${px-2},${py-15+w*5} ${px+1},${py-19+w*5} C${px+4},${py-23+w*5} ${px+7},${py-15+w*5} ${px+9},${py-19+w*5}`}
                  fill="none" stroke="#00e5ff" strokeWidth={2-w*0.4}>
                  <animate attributeName="opacity" values="1;0.1;1" dur={`${0.7+w*0.15}s`} repeatCount="indefinite"/>
                </path>))}
              </g>)
            })}

            {/* Nuclear flash icons */}
            {epi&&ana?.nuclear_risk?.filter(n=>n.risk==="critical"||n.risk==="elevated").map(nr=>{
              const pl=NUCLEAR.find(n=>n.id===nr.id); if(!pl) return null
              const [nx,ny]=proj.current([pl.lon,pl.lat])
              const col=nr.risk==="critical"?"#ff2020":"#ff8800"
              const dur=nr.risk==="critical"?"0.28s":"0.55s"
              return (<g key={`nfl-${nr.id}`}>
                {[0,60,120].map(a=>{ const r2=Math.PI*a/180
                  return (<path key={a}
                    d={`M${(nx+Math.cos(r2)*7).toFixed(1)},${(ny+Math.sin(r2)*7).toFixed(1)} A3,3 0 0,1 ${(nx+Math.cos(r2+Math.PI/3)*7).toFixed(1)},${(ny+Math.sin(r2+Math.PI/3)*7).toFixed(1)} L${nx},${ny} Z`}
                    fill={col} opacity="0.9">
                    <animate attributeName="opacity" values="0.9;0;0.9" dur={dur} repeatCount="indefinite"/>
                  </path>)
                })}
                <circle cx={nx} cy={ny} r="3" fill={col}>
                  <animate attributeName="opacity" values="0.9;0;0.9" dur={dur} repeatCount="indefinite"/>
                </circle>
              </g>)
            })}

            {/* Epicenter */}
            {epi&&<g filter="url(#epiGlow)">
              <circle cx={epi.x} cy={epi.y} r={6} fill="#ff3322"/>
              <line x1={epi.x-18} y1={epi.y} x2={epi.x-10} y2={epi.y} stroke="#ff3322" strokeWidth={2.5}/>
              <line x1={epi.x+10} y1={epi.y} x2={epi.x+18} y2={epi.y} stroke="#ff3322" strokeWidth={2.5}/>
              <line x1={epi.x} y1={epi.y-18} x2={epi.x} y2={epi.y-10} stroke="#ff3322" strokeWidth={2.5}/>
              <line x1={epi.x} y1={epi.y+10} x2={epi.x} y2={epi.y+18} stroke="#ff3322" strokeWidth={2.5}/>
            </g>}
          </g>{/* end zoomable group */}
        </svg>

        {/* Map overlay UI */}
        <div style={{position:"absolute",bottom:10,left:10,fontSize:11,color:"#0099bb",lineHeight:1.9,pointerEvents:"auto"}}>
          <div style={{display:"flex",alignItems:"center",gap:5,cursor:"pointer",opacity:showFaults?1:0.4}}
            onClick={e=>{e.stopPropagation();setShowFaults(f=>!f)}}>
            <div style={{width:16,height:1.5,background:"#ff9922"}}/><span>FAULTS {showFaults?"▪":"▫"}</span>
          </div>
          {showFaults&&FAULT_LINES.slice(0,4).map(fl=>(
            <div key={fl.id} style={{display:"flex",alignItems:"center",gap:4,paddingLeft:3}}>
              <div style={{width:12,height:1.5,background:fl.color,opacity:0.7}}/>
              <span style={{fontSize:10,opacity:0.7,color:"#007799"}}>{fl.name}</span>
            </div>
          ))}
          <div style={{marginTop:3,display:"flex",alignItems:"center",gap:5}}>
            <svg width="8" height="8"><polygon points="4,0 8,8 0,8" fill="#00cc66"/></svg>
            <span>NUCLEAR</span>
          </div>
        </div>
        {/* Zoom controls */}
        <div style={{position:"absolute",top:10,right:10,display:"inline-flex",flexDirection:"column",gap:3,width:"fit-content"}}>
          {[{l:"+",s:1.5},{l:"−",s:1/1.5},{l:"⌂",s:null}].map(({l,s})=>(
            <button key={l} onClick={e=>{
              e.stopPropagation()
              const svg=d3.select(svgRef.current)
              if(s===null) svg.call(zoomRef.current.transform,d3.zoomIdentity)
              else svg.call(zoomRef.current.scaleBy,s)
            }} style={{width:18,height:18,background:"#001a33",border:"1px solid #003366",color:"#00e5ff",
              fontSize:l==="⌂"?8:12,cursor:"pointer",borderRadius:3,lineHeight:1,fontFamily:"inherit"}}>
              {l}
            </button>
          ))}
        </div>
        {epi&&<div style={{position:"absolute",bottom:10,right:10,fontSize:11,color:"#00aacc",textAlign:"right",lineHeight:1.7}}>
          <div>{epi.lat.toFixed(2)}°N {epi.lon.toFixed(2)}°E</div>
          <div>M{mag.toFixed(1)} · {dep}km · ×{mapT.k.toFixed(1)}</div>
        </div>}
      </div>

      {/* ══════════════════════════════════════════════════════════
          INTEL PANEL
      ══════════════════════════════════════════════════════════ */}
      <div style={{
        flex:isMobile?"none":"0 0 280px",
        display:isMobile&&mobileTab!=="intel"?"none":"flex",
        flexDirection:"column",
        height:isMobile?"calc(100vh - 48px)":"100%",
        overflow:"hidden",
      }}>
        {/* Header + controls */}
        <div style={{padding:"10px 12px 8px",borderBottom:"1px solid #001a33",background:"#000b1a",flexShrink:0}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:8}}>
            <span style={{fontSize:14,fontWeight:700,letterSpacing:"0.06em",color:"#00e5ff",textShadow:"0 0 12px rgba(0,229,255,0.5)"}}>震度</span>
            <span style={{fontSize:10,color:"#0099bb",letterSpacing:"0.1em",fontWeight:600}}>SEISMIC INTEL</span>
          </div>
          {[["MAG",4,9.1,0.1,mag,v=>setMag(parseFloat(v)),mag.toFixed(1)],["DEPTH",5,100,5,dep,v=>setDep(parseInt(v)),dep+"km"]].map(([l,mn,mx,st,val,fn,d])=>(
            <div key={l} style={{display:"flex",alignItems:"center",gap:6,marginBottom:l==="MAG"?4:0}}>
              <span style={{fontSize:11,color:"#00aacc",letterSpacing:"0.07em",minWidth:42,fontWeight:600}}>{l}</span>
              <input type="range" min={mn} max={mx} step={st} value={val} onChange={e=>fn(e.target.value)}
                style={{flex:1,accentColor:"#00e5ff",height:3}}/>
              <span style={{fontSize:11,fontWeight:700,minWidth:32,textAlign:"right",color:"#00e5ff"}}>{d}</span>
            </div>
          ))}
        </div>

        {/* Analysis content */}
        <div style={{flex:1,overflowY:"auto",padding:"10px 12px"}}>
          {!epi&&!loading&&<div style={{paddingTop:32,textAlign:"center"}}>
            <div style={{fontSize:28,marginBottom:8,color:"#00e5ff",opacity:0.15,fontWeight:700}}>震</div>
            <div style={{fontSize:12,color:"#0099bb",letterSpacing:"0.08em",fontWeight:600}}>CLICK MAP TO SIMULATE</div>
            <div style={{fontSize:11,marginTop:6,color:"#006688"}}>Scroll to zoom · Drag to pan</div>
          </div>}
          {loading&&<div style={{paddingTop:32,textAlign:"center",lineHeight:2.4}}>
            <div style={{fontSize:12,color:"#00e5ff",marginBottom:4,letterSpacing:"0.08em",fontWeight:700}}>ANALYSING</div>
            {["FAULT ZONES","TREMOR EXTENT","TSUNAMI PATH","NUCLEAR RISK"].map(s=>(
              <div key={s} style={{fontSize:11,color:"#0077aa",fontWeight:600}}>{s}</div>
            ))}
          </div>}

          {ana&&!loading&&<div style={{fontSize:12}}>
            {/* Severity badge */}
            <div style={{padding:"6px 10px",borderRadius:5,marginBottom:9,background:sev[0],border:`1px solid ${sev[1]}40`,
              display:"flex",justifyContent:"space-between",alignItems:"center",boxShadow:`0 0 14px ${sev[1]}22`}}>
              <span style={{fontSize:11,fontWeight:700,letterSpacing:"0.09em",color:sev[1],textShadow:`0 0 8px ${sev[1]}`}}>{(ana.severity||"").toUpperCase()}</span>
              <span style={{fontSize:10,color:sev[1],opacity:0.8}}>{ana.fault_zone}</span>
            </div>

            {/* Cascade */}
            {ana.cascade_chain?.length>0&&<div style={{marginBottom:9}}>
              <div style={{fontSize:11,color:"#0099bb",letterSpacing:"0.1em",marginBottom:4,fontWeight:700}}>CASCADE</div>
              <div style={{display:"flex",flexWrap:"wrap",gap:3,alignItems:"center"}}>
                {ana.cascade_chain.map((s,i)=><span key={i} style={{display:"flex",alignItems:"center",gap:2}}>
                  <span style={{fontSize:11,padding:"2px 7px",background:"#000b1a",border:"1px solid #002244",borderRadius:3,color:"#00ccdd",fontWeight:600}}>{s}</span>
                  {i<ana.cascade_chain.length-1&&<span style={{fontSize:11,color:"#0055aa"}}>›</span>}
                </span>)}
              </div>
            </div>}

            {/* Tsunami */}
            {tsunamiOn&&<div style={{marginBottom:9,padding:"8px 10px",background:"#000b1a",border:"1px solid #003366",borderRadius:6,boxShadow:"0 0 16px rgba(0,100,200,0.1)"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:5}}>
                <span style={{fontSize:12,color:"#00aadd",letterSpacing:"0.1em",fontWeight:700}}>TSUNAMI</span>
                <span style={{fontSize:11,fontWeight:700,color:ana.tsunami.risk==="extreme"?"#ff4444":ana.tsunami.risk==="high"?"#ff8800":"#00ccff",
                  textShadow:"0 0 8px currentColor"}}>{ana.tsunami.risk.toUpperCase()}</span>
              </div>
              <div style={{display:"flex",gap:10,marginBottom:6,flexWrap:"wrap"}}>
                {ana.tsunami.max_height_m&&<div>
                  <div style={{fontSize:10,color:"#0088aa",letterSpacing:"0.06em",fontWeight:600}}>WAVE HEIGHT</div>
                  <div style={{fontSize:16,color:"#00e5ff",fontWeight:700,textShadow:"0 0 10px #00e5ff"}}>{ana.tsunami.max_height_m}m</div>
                </div>}
                {ana.tsunami.warning_min&&<div>
                  <div style={{fontSize:10,color:"#0088aa",letterSpacing:"0.06em",fontWeight:600}}>FIRST WAVE</div>
                  <div style={{fontSize:16,color:"#00e5ff",fontWeight:700,textShadow:"0 0 10px #00e5ff"}}>{ana.tsunami.warning_min}min</div>
                </div>}
              </div>
              {ana.tsunami.estimated_casualties!=null&&<div style={{fontSize:11,color:"#ff7755",fontWeight:700,marginBottom:5,textShadow:"0 0 6px #ff5533"}}>
                ~{ana.tsunami.estimated_casualties.toLocaleString()} est. casualties
              </div>}
              {ana.affected_prefectures?.filter(p=>p.risk==="tsunami"||p.risk==="both").map(p=>(
                <div key={p.id} style={{display:"flex",alignItems:"center",gap:5,marginBottom:2}}>
                  <div style={{width:5,height:5,borderRadius:"50%",background:"#00b4d8",boxShadow:"0 0 5px #00b4d8",flexShrink:0}}/>
                  <span style={{flex:1,fontSize:12,color:"#00ccee",fontWeight:600}}>{p.name}</span>
                  <span style={{fontSize:11,color:"#0088aa"}}>{p.distance_km}km</span>
                  {p.tsunami_height_m&&<span style={{fontSize:12,color:"#00e5ff",fontWeight:700}}>{p.tsunami_height_m}m</span>}
                </div>
              ))}
            </div>}

            {/* Shaking */}
            {ana.affected_prefectures?.filter(p=>p.risk==="shaking").length>0&&<div style={{marginBottom:9}}>
              <div style={{fontSize:11,color:"#0099bb",letterSpacing:"0.1em",marginBottom:4,fontWeight:700}}>GROUND SHAKING</div>
              {ana.affected_prefectures.filter(p=>p.risk==="shaking").slice(0,6).map(p=>(
                <div key={p.id} style={{display:"flex",alignItems:"center",gap:5,marginBottom:3}}>
                  <div style={{width:6,height:6,borderRadius:"50%",background:iCol(p.intensity)||"#0088aa",flexShrink:0}}/>
                  <span style={{flex:1,fontSize:12,color:"#00ccee",fontWeight:600}}>{p.name}</span>
                  <span style={{fontSize:11,color:"#0088aa"}}>{p.distance_km}km</span>
                  <span style={{fontSize:11,background:"#000b1a",border:"1px solid #002244",padding:"1px 6px",borderRadius:3,color:"#00e5ff",fontWeight:700,minWidth:16,textAlign:"center"}}>{p.shindo}</span>
                </div>
              ))}
            </div>}

            {/* Nuclear */}
            {ana.nuclear_risk?.filter(n=>n.risk!=="none").length>0&&<div style={{marginBottom:9,padding:"8px 10px",background:"#0c0005",border:"1px solid #440011",borderRadius:5,boxShadow:"0 0 14px rgba(200,0,0,0.07)"}}>
              <div style={{fontSize:11,color:"#ff4455",letterSpacing:"0.1em",marginBottom:4,fontWeight:700}}>NUCLEAR RISK</div>
              {ana.nuclear_risk.filter(n=>n.risk!=="none").map(n=>(
                <div key={n.id} style={{display:"flex",alignItems:"center",gap:4,marginBottom:3}}>
                  <svg width="8" height="8"><polygon points="4,0 8,8 0,8" fill="#ff2244"/></svg>
                  <span style={{flex:1,fontSize:12,color:"#cc6655",fontWeight:600}}>{n.name}</span>
                  <span style={{fontSize:11,color:"#882233"}}>{n.distance_km}km</span>
                  <span style={{fontSize:11,color:"#ff3355",fontWeight:700,textShadow:"0 0 6px #ff2244"}}>{n.risk.toUpperCase()}</span>
                </div>
              ))}
            </div>}

            {/* Analogs */}
            {ana.historical_analogs?.length>0&&<div style={{marginBottom:9}}>
              <div style={{fontSize:11,color:"#0099bb",letterSpacing:"0.1em",marginBottom:4,fontWeight:700}}>HISTORICAL ANALOGS</div>
              {ana.historical_analogs.slice(0,3).map((a,i)=>(
                <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"5px 9px",marginBottom:3,background:"#000b1a",border:"1px solid #002244",borderRadius:4}}>
                  <span style={{fontSize:12,color:"#00ccdd",fontWeight:600}}>{a.name} <span style={{color:"#0077aa",fontSize:11}}>({a.year})</span></span>
                  <span style={{color:"#0099bb",fontSize:12,fontWeight:700}}>M{a.magnitude}</span>
                </div>
              ))}
            </div>}

            {/* Insight */}
            {ana.insight&&<div style={{fontSize:12,lineHeight:1.75,color:"#a0e4ff",fontWeight:500,padding:"9px 12px",borderLeft:"2px solid #0055aa",background:"#000f1f",borderRadius:"0 6px 6px 0"}}>{ana.insight}</div>}
          </div>}
        </div>
      </div>



      {/* ══════════════════════════════════════════════════════════
          震度 CHAT PANEL
      ══════════════════════════════════════════════════════════ */}
      <div style={{
        flex:1,
        display:isMobile&&mobileTab!=="chat"?"none":"flex",
        flexDirection:"column",
        overflow:"hidden",
        height:isMobile?"calc(100vh - 48px)":"100%",
        borderLeft:isMobile?"none":"1px solid #001a33",
      }}>
        <div style={{padding:"14px 18px 12px",borderBottom:"1px solid #001a33",background:"#000b1a",flexShrink:0}}>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:8,height:8,borderRadius:"50%",background:"#00e5ff",boxShadow:"0 0 10px #00e5ff"}}/>
            <div>
              <div style={{fontSize:15,fontWeight:800,letterSpacing:"0.08em",color:"#00e5ff",textShadow:"0 0 12px rgba(0,229,255,0.5)"}}>震度 SHINDO</div>
              <div style={{fontSize:10,color:"#005577",letterSpacing:"0.12em",marginTop:1}}>SEISMIC INTELLIGENCE AGENT</div>
            </div>
          </div>
        </div>
        <div style={{flex:1,overflowY:"auto",padding:"14px"}}>
          {chatMsgs.map((m,i)=><ChatBubble key={i} msg={m}/>)}
          {chatLoading&&<div style={{padding:"10px 14px",background:"#000f1f",border:"1px solid #001a2e",borderRadius:6,color:"#004466",fontSize:13}}>
            <span>analyzing </span>
            {[0,1,2].map(i=><span key={i} style={{display:"inline-block",width:4,height:4,borderRadius:"50%",background:"#00e5ff",margin:"0 2px",animation:`bounce 1.2s ${i*0.2}s infinite`}}/>)}
          </div>}
          <div ref={chatEndRef}/>
        </div>
        <div style={{padding:"10px 14px 14px",borderTop:"1px solid #001a33",flexShrink:0,background:"#000b1a"}}>
          <div style={{display:"flex",gap:6,alignItems:"flex-end"}}>
            <textarea value={chatInput} onChange={e=>setChatInput(e.target.value)}
              onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat()}}}
              placeholder="Ask about fault zones, tsunami risk, historical events…"
              rows={2}
              style={{flex:1,background:"#000f1f",border:"1px solid #002244",borderRadius:6,
                padding:"8px 10px",color:"#7df9ff",fontSize:14,fontFamily:"inherit",
                resize:"none",outline:"none",lineHeight:1.5}}/>
            <button onClick={sendChat} disabled={!chatInput.trim()||chatLoading}
              style={{height:50,padding:"0 14px",background:chatInput.trim()&&!chatLoading?"#003366":"#000f1f",
                border:"1px solid #003366",borderRadius:6,
                color:chatInput.trim()&&!chatLoading?"#00e5ff":"#002233",
                cursor:chatInput.trim()&&!chatLoading?"pointer":"default",
                fontSize:18,fontFamily:"inherit",transition:"all 0.2s"}}>›</button>
          </div>
          <div style={{fontSize:10,color:"#003344",marginTop:5}}>Enter to send · Shift+Enter for newline</div>
        </div>
      </div>

      {/* ── MOBILE BOTTOM TAB BAR ─────────────────────────────── */}
      {isMobile&&<div style={{display:"flex",height:48,flexShrink:0,borderTop:"1px solid #001a33",background:"#000b1a"}}>
        {[["map","MAP"],["intel","INTEL"],["chat","CHAT"]].map(([t,label])=>(
          <button key={t} onClick={()=>{ setMobileTab(t); if(t==="chat") setTimeout(()=>chatEndRef.current?.scrollIntoView(),100) }}
            style={{flex:1,background:mobileTab===t?"#001a33":"none",border:"none",
              borderTop:`2px solid ${mobileTab===t?"#00e5ff":"transparent"}`,
              color:mobileTab===t?"#00e5ff":"#004466",
              fontSize:11,cursor:"pointer",fontFamily:"inherit",letterSpacing:"0.1em",fontWeight:700}}>
            {t==="intel"&&ana&&!loading&&<span style={{display:"block",fontSize:7,color:"#ff9922",marginBottom:1}}>●</span>}
            {label}
          </button>
        ))}
      </div>}

      <style>{`
        @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
        textarea::placeholder { color: #003a55; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #000510; }
        ::-webkit-scrollbar-thumb { background: #001a33; border-radius: 2px; }
      `}</style>
    </div>
  )
}
