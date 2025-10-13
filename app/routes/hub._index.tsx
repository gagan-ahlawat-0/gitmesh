import { Navigate } from '@remix-run/react';

export default function HubIndex() {
  return <Navigate to="/hub/overview" replace />;
}
