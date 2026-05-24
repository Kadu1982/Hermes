'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, getToken } from '@/lib/api';

type DeviceDetail = {
  id: string;
  name: string;
  platform: string;
  last_seen: string | null;
  revoked_at: string | null;
  policy_version: number;
  token_version: number;
  inventory: Record<string, unknown> | null;
  public_key: string | null;
  created_at: string;
};

type CommandItem = {
  id: string;
  type: string;
  status: string;
  result: Record<string, unknown> | null;
  payload: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
  notify_channel: string | null;
  notify_on: string | null;
  source_text: string | null;
};

const COMMAND_TYPES = ['ping', 'get_inventory', 'request_upload', 'request_download', 'revoke_local', 'noop', 'speak', 'server_docker_ps'];

export default function DeviceDetail() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [device, setDevice] = useState<DeviceDetail | null>(null);
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [ctype, setCtype] = useState('ping');
  const [payload, setPayload] = useState('{}');
  const [notifyChannel, setNotifyChannel] = useState('silent');
  const [notifyOn, setNotifyOn] = useState('done');
  const [msg, setMsg] = useState('');

  async function refresh() {
    const [deviceRes, commandsRes] = await Promise.all([
      apiFetch(`/devices/${id}`),
      apiFetch(`/devices/${id}/commands?limit=30&offset=0`),
    ]);

    if (!deviceRes.ok) {
      setMsg(await deviceRes.text());
    } else {
      setDevice(await deviceRes.json());
    }

    if (!commandsRes.ok) {
      setMsg(await commandsRes.text());
      return;
    }

    const data = await commandsRes.json();
    setCommands(data.items);
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace('/');
      return;
    }
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [id, router]);

  async function sendCmd(e: React.FormEvent) {
    e.preventDefault();
    setMsg('');
    let parsed: Record<string, unknown> | null = null;
    try {
      parsed = payload.trim() ? JSON.parse(payload) : null;
    } catch {
      setMsg('Invalid JSON payload');
      return;
    }

    const res = await apiFetch(`/devices/${id}/commands`, {
      method: 'POST',
      body: JSON.stringify({
        type: ctype,
        payload: parsed,
        notify_channel: notifyChannel,
        notify_on: notifyOn,
      }),
    });

    if (!res.ok) {
      setMsg(await res.text());
      return;
    }

    await refresh();
  }

  async function revoke() {
    const res = await apiFetch(`/devices/${id}/revoke`, { method: 'POST' });
    if (!res.ok) {
      setMsg(await res.text());
      return;
    }
    await refresh();
  }

  return (
    <main style={{ maxWidth: 980, margin: '24px auto', padding: 16 }}>
      <Link href="/dashboard">← Devices</Link>
      <h1 style={{ marginBottom: 8 }}>{device ? device.name : `Device ${id}`}</h1>
      <p style={{ marginTop: 0, color: '#666' }}>
        {device?.platform ?? 'loading'} {device?.revoked_at ? '· revoked' : ''}
      </p>

      <section style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <article style={{ border: '1px solid #ddd', borderRadius: 12, padding: 12 }}>
          <strong>Status</strong>
          <div>Last seen: {device?.last_seen ? new Date(device.last_seen).toLocaleString() : 'never'}</div>
          <div>Policy version: {device?.policy_version ?? '—'}</div>
          <div>Token version: {device?.token_version ?? '—'}</div>
        </article>
        <article style={{ border: '1px solid #ddd', borderRadius: 12, padding: 12 }}>
          <strong>Identity</strong>
          <div>ID: {device?.id ?? id}</div>
          <div>Created: {device?.created_at ? new Date(device.created_at).toLocaleString() : '—'}</div>
          <div>Public key: {device?.public_key ? 'present' : 'absent'}</div>
        </article>
        <article style={{ border: '1px solid #ddd', borderRadius: 12, padding: 12 }}>
          <strong>Inventory</strong>
          <pre style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
            {device?.inventory ? JSON.stringify(device.inventory, null, 2) : 'No inventory yet'}
          </pre>
        </article>
      </section>

      <div style={{ marginTop: 12 }}>
        <button type="button" onClick={revoke}>
          Revoke
        </button>
      </div>

      <h2 style={{ marginTop: 24 }}>New command</h2>
      <form onSubmit={sendCmd} style={{ display: 'grid', gap: 12 }}>
        <label>
          Type
          <select value={ctype} onChange={(e) => setCtype(e.target.value)} style={{ display: 'block', width: '100%' }}>
            {COMMAND_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Notify channel
          <select
            value={notifyChannel}
            onChange={(e) => setNotifyChannel(e.target.value)}
            style={{ display: 'block', width: '100%' }}
          >
            {['silent', 'voice', 'push'].map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>
        <label>
          Notify on
          <select value={notifyOn} onChange={(e) => setNotifyOn(e.target.value)} style={{ display: 'block', width: '100%' }}>
            {['done', 'failed', 'both'].map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>
        <label>
          Payload JSON
          <textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            rows={5}
            style={{ width: '100%' }}
          />
        </label>
        <button type="submit">Send</button>
      </form>

      {msg && <pre style={{ color: 'crimson', whiteSpace: 'pre-wrap' }}>{msg}</pre>}

      <h2 style={{ marginTop: 24 }}>History</h2>
      <ul style={{ paddingLeft: 18 }}>
        {commands.map((c) => (
          <li key={c.id} style={{ marginBottom: 16 }}>
            <div>
              <code>{c.type}</code> · {c.status} ·{' '}
              <small>{c.completed_at ? new Date(c.completed_at).toLocaleString() : 'pending'}</small>
            </div>
            <div style={{ color: '#666' }}>
              notify {c.notify_channel ?? '—'} / {c.notify_on ?? '—'}
            </div>
            {c.source_text && <div style={{ marginTop: 4 }}>Source: {c.source_text}</div>}
            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(c.result, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </main>
  );
}
