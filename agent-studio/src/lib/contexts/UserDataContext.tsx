"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useSession } from 'next-auth/react';
import { fetchUserLoginData, UserLoginResponse } from '@/lib/apiClient';

interface UserDataContextType {
  userData: UserLoginResponse | null;
  isLoading: boolean;
  error: string | null;
  refetchUserData: () => Promise<void>;
}

const UserDataContext = createContext<UserDataContextType | undefined>(undefined);

export const UserDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { data: session, status } = useSession();
  const [userData, setUserData] = useState<UserLoginResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (status === "authenticated") {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchUserLoginData();
        setUserData(data);
      } catch (err: any) {
        console.error("UserDataContext fetch error:", err);
        setError(err.message || "Failed to fetch user data.");
        setUserData(null); // Clear data on error
      } finally {
        setIsLoading(false);
      }
    } else if (status === "unauthenticated") {
      setUserData(null);
      setIsLoading(false);
      setError(null);
    } else { // loading
      setIsLoading(true);
    }
  }, [status]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const refetchUserData = useCallback(async () => {
    // Ensure user is still authenticated before refetching
    if (status === "authenticated") {
      await fetchData();
    } else {
      console.warn("Refetch skipped: User not authenticated.");
      // Optionally set an error or clear data if appropriate
      setUserData(null);
      setError("Cannot refetch data: User not authenticated.");
      setIsLoading(false);
    }
  }, [status, fetchData]);

  return (
    <UserDataContext.Provider value={{ userData, isLoading, error, refetchUserData }}>
      {children}
    </UserDataContext.Provider>
  );
};

export const useUserData = (): UserDataContextType => {
  const context = useContext(UserDataContext);
  if (context === undefined) {
    throw new Error('useUserData must be used within a UserDataProvider');
  }
  return context;
};
