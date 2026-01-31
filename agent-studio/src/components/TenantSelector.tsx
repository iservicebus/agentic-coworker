"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

interface TenantSelectorProps {
  onTenantSelected?: (tenant: string) => void;
}

export default function TenantSelector({ onTenantSelected }: TenantSelectorProps) {
  const [tenant, setTenant] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!tenant.trim()) {
      setError("Please enter a tenant name");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      // Call the API to validate and set tenant
      const response = await fetch("/api/auth/set-tenant", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ tenant: tenant.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle validation errors from the API
        setError(data.error || "Failed to set tenant. Please try again.");
        return;
      }

      console.log("Tenant set successfully:", tenant.trim());

      // Notify parent component if callback provided
      if (onTenantSelected) {
        onTenantSelected(tenant.trim());
      }

      // Don't redirect, just update state to show login
      // The parent component will handle showing the login button
    } catch (err) {
      console.error("Error setting tenant:", err);
      setError("Failed to connect to server. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold mb-2 text-center">Agent Studio</h1>
        <p className="text-gray-600 mb-8 text-center">Enter your tenant name to continue</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="tenant" className="block text-sm font-medium mb-2">
              Tenant Name
            </label>
            <input
              id="tenant"
              type="text"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              placeholder="e.g., default, company-name"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
              autoFocus
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Setting tenant..." : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
