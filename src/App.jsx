import { useEffect, useMemo, useState } from 'react'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { t } from './strings.js'

const BASE = import.meta.env.BASE_URL
const OWNER_COLOR = { 'ИИМК РАН': '#4e79a7', 'НовГУ': '#59a14f' }
const PLACEHOLDER = 'data:image/svg+xml;utf8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120"><rect width="120" height="120" fill="#f0efe7"/><text x="60" y="64" font-size="11" fill="#9a9a88" text-anchor="middle">нет фото</text></svg>')

function imgSrc(it) { return it.external ? it.img : BASE + it.img }

export default function App() {
  const [data, setData] = useState(null)
  const [graph, setGraph] = useState(null)
  const [lang, setLang] = useState('ru')
  const [tab, setTab] = useState('search')
  const [model, setModel] = useState('resnet')
  const [threshold, setThreshold] = useState(0.65)
  const [provider, setProvider] = useState('all')
  const [query, setQuery] = useState(null)
  const [presetOpen, setPresetOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [favs, setFavs] = useState(() => new Set())

  const L = t(lang)

  useEffect(() => {
    Promise.all([
      fetch(`${BASE}data/catalog.json`).then(r => r.json()),
      fetch(`${BASE}data/similarity_graph.json`).then(r => r.json()),
    ]).then(([c, g]) => { setData(c); setGraph(g); setQuery(c._meta.presets[0]) })
  }, [])

  const byId = useMemo(() => data ? Object.fromEntries(data.items.map(i => [i.id, i])) : {}, [data])

  const results = useMemo(() => {
    if (!data || !graph || !query) return []
    const nb = (graph[model] && graph[model][query]) || []
    return nb
      .map(n => ({ ...byId[n.id], score: n.score }))
      .filter(x => x.id && x.score >= threshold && (provider === 'all' || x.owner === provider))
  }, [data, graph, query, model, threshold, provider, byId])

  if (!data || !graph || !query) return <div className="wrap"><p>{t('ru').loading}</p></div>

  const q = byId[query]
  const owners = data._meta.owners
  const toggleFav = (id) => setFavs(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  return (
    <div className="app">
      <header className="top">
        <div className="brand">◎ {L.brand}</div>
        <div className="demo-badge">{L.demoBadge.replace('{n}', data._meta.n)}</div>
        <div className="top-right">
          <button className={'tabbtn' + (tab === 'search' ? ' active' : '')} onClick={() => setTab('search')}>{L.tabSearch}</button>
          <button className={'tabbtn' + (tab === 'dash' ? ' active' : '')} onClick={() => setTab('dash')}>{L.tabDash}</button>
          <button className="langbtn" onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}>{L.langBtn}</button>
        </div>
      </header>

      <div className="wrap">
        {tab === 'search' ? (
          <div className="search-layout">
            {/* ── params ── */}
            <aside className="panel">
              <h3>{L.queryTitle}</h3>
              <div className="query-box">
                <img src={imgSrc(q)} onError={e => { e.target.src = PLACEHOLDER }} alt="" />
                <div className="query-pick"><button className="btn ghost" onClick={() => setPresetOpen(true)}>{L.pickPreset}</button></div>
              </div>
              <h3>{L.searchParams}</h3>
              <div className="control">
                <label>{L.model}</label>
                <div className="toggle-row">
                  <button className={model === 'resnet' ? 'on' : ''} onClick={() => setModel('resnet')}>ResNet50</button>
                  <button className={model === 'clip' ? 'on' : ''} onClick={() => setModel('clip')}>CLIP</button>
                </div>
              </div>
              <div className="control">
                <label>{L.threshold}<b>{threshold.toFixed(2)}</b></label>
                <input type="range" min="0.65" max="1" step="0.01" value={threshold} onChange={e => setThreshold(+e.target.value)} />
              </div>
              <div className="control">
                <label>{L.provider}</label>
                <select value={provider} onChange={e => setProvider(e.target.value)}>
                  <option value="all">{L.allProviders}</option>
                  {owners.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="control disabled">
                <label title={L.prodOnly}>{L.preproc} <span className="pill-prod">Prod</span></label>
              </div>
              <div className="control disabled">
                <label title={L.prodOnly}>{L.tags} <span className="pill-prod">Prod</span></label>
                <div className="selbox" style={{ color: 'var(--muted)', cursor: 'not-allowed' }}>сосуд, керамика, -фаянс</div>
              </div>
              <div className="control disabled">
                <label title={L.prodOnly}>{L.domain} <span className="pill-prod">Prod</span></label>
              </div>
            </aside>

            {/* ── results ── */}
            <main>
              <div className="found-line">{L.found} <b>{results.length}</b></div>
              {results.length === 0 ? (
                <div className="empty"><b>{L.emptyTitle}</b>{L.emptyHint}</div>
              ) : (
                <div className="grid">
                  {results.map(it => (
                    <div className="card" key={it.id} onClick={() => setDetail(it)}>
                      <div className="ch"><span>{it.owner}</span><span className="score">{it.score.toFixed(2)}</span></div>
                      <div className="cimg"><img src={imgSrc(it)} onError={e => { e.target.src = PLACEHOLDER }} alt="" /></div>
                      <div className="cb">
                        <div className="code">{it.code}</div>
                        <div className="nm">{it.name}</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--muted)' }}>
                          <span>{it.material}</span>
                          <span className="star" onClick={e => { e.stopPropagation(); toggleFav(it.id) }}>{favs.has(it.id) ? '★' : '☆'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </main>

            {/* ── favorites + map ── */}
            <aside className="panel">
              <h3>{L.favorites}</h3>
              {favs.size === 0 ? <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>{L.favEmpty}</div> : (
                <div style={{ marginBottom: 14 }}>
                  {[...favs].map(id => byId[id]).filter(Boolean).map(it => (
                    <div className="fav-item" key={it.id}>
                      <img src={imgSrc(it)} onError={e => { e.target.src = PLACEHOLDER }} alt="" />
                      <div><div style={{ fontWeight: 600 }}>{it.name}</div><div style={{ color: 'var(--muted)' }}>{it.code}</div></div>
                    </div>
                  ))}
                </div>
              )}
              <h3>{L.map}</h3>
              <SiteMap items={data.items} active={new Set(results.map(r => r.site))} />
            </aside>
          </div>
        ) : (
          <Dashboard data={data} L={L} />
        )}

        <p className="foot">{L.honesty}</p>
      </div>

      {presetOpen && (
        <div className="overlay" onClick={() => setPresetOpen(false)}>
          <div className="modal" style={{ maxWidth: 640 }} onClick={e => e.stopPropagation()}>
            <div className="mh"><h3>{L.presetModalTitle}</h3><button className="xbtn" onClick={() => setPresetOpen(false)}>✕</button></div>
            <div style={{ padding: 18 }}>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginTop: 0 }}>{L.presetModalHint}</p>
              <div className="grid">
                {data._meta.presets.map(pid => byId[pid]).filter(Boolean).map(it => (
                  <div className="card" key={it.id} onClick={() => { setQuery(it.id); setPresetOpen(false) }}>
                    <div className="cimg"><img src={imgSrc(it)} onError={e => { e.target.src = PLACEHOLDER }} alt="" /></div>
                    <div className="cb"><div className="nm">{it.name}</div><div className="code">{it.material}</div></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {detail && <DetailModal it={detail} L={L} onClose={() => setDetail(null)} />}
    </div>
  )
}

function DetailModal({ it, L, onClose }) {
  const row = (label, val) => val ? <div className="mfield"><b>{label}:</b> {val}</div> : null
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="mh"><h3>{L.modalTitle}</h3><button className="xbtn" onClick={onClose}>✕</button></div>
        <div className="mb">
          <div className="mimg"><img src={imgSrc(it)} onError={e => { e.target.src = PLACEHOLDER }} alt="" /></div>
          <div>
            {row(L.fCode, it.code)}
            {row(L.fName, it.name)}
            {row(L.fMaterial, it.material)}
            {row(L.fDesc, it.description)}
            {row(L.fSize, it.size)}
            {row(L.fDating, it.dating)}
            {row(L.fSquare, it.square)}
            {row(L.fObject, it.object)}
            {row(L.fExc, it.excname)}
            {row(L.fSite, it.site)}
            <div className="mfield"><b>{L.fOwner}:</b> <span className="owner-link">{it.owner}</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Статичная SVG-карта СЗ России (offline-first). lon 29.5..32.0 → x, lat 57.4..60.2 → y.
function SiteMap({ items, active }) {
  const W = 260, H = 220
  const x = lon => ((lon - 29.5) / (32.0 - 29.5)) * (W - 40) + 20
  const y = lat => (1 - (lat - 57.4) / (60.2 - 57.4)) * (H - 40) + 20
  const sites = {}
  for (const it of items) if (!sites[it.site]) sites[it.site] = { lon: it.lon, lat: it.lat, owner: it.owner }
  return (
    <div className="map-wrap" style={{ height: H }}>
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
        <rect width={W} height={H} fill="#cfe0e6" />
        <path d="M20 40 Q90 20 150 55 T250 70 L250 200 Q160 190 90 200 T20 185 Z" fill="#e4e2d2" stroke="#c7c5b4" />
        <text x={W - 8} y={H - 8} fontSize="9" fill="#7a8a90" textAnchor="end">Северо-Запад РФ</text>
        {Object.entries(sites).map(([name, s]) => {
          const on = active.has(name)
          return (
            <g key={name} className="pin-g" transform={`translate(${x(s.lon)},${y(s.lat)})`}>
              <path d="M0 0 C-6 -10 -8 -14 0 -18 C8 -14 6 -10 0 0 Z" fill={on ? OWNER_COLOR[s.owner] : '#b6b6a6'} stroke="#fff" strokeWidth="1" />
              <circle cx="0" cy="-13" r="2.4" fill="#fff" />
              {on && <text x="6" y="-8" fontSize="8" fill="#2a2a24">{name.split(' (')[0]}</text>}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function Dashboard({ data, L }) {
  const items = data.items
  const typeCount = {}
  for (const it of items) typeCount[it.macro] = (typeCount[it.macro] || 0) + 1
  const typeData = Object.entries(typeCount).map(([name, value]) => ({ name, value }))
  const siteCount = {}
  for (const it of items) siteCount[it.site] = (siteCount[it.site] || 0) + 1
  const siteData = Object.entries(siteCount).map(([name, v]) => ({ name: name.split(' (')[0], v })).sort((a, b) => b.v - a.v)
  const PIE = ['#4e79a7', '#59a14f', '#e0a03a', '#af7aa1', '#9c755f']
  return (
    <div>
      <div className="dash-block">
        <h2 style={{ color: 'var(--accent)' }}>{L.dashProdTitle}</h2>
        <div className="kpis">
          <div className="kpi fact"><div className="kv">50 000+</div><div className="kl">{L.kArtifacts}</div></div>
          <div className="kpi fact"><div className="kv">8</div><div className="kl">{L.kSites}</div></div>
          <div className="kpi fact"><div className="kv">2</div><div className="kl">{L.kModels} (ResNet50, CLIP)</div></div>
          <div className="kpi fact"><div className="kv">&gt;90%</div><div className="kl">{L.kRecall}</div></div>
          <div className="kpi fact"><div className="kv">&lt;1 c</div><div className="kl">{L.kTTFR}</div></div>
          <div className="kpi fact"><div className="kv">&lt;5%</div><div className="kl">{L.kHITL}</div></div>
        </div>
      </div>
      <div className="dash-block">
        <h2 style={{ color: 'var(--muted)' }}>{L.dashDemoTitle}</h2>
        <div className="kpis" style={{ gridTemplateColumns: 'repeat(3,1fr)', maxWidth: 560, marginBottom: 16 }}>
          <div className="kpi demo"><div className="kv">{items.length}</div><div className="kl">{L.kDemoItems}</div></div>
          <div className="kpi demo"><div className="kv">{data._meta.sites.length}</div><div className="kl">{L.kDemoSites}</div></div>
          <div className="kpi demo"><div className="kv">{data._meta.owners.length}</div><div className="kl">{L.kDemoOwners}</div></div>
        </div>
        <div className="charts">
          <div className="panel">
            <h3>{L.chartTypes}</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {typeData.map((e, i) => <Cell key={i} fill={PIE[i % PIE.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h3>{L.chartSites}</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={siteData} margin={{ top: 6, right: 8, left: 8, bottom: 30 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#7a7a6c' }} angle={-20} textAnchor="end" interval={0} height={40} />
                <YAxis tick={{ fontSize: 11, fill: '#7a7a6c' }} width={30} />
                <Tooltip />
                <Bar dataKey="v" fill="#59a14f" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
