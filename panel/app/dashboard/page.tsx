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
