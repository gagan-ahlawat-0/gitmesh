"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ImportPage() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to chat page since import is now integrated
    router.replace('/contribution/chat');
  }, [router]);

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold mb-2">Redirecting to Chat...</h2>
        <p className="text-muted-foreground">Import functionality is now integrated into the chat interface.</p>
      </div>
    </div>
  );
} 