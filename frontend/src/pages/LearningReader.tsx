import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ArrowUpRight, Check } from 'lucide-react';
import { Modal } from '../components';
import { title } from '../api';

export function LearningReader({ reader, busy, complete, close }: any) {
  const item = reader.item;
  const questions = item.checks ?? (item.question ? [{ question: item.question, options: item.options }] : []);
  const [answers, setAnswers] = useState<(number | null)[]>(questions.map(() => null));
  const [remaining, setRemaining] = useState(30);
  useEffect(() => { const started = Date.now(); const timer = window.setInterval(() => setRemaining(Math.max(0, 30 - Math.floor((Date.now() - started) / 1000))), 500); return () => window.clearInterval(timer); }, []);
  return <Modal title={item.title} close={close}><article className="resource-reader">
    <span className="eyebrow">{title(item.kind || 'guide')} · {title(item.competency)} · {item.estimated_minutes || 5} MIN</span>
    <ReactMarkdown>{item.body || ''}</ReactMarkdown>
    {item.url && <a className="button secondary" href={item.url} target="_blank" rel="noopener noreferrer">Open learning resource<ArrowUpRight size={16} /></a>}
    {questions.map((q: any, n: number) => <div className="quick-check" key={n}><h3>Quick check {n + 1}</h3><p>{q.question}</p>{q.options.map((option: string, i: number) => <label className="check-label" key={i}><input type="radio" name={`quick-check-${n}`} checked={answers[n] === i} onChange={() => setAnswers(current => current.map((answer, index) => index === n ? i : answer))} />{option}</label>)}</div>)}
    <p className="form-note">{remaining ? `Take a moment with the resource. Completion is available in ${remaining} seconds.` : 'You can complete this waypoint after reviewing the resource.'}</p>
    <button className="button primary" disabled={busy || remaining > 0 || answers.some(a => a === null)} onClick={() => complete(answers)}>Complete waypoint<Check size={16} /></button>
  </article></Modal>;
}
