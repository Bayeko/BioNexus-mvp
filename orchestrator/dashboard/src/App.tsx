import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api, connectSSE } from './api';
import type { Proposal, WorkflowDefinition, ConnectorInfo } from './api';
import { Layout } from './components/Layout';
import type { Page } from './components/Layout';
import { ApprovalQueue } from './components/ApprovalQueue';
import { WorkflowManager } from './components/WorkflowManager';
import { WorkflowCreator } from './components/WorkflowCreator';
import { ConnectorStatus } from './components/ConnectorStatus';
import { ActivityFeed } from './components/ActivityFeed';
import type { ActivityEvent } from './components/ActivityFeed';

export function App() {
  const [page, setPage] = useState<Page>('approvals');
  const [connected, setConnected] = useState(false);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const eventIdCounter = useRef(0);

  const addActivity = useCallback((type: string, message: string) => {
    const id = String(++eventIdCounter.current);
    setActivity((prev) => [{ id, type, message, timestamp: new Date().toISOString() }, ...prev.slice(0, 99)]);
  }, []);

  // Initial data fetch
  useEffect(() => {
    Promise.all([
      api.getProposals().then(setProposals),
      api.getWorkflows().then(setWorkflows),
      api.getConnectors().then(setConnectors),
    ]).catch((err) => {
      addActivity('error', `Failed to load data: ${err.message}`);
    });
  }, [addActivity]);

  // SSE connection
  useEffect(() => {
    const es = connectSSE((event, data) => {
      switch (event) {
        case 'connected':
          setConnected(true);
          addActivity('connected', 'Connected to orchestrator');
          break;
        case 'proposal:created': {
          const proposal = data as Proposal;
          setProposals((prev) => [proposal, ...prev]);
          addActivity('proposal:created', `New proposal: ${proposal.workflowName} — ${proposal.summary}`);
          break;
        }
        case 'proposal:updated': {
          const updated = data as Proposal;
          setProposals((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
          addActivity(`proposal:${updated.status}`, `Proposal ${updated.status}: ${updated.summary}`);
          break;
        }
        case 'workflow:created': {
          const wf = data as WorkflowDefinition;
          setWorkflows((prev) => [...prev, wf]);
          addActivity('workflow:created', `Workflow created: ${wf.name}`);
          break;
        }
        case 'workflow:updated': {
          const wf = data as WorkflowDefinition;
          setWorkflows((prev) => prev.map((w) => (w.id === wf.id ? wf : w)));
          addActivity('workflow:updated', `Workflow ${wf.enabled ? 'enabled' : 'disabled'}: ${wf.name}`);
          break;
        }
        case 'workflow:deleted': {
          const { id } = data as { id: string };
          setWorkflows((prev) => prev.filter((w) => w.id !== id));
          addActivity('workflow:deleted', 'Workflow removed');
          break;
        }
        case 'connector:updated':
          api.getConnectors().then(setConnectors);
          addActivity('connector:updated', 'Connector status changed');
          break;
        case 'error':
          setConnected(false);
          addActivity('error', 'Connection lost — reconnecting...');
          break;
      }
    });

    return () => es.close();
  }, [addActivity]);

  // Handlers
  const handleApprove = async (id: string) => {
    try {
      const updated = await api.approveProposal(id);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));
    } catch (err) {
      addActivity('error', `Approve failed: ${(err as Error).message}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const updated = await api.rejectProposal(id);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));
    } catch (err) {
      addActivity('error', `Reject failed: ${(err as Error).message}`);
    }
  };

  const handleToggleWorkflow = async (id: string) => {
    try {
      const updated = await api.toggleWorkflow(id);
      setWorkflows((prev) => prev.map((w) => (w.id === id ? updated : w)));
    } catch (err) {
      addActivity('error', `Toggle failed: ${(err as Error).message}`);
    }
  };

  const handleTriggerWorkflow = async (id: string) => {
    try {
      await api.triggerWorkflow(id);
      addActivity('workflow:triggered', `Workflow manually triggered`);
    } catch (err) {
      addActivity('error', `Trigger failed: ${(err as Error).message}`);
    }
  };

  const handleDeleteWorkflow = async (id: string) => {
    try {
      await api.deleteWorkflow(id);
      setWorkflows((prev) => prev.filter((w) => w.id !== id));
    } catch (err) {
      addActivity('error', `Delete failed: ${(err as Error).message}`);
    }
  };

  const handleCreateFromPrompt = async (prompt: string) => {
    const wf = await api.createWorkflowFromPrompt(prompt);
    setWorkflows((prev) => [...prev, wf]);
    addActivity('workflow:created', `AI-created workflow: ${wf.name}`);
  };

  const handleEnableConnector = async (name: string) => {
    try {
      await api.enableConnector(name);
      const updated = await api.getConnectors();
      setConnectors(updated);
    } catch (err) {
      addActivity('error', `Enable failed: ${(err as Error).message}`);
    }
  };

  const handleDisableConnector = async (name: string) => {
    try {
      await api.disableConnector(name);
      const updated = await api.getConnectors();
      setConnectors(updated);
    } catch (err) {
      addActivity('error', `Disable failed: ${(err as Error).message}`);
    }
  };

  const pendingCount = proposals.filter((p) => p.status === 'pending_approval').length;

  return (
    <Layout
      currentPage={page}
      onNavigate={setPage}
      connected={connected}
      pendingCount={pendingCount}
    >
      {page === 'approvals' && (
        <ApprovalQueue proposals={proposals} onApprove={handleApprove} onReject={handleReject} />
      )}
      {page === 'workflows' && (
        <WorkflowManager
          workflows={workflows}
          onToggle={handleToggleWorkflow}
          onTrigger={handleTriggerWorkflow}
          onDelete={handleDeleteWorkflow}
        />
      )}
      {page === 'create' && (
        <WorkflowCreator onCreateFromPrompt={handleCreateFromPrompt} />
      )}
      {page === 'connectors' && (
        <ConnectorStatus
          connectors={connectors}
          onEnable={handleEnableConnector}
          onDisable={handleDisableConnector}
        />
      )}
      {page === 'activity' && (
        <ActivityFeed events={activity} />
      )}
    </Layout>
  );
}
