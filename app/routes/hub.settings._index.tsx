import { Navigate } from '@remix-run/react';

export default function HubSettingsIndex() {
  return <Navigate to="/hub/settings/profile" replace />;
}
