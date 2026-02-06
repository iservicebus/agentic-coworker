"use client";

import { useSession } from "next-auth/react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { logger } from '@/lib/logger';
import { getTenantFromCookie } from '@/lib/tenantUtils';

interface AuthGuardProps {
  children: React.ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [tenantChecked, setTenantChecked] = useState(false);

  useEffect(() => {
    logger.info("status is", status)
    if (status === "loading") {
      // Optionally, show a loading spinner or skeleton screen
      return;
    }

    // Check if tenant cookie exists
    const tenant = getTenantFromCookie();

    if (!tenant) {
      // No tenant cookie found, redirect to home for tenant selection
      logger.info("No tenant cookie found, redirecting to home");
      const queryString = searchParams.toString();
      // Ensure pathname is clean (starts with / and doesn't contain host)
      const cleanPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
      const fullPath = queryString ? `${cleanPath}?${queryString}` : cleanPath;
      router.push(`/?callbackUrl=${encodeURIComponent(fullPath)}`);
      return;
    }

    setTenantChecked(true);

    if (status === "unauthenticated") {
      // Build full URL with path and query parameters
      const queryString = searchParams.toString();
      // Ensure pathname is clean (starts with / and doesn't contain host)
      const cleanPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
      const fullPath = queryString ? `${cleanPath}?${queryString}` : cleanPath;
      router.push(`/?callbackUrl=${encodeURIComponent(fullPath)}`); // Redirect to home/login page
    }
  }, [session, status, router, pathname, searchParams]);

  // If authenticated and tenant is checked, render the children
  // If loading, you might want to render a loading state or null
  if (status === "authenticated" && tenantChecked) {
    return <>{children}</>;
  }

  // While loading or if unauthenticated and redirecting, render null or a loading indicator
  return null;
};

export default AuthGuard;
