'use client';

export default function SessionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      style={{
        padding: 40,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        gap: 16,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--accent-red)' }}>
        Session error
      </div>
      <div
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-default)',
          borderRadius: 8,
          padding: '12px 16px',
          fontSize: 13,
          color: 'var(--text-secondary)',
          maxWidth: 600,
          wordBreak: 'break-word',
          textAlign: 'left',
          fontFamily: 'monospace',
        }}
      >
        <div style={{ color: 'var(--accent-red)', marginBottom: 6 }}>{error.message}</div>
        {error.stack && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'pre-wrap' }}>
            {error.stack.split('\n').slice(1, 6).join('\n')}
          </div>
        )}
      </div>
      <button
        onClick={reset}
        style={{
          padding: '8px 20px',
          background: 'var(--accent)',
          color: 'var(--accent-fg)',
          border: 'none',
          borderRadius: 6,
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Try again
      </button>
    </div>
  );
}
