import { Outlet } from '@remix-run/react';
import { HubLayout } from '~/components/hub/HubLayoutSimple';

export default function Hub() {
  return (
    <HubLayout>
      <Outlet />
    </HubLayout>
  );
}
