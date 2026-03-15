import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Instruments from './pages/Instruments';
import Samples from './pages/Samples';
import Measurements from './pages/Measurements';
import AuditLog from './pages/AuditLog';
import Parsing from './pages/Parsing';
import MeasurementsGlobal from './pages/MeasurementsGlobal';
import Integrations from './pages/Integrations';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/instruments" element={<Instruments />} />
        <Route path="/samples" element={<Samples />} />
        <Route path="/samples/:sampleId/measurements" element={<Measurements />} />
        <Route path="/measurements" element={<MeasurementsGlobal />} />
        <Route path="/audit" element={<AuditLog />} />
        <Route path="/parsing" element={<Parsing />} />
        <Route path="/integrations" element={<Integrations />} />
      </Route>
    </Routes>
  );
}

