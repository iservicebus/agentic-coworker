"use client"; // Required for useSession and useRouter

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import LoginButton from "@/components/auth/LoginButton";
import TenantSelector from "@/components/TenantSelector";
import { getTenantFromCookie } from "@/lib/tenantUtils";
import Image from "next/image"; // Keep Image if needed for logo, etc.

export default function HomeContent() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl");
  const [tenantChecked, setTenantChecked] = useState(false);
  const [hasTenant, setHasTenant] = useState(false);

  // Check if tenant is already set in cookie
  useEffect(() => {
    const checkTenantCookie = () => {
      const tenant = getTenantFromCookie();
      console.log("Checking tenant cookie:", tenant);
      setHasTenant(!!tenant);
      setTenantChecked(true);
    };
    
    checkTenantCookie();
  }, []);

  useEffect(() => {
    // If session is loaded and user is authenticated, redirect to Agent Studio
    if (status === "authenticated" && hasTenant && tenantChecked) {
      // Extract pathname from callbackUrl if it's a full URL, otherwise use as-is
      let targetUrl = callbackUrl || "/portal";
      try {
        // If callbackUrl is a full URL, extract just the pathname
        if (targetUrl.includes('://') || targetUrl.includes('localhost') || targetUrl.includes('host.docker.internal')) {
          const url = new URL(targetUrl, window.location.origin);
          targetUrl = url.pathname + url.search + url.hash;
        }
      } catch (e) {
        // If URL parsing fails, use as-is (it's already a path)
        console.log("Using callbackUrl as-is:", targetUrl);
      }
      console.log("Redirecting authenticated user to:", targetUrl);
      router.push(targetUrl);
    }
  }, [status, router, callbackUrl, hasTenant, tenantChecked]);

  // If tenant check is not complete yet, show loading
  if (!tenantChecked) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-8 font-[family-name:var(--font-geist-sans)]">
        <p>Loading...</p>
      </div>
    );
  }

  // If session is loading, show a loading message or spinner
  if (status === "loading") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-8 font-[family-name:var(--font-geist-sans)]">
        <p>Loading session...</p>
      </div>
    );
  }

  // If user is not authenticated and no tenant selected, show tenant selector first
  if (status === "unauthenticated" && !hasTenant) {
    return <TenantSelector onTenantSelected={() => {
      console.log("Tenant selected callback triggered");
      // Re-check the cookie after tenant is set
      const tenant = getTenantFromCookie();
      console.log("Cookie after tenant selection:", tenant);
      setHasTenant(!!tenant);
    }} />;
  }

  // If tenant is selected but not authenticated, show login page
  if (status === "unauthenticated" && hasTenant) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-8 font-[family-name:var(--font-geist-sans)]">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-6">Agent Studio</h1>
          <LoginButton />
        </div>
      </div>
    );
  }

  // If authenticated but no tenant, redirect back to tenant selector
  if (status === "authenticated" && !hasTenant) {
    return <TenantSelector onTenantSelected={() => {
      console.log("Tenant selected callback triggered (authenticated)");
      // Re-check the cookie after tenant is set
      const tenant = getTenantFromCookie();
      console.log("Cookie after tenant selection (authenticated):", tenant);
      setHasTenant(!!tenant);
    }} />;
  }

  // Fallback for authenticated users before redirect (e.g., brief "Redirecting..." message)
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 font-[family-name:var(--font-geist-sans)]">
      <p>Redirecting to Agent Studio...</p>
    </div>
  );
}
