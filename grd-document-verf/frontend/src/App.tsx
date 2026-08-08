import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import './Logo.css'
import './CaseDetails.css'
import BaseDashboard from './BaseDashboard'

type Session = { access_token:string; display_name:string; email:string; role:string; permissions:string[] }
type CaseDocument = {id:string;filename:string;document_type:string;detected_file_type:string;size_bytes:number;page_count:number;password_protected:boolean;status:string;malware_scan_status:string;observations:string[];updated_at:string}
type CaseItem = { id:string; name:string; reference:string|null; status:string; documents:CaseDocument[]; updated_at:string }
const roles = [
  ['organisation_admin','Organisation Admin'],['verification_executive','Verification Executive'],
  ['fraud_analyst','Fraud Analyst'],['reviewer','Reviewer'],['senior_approver','Senior Approver'],
  ['auditor','Auditor'],['api_client','API Client'],['system_admin','System Admin']
]
const moreItems = [
  ['documents','Document Verification','Upload and validate financial documents'],['cases','Cases & Workflow','Manage multi-document verification cases'],
  ['reviews','Review Queue','Approve or reject findings'],['roles','Users & Permissions','Organisation roles and access'],
  ['audit','Audit History','Read-only activity and status history'],['settings','System Settings','Organisation and infrastructure settings']
]
const availablePages = new Set(['dashboard', ...moreItems.map(([id])=>id)])

function initialPage(){
  const requested = new URLSearchParams(window.location.search).get('page') || 'dashboard'
  return availablePages.has(requested) ? requested : 'dashboard'
}

function formatBytes(value:number){return value<1024?`${value} B`:value<1024*1024?`${(value/1024).toFixed(1)} KB`:`${(value/(1024*1024)).toFixed(1)} MB`}
function readable(value:string){return value.replaceAll('_',' ').toLowerCase().replace(/\b\w/g,letter=>letter.toUpperCase())}

function App(){
  const [session,setSession]=useState<Session|null>(()=>{try{return JSON.parse(localStorage.getItem('grd_session')||'null')}catch{return null}})
  const [page,setPage]=useState(initialPage)
  if(!session) return <Login onLogin={value=>{localStorage.setItem('grd_session',JSON.stringify(value));setSession(value)}} />
  return <Dashboard session={session} page={page} setPage={setPage} logout={()=>{localStorage.removeItem('grd_session');setSession(null)}} />
}

