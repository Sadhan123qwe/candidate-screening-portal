import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { Backdrop } from "./components/ui/Backdrop";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidatesPage } from "./pages/CandidatesPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { ModelMetricsPage } from "./pages/ModelMetricsPage";

export function App() {
  return (
    <>
      <Backdrop />
      <div className="app-layer">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/applications" element={<ApplicationsPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/jobs/:id" element={<JobDetailPage />} />
              <Route path="/candidates" element={<CandidatesPage />} />
              <Route path="/candidates/:id" element={<CandidateDetailPage />} />
              <Route path="/model" element={<ModelMetricsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/applications" replace />} />
        </Routes>
      </div>
    </>
  );
}
