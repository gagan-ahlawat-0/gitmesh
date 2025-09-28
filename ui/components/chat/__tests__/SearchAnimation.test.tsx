import React from 'react';
import { render, screen } from '@testing-library/react';
import { 
  SearchAnimation, 
  FileSearchAnimation, 
  CodeSearchAnimation, 
  CacheSearchAnimation,
  PulseAnimation,
  MinimalSpinner
} from '../SearchAnimation';

describe('SearchAnimation', () => {
  it('renders default search animation', () => {
    render(<SearchAnimation />);
    
    expect(screen.getByText('Searching...')).toBeInTheDocument();
    // Should have animated dots
    expect(document.querySelectorAll('[class*="bg-primary rounded-full"]')).toHaveLength(3);
  });

  it('renders with custom message', () => {
    render(<SearchAnimation message="Custom search message" />);
    
    expect(screen.getByText('Custom search message')).toBeInTheDocument();
  });

  it('renders different types correctly', () => {
    const { rerender } = render(<SearchAnimation type="file" />);
    expect(screen.getByText('Searching files...')).toBeInTheDocument();

    rerender(<SearchAnimation type="code" />);
    expect(screen.getByText('Analyzing code...')).toBeInTheDocument();

    rerender(<SearchAnimation type="cache" />);
    expect(screen.getByText('Checking cache...')).toBeInTheDocument();
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<SearchAnimation size="sm" />);
    let container = screen.getByText('Searching...').closest('div');
    expect(container).toHaveClass('gap-2', 'p-2');

    rerender(<SearchAnimation size="lg" />);
    container = screen.getByText('Searching...').closest('div');
    expect(container).toHaveClass('gap-4', 'p-4');
  });

  it('applies custom className', () => {
    render(<SearchAnimation className="custom-class" />);
    
    const container = screen.getByText('Searching...').closest('div');
    expect(container).toHaveClass('custom-class');
  });
});

describe('Specialized Search Animations', () => {
  it('renders FileSearchAnimation with correct defaults', () => {
    render(<FileSearchAnimation />);
    expect(screen.getByText('Searching files...')).toBeInTheDocument();
  });

  it('renders CodeSearchAnimation with correct defaults', () => {
    render(<CodeSearchAnimation />);
    expect(screen.getByText('Analyzing code...')).toBeInTheDocument();
  });

  it('renders CacheSearchAnimation with correct defaults', () => {
    render(<CacheSearchAnimation />);
    expect(screen.getByText('Checking cache...')).toBeInTheDocument();
  });

  it('allows custom messages in specialized animations', () => {
    render(<FileSearchAnimation message="Custom file message" />);
    expect(screen.getByText('Custom file message')).toBeInTheDocument();
  });
});

describe('PulseAnimation', () => {
  it('renders pulse animation with correct number of dots', () => {
    render(<PulseAnimation />);
    
    // Should have 3 animated dots
    const dots = document.querySelectorAll('[class*="bg-primary rounded-full"]');
    expect(dots).toHaveLength(3);
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<PulseAnimation size="sm" />);
    let dots = document.querySelectorAll('[class*="bg-primary rounded-full"]');
    expect(dots[0]).toHaveClass('w-2', 'h-2');

    rerender(<PulseAnimation size="lg" />);
    dots = document.querySelectorAll('[class*="bg-primary rounded-full"]');
    expect(dots[0]).toHaveClass('w-4', 'h-4');
  });

  it('applies custom className', () => {
    render(<PulseAnimation className="custom-pulse" />);
    
    const container = document.querySelector('.custom-pulse');
    expect(container).toBeInTheDocument();
  });
});

describe('MinimalSpinner', () => {
  it('renders spinner with correct styling', () => {
    render(<MinimalSpinner />);
    
    const spinner = document.querySelector('[class*="border-2 border-primary border-t-transparent rounded-full"]');
    expect(spinner).toBeInTheDocument();
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<MinimalSpinner size="sm" />);
    let spinner = document.querySelector('[class*="border-2"]');
    expect(spinner).toHaveClass('w-3', 'h-3');

    rerender(<MinimalSpinner size="lg" />);
    spinner = document.querySelector('[class*="border-2"]');
    expect(spinner).toHaveClass('w-6', 'h-6');
  });

  it('applies custom className', () => {
    render(<MinimalSpinner className="custom-spinner" />);
    
    const spinner = document.querySelector('.custom-spinner');
    expect(spinner).toBeInTheDocument();
  });
});

describe('Animation Behavior', () => {
  it('has proper motion properties for SearchAnimation', () => {
    render(<SearchAnimation />);
    
    // Check that the component has motion properties
    const container = screen.getByText('Searching...').closest('div');
    expect(container).toBeInTheDocument();
    
    // The motion div should be present (framer-motion adds specific attributes)
    expect(container).toHaveAttribute('style');
  });

  it('has animated elements for PulseAnimation', () => {
    render(<PulseAnimation />);
    
    const dots = document.querySelectorAll('[class*="bg-primary rounded-full"]');
    expect(dots).toHaveLength(3);
    
    // Each dot should have motion styling
    dots.forEach(dot => {
      expect(dot).toHaveAttribute('style');
    });
  });

  it('has rotating animation for MinimalSpinner', () => {
    render(<MinimalSpinner />);
    
    const spinner = document.querySelector('[class*="border-2"]');
    expect(spinner).toHaveAttribute('style');
  });
});

describe('Accessibility', () => {
  it('provides meaningful text content', () => {
    render(<SearchAnimation />);
    expect(screen.getByText('Searching...')).toBeInTheDocument();
  });

  it('maintains readability with custom messages', () => {
    render(<SearchAnimation message="Processing your request, please wait..." />);
    expect(screen.getByText('Processing your request, please wait...')).toBeInTheDocument();
  });

  it('has appropriate contrast with primary colors', () => {
    render(<SearchAnimation />);
    
    const dots = document.querySelectorAll('[class*="bg-primary"]');
    expect(dots.length).toBeGreaterThan(0);
    
    // Dots should use primary color for good contrast
    dots.forEach(dot => {
      expect(dot).toHaveClass('bg-primary');
    });
  });
});