'use client';

import React, { useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import './layout.css'; // Ensure layout styles are applied

interface LayoutProps {
  children: ReactNode; // To render page-specific content
}

export default function Layout({ children }: LayoutProps) {
  const [isResizing, setIsResizing] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(250);
  // Initialize collapsed state based on initial window width
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window !== 'undefined') { // Ensure window exists
        return window.innerWidth < 768;
    }
    return false; // Default server-side or if window undefined initially
  });
  const sidebarRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  // Ref to store the previous width to detect breakpoint crossing
  const previousWidthRef = useRef<number>(typeof window !== 'undefined' ? window.innerWidth : 0);

  // Logging helper (console log for simplicity in this component)
  const addLog = useCallback((message: string) => {
    console.log(`[Layout] ${new Date().toLocaleTimeString()}: ${message}`);
  }, []);


  const startResizing = useCallback((mouseDownEvent: React.MouseEvent) => {
    if (isCollapsed) return;
    setIsResizing(true);
    mouseDownEvent.preventDefault();
  }, [isCollapsed]);

  const stopResizing = useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = useCallback((mouseMoveEvent: MouseEvent) => {
    // Use containerRef if resizing calculation depends on the container dimensions
    if (isResizing && sidebarRef.current && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect();
        let newWidth = mouseMoveEvent.clientX - containerRect.left;

        const minWidth = 150;
        // Adjust maxWidth calculation if needed based on containerRef or viewport
        const maxWidth = Math.max(minWidth, window.innerWidth - 150); // Example: ensure content min width
        if (newWidth < minWidth) newWidth = minWidth;
        if (newWidth > maxWidth) newWidth = maxWidth;

        setSidebarWidth(newWidth);
    } else if (isResizing && sidebarRef.current) {
        // Fallback or alternative calculation if containerRef is not essential
        let newWidth = mouseMoveEvent.clientX - sidebarRef.current.getBoundingClientRect().left;
        const minWidth = 150;
        const maxWidth = window.innerWidth - 150; // Simpler calculation based on viewport
        if (newWidth < minWidth) newWidth = minWidth;
        if (newWidth > maxWidth) newWidth = maxWidth;
        setSidebarWidth(newWidth);
    }
  }, [isResizing]);


  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => resize(e);
    const handleMouseUp = () => stopResizing();

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizing, resize, stopResizing]);

  // Effect for handling resize events to auto-collapse/expand only when breakpoint is crossed
  useEffect(() => {
    const handleResize = () => {
        const currentWidth = window.innerWidth;
        const breakpoint = 768;
        const previousWidth = previousWidthRef.current;

        // Check if breakpoint was crossed
        const crossedBreakpoint =
            (previousWidth < breakpoint && currentWidth >= breakpoint) || // Small to Large
            (previousWidth >= breakpoint && currentWidth < breakpoint);   // Large to Small

        if (crossedBreakpoint) {
            addLog(`Breakpoint crossed: ${previousWidth} -> ${currentWidth}. Auto-toggling collapse.`);
            setIsCollapsed(currentWidth < breakpoint); // Set state based on new size after crossing
        }

        // Update previous width for next resize event comparison
        previousWidthRef.current = currentWidth;
    };

    // Set initial previous width ref value after mount
    previousWidthRef.current = window.innerWidth;

    window.addEventListener('resize', handleResize);
    // Cleanup listener on unmount
    return () => window.removeEventListener('resize', handleResize);
  }, [addLog]); // Include addLog in dependency array

  // Toggle logic remains a simple flip
  const toggleSidebar = () => {
    addLog(`Manual toggle triggered. Current state: ${isCollapsed}, toggling.`);
    setIsCollapsed(prevState => !prevState);
  };

  return (
    <div ref={containerRef} className="layout-container">
      <Header toggleSidebar={toggleSidebar} />
      <div className="layout-body">
        <Sidebar
          isCollapsed={isCollapsed}
          sidebarWidth={sidebarWidth}
          startResizing={startResizing}
          sidebarRef={sidebarRef}
        />
        {/* Render the page-specific content here */}
        <main className="layout-content">
          {children}
        </main>
      </div>
    </div>
  );
}
