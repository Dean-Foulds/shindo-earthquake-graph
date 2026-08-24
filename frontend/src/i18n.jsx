/* eslint-disable react-refresh/only-export-components --
   Deliberately one module: the dictionaries, the hook and the two components
   that read them travel together. Splitting them only to satisfy fast refresh
   would scatter the translations across three files. */
import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { MONO } from "./fonts"

const STORE = "shindo.lang"

export const LANGS = [
  { id: "en", label: "EN" },
  { id: "ja", label: "日本語" },
]

// ── UI strings ───────────────────────────────────────────────────
// Keys are flat and dotted. `{name}` placeholders are filled by t(key, vars).
const EN = {
  // shell
  "nav.signOut":        "SIGN OUT",
  "nav.dashboard":      "DATA DASHBOARD →",
  "nav.backToShindo":   "← SHINDO",
  "nav.dashboardTitle": "DATA ANALYSIS DASHBOARD",
  "nav.language":       "Language",

  // login
  "login.tagline":         "Japan seismic risk analysis",
  "login.signup":          "SIGN UP",
  "login.signin":          "SIGN IN",
  "login.email":           "EMAIL",
  "login.password":        "PASSWORD",
  "login.passwordHint":    "At least 10 characters.",
  "login.passwordTooShort":"Password must be at least 10 characters",
  "login.unreachable":     "Can't reach the server. Is the backend running?",
  "login.createAccount":   "CREATE ACCOUNT",
  "login.note":            "An account is required because each simulation calls a language model. Simulations are capped per account.",

  // chat
  "chat.greeting":        "Hello — I'm 震度 (Shindo), your seismic risk assistant.\n\nClick anywhere on Japan to run a simulation, then ask me anything about the event, fault zones, or historical precedents.",
  "chat.subtitle":        "SEISMIC INTELLIGENCE AGENT",
  "chat.you":             "YOU",
  "chat.placeholder":     "Ask about fault zones, tsunami risk, historical events…",
  "chat.placeholderDash": "Ask about fault zones, nuclear risk, historical events…",
  "chat.hint":            "Enter to send · Shift+Enter for newline",
  "chat.thinking":        "analyzing",
  "chat.error":           "Error: {msg}",
  "chat.backendHint":     "Is the backend running? cd backend && uvicorn app.main:app --reload",

  // live feed / map
  "live.title":     "● SEISMIC CONDITIONS",
  "live.summary":   "{n} events · M{min}–M{max}",
  "live.window":    "last 20 days · hover dots for detail",
  "live.cta":       "CLICK MAP TO SIMULATE →",
  "live.back":      "← LIVE CONDITIONS",
  "legend.faults":  "FAULTS",
  "legend.nuclear": "NUCLEAR",
  "legend.recent":  "RECENT EVENTS",

  // intel panel
  "intel.title":            "SEISMIC INTEL",
  "intel.mag":              "MAG",
  "intel.depth":            "DEPTH",
  "intel.belowSurface":     "BELOW SURFACE",
  "intel.depthAuto":        "DEPTH AUTO",
  "intel.offshore":         "OFFSHORE",
  "intel.onshore":          "ONSHORE",
  "intel.clickToSimulate":  "CLICK MAP TO SIMULATE",
  "intel.mapHint":          "Scroll to zoom · Drag to pan",
  "intel.recentCount":      "● {n} RECENT EVENTS",
  "intel.analysing":        "ANALYSING",
  "intel.step.faults":      "FAULT ZONES",
  "intel.step.tremor":      "TREMOR EXTENT",
  "intel.step.tsunami":     "TSUNAMI PATH",
  "intel.step.nuclear":     "NUCLEAR RISK",
  "intel.step.neo4j":       "NEO4J INFERENCE",
  "intel.impact":           "ESTIMATED IMPACT",
  "intel.casualties":       "CASUALTIES",
  "intel.displaced":        "DISPLACED",
  "intel.impactNote":       "MODEL ESTIMATE · NOT AN OFFICIAL FORECAST",
  "intel.cascade":          "CASCADE",
  "intel.tsunami":          "TSUNAMI",
  "intel.waveHeight":       "WAVE HEIGHT",
  "intel.firstWave":        "FIRST WAVE",
  "intel.tsunamiCasualties":"~{n} est. casualties",
  "intel.neo4jBasis":       "NEO4J HISTORICAL BASIS",
  "intel.eventCount":       "{n} events",
  "intel.jma":              "JMA",
  "intel.observedRange":    "OBSERVED RANGE",
  "intel.avg":              "AVG",
  "intel.neo4jLoading":     "NEO4J INFERENCE LOADING…",
  "intel.shaking":          "GROUND SHAKING",
  "intel.nuclear":          "NUCLEAR RISK",
  "intel.analogs":          "HISTORICAL ANALOGS",
  "intel.deaths":           "{n} deaths",
  "intel.analysisFailed":   "Analysis failed",
  "intel.backendDown":      "Backend unreachable — cd backend && uvicorn app.main:app --reload",
  "intel.unknownPlace":     "Japan",

  "unit.km":  "{n}km",
  "unit.m":   "{n}m",
  "unit.min": "{n}min",

  // depth regimes
  "depth.shallow":    "SHALLOW CRUSTAL",
  "depth.transition": "TRANSITION",
  "depth.intraslab":  "INTRASLAB",
  "depth.deep":       "DEEP INTRASLAB",

  // severities / risk levels
  "sev.minor":        "MINOR",
  "sev.moderate":     "MODERATE",
  "sev.strong":       "STRONG",
  "sev.major":        "MAJOR",
  "sev.catastrophic": "CATASTROPHIC",

  "tsrisk.none":     "NONE",
  "tsrisk.low":      "LOW",
  "tsrisk.moderate": "MODERATE",
  "tsrisk.high":     "HIGH",
  "tsrisk.extreme":  "EXTREME",

  "nrisk.none":       "NONE",
  "nrisk.monitoring": "MONITORING",
  "nrisk.elevated":   "ELEVATED",
  "nrisk.critical":   "CRITICAL",

  // dashboard — tabs & KPIs
  "dash.tab.eda":         "EDA CHARTS",
  "dash.tab.edaShort":    "EDA",
  "dash.tab.risk":        "RISK ANALYSIS",
  "dash.tab.riskShort":   "RISK",
  "dash.tab.cypher":      "CYPHER QUERIES",
  "dash.tab.cypherShort": "CYPHER",

  "dash.kpi.total":        "TOTAL EVENTS (M4+)",
  "dash.kpi.totalSub":     "1900 – 2024",
  "dash.kpi.deadliest":    "DEADLIEST EVENT",
  "dash.kpi.deadliestSub": "Tohoku 2011 · 22k deaths",
  "dash.kpi.faults":       "ACTIVE FAULT ZONES",
  "dash.kpi.faultsSub":    "monitored in graph",
  "dash.kpi.npp":          "NUCLEAR FACILITIES",
  "dash.kpi.nppSub":       "tracked in graph",
  "dash.kpi.annual":       "AVG ANNUAL M6+",
  "dash.kpi.annualSub":    "past 50 years",

  // dashboard — charts
  "dash.magDist":       "MAGNITUDE DISTRIBUTION",
  "dash.magDistNote":   "38% of events M4.0–4.4. Each magnitude step is ~31.6× more energy.",
  "dash.depthDist":     "DEPTH DISTRIBUTION (km)",
  "dash.depthDistNote": "35% shallow crustal (10–30km) — highest surface shaking. Deep intraslab events less destructive but broader reach.",
  "dash.decade":        "EVENTS PER DECADE (M4+)",
  "dash.decadeNote":    "Increasing trend due to improved seismic network coverage (not actual increase). Red bars = high tsunami years.",
  "dash.decadeTsSuffix":"ts",
  "dash.faultDeaths":   "FAULT ZONE TOTAL DEATHS",
  "dash.faultDeathsNote":"Sagami Trough leads due to 1923 Great Kanto (99,000 deaths). Japan Trench second: 2011 Tohoku (22,000).",
  "dash.prefIndex":     "PREFECTURE COMPOSITE RISK INDEX (top 8)",
  "dash.prefFormula":   "Score = quake_count + tsunami_count×10 + npp_count×5 + subduction_zones×8",
  "dash.th.prefecture": "PREFECTURE",
  "dash.th.riskScore":  "RISK SCORE",
  "dash.th.quakes":     "QUAKES",
  "dash.th.tsunamis":   "TSUNAMIS",
  "dash.th.npp":        "NPP",
  "dash.th.riskBar":    "RISK BAR",

  // dashboard — risk tab
  "risk.disclaimerTitle": "STATISTICAL ANALYSIS — NOT PREDICTION",
  "risk.disclaimer":      "These figures represent historical recurrence rates derived from 75 years of seismic records. Earthquake timing is inherently unpredictable. A ratio above 1.0× indicates a fault zone has exceeded its historical average recurrence interval — this does not imply imminent occurrence.",
  "risk.loading":         "Loading recurrence data from graph…",
  "risk.error":           "Could not load risk data: {msg}",
  "risk.rankedTitle":     "HISTORICAL OVERDUE RATIO — RANKED",
  "risk.basedOn":         "Based on {n} events · {from}–{to}",
  "risk.overdueLabel":    "M{tier}+ overdue {score}×",
  "risk.predictedMax":    "Predicted max:",
  "risk.lastMajor":       "Last major:",
  "risk.totalEvents":     "{n} total events",
  "risk.th.tier":         "TIER",
  "risk.th.events":       "EVENTS",
  "risk.th.avgInterval":  "AVG INTERVAL",
  "risk.th.lastEvent":    "LAST EVENT",
  "risk.th.yrsSince":     "YRS SINCE",
  "risk.th.overdue":      "OVERDUE RATIO",
  "risk.lowN":            "low n",
  "risk.years":           "{n} yr",

  // fault types
  "faulttype.subduction":  "subduction",
  "faulttype.strike_slip": "strike-slip",
  "faulttype.crustal":     "crustal",
  "faulttype.reverse":     "reverse",
  "faulttype.intraslab":   "intraslab",

  // dashboard — cypher tab
  "cy.howTo":       "HOW TO USE",
  "cy.howTo.open":  "Open",
  "cy.howTo.db":    "your database",
  "cy.howTo.tab":   "tab. Paste any query below and run it.",
  "cy.howTo.schema":"Queries use the SHINDO graph schema:",
  "cy.schema":      "GRAPH SCHEMA",
  "cy.copy":        "copy",
  "cy.copied":      "✓ copied",

  "cy.1.title": "Cascade Trace — 2011 Tohoku",
  "cy.1.desc":  "Follow a full disaster chain: fault zone → earthquake → tsunami → prefecture → nuclear facility.",
  "cy.2.title": "Compounded Risk Corridors",
  "cy.2.desc":  "Prefectures on subduction faults with a nuclear plant and Pacific coast exposure.",
  "cy.3.title": "Historical Analog Finder",
  "cy.3.desc":  "Find past M7.5+ subduction events to use as analogs for Nankai Trough scenarios.",
  "cy.4.title": "Nuclear Proximity Risk",
  "cy.4.desc":  "Every M6.5+ earthquake that struck within 50km of a nuclear plant.",
  "cy.5.title": "Decade Pattern Analysis",
  "cy.5.desc":  "Which decades saw the most seismic activity and tsunami events?",
  "cy.6.title": "Fault Zone Lethality Ranking",
  "cy.6.desc":  "Rank fault zones by total documented deaths and predicted future maximum.",
  "cy.7.title": "Hamaoka Nuclear Risk",
  "cy.7.desc":  "All historical quakes within 50km of Hamaoka — the plant above the Nankai Trough.",
  "cy.8.title": "Prefecture Composite Risk Index",
  "cy.8.desc":  "Score each prefecture across four dimensions: quake count, tsunami exposure, NPP proximity, subduction fault coverage.",
  "cy.9.title": "Graph Schema Check",
  "cy.9.desc":  "Verify node counts and relationship types loaded correctly in Neo4j Aura.",
}

