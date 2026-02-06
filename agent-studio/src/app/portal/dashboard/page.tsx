'use client';

import React, { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import { getWorkflowsWithToolCount, WorkflowToolCount, WorkflowsWithTotalCount } from '@/lib/apiClient';
import styles from './DashboardPage.module.css';
import { getTenantFromCookie } from '@/lib/tenantUtils';
const DashboardPage: React.FC = () => {
  const [workflows, setWorkflows] = useState<WorkflowToolCount[]>([]);
  const [totalMcpToolCount, setTotalMcpToolCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowToolCount | null>(null);
  const [expandedWorkflows, setExpandedWorkflows] = useState<Set<string>>(new Set());


    const [tenantName, setTenantName] = useState<string | null>(null);
  
    // Get tenant from cookie on component mount
    useEffect(() => {
      const tenant = getTenantFromCookie();
      setTenantName(tenant);
    }, []);
  
  useEffect(() => {
    const fetchWorkflows = async () => {
      if (!tenantName) {
        return;
      }
      
      try {
        setIsLoading(true);
        const data: WorkflowsWithTotalCount = await getWorkflowsWithToolCount(tenantName);
        setWorkflows(data.workflows);
        setTotalMcpToolCount(data.total_mcp_tool_count);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load workflows');
        console.error('Error fetching workflows:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkflows();
  }, [tenantName]);

  if (isLoading) {
    return (
      <Layout>
        <div className={styles.container}>
          <div className={styles.loading}>Loading workflows...</div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className={styles.container}>
          <div className={styles.error}>Error: {error}</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.hero}>
          <h1 className={styles.title}>AI Integration Readiness Dashboard</h1>
          <p className={styles.subtitle}>
            MCP Tool Availability Across Business Workflows
          </p>
          <p className={styles.description}>
            Visualize your organization's Agentic AI readiness by exploring MCP tool coverage across key business workflows. 
            Each workflow step shows the number of available AI tools, indicating automation potential and integration opportunities.
          </p>
        </div>

        <div className={styles.statsBar}>
          <div className={styles.statCard}>
            <div className={styles.statNumber}>{workflows.length}</div>
            <div className={styles.statLabel}>Business Workflows</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statNumber}>{totalMcpToolCount}</div>
            <div className={styles.statLabel}>Total MCP Tools</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statNumber}>
              {workflows.reduce((sum, w) => sum + w.workflow_steps.length, 0)}
            </div>
            <div className={styles.statLabel}>Workflow Steps</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statNumber}>
              {Math.round(
                (workflows.reduce((sum, w) => sum + w.workflow_steps.filter(s => s.tool_count > 0).length, 0) /
                workflows.reduce((sum, w) => sum + w.workflow_steps.length, 0)) * 100
              )}%
            </div>
            <div className={styles.statLabel}>Steps with Tools</div>
          </div>
        </div>

        <div className={styles.workflowList}>
          {workflows.map((workflow) => {
            const isExpanded = expandedWorkflows.has(workflow.id);
            
            return (
              <div key={workflow.id} className={styles.workflowSection}>
                <div 
                  className={styles.workflowHeader}
                  onClick={() => {
                    const newExpanded = new Set(expandedWorkflows);
                    if (isExpanded) {
                      newExpanded.delete(workflow.id);
                    } else {
                      newExpanded.add(workflow.id);
                    }
                    setExpandedWorkflows(newExpanded);
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <div className={styles.workflowTitleSection}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span className={styles.expandIcon}>
                        {isExpanded ? '▼' : '▶'}
                      </span>
                      <h2 className={styles.workflowLabel}>{workflow.label}</h2>
                    </div>
                    <p className={styles.workflowDescription}>{workflow.description}</p>
                  </div>
                  <div className={styles.toolCount}>
                    <span className={styles.toolCountNumber}>{workflow.tool_count}</span>
                    <span className={styles.toolCountLabel}>total tools</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className={styles.stepsContainer}>
                {workflow.workflow_steps.map((step, index) => (
                  <React.Fragment key={step.id}>
                    <div className={styles.stepBox}>
                      <div className={styles.stepBoxHeader}>
                        <div className={styles.stepNumber}>{step.step_order}</div>
                        <div className={styles.stepContent}>
                          <h3 className={styles.stepLabel}>{step.label}</h3>
                          {step.domains && step.domains.length > 0 && (
                            <div className={styles.domainsList}>
                              {step.domains.map((domain) => (
                                <div key={domain.name} className={styles.domainChip}>
                                  <span className={styles.domainLabel}>{domain.label}</span>
                                  <span className={styles.domainToolCount}>
                                    {domain.tool_count} {domain.tool_count === 1 ? 'tool' : 'tools'}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className={styles.stepToolCount}>
                          <span className={styles.stepToolNumber}>{step.tool_count}</span>
                          <span className={styles.stepToolLabel}>tools</span>
                        </div>
                      </div>
                    </div>
                    {index < workflow.workflow_steps.length - 1 && (
                      <div className={styles.stepConnector}>↓</div>
                    )}
                  </React.Fragment>
                ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Layout>
  );
};

export default DashboardPage;
