import React, { useState } from 'react';
import { 
  Paper, TextInput, PasswordInput, Button, Title, Text, 
  Container, Stack, Select, Group 
} from '@mantine/core';
import { motion } from 'framer-motion';
import api from '../api';

const RegisterStaff = ({ onToggle }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'staff', // Default role
    phone_number: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      // Sending data to Django
      await api.post('accounts/register/', formData);
      alert('Staff Member Registered Successfully!');
      onToggle(); // Return to dashboard
    } catch (err) {
      // This helps us see exactly what Django is complaining about
      const backendError = err.response?.data;
      if (backendError) {
        // Show the first specific error found (e.g. "Username already exists")
        const firstErrorKey = Object.keys(backendError)[0];
        setError(`${firstErrorKey}: ${backendError[firstErrorKey][0]}`);
      } else {
        setError('Registration failed. Please check your connection.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size={420} my={40}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <Paper radius="md" p="xl" withBorder style={{ background: 'rgba(255,255,255,0.5)', backdropFilter: 'blur(10px)' }}>
          <Title order={2} ta="center" mb="md" style={{ fontFamily: 'Playfair Display' }}>
            Register New Staff
          </Title>
          
          <form onSubmit={handleRegister}>
            <Stack>
              <TextInput 
                label="Username" 
                placeholder="Unique username" 
                required 
                value={formData.username}
                onChange={(e) => setFormData({...formData, username: e.target.value})}
              />
              
              <TextInput 
                label="Email Address" 
                placeholder="staff@studio.com" 
                required 
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />

              <Select 
                label="System Role" 
                data={[
                  { value: 'admin', label: 'Admin (Full Access)' },
                  { value: 'staff', label: 'Staff (Project Access)' }
                ]}
                value={formData.role}
                onChange={(val) => setFormData({...formData, role: val})}
              />

              <TextInput 
                label="Phone Number" 
                placeholder="+1 234 567 890" 
                value={formData.phone_number}
                onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
              />

              <PasswordInput 
                label="Temporary Password" 
                placeholder="Enter password" 
                required 
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
              />

              {error && <Text color="red" size="xs" fw={700}>{error}</Text>}

              <Button type="submit" fullWidth mt="md" color="dark" loading={loading} radius="xl">
                Create Account
              </Button>
              
              <Button variant="subtle" color="gray" onClick={onToggle}>
                Cancel
              </Button>
            </Stack>
          </form>
        </Paper>
      </motion.div>
    </Container>
  );
};

export default RegisterStaff;