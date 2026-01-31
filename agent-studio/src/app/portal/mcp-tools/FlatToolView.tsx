'use client';

import React from 'react';
import ToolDefinitionUI from '@/components/ToolDefinitionUI';
import ToolDomainNavigation from '@/components/ToolDefinitionUI/ToolDomainNavigation';
import HierarchicalToolFilter from '@/components/HierarchicalToolFilter';
import { McpToolInfo } from '@/lib/apiClient';
import { ToolFilter } from '@/lib/apiClient';
import styles from './McpToolsPage.module.css';

interface FlatToolViewProps {
  // Tools state
  tools: McpToolInfo[];

  // Search state (deprecated - now included in filter)
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  onSearch: (e: React.FormEvent) => void;

  // Filter state (using ToolFilter)
  onFilterChange: (filter: ToolFilter) => void;
  
  // Filter key to force remount
  filterKey?: string;
  
  // Tool editing state
  viewingToolId: string | null;
  editedToolJson: string;
  originalToolJson: string;
  onToggleView: (toolId: string) => void;
  onEditedToolJsonChange: (json: string) => void;
  onSaveToStaging: () => Promise<void>;
  isSavingToStaging: boolean;
  
  // Filter actions
  onSaveFilterToAgentProfile: () => void;
  onApplyAgentFilter: () => void;
  isSavingFilter: boolean;
  isLoadingAgentFilter: boolean;
  
  // Loading and messages
  isLoading: boolean;
  error: string | null;
  successMessage: string | null;
  
  // User context
  tenantName?: string;
  agentId?: string;
  isAdminMode: boolean;
  
  // Refresh
  onRefresh: () => Promise<void>;
}

const FlatToolView: React.FC<FlatToolViewProps> = ({
  tools,
  searchQuery,
  onSearchQueryChange,
  onSearch,
  onFilterChange,
  filterKey,
  viewingToolId,
  editedToolJson,
  originalToolJson,
  onToggleView,
  onEditedToolJsonChange,
  onSaveToStaging,
  isSavingToStaging,
  onSaveFilterToAgentProfile,
  onApplyAgentFilter,
  isSavingFilter,
  isLoadingAgentFilter,
  isLoading,
  error,
  successMessage,
  tenantName,
  agentId,
  isAdminMode,
  onRefresh
}) => {
  return (
    <>
      {/* Hierarchical Tool Filter - Replaces both search and filter */}
      <div className={styles.filterContainer}>
        <HierarchicalToolFilter
          key={filterKey}
          agentId={agentId}
          tenantName={tenantName}
          showSaveButton={!!agentId}
          showLoadButton={!!agentId}
          collapsible={true}
          autoLoadFilter={false}
          showToolQuery={true}
          showRoleDescription={false}
          title="Filters"
          onFilterChange={onFilterChange}
          onFilterSaved={onSaveFilterToAgentProfile}
          onFilterLoaded={onApplyAgentFilter}
          className={styles.filter}
        />
      </div>
      
      {/* Display general page errors or success messages here */}
      {error && !viewingToolId && <p className={styles.error}>Error: {error}</p>}
      {successMessage && !viewingToolId && <p className={styles.success}>{successMessage}</p>}

      <div className={styles.serviceListContainer}>
        <h2 className={styles.subTitle}>
          Available Tools ({tools.length})
          {isAdminMode && <span className={styles.adminBadge}>Admin View</span>}
        </h2>
        {tools.length === 0 && !isLoading && <p>No MCP tools found.</p>}
        {isLoading && tools.length > 0 && <p>Refreshing tool list...</p>}
        <ul className={styles.serviceList}>
          {tools.map((tool) => (
            <li key={tool.id} className={`${styles.serviceListItem} ${viewingToolId === tool.id ? styles.selected : ''}`}>
              <div className={styles.serviceHeader}>
                <div className={styles.toolInfo}>
                  <span className={styles.toolName}>{tool.name || 'Unnamed Tool'}</span>
                  {tool.cosine_similarity && (
                    <span className={styles.similarity}>
                      Similarity: {(tool.cosine_similarity * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                <button
                  onClick={() => onToggleView(tool.id)}
                  className={viewingToolId === tool.id ? styles.cancelButton : styles.viewButton}
                >
                  {viewingToolId === tool.id ? 'Cancel Edit' : 'View/Edit Details'}
                </button>
              </div>
              {tool.description && (
                <p className={styles.toolDescription}>{tool.description}</p>
              )}
              
              {/* Domain Navigation - Show in short view */}
              <div className={styles.domainNavigationContainer}>
                <ToolDomainNavigation
                  toolId={tool.id}
                  toolName={tool.name}
                  tenantName={tenantName || ''}
                  className="w-full"
                />
              </div>
              
              {viewingToolId === tool.id && (
                <div className={styles.detailsContainer}>
                  {/* Display specific errors/success for the current editing session */}
                  {error && viewingToolId && <p className={styles.error}>Error: {error}</p>}
                  {successMessage && viewingToolId && <p className={styles.success}>{successMessage}</p>}
                  <ToolDefinitionUI
                    editedToolJson={editedToolJson}
                    originalToolJson={originalToolJson}
                    onEditedToolJsonChange={onEditedToolJsonChange}
                    onSaveToStaging={onSaveToStaging}
                    isLoading={isSavingToStaging}
                    pageType="mcp"
                    serviceId={tool.id}
                    onDeleteSuccess={() => {
                      onToggleView(tool.id);
                      onRefresh();
                    }}
                    onRegisterSuccess={() => {
                      onToggleView(tool.id);
                      onRefresh();
                    }}
                    tenantName={tenantName}
                    agentId={agentId}
                    isAdminMode={isAdminMode}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
        <button onClick={onRefresh} disabled={isLoading} className={styles.refreshButton}>
          {isLoading ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>
    </>
  );
};

export default FlatToolView;
