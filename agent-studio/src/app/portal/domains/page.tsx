'use client';

import React, { useState, useEffect } from 'react';
import HierarchicalNavigation from '@/components/HierarchicalNavigation';
import RoleDomainNavigation from '@/components/RoleDomainNavigation';
import Layout from '@/components/Layout';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getTenantFromCookie } from '@/lib/tenantUtils';
import styles from './DomainsPage.module.css';

const DomainsPage: React.FC = () => {
  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const userRoles = userData?.roles || [];
  const [navigationMode, setNavigationMode] = useState<'hierarchical' | 'role-domain'>('hierarchical');
  const [tenantName, setTenantName] = useState<string | null>(null);

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantName(tenant);
  }, []);

  // Check if user has admin access
  const hasAdminAccess = userRoles.includes('administrator');

  if (isUserLoading) {
    return <Layout><div className={styles.container}><p>Loading user data...</p></div></Layout>;
  }

  if (userError) {
    return <Layout><div className={styles.container}><p>Error loading user data: {userError}</p></div></Layout>;
  }

  if (!hasAdminAccess) {
    return (
      <Layout>
        <div className={styles.container}>
          <h1 className={styles.title}>Access Denied</h1>
          <p className={styles.description}>
            You don't have permission to access the domain navigation. Admin access is required.
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <h1 className={styles.title}>Domain Navigation</h1>
        <p className={styles.description}>
          Navigate through the hierarchical structure of domains, capabilities, skills, and MCP tools.
        </p>
        
        {/* Navigation Mode Toggle */}
        <div className="mb-6">
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
            <button
              onClick={() => setNavigationMode('hierarchical')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                navigationMode === 'hierarchical'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              All Domains
            </button>
            <button
              onClick={() => setNavigationMode('role-domain')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                navigationMode === 'role-domain'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Role and Domain
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {navigationMode === 'hierarchical' 
              ? 'Browse all domains, capabilities, and skills in the system.'
              : hasAdminAccess 
                ? 'View all system roles and their associated domains (Admin Mode).'
                : 'Navigate domains and capabilities based on your assigned roles.'
            }
          </p>
        </div>

        {/* Navigation Content */}
        {navigationMode === 'hierarchical' ? (
          <HierarchicalNavigation />
        ) : (
          <RoleDomainNavigation 
            isAdminMode={hasAdminAccess} 
            tenantName={tenantName || undefined}
          />
        )}
      </div>
    </Layout>
  );
};

export default DomainsPage;