function Login({onLogin}:{onLogin:(session:Session)=>void}){
  const [role,setRole]=useState('verification_executive'),[email,setEmail]=useState('abacusnikitaars@gmail.com')
  const [password,setPassword]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(false)
  async function submit(e:FormEvent){e.preventDefault();setLoading(true);setError('');try{
    const r=await fetch('/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password,requested_role:role,business_type:'Bank'})})
    if(!r.ok){const x=await r.json();throw new Error(x.detail||'Sign in failed')} onLogin(await r.json())
  }catch(e){setError(e instanceof Error?e.message:'Sign in failed')}finally{setLoading(false)}}
  return <main className="login-page"><div className="login-shell">
    <section className="login-brand"><img className="reference-logo" src="/Artboard.png" alt="GRD — Getting Recruitments Done" /></section>
    <form className="login-form" onSubmit={submit}><div><p className="kicker">WELCOME BACK</p><h2>Login to GRD Verify</h2><p className="muted">Your verification command centre</p></div>
      <label>CHOOSE ACCESS<select value={role} onChange={e=>setRole(e.target.value)}>{roles.map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
      <label>BUSINESS TYPE<select><option>Bank</option><option>NBFC</option><option>Verification Agency</option></select></label>
      <label>EMAIL ADDRESS<input value={email} onChange={e=>setEmail(e.target.value)} type="email" required/></label>
      <label>PASSWORD<input value={password} onChange={e=>setPassword(e.target.value)} type="password" required placeholder="Enter your password"/></label>
      {error&&<p className="form-error">{error}</p>}<button disabled={loading}>{loading?'Signing in…':'Sign In'} <span>→</span></button>
      <p className="login-help">Local demo: use the account matching the selected access.</p>
    </form></div></main>
}

function Dashboard({session,page,setPage,logout}:{session:Session;page:string;setPage:(v:string)=>void;logout:()=>void}){
 const [more,setMore]=useState(false)
 return <div className="app-shell"><header className="nav"><button className="logo" onClick={()=>setPage('dashboard')}><img src="/grd-header-logo.png" alt="GRD" /></button><nav>
  <button onClick={()=>setPage('dashboard')} className={page==='dashboard'?'active':''}>◫ Dashboard</button>
  <div className="more-wrap"><button className={page!=='dashboard'?'active':''} onClick={()=>setMore(!more)} aria-expanded={more}>☷ More⌄</button>{more&&<div className="more-menu">{moreItems.map(([id,label,desc])=><button className={page===id?'active':''} key={id} onClick={()=>{setPage(id);setMore(false)}}><b>{label}</b><small>{desc}</small></button>)}</div>}</div>
 </nav><div className="profile"><span className="role-pill">{session.role.replaceAll('_',' ')}</span><button onClick={logout}>{session.display_name} ⌄</button></div></header>
 <div className="subbar"><span>Good afternoon, <b>{session.display_name}</b> — here is your document verification command centre.</span><span>{new Date().toLocaleDateString('en-IN',{weekday:'short',day:'2-digit',month:'short',year:'numeric'})}</span></div>
 {page==='dashboard'?<Overview setPage={setPage} displayName={session.display_name}/>:<Module page={page} session={session}/>}</div>
}

function Overview({setPage,displayName}:{setPage:(v:string)=>void;displayName:string}){const stats=[['Documents today','0','Awaiting submissions','blue'],['Cases processing','0','Pipeline clear','cyan'],['Needs review','0','Analyst attention','orange'],['High risk','0','Priority follow-up','red'],['Verified','0','Completed today','green'],['Failed','0','Retry required','grey']]
 return <main className="dashboard"><BaseDashboard displayName={displayName}/><section className="verification-centre">
 <section className="welcome"><div><p className="kicker">DOCUMENT VERIFICATION</p><h1>Verification command centre</h1><p>Monitor cases, document processing and review decisions across your organisation.</p></div><button onClick={()=>setPage('documents')}>＋ Submit Document</button></section>
 <section className="attention"><h3>Verification Attention</h3><div className="stats">{stats.map(([a,b,c,d])=><article key={a}><i className={d}>◇</i><div><small>{a}</small><strong>{b}</strong><span>{c}</span></div></article>)}</div></section>
 <div className="dashboard-grid"><section className="panel"><div className="panel-title"><h3>Processing pipeline</h3><button onClick={()=>setPage('cases')}>View cases →</button></div><div className="pipeline">{['UPLOADED','VALIDATING','PROCESSING','NEEDS REVIEW','VERIFIED'].map((x,i)=><div key={x}><span>{i+1}</span><b>{x}</b><strong>0</strong></div>)}</div></section>
 <section className="panel"><div className="panel-title"><h3>Risk distribution</h3></div><div className="empty"><div>✓</div><b>No active risk signals</b><span>New verification results will appear here.</span></div></section></div>
 <section className="panel"><div className="panel-title"><h3>Recent cases</h3><button onClick={()=>setPage('cases')}>Open case manager →</button></div><div className="table-head"><span>CASE</span><span>DOCUMENTS</span><span>STATUS</span><span>RISK</span><span>UPDATED</span></div><div className="table-empty">No cases submitted in this session.</div></section></section></main>}

function Module({page,session}:{page:string;session:Session}){if(page==='documents')return <DocumentUpload session={session}/>;if(page==='cases')return <Cases session={session}/>;
 const item=moreItems.find(x=>x[0]===page);const permissionMap:Record<string,string>={reviews:'finding:review',audit:'audit:view',roles:'organisation:manage',settings:'infrastructure:manage'};const allowed=!permissionMap[page]||session.permissions.includes(permissionMap[page]);
 return <main className="module"><p className="kicker">MORE / {item?.[1].toUpperCase()}</p><h1>{item?.[1]}</h1><p className="muted">{item?.[2]}</p><section className="panel module-panel">{allowed?<div className="empty"><div>◎</div><b>{page==='reviews'?'No cases currently require review':'Module ready for organisation data'}</b><span>This view is tenant-scoped and respects your {session.role.replaceAll('_',' ')} permissions.</span></div>:<div className="denied"><b>Access restricted</b><p>Your role does not have permission to open this module.</p></div>}</section></main>}

function DocumentUpload({session}:{session:Session}){const [file,setFile]=useState<File|null>(null),[type,setType]=useState('bank_statement'),[message,setMessage]=useState('');async function submit(e:FormEvent){e.preventDefault();if(!file)return;const b=new FormData();b.append('file',file);b.append('document_type',type);try{const r=await fetch('/api/v1/documents',{method:'POST',headers:{Authorization:`Bearer ${session.access_token}`},body:b});const payload=await r.json().catch(()=>null);if(r.ok){setMessage('Document submitted and case created. Open Cases & Workflow to view observations.');return}const detail=payload?.detail;setMessage(r.status===401?'Your session expired. Please sign out and log in again.':typeof detail==='string'?detail:detail?.message||`Submission failed (${r.status}).`)}catch{setMessage('Cannot reach the verification API. Confirm FastAPI is running on port 8003.')}}
return <main className="module"><p className="kicker">MORE / DOCUMENT VERIFICATION</p><h1>Submit a document</h1><p className="muted">Start verification for the Phase 1 financial document categories.</p><form className="panel upload-module" onSubmit={submit}><label>DOCUMENT TYPE<select value={type} onChange={e=>setType(e.target.value)}><option value="bank_statement">Bank statement</option><option value="salary_slip">Salary slip</option><option value="vendor_invoice">Vendor invoice / expense bill</option></select></label><label className="upload-box"><input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={e=>setFile(e.target.files?.[0]||null)}/><span>⇧</span><b>{file?.name||'Choose PDF or image'}</b><small>PDF, PNG or JPEG</small></label>{message&&<p>{message}</p>}<button>Start verification →</button></form></main>}

function Cases({session}:{session:Session}){
 const [cases,setCases]=useState<CaseItem[]>([]),[name,setName]=useState(''),[openCase,setOpenCase]=useState<string|null>(null)
 const [retrying,setRetrying]=useState<string|null>(null),[actionMessage,setActionMessage]=useState<{text:string;error:boolean}|null>(null)
 const auth={Authorization:`Bearer ${session.access_token}`}
 async function load(){const r=await fetch('/api/v1/cases',{headers:auth});if(r.ok)setCases(await r.json())}
 useEffect(()=>{load();const timer=window.setInterval(load,3000);return()=>window.clearInterval(timer)},[])
 async function create(e:FormEvent){e.preventDefault();const r=await fetch('/api/v1/cases',{method:'POST',headers:{...auth,'Content-Type':'application/json'},body:JSON.stringify({name})});if(r.ok){setName('');load()}}
 async function retry(document:CaseDocument){
  setRetrying(document.id);setActionMessage(null)
  try{
   const r=await fetch(`/api/v1/documents/${document.id}/retry`,{method:'POST',headers:auth})
   const payload=await r.json().catch(()=>null)
   if(!r.ok){
    const detail=typeof payload?.detail==='string'?payload.detail:'Retry request failed.'
    const retryAfter=r.headers.get('Retry-After')
    setActionMessage({text:retryAfter?`${detail} Try again in ${retryAfter} seconds.`:detail,error:true})
    return
   }
   setActionMessage({text:`${document.filename} was queued for processing again.`,error:false})
   await load()
  }catch{
   setActionMessage({text:'Cannot reach the verification API. Retry was not submitted.',error:true})
  }finally{setRetrying(null)}
 }
 return <main className="module"><p className="kicker">MORE / CASES & WORKFLOW</p><h1>Verification cases</h1><p className="muted">Select a case to review its documents and processing observations.</p><form className="create-case panel" onSubmit={create}><input value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. Loan Application Case" required/><button>＋ Create case</button></form>{actionMessage&&<p className={`retry-feedback ${actionMessage.error?'error':'success'}`}>{actionMessage.text}</p>}<section className="panel cases-list">{cases.length?cases.map(c=><div className="case-entry" key={c.id}><button className={`case-row ${openCase===c.id?'open':''}`} onClick={()=>setOpenCase(openCase===c.id?null:c.id)}><div><b>{c.name}</b><small>{c.id}</small></div><span>{c.documents.length} document{c.documents.length===1?'':'s'}</span><em>{c.status}</em><time>{new Date(c.updated_at).toLocaleString()}</time></button>{openCase===c.id&&<div className="case-documents">{c.documents.length?c.documents.map(document=>{const canRetry=document.status==='FAILED'&&document.malware_scan_status!=='INFECTED'&&session.permissions.includes('case:submit');return <article className="case-document" key={document.id}><header><div><b>{document.filename}</b><small>{readable(document.document_type)} · Updated {new Date(document.updated_at).toLocaleString()}</small></div><div className="case-document-actions"><span className={`document-status ${document.status.toLowerCase()}`}>{readable(document.status)}</span>{canRetry&&<button type="button" className="retry-processing" disabled={retrying===document.id} onClick={()=>retry(document)}>{retrying===document.id?'Retrying...':'Retry processing'}</button>}</div></header><div className="document-facts"><span>Detected: {document.detected_file_type.toUpperCase()}</span><span>{formatBytes(document.size_bytes)}</span><span>{document.page_count} page{document.page_count===1?'':'s'}</span><span>Malware: {readable(document.malware_scan_status)}</span><span>{document.password_protected?'Password protected':'No password protection'}</span></div><ul className="document-observations">{document.observations.map((observation,index)=><li key={`${document.id}-${index}`}>{observation}</li>)}</ul></article>}):<div className="case-no-documents">No documents or observations are available for this case.</div>}</div>}</div>):<div className="empty"><div>▱</div><b>No cases yet</b><span>Create your first multi-document case above.</span></div>}</section></main>
}
export default App
