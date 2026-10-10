import React, { useState, useEffect } from 'react';
import { 
  AppShell, Group, Text, Title, Button, Avatar, Loader, Center, Burger, Box, NavLink, Stack, Container 
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { 
  IconLayoutDashboard, IconUsers, IconBriefcase, IconSettings, IconLogout, IconUserPlus 
} from '@tabler/icons-react';
import Login from './pages/Login';
import Signup from './pages/RegisterStaff';
import Dashboard from './pages/Dashboard';
import Customers from './pages/Customers';
import Projects from './pages/Projects';
import api from './api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('access_token'));
  const [data, setData] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [currentView, setCurrentView] = useState('dashboard');
  const [opened, { toggle, close }] = useDisclosure();

  const fetchInitialData = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [dashRes, profileRes] = await Promise.all([
        api.get('dashboard/summary/'),
        api.get('accounts/profile/')
      ]);
      setData(dashRes.data);
      setUser(profileRes.data);
    } catch (err) {
      if (err.response?.status === 401) handleLogout();
      else setLoadError('We could not load your workspace. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) { fetchInitialData(); }
  }, [isAuthenticated]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setData(null);
    setCurrentView('dashboard');
    setIsAuthenticated(false);
    setUser(null);
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setLoading(true); // Trigger re-fetch
  };

  const goToNewProject = () => {
    setCurrentView('projects');
    close();
  };

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  if (loadError) return <Center h="100svh"><Stack align="center"><Text role="alert">{loadError}</Text><Button color="dark" onClick={fetchInitialData}>Try again</Button><Button variant="subtle" onClick={handleLogout}>Back to sign in</Button></Stack></Center>;

  if (loading) return <Center h="100vh"><Loader color="yellow" size="xl" type="dots" /></Center>;

  return (
    <AppShell
      header={{ height: 70 }}
      navbar={{ width: 280, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
      styles={{
        main: { background: '#f5f3ee', minHeight: '100vh' }
      }}
    >
      <AppShell.Header p="md" style={{ background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(10px)' }}>
        <Group justify="space-between" h="100%">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={3} style={{ fontFamily: 'Playfair Display' }}>STUDIO.<Text span c="yellow.6">OS</Text></Title>
          </Group>
          <Group visibleFrom="sm">
            <Text size="sm" fw={700}>{user?.username}</Text>
            <Avatar color="yellow" radius="xl">{user?.username?.charAt(0).toUpperCase()}</Avatar>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md" style={{ background: '#18211e', color: '#e6e8e3' }}>
        <Stack justify="space-between" h="100%">
          <Box>
            <NavLink label="Dashboard" leftSection={<IconLayoutDashboard size={20} />} active={currentView === 'dashboard'} color="yellow" onClick={() => { setCurrentView('dashboard'); close(); }} />
            <NavLink label="Customers" leftSection={<IconUsers size={20} />} active={currentView === 'customers'} color="yellow" onClick={() => { setCurrentView('customers'); close(); }} />
            <NavLink label="Projects" leftSection={<IconBriefcase size={20} />} active={currentView === 'projects'} color="yellow" onClick={() => { setCurrentView('projects'); close(); }} />
            {user?.role === 'admin' && (
                <NavLink label="Register Staff" leftSection={<IconUserPlus size={20} />} active={currentView === 'signup'} color="yellow" onClick={() => { setCurrentView('signup'); close(); }} />
            )}
          </Box>
          <Button variant="subtle" color="gray" leftSection={<IconLogout size={18} />} onClick={handleLogout}>Logout</Button>
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <Container size="xl" pt="sm">
          {currentView === 'dashboard' && <Dashboard data={data} onNewProject={goToNewProject} />}
          {currentView === 'customers' && <Customers />}
          {currentView === 'projects' && <Projects />} 
          {currentView === 'signup' && <Signup onToggle={() => setCurrentView('dashboard')} />} 
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}

export default App;
