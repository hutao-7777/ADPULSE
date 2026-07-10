import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import Dashboard from './pages/Dashboard';
import RTBEngine from './pages/RTBEngine';
import AttributionTraffic from './pages/AttributionTraffic';
import ABTesting from './pages/ABTesting';
import AgentLoop from './pages/AgentLoop';
import ApiKeysPage from './pages/ApiKeysPage';

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/*"
          element={
            <Layout>
              <Routes>
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/rtb"
                  element={
                    <ProtectedRoute>
                      <RTBEngine />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/attribution"
                  element={
                    <ProtectedRoute>
                      <AttributionTraffic />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/abtesting"
                  element={
                    <ProtectedRoute>
                      <ABTesting />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/agent"
                  element={
                    <ProtectedRoute>
                      <AgentLoop />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/api-keys"
                  element={
                    <ProtectedRoute>
                      <ApiKeysPage />
                    </ProtectedRoute>
                  }
                />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </>
  );
}

export default App;
