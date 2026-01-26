import Layout from './components/Layout';
import TasksWidget from './components/TasksWidget';
import EnergyChart from './components/EnergyChart';
import HealthMetrics from './components/HealthMetrics';
import './styles/index.css';

function App() {
  return (
    <Layout>
      {/* Dashboard Grid */}
      <div className="grid grid-cols-4 gap-lg">
        {/* Tasks Widget */}
        <TasksWidget refreshInterval={60000} />

        {/* Energy Widget */}
        <EnergyChart refreshInterval={60000} />

        {/* Health Widget */}
        <HealthMetrics refreshInterval={60000} />

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