const JA = {
  // shell
  "nav.signOut":        "ログアウト",
  "nav.dashboard":      "データ分析 →",
  "nav.backToShindo":   "← 震度",
  "nav.dashboardTitle": "データ分析ダッシュボード",
  "nav.language":       "言語",

  // login
  "login.tagline":         "日本の地震リスク解析",
  "login.signup":          "新規登録",
  "login.signin":          "ログイン",
  "login.email":           "メールアドレス",
  "login.password":        "パスワード",
  "login.passwordHint":    "10文字以上で入力してください。",
  "login.passwordTooShort":"パスワードは10文字以上で入力してください",
  "login.unreachable":     "サーバーに接続できません。バックエンドは起動していますか？",
  "login.createAccount":   "アカウント作成",
  "login.note":            "シミュレーションのたびに言語モデルを呼び出すため、アカウントが必要です。実行回数はアカウントごとに上限があります。",

  // chat
  "chat.greeting":        "こんにちは。地震リスクアシスタントの震度（シンド）です。\n\n日本地図上の任意の地点をクリックするとシミュレーションを実行します。地震、断層帯、過去の事例など何でもお尋ねください。",
  "chat.subtitle":        "地震インテリジェンス エージェント",
  "chat.you":             "あなた",
  "chat.placeholder":     "断層帯・津波リスク・過去の地震について質問…",
  "chat.placeholderDash": "断層帯・原子力リスク・過去の地震について質問…",
  "chat.hint":            "Enterで送信 · Shift+Enterで改行",
  "chat.thinking":        "解析中",
  "chat.error":           "エラー: {msg}",
  "chat.backendHint":     "バックエンドは起動していますか？ cd backend && uvicorn app.main:app --reload",

  // live feed / map
  "live.title":     "● 地震活動状況",
  "live.summary":   "{n}件 · M{min}〜M{max}",
  "live.window":    "過去20日間 · 点にカーソルを合わせると詳細",
  "live.cta":       "地図をクリックしてシミュレーション →",
  "live.back":      "← 現在の活動状況",
  "legend.faults":  "断層帯",
  "legend.nuclear": "原子力施設",
  "legend.recent":  "最近の地震",

  // intel panel
  "intel.title":            "地震情報",
  "intel.mag":              "規模",
  "intel.depth":            "深さ",
  "intel.belowSurface":     "地表下",
  "intel.depthAuto":        "海底深度",
  "intel.offshore":         "海域",
  "intel.onshore":          "陸域",
  "intel.clickToSimulate":  "地図をクリックしてシミュレーション",
  "intel.mapHint":          "スクロールで拡大縮小 · ドラッグで移動",
  "intel.recentCount":      "● 最近の地震 {n}件",
  "intel.analysing":        "解析中",
  "intel.step.faults":      "断層帯",
  "intel.step.tremor":      "揺れの範囲",
  "intel.step.tsunami":     "津波の経路",
  "intel.step.nuclear":     "原子力リスク",
  "intel.step.neo4j":       "NEO4J 推論",
  "intel.impact":           "想定被害",
  "intel.casualties":       "死者数",
  "intel.displaced":        "避難者数",
  "intel.impactNote":       "モデルによる推計 · 公式な予測ではありません",
  "intel.cascade":          "被害の連鎖",
  "intel.tsunami":          "津波",
  "intel.waveHeight":       "最大波高",
  "intel.firstWave":        "第一波到達",
  "intel.tsunamiCasualties":"想定死者数 約{n}人",
  "intel.neo4jBasis":       "NEO4J 過去事例",
  "intel.eventCount":       "{n}件",
  "intel.jma":              "気象庁",
  "intel.observedRange":    "観測範囲",
  "intel.avg":              "平均",
  "intel.neo4jLoading":     "NEO4J 推論を取得中…",
  "intel.shaking":          "地震動",
  "intel.nuclear":          "原子力リスク",
  "intel.analogs":          "過去の類似事例",
  "intel.deaths":           "死者{n}人",
  "intel.analysisFailed":   "解析に失敗しました",
  "intel.backendDown":      "バックエンドに接続できません — cd backend && uvicorn app.main:app --reload",
  "intel.unknownPlace":     "日本",

  "unit.km":  "{n}km",
  "unit.m":   "{n}m",
  "unit.min": "{n}分",

  // depth regimes
  "depth.shallow":    "浅発地殻内",
  "depth.transition": "遷移帯",
  "depth.intraslab":  "スラブ内",
  "depth.deep":       "深発スラブ内",

  // severities / risk levels
  "sev.minor":        "軽微",
  "sev.moderate":     "中程度",
  "sev.strong":       "大きい",
  "sev.major":        "甚大",
  "sev.catastrophic": "壊滅的",

  "tsrisk.none":     "なし",
  "tsrisk.low":      "低",
  "tsrisk.moderate": "中",
  "tsrisk.high":     "高",
  "tsrisk.extreme":  "極めて高い",

  "nrisk.none":       "なし",
  "nrisk.monitoring": "監視",
  "nrisk.elevated":   "警戒",
  "nrisk.critical":   "重大",

  // dashboard — tabs & KPIs
  "dash.tab.eda":         "EDAチャート",
  "dash.tab.edaShort":    "EDA",
  "dash.tab.risk":        "リスク解析",
  "dash.tab.riskShort":   "リスク",
  "dash.tab.cypher":      "Cypherクエリ",
  "dash.tab.cypherShort": "Cypher",

  "dash.kpi.total":        "総地震数 (M4以上)",
  "dash.kpi.totalSub":     "1900年 – 2024年",
  "dash.kpi.deadliest":    "最大被害の地震",
  "dash.kpi.deadliestSub": "東北 2011年 · 死者約2.2万人",
  "dash.kpi.faults":       "活断層帯",
  "dash.kpi.faultsSub":    "グラフで監視中",
  "dash.kpi.npp":          "原子力施設",
  "dash.kpi.nppSub":       "グラフに登録済み",
  "dash.kpi.annual":       "年平均 M6以上",
  "dash.kpi.annualSub":    "過去50年間",

  // dashboard — charts
  "dash.magDist":       "マグニチュード分布",
  "dash.magDistNote":   "全体の38%がM4.0〜4.4。マグニチュードが1上がるとエネルギーは約31.6倍になります。",
  "dash.depthDist":     "震源深さ分布 (km)",
  "dash.depthDistNote": "35%が浅発地殻内 (10〜30km) で、地表の揺れが最も強くなります。深発スラブ内地震は破壊力は小さいものの影響範囲は広くなります。",
  "dash.decade":        "10年ごとの地震数 (M4以上)",
  "dash.decadeNote":    "増加傾向は観測網の充実によるもので、実際の地震増加ではありません。赤いバーは津波の多い年代です。",
  "dash.decadeTsSuffix":"件",
  "dash.faultDeaths":   "断層帯別 死者数合計",
  "dash.faultDeathsNote":"相模トラフが最多。1923年の関東大震災 (死者99,000人) によるものです。次いで日本海溝、2011年の東北地方太平洋沖地震 (22,000人)。",
  "dash.prefIndex":     "都道府県別 複合リスク指数 (上位8)",
  "dash.prefFormula":   "スコア = 地震数 + 津波数×10 + 原子力施設数×5 + 沈み込み帯数×8",
  "dash.th.prefecture": "都道府県",
  "dash.th.riskScore":  "リスク指数",
  "dash.th.quakes":     "地震数",
  "dash.th.tsunamis":   "津波数",
  "dash.th.npp":        "原発",
  "dash.th.riskBar":    "リスク",

  // dashboard — risk tab
  "risk.disclaimerTitle": "統計分析であり予知ではありません",
  "risk.disclaimer":      "以下の数値は75年分の地震記録から算出した過去の再来間隔です。地震の発生時期は本質的に予測できません。比率が1.0×を超えることは、その断層帯が過去の平均再来間隔を超過していることを示すだけで、発生が差し迫っていることを意味するものではありません。",
  "risk.loading":         "グラフから再来間隔データを読み込み中…",
  "risk.error":           "リスクデータを読み込めませんでした: {msg}",
  "risk.rankedTitle":     "過去平均に対する経過比 — ランキング",
  "risk.basedOn":         "{n}件の地震に基づく · {from}年〜{to}年",
  "risk.overdueLabel":    "M{tier}以上 経過比 {score}×",
  "risk.predictedMax":    "想定最大規模:",
  "risk.lastMajor":       "直近の大地震:",
  "risk.totalEvents":     "総地震数 {n}件",
  "risk.th.tier":         "規模区分",
  "risk.th.events":       "地震数",
  "risk.th.avgInterval":  "平均間隔",
  "risk.th.lastEvent":    "直近発生",
  "risk.th.yrsSince":     "経過年数",
  "risk.th.overdue":      "経過比",
  "risk.lowN":            "標本少",
  "risk.years":           "{n}年",

  // fault types
  "faulttype.subduction":  "沈み込み帯",
  "faulttype.strike_slip": "横ずれ断層",
  "faulttype.crustal":     "地殻内",
  "faulttype.reverse":     "逆断層",
  "faulttype.intraslab":   "スラブ内",

  // dashboard — cypher tab
  "cy.howTo":       "使い方",
  "cy.howTo.open":  "開く:",
  "cy.howTo.db":    "対象のデータベース",
  "cy.howTo.tab":   "タブ。下のクエリを貼り付けて実行してください。",
  "cy.howTo.schema":"クエリは SHINDO グラフスキーマを使用します:",
  "cy.schema":      "グラフスキーマ",
  "cy.copy":        "コピー",
  "cy.copied":      "✓ コピー済み",

  "cy.1.title": "連鎖被害の追跡 — 2011年 東北",
  "cy.1.desc":  "災害の連鎖を一括で辿ります: 断層帯 → 地震 → 津波 → 都道府県 → 原子力施設。",
  "cy.2.title": "複合リスク回廊",
  "cy.2.desc":  "沈み込み帯上にあり、原子力施設を抱え、太平洋側に面する都道府県。",
  "cy.3.title": "過去の類似事例の検索",
  "cy.3.desc":  "南海トラフのシナリオの類似事例となる、過去のM7.5以上の沈み込み帯地震を抽出します。",
  "cy.4.title": "原子力施設への近接リスク",
  "cy.4.desc":  "原子力施設から50km以内で発生したM6.5以上のすべての地震。",
  "cy.5.title": "年代別パターン分析",
  "cy.5.desc":  "地震活動と津波が最も多かった年代はどこか。",
  "cy.6.title": "断層帯別 致死性ランキング",
  "cy.6.desc":  "記録された死者数の合計と想定最大規模で断層帯を順位付けします。",
  "cy.7.title": "浜岡原発のリスク",
  "cy.7.desc":  "南海トラフ上に位置する浜岡原発から50km以内で発生した過去のすべての地震。",
  "cy.8.title": "都道府県別 複合リスク指数",
  "cy.8.desc":  "地震数・津波の曝露・原子力施設への近接・沈み込み帯の被覆という4つの観点で各都道府県を評価します。",
  "cy.9.title": "グラフスキーマの確認",
  "cy.9.desc":  "Neo4j Aura にノード数とリレーション種別が正しく読み込まれているかを検証します。",
}

