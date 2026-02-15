import React, { useState } from 'react';
import { Paper, TextInput, PasswordInput, Button, Title, Text, Container } from '@mantine/core';
import { motion } from 'framer-motion';
import api from '../api';

const Login = ({ onLoginSuccess, onToggleSignup }) => { // <--- FIXED: Added onToggleSignup here
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
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: '#1A1B1E', height: '100vh', display: 'flex', alignItems: 'center' }}>
      <Container size={420}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Paper radius="lg" p="xl" withBorder style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.1)' }}>
            <Title order={2} c="white" ta="center" style={{ fontFamily: 'Playfair Display' }}>
              STUDIO.<Text span c="yellow.5">OS</Text>
            </Title>
            <Text c="dimmed" size="sm" ta="center" mt={5} mb={30}>Enter your credentials to manage the studio.</Text>

            <form onSubmit={handleLogin}>
              <TextInput 
                label={<Text c="gray.5" size="xs" fw={700}>USERNAME</Text>}
                placeholder="Your username" 
                required 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                styles={{ input: { background: 'rgba(255,255,255,0.05)', color: 'white', border: 'none' } }}
              />
              <PasswordInput 
                label={<Text c="gray.5" size="xs" fw={700} mt="md">PASSWORD</Text>}
                placeholder="Your password" 
                required 
                mt="md" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                styles={{ input: { background: 'rgba(255,255,255,0.05)', color: 'white', border: 'none' } }}
              />
              {error && <Text color="red" size="sm" mt="sm">{error}</Text>}
              <Button type="submit" fullWidth mt="xl" color="yellow" loading={loading} radius="md">
                Sign In
              </Button>
            </form>

            {/* THE CLICK HANDLER THAT WAS CRASHING */}
          </Paper>
        </motion.div>
      </Container>
    </div>
  );
};

export default Login;