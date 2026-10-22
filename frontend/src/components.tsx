import { useContext, createContext, useState, useEffect, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, CircleDashed, CircleHelp, CircleX, Sparkles, ArrowUpRight, Check, AlertTriangle, LoaderCircle, Database, Coffee, Braces, Code2, Leaf, X, ArrowRight } from 'lucide-react';
import { title } from './api';

export const ToastContext = createContext<(message: string, error?: boolean) => void>(() => {});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);
  useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(null),8000);return()=>clearTimeout(t);},[toast]);
  return <ToastContext.Provider value={(message, error = false) => { setToast({ message, error }); }}>
    {children}{toast && <div className={'toast ' + (toast.error ? 'toast-error' : '')} role={toast.error ? 'alert' : 'status'}>{toast.error ? <AlertTriangle size={19} /> : <Check size={19} />}<span>{toast.message}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast(null)}><X size={16} /></button></div>}
  </ToastContext.Provider>;
}
export function useAction() {
  const notify = useContext(ToastContext); const [busy, setBusy] = useState(false);
  return { busy, notify, act: async <T,>(fn: () => Promise<T>, message?: string): Promise<T | undefined> => { setBusy(true); try { const value = await fn(); if (message) notify(message); return value; } catch (e) { notify(e instanceof Error ? e.message : 'Please try again.', true); return undefined; } finally { setBusy(false); } } };
}
export function Brand({ small = false }: { small?: boolean }) { return <Link to="/" className="brand" aria-label="SkillTrial home"><span className="brand-mark"><Sparkles size={small ? 18 : 22} strokeWidth={1.8} /></span><span>Skill<span className="brand-light">Trial</span><sup>✦</sup></span></Link>; }
export function Status({ status }: { status?: string }) {
  const map: Record<string, any> = { verified: [ShieldCheck, 'Verified'], partially_verified: [CircleDashed, 'Partially Verified'], not_verified: [CircleX, 'Not Verified'], insufficient_evidence: [CircleHelp, 'Insufficient Evidence'], practice: [Code2, 'Practice'] };
  const [Icon, label] = map[status || ''] || [CircleDashed, 'Not assessed'];
  return <span className={'status status-' + (status || 'unassessed')}><Icon size={14} />{label}</span>;
}
export function SkillIcon({ skill, size = 22 }: { skill: string; size?: number }) { const Icon = ({ sql: Database, java: Coffee, javascript: Braces, 'spring-boot': Leaf } as any)[skill] || Code2; return <span className={'skill-icon skill-' + skill}><Icon size={size} strokeWidth={1.6} /></span>; }
export function Difficulty({ level }: { level: string }) { return <span className="difficulty"><span>{[0, 1, 2].map(i => <i key={i} className={i <= ['beginner', 'intermediate', 'advanced'].indexOf(level) ? 'filled' : ''} />)}</span>{title(level)}</span>; }
export function PageTitle({ eyebrow, title: heading, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) { return <div className="page-title"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{heading}</h1>{description && <p>{description}</p>}</div>{action}</div>; }
export function Empty({ title: heading, text, to, cta = 'Get started' }: { title: string; text: string; to?: string; cta?: string }) { return <div className="empty"><span className="empty-orbit"><Sparkles size={30} /></span><h3>{heading}</h3><p>{text}</p>{to && <Link className="button primary" to={to}>{cta}<ArrowRight size={16} /></Link>}</div>; }
export function Loading() { return <div className="loading" role="status"><LoaderCircle className="spin" size={22} /><span>Getting your workspace ready…</span></div>; }
export function ErrorPanel({ error, retry }: { error: any; retry: () => void }) { return <div className="error-panel" role="alert"><AlertTriangle size={23} /><div><h3>We couldn’t load this.</h3><p>{error?.message || 'Please try again.'}</p><button className="button secondary" onClick={retry}>Try again</button></div></div>; }
export function Progress({ value, label }: { value: number; label?: string }) { return <div className="progress" role="progressbar" aria-label={label || 'Progress'} aria-valuenow={Math.min(100, Math.round(value * 100))} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }} /></div>; }
export function Stars({ competencies = [], compact = false }: { competencies?: any[]; compact?: boolean }) {
  const pts = [[40, 60], [155, 28], [242, 78], [130, 136], [285, 155], [45, 178], [235, 220]];
  const rows = competencies;
  return <svg className={'constellation ' + (compact ? 'compact' : '')} viewBox="0 0 340 265" role="img" aria-label={rows.map((c: any) => title(c.name) + ': ' + title(c.status)).join(', ')}>
    <defs><radialGradient id="starGlow"><stop stopColor="#aa92ff" stopOpacity=".25" /><stop offset="1" stopColor="#aa92ff" stopOpacity="0" /></radialGradient></defs>
    {rows.slice(1, 7).map((_: any, i: number) => <line key={i} x1={pts[i][0]} y1={pts[i][1]} x2={pts[i + 1][0]} y2={pts[i + 1][1]} stroke="currentColor" strokeOpacity=".18" strokeWidth="1" />)}
    {rows.slice(0, 7).map((c: any, i: number) => <g key={c.name} transform={`translate(${pts[i][0]},${pts[i][1]})`}><title>{title(c.name) + ': ' + title(c.status)}</title>{c.status === 'demonstrated' && <circle r="28" fill="url(#starGlow)" />}<circle r={c.status === 'demonstrated' ? 5 : 4} fill={c.status === 'demonstrated' ? '#cdbfff' : 'var(--surface)'} stroke={c.status === 'not_assessed' ? 'var(--muted)' : '#a18ae4'} strokeDasharray={c.status === 'not_assessed' ? '2 2' : undefined} /><text x="0" y="21" textAnchor="middle" fill="currentColor" fontSize="10">{title(c.name)}</text></g>)}
  </svg>;
}
export function SectionLink({ to, children }: { to: string; children: ReactNode }) { return <Link className="text-link" to={to}>{children}<ArrowUpRight size={15} /></Link>; }
export function Modal({ title: heading, children, close }: { title: string; children: ReactNode; close: () => void }) {
  const ref=useRef<HTMLElement>(null);
  useEffect(()=>{const previous=document.activeElement as HTMLElement;ref.current?.querySelector<HTMLElement>('button,input,select,textarea,a[href]')?.focus();return ()=>previous?.focus();},[]);
  return <div className="modal-backdrop" onClick={close}><section ref={ref} className="modal" role="dialog" aria-modal="true" aria-label={heading} onClick={e => e.stopPropagation()} onKeyDown={e => {if(e.key==='Escape')close();if(e.key==='Tab'){const all=Array.from(ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]')||[]);const first=all[0],last=all[all.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}}}><div className="section-heading"><h2>{heading}</h2><button aria-label="Close dialog" className="icon-button" onClick={close}><X size={20} /></button></div>{children}</section></div>;
}
