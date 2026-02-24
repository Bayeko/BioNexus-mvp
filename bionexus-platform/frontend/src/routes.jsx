import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';

export default function AppRoutes({ user, onLogin, onLogout }) {
  if (!user) {
    return <Login onLogin={onLogin} />;
  }

  return (
    <Routes>
      <Route path="/" element={<Dashboard username={user} onLogout={onLogout} />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
