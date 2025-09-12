"use client";

import React from 'react';
import { cn } from '@/lib/utils';
import Navbar from '@/components/Navbar';

interface VSCodeLayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
  showSidebar?: boolean;
  title?: string;
  className?: string;
}

export const VSCodeLayout: React.FC<VSCodeLayoutProps> = ({
  children,
  sidebar,
  showSidebar = true,
  title,
  className
}) => {
  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Top Navbar */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border">
        <Navbar />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex pt-16 overflow-hidden">
        {/* Sidebar */}
        {showSidebar && sidebar && (
          <div className="w-80 border-r border-border bg-background/50 backdrop-blur-sm flex-shrink-0">
            <div className="h-full overflow-hidden">
              {sidebar}
            </div>
          </div>
        )}

        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Title bar if provided */}
          {title && (
            <div className="px-6 py-3 border-b border-border bg-background/50 backdrop-blur-sm">
              <h1 className="text-lg font-semibold text-foreground">{title}</h1>
            </div>
          )}
          
          {/* Content area */}
          <div className={cn("flex-1 overflow-auto", className)}>
            <div className="h-full">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VSCodeLayout;
