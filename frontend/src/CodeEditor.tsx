import Editor, { loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor/editor/editor.api.js';
import EditorWorker from 'monaco-editor/editor/editor.worker.js?worker';
import 'monaco-editor/languages/definitions/python/register.js';
import 'monaco-editor/languages/definitions/java/register.js';
import 'monaco-editor/languages/definitions/javascript/register.js';
import 'monaco-editor/languages/definitions/sql/register.js';
(self as any).MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });
monaco.editor.defineTheme('skilltrial-aurora',{base:'vs-dark',inherit:true,rules:[{token:'keyword',foreground:'b69cff'},{token:'string',foreground:'9ed8c4'}],colors:{'editor.background':'#101a2b','editorLineNumber.foreground':'#6f829e','editorCursor.foreground':'#8bd6c2'}});
monaco.editor.defineTheme('skilltrial-solar',{base:'vs',inherit:true,rules:[{token:'keyword',foreground:'7043c0'},{token:'string',foreground:'176b53'}],colors:{'editor.background':'#fff9ea','editorLineNumber.foreground':'#827966','editorCursor.foreground':'#b04e25'}});
export default function CodeEditor({ value, language, onChange, readOnly = false, editorTheme = 'midnight' }: { value: string; language: string; onChange: (s: string) => void; readOnly?: boolean; editorTheme?: string }) {
  const theme=editorTheme==='aurora'?'skilltrial-aurora':editorTheme==='solar'?'skilltrial-solar':'vs-dark';
  return <Editor height="390px" language={language} theme={theme} value={value} onChange={v => onChange(v || '')} options={{ readOnly, editContext: false, minimap: { enabled: false }, fontSize: 14, fontFamily: 'Consolas, monospace', fontLigatures: false, padding: { top: 20, bottom: 20 }, scrollBeyondLastLine: false, wordWrap: 'on', automaticLayout: true, tabSize: 4, accessibilitySupport: 'auto', ariaLabel: 'Challenge code editor' }} loading={<div className="loading">Loading code editor…</div>} />;
}
