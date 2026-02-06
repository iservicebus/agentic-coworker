import React, { RefObject, useEffect, useState } from 'react';
import Link from 'next/link';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getAgentsByUsername, AgentInfo } from "@/lib/apiClient";
import { getTenantFromCookie } from '@/lib/tenantUtils';

// Define an interface for individual navigation items
interface NavItem {
  href: string;
  label: string;
  icon?: React.JSX.Element; // Optional icon element
  subItems?: NavItem[];
}

interface SidebarProps {
  isCollapsed: boolean;
  sidebarWidth: number;
  startResizing: (event: React.MouseEvent) => void;
  sidebarRef: RefObject<HTMLDivElement | null>;
}

// Helper function to create agent-specific menu items
const createAgentMenuItems = (agentId: string): NavItem[] => [
  {
    href: `/portal/mcp-tools?agent_id=${agentId}`,
    label: "Agent Tools",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232a3 3 0 00-4.243 4.243l7.071 7.071a3 3 0 104.243-4.243l-7.071-7.071z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 14.25l-1.5 1.5a2.25 2.25 0 01-3.182-3.182l1.5-1.5" />
      </svg>
    )
  },
  { 
    href: "#", 
    label: "API Credentials", 
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9A3.75 3.75 0 119 9a3.75 3.75 0 016.75 0zM19.5 9.75a.75.75 0 01.75.75v2.25a.75.75 0 01-.75.75h-1.5v1.5a.75.75 0 01-.75.75h-1.5v1.5a.75.75 0 01-.75.75h-2.25a.75.75 0 01-.75-.75v-2.25a.75.75 0 01.75-.75h1.5v-1.5a.75.75 0 01.75-.75h1.5v-1.5a.75.75 0 01.75-.75h2.25z" />
      </svg>
    ),
    subItems: [
      {
        href: `/portal/service-secrets?agent_id=${agentId}`,
        label: "App APIKeys",
      },
      {
        href: `/portal/provider-tokens?agent_id=${agentId}`,
        label: "OAuth Tokens",
      }
    ]
  },
  {
    href: `/portal/agent-profile?agent_id=${agentId}`,
    label: "Agent Profile",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    )
  },
  {
    href: `/portal/agent-chat?agent_id=${agentId}`,
    label: "Agent Chat",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
      </svg>
    )
  },
];

// Example navigation items (can be moved to a config file or passed as props)
const baseNavItems: NavItem[] = [
  {
    href: "/portal",
    label: "Home",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955a.75.75 0 011.06 0l8.955 8.955M3 11.25V21h6V15h6v6h6V11.25M12 2.25V6" />
      </svg>
    )
  },
  {
    href: "/portal/dashboard",
    label: "Dashboard",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
      </svg>
    )
  },
];

