'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch, setToken } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'pw' | '2fa'>('pw');
  const [partial, setPartial] = useState('');
  const [err, setErr] = useState('');
  const [info, setInfo] = useState('');

  useEffect(() => {
    const m = sessionStorage.getItem('hermes_login_message');
    if (m) {
      setInfo(m);
      sessionStorage.removeItem('hermes_login_message');
    }
  }, []);

  async function loginPw(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    const res = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      setErr(await res.text());
      return;
    }
    const data = await res.json();
    setPartial(data.access_token);
    if (data.requires_2fa) setStep('2fa');
    else {
      setToken(data.access_token);
      router.push('/dashboard');
    }
  }

  async function login2fa(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    const res = await apiFetch('/auth/2fa/verify', {
      method: 'POST',
      body: JSON.stringify({ access_token: partial, code }),
    });
    if (!res.ok) {
      setErr(await res.text());
      return;
    }
    const data = await res.json();
    setToken(data.access_token);
    router.push('/dashboard');
  }

  return (
    <main style={{ maxWidth: 400, margin: '48px auto', padding: 16 }}>
      <h1>Hermes Admin</h1>
      {step === 'pw' ? (
        <form onSubmit={loginPw}>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: '100%' }} />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: '100%' }} />
          <button type="submit">Continue</button>
        </form>
      ) : (
        <form onSubmit={login2fa}>
          <p>Enter TOTP code</p>
          <input value={code} onChange={(e) => setCode(e.target.value)} style={{ width: '100%' }} />
          <button type="submit">Verify</button>
        </form>
      )}
      {info && <p style={{ color: '#b45309', marginTop: 12 }}>{info}</p>}
      {err && <pre style={{ color: 'crimson' }}>{err}</pre>}
      <p style={{ fontSize: 13, color: '#666', marginTop: 16 }}>
        Use <strong>admin@example.com</strong> (não admin@hermes.local). Após a senha, confirme o código do Google Authenticator.
      </p>
    </main>
  );
}
