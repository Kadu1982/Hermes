'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiFetch, getToken } from '@/lib/api';

export default function PairingPage() {
  const router = useRouter();
  const [label, setLabel] = useState('');
  const [out, setOut] = useState<any>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!getToken()) router.replace('/');
  }, [router]);

  async function gen(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    const res = await apiFetch('/pairing/codes', {
      method: 'POST',
      body: JSON.stringify({ label: label || null }),
    });
    if (!res.ok) {
      setErr(await res.text());
      return;
    }
    setOut(await res.json());
  }

  return (
    <main style={{ maxWidth: 560, margin: '24px auto', padding: 16 }}>
      <Link href="/dashboard">← Back</Link>
      <h1>Pairing code</h1>
      <form onSubmit={gen}>
        <label>Label (optional)</label>
        <input value={label} onChange={(e) => setLabel(e.target.value)} style={{ width: '100%' }} />
        <button type="submit">Generate</button>
      </form>
      {out && (
        <p>
          Code: <strong>{out.code}</strong> (expires {out.expires_at})
        </p>
      )}
      {err && <pre style={{ color: 'crimson' }}>{err}</pre>}
    </main>
  );
}
