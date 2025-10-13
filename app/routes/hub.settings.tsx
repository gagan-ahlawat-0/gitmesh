import { Outlet } from '@remix-run/react';
import { HubSettingsLayout } from '~/components/hub/settings/HubSettingsLayout';

export default function HubSettings() {
  return (
    <HubSettingsLayout>
      <Outlet />
    </HubSettingsLayout>
  );
}
