import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import PublishersPage from "./pages/PublishersPage";
import AdUnitsPage from "./pages/AdUnitsPage";
import TrafficQuality from "./pages/TrafficQuality";
import ApiKeysPage from "./pages/ApiKeysPage";

function App() {
  return (
    <>
      <Toaster position="top-right" toastOptions={{ style: { background: "#1e293b", color: "#f1f5f9", border: "1px solid #334155" } }} />
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/*" element={<Layout>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/publishers" element={<PublishersPage />} />
            <Route path="/ad-units" element={<AdUnitsPage />} />
            <Route path="/traffic" element={<TrafficQuality />} />
            <Route path="/api-keys" element={<ApiKeysPage />} />
          </Routes>
        </Layout>} />
      </Routes>
    </>
  );
}
export default App;
