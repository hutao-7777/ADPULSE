import { Routes, Route } from 'react-router-dom';

import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import RTBEngine from './pages/RTBEngine';
import AttributionTraffic from './pages/AttributionTraffic';
import ABTesting from './pages/ABTesting';
import AgentLoop from './pages/AgentLoop';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/rtb" element={<RTBEngine />} />
        <Route path="/attribution" element={<AttributionTraffic />} />
        <Route path="/abtesting" element={<ABTesting />} />
        <Route path="/agent" element={<AgentLoop />} />
      </Routes>
    </Layout>
  );
}

export default App;
