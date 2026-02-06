import React from 'react';
import Layout from '@/components/Layout';

const AgentStudioPage = () => {
  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 p-4 sm:p-6 md:p-8">
        <div className="max-w-6xl mx-auto">

          {/* Hero Section */}
          <header className="mb-12 text-center bg-white shadow-xl rounded-lg p-8 md:p-12">
            <h1 className="text-5xl font-bold text-gray-900 mb-4">
              Welcome to Agent Studio
            </h1>
            <p className="text-xl text-gray-600 mb-6">
              Build, govern, and empower AI agents with enterprise-grade tools and security
            </p>
            <p className="text-lg text-gray-700 max-w-3xl mx-auto leading-relaxed">
              Agent Studio is a comprehensive platform for the complete AI agent lifecycle—from converting APIs
              into agent tools, to organizing capabilities hierarchically, to governing agent access with
              enterprise security and multi-tenant isolation.
            </p>
          </header>

          {/* Core Capabilities Grid */}
          <section className="mb-12">
            <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">
              Core Capabilities
            </h2>
            <div className="grid md:grid-cols-2 gap-6">

              {/* Universal API Integration */}
              <div className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow duration-300">
                <div className="flex items-start mb-4">
                  <div className="bg-indigo-100 rounded-lg p-3 mr-4">
                    <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Universal API Integration</h3>
                    <p className="text-gray-600 leading-relaxed">
                      Convert REST APIs to MCP tools from multiple sources: API documentation websites,
                      OpenAPI specifications, and Postman collections. Built-in validation and testing
                      ensure tools work correctly before deployment.
                    </p>
                  </div>
                </div>
              </div>

              {/* Hierarchical Organization */}
              <div className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow duration-300">
                <div className="flex items-start mb-4">
                  <div className="bg-purple-100 rounded-lg p-3 mr-4">
                    <svg className="w-8 h-8 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Business-Aligned Hierarchy</h3>
                    <p className="text-gray-600 leading-relaxed">
                      Organize tools using a bottom-up approach: Role → Domain → Capability → Skill → Tool.
                      This business-aligned structure ensures agents have the right tools for their responsibilities
                      and enables clear governance boundaries.
                    </p>
                  </div>
                </div>
              </div>

              {/* Enterprise Security */}
              <div className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow duration-300">
                <div className="flex items-start mb-4">
                  <div className="bg-green-100 rounded-lg p-3 mr-4">
                    <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Enterprise-Grade Security</h3>
                    <p className="text-gray-600 leading-relaxed">
                      OAuth 2.0 integration with multiple providers (Google, GitHub, LinkedIn, Keycloak, ServiceNow).
                      AES-256-GCM encryption for credentials, multi-tenant data isolation, and automatic token
                      refresh for seamless security management.
                    </p>
                  </div>
                </div>
              </div>

              {/* Agent Governance */}
              <div className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow duration-300">
                <div className="flex items-start mb-4">
                  <div className="bg-blue-100 rounded-lg p-3 mr-4">
                    <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Agent Governance & RBAC</h3>
                    <p className="text-gray-600 leading-relaxed">
                      Fine-grained role-based access control determines which tools each agent can access.
                      Manage agent profiles, track human-agent relationships, and enforce resource allocation
                      policies across your organization.
                    </p>
                  </div>
                </div>
              </div>

            </div>
          </section>

          {/* Complete Lifecycle */}
          <section className="mb-12 bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">
              Complete Agent Lifecycle
            </h2>
            <div className="grid md:grid-cols-3 gap-8">

              <div className="text-center">
                <div className="bg-indigo-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-indigo-600">1</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-3">Import & Validate</h3>
                <p className="text-gray-600 leading-relaxed">
                  Import APIs from multiple formats, annotate with semantic metadata, and validate
                  with built-in testing tools. Save to staging for review before deployment.
                </p>
              </div>

              <div className="text-center">
                <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-purple-600">2</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-3">Organize & Govern</h3>
                <p className="text-gray-600 leading-relaxed">
                  Structure tools hierarchically by business domains and capabilities. Assign roles
                  and permissions to agents, ensuring they only access appropriate tools.
                </p>
              </div>

              <div className="text-center">
                <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-green-600">3</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-3">Deploy & Monitor</h3>
                <p className="text-gray-600 leading-relaxed">
                  Register tools for agent use, manage OAuth credentials, and monitor agent-tool
                  interactions. Scale across multiple tenants with complete data isolation.
                </p>
              </div>

            </div>
          </section>

          {/* Additional Features */}
          <section className="mb-12">
            <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">
              Additional Features
            </h2>
            <div className="grid md:grid-cols-3 gap-6">

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
                  <svg className="w-5 h-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                  Runtime Testing
                </h3>
                <p className="text-gray-600 text-sm">
                  Built-in tool validation with sample data generation and schema verification before production.
                </p>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
                  <svg className="w-5 h-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                  Multi-Tenant Architecture
                </h3>
                <p className="text-gray-600 text-sm">
                  Complete tenant isolation for data, tools, credentials, and configurations.
                </p>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
                  <svg className="w-5 h-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Vector Search
                </h3>
                <p className="text-gray-600 text-sm">
                  Semantic tool discovery using embeddings and cosine similarity for intelligent matching.
                </p>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
                  <svg className="w-5 h-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  Credential Management
                </h3>
                <p className="text-gray-600 text-sm">
                  Secure OAuth token storage and management with automatic refresh and encryption.
                </p>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
                  <svg className="w-5 h-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Human-Agent Collaboration
                </h3>
                <p className="text-gray-600 text-sm">
                  Multi-user per agent with owner/member/viewer roles for collaborative workflows.
                </p>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
                  <svg className="w-5 h-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Business Process Flows
                </h3>
                <p className="text-gray-600 text-sm">
                  Map tools to business workflows with domain-specific organization and metrics.
                </p>
              </div>

            </div>
          </section>

          {/* Technology Stack */}
          <section className="mb-12 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg shadow-md p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-4 text-center">
              Built with Modern Technologies
            </h2>
            <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-700">
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">Next.js 15</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">React 19</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">TypeScript</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">PostgreSQL + pgvector</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">NextAuth.js</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">OAuth 2.0</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">MCP Protocol</span>
              <span className="bg-white px-4 py-2 rounded-full shadow-sm">Docker</span>
            </div>
          </section>

          {/* Call to Action */}
          <footer className="text-center bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Ready to Empower Your AI Agents?
            </h2>
            <p className="text-gray-700 leading-relaxed mb-6 max-w-2xl mx-auto">
              Agent Studio provides everything you need to build, deploy, and govern enterprise AI agents
              at scale. From API integration to security management, we've got you covered.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/portal/dashboard"
                className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                View Dashboard
              </a>
              <a
                href="/portal/tool-importer"
                className="bg-gray-200 text-gray-800 px-6 py-3 rounded-lg hover:bg-gray-300 transition-colors font-medium"
              >
                Import Your First API
              </a>
            </div>
          </footer>

        </div>
      </div>
    </Layout>
  );
};

export default AgentStudioPage;
