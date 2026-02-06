'use client';

import React from 'react';
import ToolDefinitionUI from '@/components/ToolDefinitionUI';
import {
  DomainToolCount,
  CapabilityToolSkillCount,
  SkillInfo,
  McpToolInfo
} from '@/lib/apiClient';
import styles from './McpToolsPage.module.css';

interface HierarchicalToolViewProps {
  // Domain state
  domains: DomainToolCount[];
  selectedDomain: DomainToolCount | null;
  onDomainClick: (domain: DomainToolCount) => void;
  
  // Capability state
  capabilities: CapabilityToolSkillCount[];
  selectedCapability: CapabilityToolSkillCount | null;
  onCapabilityClick: (capability: CapabilityToolSkillCount) => void;
  
  // View mode state
  viewMode: 'tools' | 'skills' | null;
  onViewTools: () => Promise<void>;
  onViewSkills: () => Promise<void>;
  
  // Skills state
  skills: SkillInfo[];
  selectedSkill: SkillInfo | null;
  onSkillClick: (skill: SkillInfo) => Promise<void>;
  
  // Tools state
  tools: McpToolInfo[];
  skillTools: McpToolInfo[];
  
  // Tool editing state
  viewingToolId: string | null;
  editedToolJson: string;
  originalToolJson: string;
  onToggleView: (toolId: string) => void;
  onEditedToolJsonChange: (json: string) => void;
  onSaveToStaging: () => Promise<void>;
  isSavingToStaging: boolean;
  
  // Navigation
  onBack: () => void;
  
  // Loading and messages
  isLoading: boolean;
  successMessage: string | null;
  
  // User context
  tenantName?: string;
  agentId?: string;
  isAdminMode: boolean;
}

