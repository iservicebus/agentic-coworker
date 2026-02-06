"use client";

import React from 'react';
// import { useSession } from "next-auth/react"; // No longer directly needed for agentData fetching
// import { useRouter } from "next/navigation"; // No longer needed
// import { fetchUserLoginData, UserLoginResponse } from "@/lib/apiClient"; // Handled by context
import { useUserData } from "@/lib/contexts/UserDataContext";
import LoginButton from "@/components/auth/LoginButton";

interface HeaderProps {
  toggleSidebar: () => void;
}

const Header: React.FC<HeaderProps> = ({ toggleSidebar }) => {
  // const { data: session, status } = useSession(); // status from useSession might still be useful for general loading state if needed
  const { userData, isLoading, error } = useUserData();

  return (
    <header className="layout-header flex justify-between items-center p-4 bg-slate-50 text-slate-800 border-b border-slate-200">
      <div className="flex items-center">
        <button 
          onClick={toggleSidebar} 
          className="menu-button md:hidden text-slate-600 hover:text-slate-800 mr-4 p-2 rounded hover:bg-slate-200 transition-colors"
          aria-label="Toggle sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <span className="text-xl font-semibold text-slate-700">Agent Studio</span>
      </div>
      
      <div className="flex items-center space-x-6">
        {isLoading && <p className="text-sm text-slate-500">Loading user...</p>}
        {error && <p className="text-red-500 text-sm">Error: {error}</p>}
        {!isLoading && !error && userData && (
          <div className="flex items-center space-x-3">
            {userData.user_type && (
              <div className={`px-4 py-2 rounded-lg font-semibold text-sm shadow-sm ${
                userData.user_type === 'agent' 
                  ? 'bg-purple-100 text-purple-800 border border-purple-300' 
                  : 'bg-blue-100 text-blue-800 border border-blue-300'
              }`}>
                <span className="uppercase tracking-wide">
                  {userData.user_type === 'agent' ? '🤖 Agent' : '👤 Human'}
                </span>
              </div>
            )}
          </div>
        )}
        <LoginButton />
      </div>
    </header>
  );
};

export default Header;
