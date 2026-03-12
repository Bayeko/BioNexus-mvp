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
import { ToastContainer, useToasts } from './components/Toast';

export function App() {
  const [page, setPage] = useState<Page>('approvals');
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const eventIdCounter = useRef(0);
  const { toasts, addToast, dismissToast } = useToasts();

  const addActivity = useCallback((type: string, message: string) => {
    const id = String(++eventIdCounter.current);
    setActivity((prev) => [{ id, type, message, timestamp: new Date().toISOString() }, ...prev.slice(0, 99)]);
  }, []);

  // Initial data fetch
  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getProposals().then(setProposals),
      api.getWorkflows().then(setWorkflows),
      api.getConnectors().then(setConnectors),
    ]).catch((err) => {
      addActivity('error', `Failed to load data: ${err.message}`);
      addToast('error', 'Failed to connect to server');
    }).finally(() => setLoading(false));
  }, [addActivity, addToast]);

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
          if (proposal.autoApproved) {
            const risk = proposal.riskLevel ?? 'green';
            addActivity('proposal:auto-approved', `Auto-approved [${risk}]: ${proposal.workflowName} — ${proposal.summary}`);
            addToast('info', `Auto-approved: ${proposal.summary.slice(0, 60)}`);
          } else {
            addActivity('proposal:created', `New proposal: ${proposal.workflowName} — ${proposal.summary}`);
            addToast('info', `New proposal: ${proposal.summary.slice(0, 60)}`);
          }
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
  }, [addActivity, addToast]);

  // Handlers
  const handleApprove = async (id: string) => {
    try {
      const updated = await api.approveProposal(id);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));
      addToast('success', 'Proposal approved');
    } catch (err) {
      addActivity('error', `Approve failed: ${(err as Error).message}`);
      addToast('error', `Approve failed: ${(err as Error).message}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const updated = await api.rejectProposal(id);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));
      addToast('success', 'Proposal rejected');
    } catch (err) {
      addActivity('error', `Reject failed: ${(err as Error).message}`);
      addToast('error', `Reject failed: ${(err as Error).message}`);
    }
  };

  const handleChat = async (id: string, message: string) => {
    try {
      const { chatHistory } = await api.chatWithProposal(id, message);
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, chatHistory } : p)),
      );
    } catch (err) {
      addActivity('error', `Chat failed: ${(err as Error).message}`);
      addToast('error', `Chat failed: ${(err as Error).message}`);
    }
  };

  const handleRevise = async (id: string) => {
    try {
      const updated = await api.reviseProposal(id);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));
      addActivity('proposal:revised', `Proposal revised: ${updated.summary}`);
      addToast('success', 'Proposal revised');
    } catch (err) {
      addActivity('error', `Revise failed: ${(err as Error).message}`);
      addToast('error', `Revise failed: ${(err as Error).message}`);
    }
  };

  const handleUndo = async (id: string) => {
    try {
      const updated = await api.undoProposal(id);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));
      addActivity('proposal:undone', `Auto-approved proposal undone: ${updated.summary}`);
      addToast('success', 'Proposal undone');
    } catch (err) {
      addActivity('error', `Undo failed: ${(err as Error).message}`);
      addToast('error', `Undo failed: ${(err as Error).message}`);
    }
  };

  const handleToggleWorkflow = async (id: string) => {
    try {
      const updated = await api.toggleWorkflow(id);
      setWorkflows((prev) => prev.map((w) => (w.id === id ? updated : w)));
      addToast('success', `Workflow ${updated.enabled ? 'enabled' : 'disabled'}`);
    } catch (err) {
      addActivity('error', `Toggle failed: ${(err as Error).message}`);
      addToast('error', `Toggle failed: ${(err as Error).message}`);
    }
  };

  const handleTriggerWorkflow = async (id: string) => {
    try {
      await api.triggerWorkflow(id);
      addActivity('workflow:triggered', 'Workflow manually triggered');
      addToast('success', 'Workflow triggered');
    } catch (err) {
      addActivity('error', `Trigger failed: ${(err as Error).message}`);
      addToast('error', `Trigger failed: ${(err as Error).message}`);
    }
  };

  const handleDeleteWorkflow = async (id: string) => {
    try {
      await api.deleteWorkflow(id);
      setWorkflows((prev) => prev.filter((w) => w.id !== id));
      addToast('success', 'Workflow deleted');
    } catch (err) {
      addActivity('error', `Delete failed: ${(err as Error).message}`);
      addToast('error', `Delete failed: ${(err as Error).message}`);
    }
  };

  const handleCreateFromPrompt = async (prompt: string) => {
    const wf = await api.createWorkflowFromPrompt(prompt);
    setWorkflows((prev) => [...prev, wf]);
    addActivity('workflow:created', `AI-created workflow: ${wf.name}`);
    addToast('success', `Workflow created: ${wf.name}`);
  };

  const handleEnableConnector = async (name: string) => {
    try {
      await api.enableConnector(name);
      const updated = await api.getConnectors();
      setConnectors(updated);
      addToast('success', `${name} enabled`);
    } catch (err) {
      addActivity('error', `Enable failed: ${(err as Error).message}`);
      addToast('error', `Enable failed: ${(err as Error).message}`);
    }
  };

  const handleDisableConnector = async (name: string) => {
    try {
      await api.disableConnector(name);
      const updated = await api.getConnectors();
      setConnectors(updated);
      addToast('success', `${name} disabled`);
    } catch (err) {
      addActivity('error', `Disable failed: ${(err as Error).message}`);
      addToast('error', `Disable failed: ${(err as Error).message}`);
    }
  };

  const pendingCount = proposals.filter((p) => p.status === 'pending_approval').length;

  return (
    <>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <Layout
        currentPage={page}
        onNavigate={setPage}
        connected={connected}
        pendingCount={pendingCount}
      >
        {loading ? (
          <div className="loading-state">
            <span className="spinner" />
            Loading...
          </div>
        ) : (
          <>
            {page === 'approvals' && (
              <ApprovalQueue proposals={proposals} onApprove={handleApprove} onReject={handleReject} onChat={handleChat} onRevise={handleRevise} onUndo={handleUndo} />
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
          </>
        )}
      </Layout>
    </>
  );
}
