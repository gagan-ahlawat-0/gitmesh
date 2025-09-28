"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Search, FileText, Code, Database } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchAnimationProps {
  type?: 'search' | 'file' | 'code' | 'cache';
  message?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const SearchAnimation: React.FC<SearchAnimationProps> = ({
  type = 'search',
  message,
  className,
  size = 'md'
}) => {
  const getIcon = () => {
    switch (type) {
      case 'file':
        return FileText;
      case 'code':
        return Code;
      case 'cache':
        return Database;
      default:
        return Search;
    }
  };

  const getDefaultMessage = () => {
    switch (type) {
      case 'file':
        return 'Searching files...';
      case 'code':
        return 'Analyzing code...';
      case 'cache':
        return 'Checking cache...';
      default:
        return 'Searching...';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return {
          container: 'gap-2 p-2',
          icon: 'w-4 h-4',
          text: 'text-xs',
          dots: 'w-1 h-1'
        };
      case 'lg':
        return {
          container: 'gap-4 p-4',
          icon: 'w-6 h-6',
          text: 'text-base',
          dots: 'w-2 h-2'
        };
      default:
        return {
          container: 'gap-3 p-3',
          icon: 'w-5 h-5',
          text: 'text-sm',
          dots: 'w-1.5 h-1.5'
        };
    }
  };

  const Icon = getIcon();
  const displayMessage = message || getDefaultMessage();
  const sizeClasses = getSizeClasses();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn(
        "flex items-center bg-muted/30 rounded-lg border border-border/50",
        sizeClasses.container,
        className
      )}
    >
      {/* Animated Icon */}
      <motion.div
        animate={{ 
          rotate: [0, 360],
          scale: [1, 1.1, 1]
        }}
        transition={{ 
          rotate: { duration: 2, repeat: Infinity, ease: "linear" },
          scale: { duration: 1, repeat: Infinity, ease: "easeInOut" }
        }}
        className="text-primary"
      >
        <Icon className={sizeClasses.icon} />
      </motion.div>

      {/* Message */}
      <span className={cn("text-muted-foreground font-medium", sizeClasses.text)}>
        {displayMessage}
      </span>

      {/* Animated Dots */}
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((index) => (
          <motion.div
            key={index}
            animate={{
              opacity: [0.3, 1, 0.3],
              scale: [0.8, 1.2, 0.8]
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay: index * 0.2,
              ease: "easeInOut"
            }}
            className={cn(
              "bg-primary rounded-full",
              sizeClasses.dots
            )}
          />
        ))}
      </div>
    </motion.div>
  );
};

// Specialized search animations for different contexts
export const FileSearchAnimation: React.FC<Omit<SearchAnimationProps, 'type'>> = (props) => (
  <SearchAnimation {...props} type="file" />
);

export const CodeSearchAnimation: React.FC<Omit<SearchAnimationProps, 'type'>> = (props) => (
  <SearchAnimation {...props} type="code" />
);

export const CacheSearchAnimation: React.FC<Omit<SearchAnimationProps, 'type'>> = (props) => (
  <SearchAnimation {...props} type="cache" />
);

// Pulse animation for minimal loading states
export const PulseAnimation: React.FC<{
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}> = ({ className, size = 'md' }) => {
  const getSizeClass = () => {
    switch (size) {
      case 'sm':
        return 'w-2 h-2';
      case 'lg':
        return 'w-4 h-4';
      default:
        return 'w-3 h-3';
    }
  };

  return (
    <div className={cn("flex items-center gap-1", className)}>
      {[0, 1, 2].map((index) => (
        <motion.div
          key={index}
          animate={{
            opacity: [0.3, 1, 0.3],
            scale: [0.8, 1.2, 0.8]
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: index * 0.15,
            ease: "easeInOut"
          }}
          className={cn(
            "bg-primary rounded-full",
            getSizeClass()
          )}
        />
      ))}
    </div>
  );
};

// Minimal spinner for inline loading
export const MinimalSpinner: React.FC<{
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}> = ({ className, size = 'md' }) => {
  const getSizeClass = () => {
    switch (size) {
      case 'sm':
        return 'w-3 h-3';
      case 'lg':
        return 'w-6 h-6';
      default:
        return 'w-4 h-4';
    }
  };

  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
      className={cn("border-2 border-primary border-t-transparent rounded-full", getSizeClass(), className)}
    />
  );
};

export default SearchAnimation;