const DICT = { en: EN, ja: JA }

// ── Localised entity names ───────────────────────────────────────
// Resolved from the stable id rather than from whatever name the model returned,
// so a prefecture keeps its correct label in both locales.
const PREF_JA = {
  hokkaido:"北海道", aomori:"青森県", iwate:"岩手県", miyagi:"宮城県", akita:"秋田県",
  yamagata:"山形県", fukushima:"福島県", ibaraki:"茨城県", tochigi:"栃木県", gunma:"群馬県",
  saitama:"埼玉県", chiba:"千葉県", tokyo:"東京都", kanagawa:"神奈川県", niigata:"新潟県",
  toyama:"富山県", ishikawa:"石川県", fukui:"福井県", yamanashi:"山梨県", nagano:"長野県",
  gifu:"岐阜県", shizuoka:"静岡県", aichi:"愛知県", mie:"三重県", shiga:"滋賀県",
  kyoto:"京都府", osaka:"大阪府", hyogo:"兵庫県", nara:"奈良県", wakayama:"和歌山県",
  tottori:"鳥取県", shimane:"島根県", okayama:"岡山県", hiroshima:"広島県", yamaguchi:"山口県",
  tokushima:"徳島県", kagawa:"香川県", ehime:"愛媛県", kochi:"高知県", fukuoka:"福岡県",
  saga:"佐賀県", nagasaki:"長崎県", kumamoto:"熊本県", oita:"大分県", miyazaki:"宮崎県",
  kagoshima:"鹿児島県", okinawa:"沖縄県",
}

