"use client";

import { useAuth } from '@/contexts/AuthContext';
import { Suspense } from 'react';
import { ProfileView } from '@/components/hub/profile/ProfileView';
import { ProfileSkeleton } from '@/components/hub/profile/ProfileSkeleton';

function MyProfilePageContent() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
        <div className="text-center">
          <p>Please log in to view your profile.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <ProfileView username={user.login} isOwnProfile={true} />
    </div>
  );
}

export default function MyProfilePage() {
  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <MyProfilePageContent />
    </Suspense>
  );
}
