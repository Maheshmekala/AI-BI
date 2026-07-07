import { useDatasets } from './hooks/use-datasets';
import { useChat } from './hooks/use-chat';
import { useInsights } from './hooks/use-insights';
import { useModels } from './hooks/use-models';
import { Sidebar } from './components/layout/sidebar';
import { LandingPage } from './pages/landing';
import { ChatPage } from './pages/chat';
import { DashboardPage } from './pages/dashboard';
import { InsightsPage } from './pages/insights';
import { SourcesPage } from './pages/sources';
import { ChartsPage } from './pages/charts';
import { SettingsPage } from './pages/settings';
import { DashboardProvider } from './context/dashboard-context';
import { useState } from 'react';

type Page = 'landing' | 'chat' | 'dashboard' | 'insights' | 'sources' | 'charts' | 'settings';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('landing');
  const datasets = useDatasets();
  const chat = useChat();
  const insights = useInsights();
  const models = useModels();

  const hasData = datasets.activeDataset !== null;

  const renderPage = () => {
    if (!hasData && (currentPage === 'chat' || currentPage === 'dashboard' || currentPage === 'insights' || currentPage === 'charts')) {
      return <LandingPage onNavigate={setCurrentPage} datasets={datasets} />;
    }

    switch (currentPage) {
      case 'landing':
        return <LandingPage onNavigate={setCurrentPage} datasets={datasets} />;
      case 'chat':
        return <ChatPage dataset={datasets.activeDataset!} chat={chat} models={models} />;
      case 'dashboard':
        return (
          <DashboardProvider>
            <DashboardPage dataset={datasets.activeDataset!} />
          </DashboardProvider>
        );
      case 'insights':
        return <InsightsPage dataset={datasets.activeDataset!} insights={insights} />;
      case 'sources':
        return <SourcesPage datasets={datasets} />;
      case 'charts':
        return <ChartsPage dataset={datasets.activeDataset!} />;
      case 'settings':
        return <SettingsPage />;
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        datasets={datasets}
        models={models}
        hasData={hasData}
      />
      <main className="flex-1 ml-[260px] p-6">
        {renderPage()}
      </main>
    </div>
  );
}

export default App;