const NUCLEAR_JA = {
  fukushima_daiichi:"福島第一原発", fukushima_daini:"福島第二原発", onagawa:"女川原発",
  tokai_daini:"東海第二原発", kashiwazaki_kariwa:"柏崎刈羽原発", shika:"志賀原発",
  mihama:"美浜原発", ohi:"大飯原発", takahama:"高浜原発", hamaoka:"浜岡原発",
  shimane_npp:"島根原発", shimane:"島根原発", ikata:"伊方原発", genkai:"玄海原発",
  sendai_npp:"川内原発", tomari:"泊原発",
}

const FAULT_JA = {
  japan_trench:"日本海溝", nankai_trough:"南海トラフ", sagami_trough:"相模トラフ",
  ryukyu_trench:"琉球海溝", median_tectonic_line:"中央構造線",
  itoigawa_shizuoka:"糸魚川–静岡構造線", noto_peninsula:"能登半島断層帯",
  intraplate_generic:"プレート内（地殻内）", deep_slab:"深発スラブ内",
}

export const prefName    = (lang, id, fallback) => (lang === "ja" && PREF_JA[id])    || fallback || id
export const nuclearName = (lang, id, fallback) => (lang === "ja" && NUCLEAR_JA[id]) || fallback || id
export const faultName   = (lang, id, fallback) => (lang === "ja" && FAULT_JA[id])   || fallback || id

