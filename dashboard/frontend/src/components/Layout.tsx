import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--color-bg-primary)',
      padding: '0',
    }}>
      {/* Header */}
      <header style={{
        backgroundColor: 'var(--color-bg-secondary)',
        borderBottom: '1px solid var(--color-border)',
        padding: 'var(--spacing-lg) var(--spacing-xl)',
        boxShadow: 'var(--shadow-md)',
      }}>
        <div style={{
          maxWidth: '1600px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <h1 style={{
              fontSize: '1.75rem',
              fontWeight: '700',
              color: 'var(--color-text-primary)',
              margin: '0',
              letterSpacing: '-0.025em',
            }}>
              ⚡ Thanos Dashboard
            </h1>
            <p style={{
              fontSize: '0.875rem',
              color: 'var(--color-text-muted)',
              margin: '0.25rem 0 0 0',
            }}>
              The Executor's Command Center
            </p>
          </div>
          <div style={{
            fontSize: '0.875rem',
            color: 'var(--color-text-secondary)',
          }}>
            {new Date().toLocaleDateString('en-US', {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            })}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{
        maxWidth: '1600px',
        margin: '0 auto',
        padding: 'var(--spacing-xl)',
      }}>
        {children}
      </main>

      {/* Footer */}
      <footer style={{
        backgroundColor: 'var(--color-bg-secondary)',
        borderTop: '1px solid var(--color-border)',
        padding: 'var(--spacing-lg) var(--spacing-xl)',
        marginTop: 'auto',
        textAlign: 'center',
      }}>
        <p style={{
          fontSize: '0.875rem',
          color: 'var(--color-text-muted)',
          margin: '0',
        }}>
          "Dread it. Run from it. The work arrives all the same."
        </p>
      </footer>
    </div>
  );
};

export default Layout;
