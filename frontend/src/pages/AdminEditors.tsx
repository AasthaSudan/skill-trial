import { useState } from 'react';
import { ArrowRight, Plus, Trash2 } from 'lucide-react';
import { Modal } from '../components';
import { title } from '../api';

const blankCheck = () => ({ question: '', options: ['', ''], answer: 0 });

export function ResourceForm({ resource, catalog, challenges, busy, save, close }: any) {
  const [draft, setDraft] = useState<any>(() => ({ kind: 'guide', difficulty: 'beginner', estimated_minutes: 5, url: '', body: '', ...resource,
    competencies: resource.competencies || [resource.competency || 'collections'],
    checks: resource.checks ?? (resource.question ? [{ question: resource.question, options: resource.options, answer: resource.answer }] : []) }));
  const update = (key: string, value: any) => setDraft((r: any) => ({ ...r, [key]: value }));
  const skill = catalog.find((s: any) => s.slug === draft.skill);
  const changeCheck = (n: number, key: string, value: any) => update('checks', draft.checks.map((q: any, i: number) => i === n ? { ...q, [key]: value } : q));
  return <Modal title={resource.editDraft ? 'Edit resource draft' : 'Learning resource revision'} close={close}>
    <form className="admin-resource-form" onSubmit={e => { e.preventDefault(); const { slug, skill, competencies, title, body, kind, url, difficulty, estimated_minutes, checks, challenge_id } = draft; save({ slug: slug || undefined, skill, competencies, title, body, kind, url: kind === 'practice_challenge' ? '' : url, difficulty, estimated_minutes, checks: kind === 'practice_challenge' ? [] : checks, challenge_id: kind === 'practice_challenge' ? challenge_id : undefined }, resource.editDraft ? resource.id : undefined); }}>
      <p>New revisions preserve existing learning paths. Validate, obtain an independent review, then publish.</p>
      <label>Resource slug<input value={draft.slug || ''} readOnly={resource.editDraft} pattern="[a-z0-9][a-z0-9-]{2,79}" onChange={e => update('slug', e.target.value)} placeholder="python-algorithms-guide" /></label>
      <div className="admin-two-fields"><label>Skill<select value={draft.skill} onChange={e => { const s = catalog.find((s: any) => s.slug === e.target.value); setDraft({ ...draft, skill: e.target.value, competencies: s?.competencies.slice(0, 1) || [], challenge_id: '' }); }}>{catalog.filter((s: any) => s.competencies.length).map((s: any) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</select></label><label>Kind<select value={draft.kind} onChange={e => update('kind', e.target.value)}>{['article', 'video', 'guide', 'interactive', 'practice_challenge'].map(k => <option key={k} value={k}>{title(k)}</option>)}</select></label></div>
      <fieldset><legend>Competencies</legend><div className="permission-list">{skill?.competencies.map((c: string) => <label key={c}><input type="checkbox" checked={draft.competencies.includes(c)} onChange={e => update('competencies', e.target.checked ? [...draft.competencies, c] : draft.competencies.filter((v: string) => v !== c))} />{title(c)}</label>)}</div></fieldset>
      <label>Title<input required minLength={5} maxLength={120} value={draft.title || ''} onChange={e => update('title', e.target.value)} /></label>
      <div className="admin-two-fields"><label>Difficulty<select value={draft.difficulty} onChange={e => update('difficulty', e.target.value)}>{['beginner', 'intermediate', 'advanced'].map(k => <option key={k}>{k}</option>)}</select></label><label>Estimated minutes<input required type="number" min={1} max={240} value={draft.estimated_minutes} onChange={e => update('estimated_minutes', Number(e.target.value))} /></label></div>
      {draft.kind === 'practice_challenge' ? <label>Published practice challenge<select required value={draft.challenge_id || ''} onChange={e => update('challenge_id', e.target.value)}><option value="">Choose a challenge</option>{challenges.filter((c: any) => c.pool === 'practice' && c.status === 'published' && c.skill === draft.skill).map((c: any) => <option key={c.id} value={c.id}>{c.title} · v{c.version}</option>)}</select></label> : <>
        <label>HTTPS resource URL (optional)<input type="url" maxLength={2000} value={draft.url} placeholder="https://…" onChange={e => update('url', e.target.value)} /></label>
        <label>Markdown content{draft.url ? ' or summary' : ''}<textarea required={!draft.url} minLength={draft.url ? undefined : 80} maxLength={8000} rows={7} value={draft.body} onChange={e => update('body', e.target.value)} /></label>
      </>}
      {draft.kind !== 'practice_challenge' && <><div className="section-heading"><div><h3>Optional quick check</h3><p>Use no questions, or two to five multiple-choice questions.</p></div><button type="button" className="button secondary small" disabled={draft.checks.length >= 5} onClick={() => update('checks', draft.checks.length ? [...draft.checks, blankCheck()] : [blankCheck(), blankCheck()])}><Plus size={14} />Add question</button></div>
        {draft.checks.map((q: any, n: number) => <fieldset key={n}><legend>Question {n + 1}</legend><label>Prompt<input required minLength={10} maxLength={240} value={q.question} onChange={e => changeCheck(n, 'question', e.target.value)} /></label><label>Choices, one per line<textarea required rows={4} value={q.options.join('\n')} onChange={e => changeCheck(n, 'options', e.target.value.split('\n'))} /></label><label>Correct choice<select value={q.answer} onChange={e => changeCheck(n, 'answer', Number(e.target.value))}>{q.options.map((option: string, i: number) => <option key={i} value={i}>{i + 1}. {option || 'Choice'}</option>)}</select></label><button type="button" className="button secondary small" onClick={() => update('checks', draft.checks.filter((_: any, i: number) => i !== n))}><Trash2 size={14} />Remove question</button></fieldset>)}</>}
      <button className="button primary" disabled={busy || !draft.competencies.length || (draft.kind !== 'practice_challenge' && draft.checks.length === 1)}>Save draft<ArrowRight size={16} /></button>
    </form>
  </Modal>;
}

export function BadgeForm({ badge, rules, busy, save, close }: any) {
  const [draft, setDraft] = useState<any>({ category: 'behavior', status: 'active', ...badge });
  const update = (key: string, value: any) => setDraft((r: any) => ({ ...r, [key]: value }));
  const rule = rules.find((r: any) => r.metric === draft.metric);
  const params = rule?.params.thresholds || { min_items: 1, max_items: 3, minimum: 1, maximum: 100000 };
  return <Modal title={badge.author ? 'Edit badge definition' : 'New badge definition'} close={close}><form onSubmit={e => { e.preventDefault(); const payload = { name: draft.name, description: draft.description, icon: draft.icon, category: draft.category, status: draft.status, metric: draft.metric, thresholds: String(draft.thresholds).split(',').map(x => Number(x.trim())), ...(badge.author ? { version: badge.version } : { slug: draft.slug }) }; save(payload, badge.author ? badge.slug : undefined); }}>
    <p>Changing the earning rule creates a new version. Previously earned tiers remain in the candidate’s collection.</p>
    <label>Slug<input required readOnly={!!badge.author} pattern="[a-z0-9][a-z0-9-]{2,59}" value={draft.slug} onChange={e => update('slug', e.target.value)} /></label>
    <label>Name<input required minLength={3} maxLength={80} value={draft.name} onChange={e => update('name', e.target.value)} /></label>
    <label>Description<input required minLength={8} maxLength={240} value={draft.description} onChange={e => update('description', e.target.value)} /></label>
    <div className="admin-two-fields"><label>Category<select value={draft.category} onChange={e => update('category', e.target.value)}>{['skill', 'behavior', 'milestone'].map(k => <option key={k}>{k}</option>)}</select></label><label>Status<select value={draft.status} onChange={e => update('status', e.target.value)}><option value="active">Active</option><option value="archived">Archived</option></select></label></div>
    <label>Icon<select value={draft.icon} onChange={e => update('icon', e.target.value)}>{['Award', 'Sparkles', 'Code2', 'ScanLine', 'ShieldCheck', 'Flame'].map(k => <option key={k}>{k}</option>)}</select></label>
    <label>Earning rule<select value={draft.metric} onChange={e => update('metric', e.target.value)}>{rules.map((r: any) => <option key={r.metric} value={r.metric}>{r.label}</option>)}</select></label>
    <label>Tier thresholds, separated by commas<input required pattern="[0-9]+(\s*,\s*[0-9]+){0,2}" value={draft.thresholds} onChange={e => update('thresholds', e.target.value)} /></label><p className="form-note">{params.min_items}–{params.max_items} increasing thresholds, from {params.minimum} to {params.maximum}.</p>
    {badge.author && <details><summary>Rule history · current v{badge.version}</summary>{(badge.history || []).map((v: any) => <p key={v.version}>v{v.version}: {title(v.metric)} · {v.thresholds.join(' / ')}</p>)}</details>}
    <button className="button primary" disabled={busy || !rules.length}>Save badge<ArrowRight size={16} /></button>
  </form></Modal>;
}
