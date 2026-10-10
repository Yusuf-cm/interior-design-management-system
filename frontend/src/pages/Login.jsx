import React, { useState } from 'react';
import { Paper, TextInput, PasswordInput, Button, Title, Text, Container } from '@mantine/core';
import { motion } from 'framer-motion';
import api from '../api';

const Login = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post('accounts/login/', { username, password });
      localStorage.setItem('access_token', res.data.access);
      localStorage.setItem('refresh_token', res.data.refresh);
      onLoginSuccess();
    } catch (err) {
      setError(err.response?.status === 401 ? 'The username or password is incorrect.' : 'The studio service is unavailable. Please try again shortly.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: 'radial-gradient(ellipse at top left, #343b33, #161d1b 65%)', minHeight: '100svh', padding: '32px 16px', display: 'flex', alignItems: 'center' }}>
      <Container size={460} w="100%">
        <Text c="gray.4" size="xs" fw={600} ta="center" mb={20} style={{ letterSpacing: "0.18em" }}>THE STUDIO WORKSPACE</Text>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Paper radius="lg" p="xl" withBorder style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.1)' }}>
            <Title order={2} c="white" ta="center" style={{ fontFamily: 'Playfair Display' }}>
              STUDIO.<Text span c="yellow.5">OS</Text>
            </Title>
            <Text c="dimmed" size="sm" ta="center" mt={5} mb={30}>A clear view of your clients, projects, and progress.</Text>

            <form onSubmit={handleLogin}>
              <TextInput 
                label={<Text c="gray.5" size="xs" fw={700}>USERNAME</Text>}
                autoComplete="username"
                placeholder="Your username" 
                required 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                styles={{ input: { background: 'rgba(255,255,255,0.05)', color: 'white', border: 'none' } }}
              />
              <PasswordInput 
                label={<Text c="gray.5" size="xs" fw={700} mt="md">PASSWORD</Text>}
                autoComplete="current-password"
                placeholder="Your password" 
                required 
                mt="md" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                styles={{ input: { background: 'rgba(255,255,255,0.05)', color: 'white', border: 'none' } }}
              />
              {error && <Text role="alert" c="red.4" size="sm" mt="sm">{error}</Text>}
              <Button type="submit" fullWidth mt="xl" color="yellow" loading={loading} radius="md">
                Sign In
              </Button>
            </form>

            <Text c="gray.5" size="xs" ta="center" mt="xl">Access is provided by your studio administrator.</Text>
          </Paper>
        </motion.div>
      </Container>
    </div>
  );
};

export default Login;
