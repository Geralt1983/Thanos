import Layout from './components/Layout';
import TasksWidget from './components/TasksWidget';
import './styles/index.css';

function App() {
  return (
    <Layout>
      {/* Dashboard Grid */}
      <div className="grid grid-cols-4 gap-lg">
        {/* Tasks Widget */}
        <TasksWidget refreshInterval={60000} />

        {/* Energy Widget */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Energy Levels</h3>
          </div>
          <div className="card-content">
            <p className="text-muted">Energy chart will appear here</p>
          </div>
        </div>

        {/* Health Widget */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Health Metrics</h3>
          </div>
          <div className="card-content">
            <p className="text-muted">Health metrics will appear here</p>
          </div>
        </div>

        {/* Correlation Widget */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Correlations</h3>
          </div>
          <div className="card-content">
            <p className="text-muted">Correlation chart will appear here</p>
          </div>
        </div>
      </div>

      {/* Status Section */}
      <div className="grid grid-cols-1 gap-md" style={{ marginTop: 'var(--spacing-xl)' }}>
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">System Status</h3>
          </div>
          <div className="card-content">
            <p className="text-secondary">
              ✓ Dashboard layout initialized
              <br />
              ✓ Grid system functional
              <br />
              ✓ Responsive design ready
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default App;