const HierarchicalToolView: React.FC<HierarchicalToolViewProps> = ({
  domains,
  selectedDomain,
  onDomainClick,
  capabilities,
  selectedCapability,
  onCapabilityClick,
  viewMode,
  onViewTools,
  onViewSkills,
  skills,
  selectedSkill,
  onSkillClick,
  tools,
  skillTools,
  viewingToolId,
  editedToolJson,
  originalToolJson,
  onToggleView,
  onEditedToolJsonChange,
  onSaveToStaging,
  isSavingToStaging,
  onBack,
  isLoading,
  successMessage,
  tenantName,
  agentId,
  isAdminMode
}) => {
  return (
    <>
      {/* Breadcrumb Navigation */}
      {(selectedDomain || selectedCapability || viewMode || selectedSkill) && (
        <div className={styles.breadcrumb}>
          <button onClick={onBack} className={styles.backButton}>
            ← Back
          </button>
          <span className={styles.breadcrumbPath}>
            {selectedDomain && <span> / {selectedDomain.label}</span>}
            {selectedCapability && <span> / {selectedCapability.label}</span>}
            {viewMode && <span> / {viewMode === 'tools' ? 'Tools' : 'Skills'}</span>}
            {selectedSkill && <span> / {selectedSkill.label}</span>}
          </span>
        </div>
      )}

      {/* Domain List */}
      {!selectedDomain && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Domains ({domains.length})</h2>
          {isLoading ? (
            <p>Loading domains...</p>
          ) : (
            <div className={styles.cardGrid}>
              {domains.map((domain) => (
                <div
                  key={domain.name}
                  className={styles.card}
                  onClick={() => onDomainClick(domain)}
                >
                  <h3 className={styles.cardTitle}>{domain.label}</h3>
                  <p className={styles.cardDescription}>{domain.description}</p>
                  <div className={styles.cardStats}>
                    <span className={styles.statBadge}>
                      {domain.tool_count} {domain.tool_count === 1 ? 'tool' : 'tools'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Capability List */}
      {selectedDomain && !selectedCapability && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>
            Capabilities in {selectedDomain.label} ({capabilities.length})
          </h2>
          {isLoading ? (
            <p>Loading capabilities...</p>
          ) : (
            <div className={styles.cardGrid}>
              {capabilities.map((capability) => (
                <div
                  key={capability.name}
                  className={styles.card}
                  onClick={() => onCapabilityClick(capability)}
                >
                  <h3 className={styles.cardTitle}>{capability.label}</h3>
                  <p className={styles.cardDescription}>{capability.description}</p>
                  <div className={styles.cardStats}>
                    <span className={styles.statBadge}>
                      {capability.tool_count} {capability.tool_count === 1 ? 'tool' : 'tools'}
                    </span>
                    <span className={styles.statBadge}>
                      {capability.skill_count} {capability.skill_count === 1 ? 'skill' : 'skills'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Capability Actions */}
      {selectedCapability && !viewMode && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>{selectedCapability.label}</h2>
          <p className={styles.description}>{selectedCapability.description}</p>
          <div className={styles.actionButtons}>
            <button
              onClick={onViewTools}
              className={styles.actionButton}
              disabled={selectedCapability.tool_count === 0}
            >
              View Tools ({selectedCapability.tool_count})
            </button>
            <button
              onClick={onViewSkills}
              className={styles.actionButton}
              disabled={selectedCapability.skill_count === 0}
            >
              View Skills ({selectedCapability.skill_count})
            </button>
          </div>
        </div>
      )}

      {/* Tools View */}
      {viewMode === 'tools' && !selectedSkill && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>
            Tools for {selectedCapability?.label} ({tools.length})
          </h2>
          {successMessage && <p className={styles.success}>{successMessage}</p>}
          {isLoading ? (
            <p>Loading tools...</p>
          ) : (
            <ul className={styles.serviceList}>
              {tools.map((tool) => (
                <li key={tool.id} className={`${styles.serviceListItem} ${viewingToolId === tool.id ? styles.selected : ''}`}>
                  <div className={styles.serviceHeader}>
                    <div className={styles.toolInfo}>
                      <span className={styles.toolName}>{tool.name || 'Unnamed Tool'}</span>
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
                  
                  {viewingToolId === tool.id && (
                    <div className={styles.detailsContainer}>
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
                          onViewTools();
                        }}
                        onRegisterSuccess={() => {
                          onToggleView(tool.id);
                          onViewTools();
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
          )}
        </div>
      )}

      {/* Skills View */}
      {viewMode === 'skills' && !selectedSkill && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>
            Skills for {selectedCapability?.label} ({skills.length})
          </h2>
          {isLoading ? (
            <p>Loading skills...</p>
          ) : (
            <div className={styles.cardGrid}>
              {skills.map((skill) => (
                <div
                  key={skill.name}
                  className={styles.card}
                  onClick={() => onSkillClick(skill)}
                >
                  <h3 className={styles.cardTitle}>{skill.label}</h3>
                  <p className={styles.cardDescription}>{skill.description}</p>
                  {skill.operational_intent && (
                    <p className={styles.cardMeta}>Intent: {skill.operational_intent}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Skill Tools View */}
      {selectedSkill && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>
            Tools for {selectedSkill.label} ({skillTools.length})
          </h2>
          {successMessage && <p className={styles.success}>{successMessage}</p>}
          {isLoading ? (
            <p>Loading tools...</p>
          ) : (
            <ul className={styles.serviceList}>
              {skillTools.map((tool) => (
                <li key={tool.id} className={`${styles.serviceListItem} ${viewingToolId === tool.id ? styles.selected : ''}`}>
                  <div className={styles.serviceHeader}>
                    <div className={styles.toolInfo}>
                      <span className={styles.toolName}>{tool.name || 'Unnamed Tool'}</span>
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
                  
                  {viewingToolId === tool.id && (
                    <div className={styles.detailsContainer}>
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
                          if (selectedSkill) {
                            onSkillClick(selectedSkill);
                          }
                        }}
                        onRegisterSuccess={() => {
                          onToggleView(tool.id);
                          if (selectedSkill) {
                            onSkillClick(selectedSkill);
                          }
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
          )}
        </div>
      )}
    </>
  );
};

export default HierarchicalToolView;