// ── Context ──────────────────────────────────────────────────────
const I18nContext = createContext(null)

function detectLang() {
  try {
    const saved = localStorage.getItem(STORE)
    if (saved === "en" || saved === "ja") return saved
  } catch {
    /* private mode — fall through to the browser preference */
  }
  return typeof navigator !== "undefined" && navigator.language?.startsWith("ja") ? "ja" : "en"
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(detectLang)

  const setLang = next => {
    try { localStorage.setItem(STORE, next) } catch { /* ignore */ }
    setLangState(next)
  }

  useEffect(() => { document.documentElement.lang = lang }, [lang])

  const value = useMemo(() => {
    const locale = lang === "ja" ? "ja-JP" : "en-US"
    const t = (key, vars) => {
      const raw = DICT[lang]?.[key] ?? EN[key] ?? key
      return vars
        ? raw.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m))
        : raw
    }
    return {
      lang,
      setLang,
      locale,
      t,
      num: n => (n == null ? "—" : Number(n).toLocaleString(locale)),
      pref:    (id, fallback) => prefName(lang, id, fallback),
      nuclear: (id, fallback) => nuclearName(lang, id, fallback),
      fault:   (id, fallback) => faultName(lang, id, fallback),
    }
  }, [lang])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>")
  return ctx
}

// ── Toggle ───────────────────────────────────────────────────────
export function LanguageToggle({ compact = false }) {
  const { lang, setLang, t } = useI18n()
  return (
    <div role="group" aria-label={t("nav.language")}
      style={{display:"inline-flex",gap:2,border:"1px solid #bdd6ea",borderRadius:6,
        padding:2,background:"#f7fbff"}}>
      {LANGS.map(l => (
        <button key={l.id} type="button" onClick={() => setLang(l.id)}
          aria-pressed={lang === l.id}
          style={{
            padding: compact ? "3px 7px" : "4px 10px",
            fontSize: compact ? 10 : 11,
            letterSpacing: "0.06em", fontWeight: 700, borderRadius: 4,
            cursor: "pointer", fontFamily: MONO,
            background: lang === l.id ? "#cfe0f0" : "transparent",
            border: `1px solid ${lang === l.id ? "#8fb6d8" : "transparent"}`,
            color: lang === l.id ? "#0369a1" : "#7398ac",
          }}>
          {l.label}
        </button>
      ))}
    </div>
  )
}
