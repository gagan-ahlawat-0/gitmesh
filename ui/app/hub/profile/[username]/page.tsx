"use client";

import { useParams } from 'next/navigation';
import { Suspense } from 'react';
import { ProfileView } from '@/components/hub/profile/ProfileView';
import { ProfileSkeleton } from '@/components/hub/profile/ProfileSkeleton';

function ProfilePageContent() {
  const params = useParams();
  const username = params.username as string;

  return (
    <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <ProfileView username={username} />
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <ProfilePageContent />
    </Suspense>
  );
}
