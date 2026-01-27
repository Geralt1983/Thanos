import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout">
      {/* Header */}
      <header className="layout-header">
        <div className="layout-header-container">
          <div>
            <h1 className="layout-header-title">
              ⚡ Thanos Dashboard
            </h1>
            <p className="layout-header-subtitle">
              The Executor's Command Center
            </p>
          </div>
          <div className="layout-header-date">
            {new Date().toLocaleDateString('en-US', {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            })}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="layout-main">
        {children}
      </main>

      {/* Footer */}
      <footer className="layout-footer">
        <p className="layout-footer-text">
          "Dread it. Run from it. The work arrives all the same."
        </p>
      </footer>
    </div>
  );
};

export default Layout;
