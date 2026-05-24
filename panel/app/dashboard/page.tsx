'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiFetch, clearToken, getToken } from '@/lib/api';

type Device = {
  id: string;
  name: string;
  platform: string;
  last_seen: string | null;
  revoked_at: string | null;
};

export default function Dashboard() {
  const router = useRouter();
  const [items, setItems] = useState<Device[]>([]);
  const [msg, setMsg] = useState('');
  const [googleText, setGoogleText] = useState('buscar e-mails não lidos');
  const [googleConfirm, setGoogleConfirm] = useState(false);
  const [googleThreadId, setGoogleThreadId] = useState<string | null>(null);
  const [googleStatus, setGoogleStatus] = useState('');
  const [googleSummary, setGoogleSummary] = useState('');
  const [googleService, setGoogleService] = useState('');
  const [googleAction, setGoogleAction] = useState('');
  const [googleRaw, setGoogleRaw] = useState('');
  const [googleData, setGoogleData] = useState<unknown>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace('/');
      return;
    }
    (async () => {
      const res = await apiFetch('/devices?limit=50&offset=0');
      if (!res.ok) {
        setMsg(await res.text());
        return;
      }
      const data = await res.json();
      setItems(data.items);
    })();
  }, [router]);

  async function runGoogle(confirmOverride = googleConfirm) {
    setGoogleStatus('Executando no Hermes...');
    setMsg('');
    const res = await apiFetch('/brain/google', {
      method: 'POST',
      body: JSON.stringify({
        text: googleText,
        confirm: confirmOverride,
        thread_id: googleThreadId,
      }),
    });
    if (!res.ok) {
      setGoogleStatus('Falha ao executar');
      setMsg(await res.text());
      return;
    }
    const data = await res.json();
    setGoogleThreadId(data.thread_id ?? null);
    setGoogleService(data.service ?? '');
    setGoogleAction(data.action ?? '');
    setGoogleSummary(data.summary ?? data.message ?? '');
    setGoogleRaw(data.raw_output ?? '');
    setGoogleData(data.data ?? null);
    setGoogleConfirm(Boolean(data.requires_confirmation));
    setGoogleStatus(data.status === 'needs_confirmation' ? 'Confirmação necessária' : 'Concluído');
  }

  return (
    <main style={{ maxWidth: 720, margin: '24px auto', padding: 16 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link href="/pairing">Pairing</Link>
        <Link href="/audit">Audit</Link>
        <button type="button" onClick={() => { clearToken(); window.location.href = '/'; }}>
          Logout
        </button>
      </nav>
      <h1>Devices</h1>
      <section style={{ border: '1px solid #ddd', borderRadius: 16, padding: 16, marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>Google Workspace</h2>
        <p style={{ color: '#666' }}>
          Fale com o Hermes para Gmail, Calendar, Drive, Docs e Sheets. O mesmo thread fica salvo para ele aprender com o uso.
        </p>
        <label style={{ display: 'block', marginBottom: 8 }}>
          Comando natural
          <textarea
            value={googleText}
            onChange={(e) => setGoogleText(e.target.value)}
            rows={4}
            style={{ width: '100%', display: 'block', marginTop: 4 }}
          />
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <button type="button" onClick={() => runGoogle(false)}>
            Executar
          </button>
          {googleConfirm && (
            <button type="button" onClick={() => runGoogle(true)}>
              Confirmar e executar
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setGoogleThreadId(null);
              setGoogleStatus('');
              setGoogleSummary('');
              setGoogleService('');
              setGoogleAction('');
              setGoogleRaw('');
              setGoogleData(null);
              setGoogleConfirm(false);
            }}
          >
            Nova thread
          </button>
        </div>
        <div style={{ color: '#555', fontSize: 14 }}>
          <div>Status: {googleStatus || 'pronto'}</div>
          <div>Thread: {googleThreadId ?? 'nova conversa'}</div>
          {(googleService || googleAction) && (
            <div>
              Ação: <code>{googleService}.{googleAction}</code>
            </div>
          )}
        </div>
        {googleSummary && <p style={{ marginBottom: 0 }}><strong>Resumo:</strong> {googleSummary}</p>}
        {googleData != null && (
          <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 12, marginTop: 12 }}>
            {JSON.stringify(googleData, null, 2)}
          </pre>
        )}
        {googleRaw && (
          <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 12, marginTop: 12 }}>
            {googleRaw}
          </pre>
        )}
      </section>
      {msg && <pre>{msg}</pre>}
      <ul>
        {items.map((d) => (
          <li key={d.id}>
            <Link href={`/devices/${d.id}`}>{d.name}</Link> — {d.platform}{' '}
            {d.revoked_at ? '(revoked)' : ''}
          </li>
        ))}
      </ul>
    </main>
  );
}
