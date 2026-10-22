import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, post, ApiError } from './api';

afterEach(()=>vi.unstubAllGlobals());
describe('same-origin API transport',()=>{
  it('attaches the CSRF token and preserves submission retry keys',async()=>{
    vi.stubGlobal('document',{cookie:'st_csrf=known-token'});
    const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({ok:true}),{status:200}));vi.stubGlobal('fetch',fetch);
    await post('/assessments/id/finish',{},'stable-retry-key');
    const [url,opts]=fetch.mock.calls[0];expect(url).toBe('/api/v1/assessments/id/finish');expect(opts.credentials).toBe('include');expect(opts.headers.get('X-CSRF-Token')).toBe('known-token');expect(opts.headers.get('Idempotency-Key')).toBe('stable-retry-key');
  });
  it('keeps infrastructure errors distinct from assessment scores',async()=>{
    vi.stubGlobal('document',{cookie:''});vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{code:'RUNNER_UNAVAILABLE',message:'Execution is unavailable.'}}),{status:503})));
    await expect(api('/run')).rejects.toMatchObject({code:'RUNNER_UNAVAILABLE',status:503,message:'Execution is unavailable.'});
  });
  it('does not replace browser-generated multipart boundaries',async()=>{
    vi.stubGlobal('document',{cookie:''});const fetch=vi.fn().mockResolvedValue(new Response('{}',{status:200}));vi.stubGlobal('fetch',fetch);await api('/resumes',{method:'POST',body:new FormData()});expect(fetch.mock.calls[0][1].headers.has('Content-Type')).toBe(false);
  });
});