const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  sidebarWidth,
  startResizing,
  sidebarRef,
}) => {
  const { userData, isLoading, error } = useUserData();
  const [userAgents, setUserAgents] = useState<AgentInfo[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);


  const [tenantName, setTenantName] = useState<string | null>(null);

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantName(tenant);
  }, []);




  // Fetch agents for human users
  useEffect(() => {
    if (userData && userData.user_type === 'human' && userData.username && tenantName) {
      setLoadingAgents(true);
      getAgentsByUsername(tenantName||'', userData.username)
        .then((agents) => {
          setUserAgents(agents);
        })
        .catch((err) => {
          console.error('Failed to fetch agents for user:', err);
          setUserAgents([]);
        })
        .finally(() => {
          setLoadingAgents(false);
        });
    }
  }, [userData, tenantName]);

  // Build navItems, conditionally adding Access Management if user has the role
  let navItems = [...baseNavItems];

  // Add user-type specific menu items
  if (userData?.user_type === 'human') {
    if (userAgents.length > 0) {
      // Create "Agents" parent menu with each agent as a submenu, and each agent has its own submenus
      const agentsMenuItem: NavItem = {
        href: "#",
        label: "Agents",
        icon: (
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </svg>
        ),
        subItems: userAgents.map((agent) => ({
          href: "#",
          label: agent.agent_id,
          icon: (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
            </svg>
          ),
          subItems: createAgentMenuItems(agent.agent_id),
        })),
      };
      navItems.push(agentsMenuItem);
    }
    
    // Add "Manage Agents" button for human users (for managing agent roles and access)
    const manageAgentsMenuItem: NavItem = {
      href: "/portal/agent-mngt?mode=user",
      label: "Manage Agents",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    };
    navItems.push(manageAgentsMenuItem);
  } else if (userData?.user_type === 'agent' && userData.username) {
    // For agent users, directly add the agent menu items without the agent name wrapper
    const agentMenuItems = createAgentMenuItems(userData.username);
    navItems.push(...agentMenuItems);
  }
  // Add administrator menu if user has administrator role
  if (userData?.roles && userData.roles.includes("administrator")) {
    navItems.push(
      // ... Administration navItem ...
      {
        href: "#",
        label: "Administration",
        icon: (
          // Gear/settings icon for administration
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.75 12a7.25 7.25 0 1114.5 0 7.25 7.25 0 01-14.5 0zm7.25-5.25a5.25 5.25 0 100 10.5 5.25 5.25 0 000-10.5zm0 2.25a3 3 0 110 6 3 3 0 010-6z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 2.25v2.25m0 15v2.25m9.75-9.75h-2.25m-15 0H2.25" />
          </svg>
        ),
        subItems: [
          {
            href: "#",
            label: "Tool Admin",
            icon: (
              // Wrench/tools icon for Tool Admin
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232a3 3 0 00-4.243 4.243l7.071 7.071a3 3 0 104.243-4.243l-7.071-7.071z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 14.25l-1.5 1.5a2.25 2.25 0 01-3.182-3.182l1.5-1.5" />
              </svg>
            ),
            subItems: [
              {
                href: "/portal/tool-importer",
                label: "Import APIs",
                icon: (
                  // Cloud upload icon for Import APIs
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75V9a4.5 4.5 0 00-9 0v3.75M12 16.5v-6m0 6l-3-3m3 3l3-3" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 16.5A2.25 2.25 0 0018 14.25H6A2.25 2.25 0 003.75 16.5" />
                  </svg>
                )
              },
              {
                href: "/portal/staging-services",
                label: "Annotate APIs",
                icon: (
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                  </svg>
                )
              },
              {
                href: "/portal/mcp-tools?mode=admin",
                label: "MCP Tools",
                icon: (
                  // Puzzle piece icon for MCP Tools
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V7.5A2.25 2.25 0 0111.25 5.25h1.5A2.25 2.25 0 0115 7.5V9m0 0h2.25A2.25 2.25 0 0119.5 11.25v1.5A2.25 2.25 0 0117.25 15H15m0 0v2.25A2.25 2.25 0 0112.75 19.5h-1.5A2.25 2.25 0 019 17.25V15m0 0H6.75A2.25 2.25 0 014.5 12.75v-1.5A2.25 2.25 0 016.75 9H9z" />
                  </svg>
                )
              }
            ]
          },
          {
            href: "/portal/agent-mngt?mode=admin",
            label: "Agent Admin",
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            )
          },
          {
            href: "/portal/user-mngt",
            label: "User Admin",
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
              </svg>
            )
          },
          {
            href: "/portal/auth-providers",
            label: "Auth Providers",
            icon: (
              // Shield/security icon for Auth Providers
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.623 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
            )
          },
              {
                href: "/portal/domains",
                label: "Domains",
                icon: (
                  // Hierarchy/tree icon for Domains
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6a1.125 1.125 0 01-1.125-1.125v-3.75zM14.25 8.625c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 01-1.125-1.125v-8.25zM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-5.25A1.125 1.125 0 013.75 18.375v-2.25z" />
                  </svg>
                )
              }

        ]
      }
    );
  }

  // Expand/collapse state for nav items
  const [expandedItems, setExpandedItems] = React.useState<Set<string>>(new Set());

  // Recursive NavItem rendering with expand/collapse using hierarchical keys
  const renderNavItem = (
    item: NavItem,
    level: number = 0,
    parentKey: string = ""
  ): React.ReactNode => {
    const hasSubItems = item.subItems && item.subItems.length > 0;
    // Use a hierarchical key for expansion state
    const itemKey = parentKey ? `${parentKey}/${item.label}` : item.label;
    const isExpanded = expandedItems.has(itemKey);

    const handleToggle = (e: React.MouseEvent) => {
      e.preventDefault();
      setExpandedItems(prev => {
        const next = new Set(prev);
        if (next.has(itemKey)) {
          next.delete(itemKey);
        } else {
          next.add(itemKey);
        }
        return next;
      });
    };

    return (
      <li key={itemKey}>
        <div className="flex items-center">
          {hasSubItems ? (
            <button
              onClick={handleToggle}
              className={`flex items-center px-3 py-2.5 ${level === 0 ? "text-base" : "text-sm"} font-medium rounded-md transition-colors group w-full text-left ${
                level === 0
                  ? "text-slate-700 hover:bg-slate-200 hover:text-slate-900"
                  : "text-slate-500 hover:bg-slate-200 hover:text-slate-900"
              }`}
              aria-expanded={isExpanded}
              aria-controls={`subitems-${itemKey}`}
              tabIndex={0}
              style={{ paddingLeft: `${8 + level * 16}px` }}
            >
              <span className={`${level === 0 ? "w-6 h-6 mr-3" : "w-4 h-4 mr-2"} flex-shrink-0`}>
                {item.icon}
              </span>
              <span className="truncate">{item.label}</span>
              <span className="ml-auto">{isExpanded ? "▼" : "▶"}</span>
            </button>
          ) : (
            <Link
              href={item.href}
              className={`flex items-center px-3 py-2.5 ${level === 0 ? "text-base" : "text-sm"} font-medium rounded-md transition-colors group w-full ${
                level === 0
                  ? "text-slate-700 hover:bg-slate-200 hover:text-slate-900"
                  : "text-slate-500 hover:bg-slate-200 hover:text-slate-900"
              }`}
              style={{ paddingLeft: `${8 + level * 16}px` }}
            >
              <span className={`${level === 0 ? "w-6 h-6 mr-3" : "w-4 h-4 mr-2"} flex-shrink-0`}>
                {item.icon}
              </span>
              <span className="truncate">{item.label}</span>
            </Link>
          )}
        </div>
        {hasSubItems && isExpanded && (
          <ul
            id={`subitems-${itemKey}`}
            className="space-y-1 mt-1"
          >
            {item.subItems!.map((subItem) =>
              renderNavItem(subItem, level + 1, itemKey)
            )}
          </ul>
        )}
      </li>
    );
  };
  return (
    <aside
      ref={sidebarRef}
      className={`layout-sidebar ${isCollapsed ? 'collapsed' : ''} bg-slate-50 border-r border-slate-200 flex flex-col`}
      style={{ width: isCollapsed ? 0 : `${sidebarWidth}px` }}
      aria-hidden={isCollapsed} // Hide from AT when visually collapsed
    >
      {!isCollapsed && (
        <>
          <div className="sidebar-content p-4 flex-grow overflow-y-auto">
            <nav>
              <ul className="space-y-1">
                {navItems.map((item) => renderNavItem(item))}
              </ul>
            </nav>
            <hr className="my-4 border-slate-200" />
            {/* Placeholder for other sidebar content if needed */}
            <div className="text-xs text-slate-400 px-3">
              Additional sidebar content can go here.
            </div>
          </div>
          
          {/* Resizer Handle - ensure it's only active when sidebar is not collapsed */}
          <div
            className="resizer"
            onMouseDown={startResizing}
            aria-hidden="true" 
          />
        </>
      )}
    </aside>
  );
};

export default Sidebar;
