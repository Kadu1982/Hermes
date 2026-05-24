'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

export default function AuditPage() {
  const [items, setItems] = useState<any[]>([]);

  function csvCell(value: unknown) {
    const text = String(value ?? '');
    return `"${text.replaceAll('"', '""')}"`;
  }

  useEffect(() => {
    (async () => {
      const res = await apiFetch('/audit?limit=200&offset=0');
      if (res.ok) {
        const data = await res.json();
        setItems(data.items);
      }
    })();
  }, []);

  const csv = [
    'id,actor_type,actor_id,action,metadata,created_at',
    ...items.map((r) =>
      [r.id, r.actor_type, r.actor_id ?? '', r.action, JSON.stringify(r.metadata ?? {}), r.created_at]
        .map(csvCell)
        .join(','),
    ),
  ].join('\n');

  return (
    <main style={{ maxWidth: 960, margin: '24px auto', padding: 16 }}>
      <Link href="/dashboard">← Back</Link>
      <h1>Audit log</h1>
      <a href={`data:text/csv,${encodeURIComponent(csv)}`} download="hermes-audit.csv">
        Download CSV
      </a>
      <table cellPadding={6} style={{ borderCollapse: 'collapse', marginTop: 12, width: '100%' }}>
        <thead>
          <tr>
            <th align="left">When</th>
            <th align="left">Actor</th>
            <th align="left">Action</th>
            <th align="left">Metadata</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id}>
              <td>{r.created_at}</td>
              <td>
                {r.actor_type}:{r.actor_id}
              </td>
              <td>{r.action}</td>
              <td>
                <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(r.metadata ?? {}, null, 2)}</pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
