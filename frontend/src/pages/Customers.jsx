import React, { useState, useEffect } from 'react';
import { 
  Table, ScrollArea, UnstyledButton, Group, Text, Center, 
  TextInput, Button, Modal, Stack, ActionIcon, Paper, Title
} from '@mantine/core';
import { IconSearch, IconPlus, IconTrash, IconPhone, IconMail } from '@tabler/icons-react';
import { motion } from 'framer-motion';
import api from '../api';

const Customers = () => {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState('');
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Form State
  const [formData, setFormData] = useState({ name: '', email: '', phone: '', address: '' });

  const fetchCustomers = async () => {
    try {
      setError('');
      const res = await api.get(`customers/?search=${search}`);
      setCustomers(res.data);
    } catch (err) {
      console.error(err);
      setError('Could not load customers. Please try again.');
    }
  };

  useEffect(() => { fetchCustomers(); }, [search]);

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.post('customers/', formData);
      setOpened(false);
      setFormData({ name: '', email: '', phone: '', address: '' });
      fetchCustomers();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.email?.[0] || 'Could not save the customer.');
    }
    finally { setLoading(false); }
  };

  const handleDeleteCustomer = async (customer) => {
    if (!window.confirm(`Delete ${customer.name}? This cannot be undone.`)) return;
    try {
      setError('');
      await api.delete(`customers/${customer.id}/`);
      setCustomers((current) => current.filter((item) => item.id !== customer.id));
    } catch (err) {
      console.error(err);
      setError('Could not delete this customer. They may still be linked to project records.');
    }
  };

  const rows = customers.map((customer) => (
    <Table.Tr key={customer.id} style={{ cursor: 'pointer' }}>
      <Table.Td>
        <Text fw={700} size="sm">{customer.name}</Text>
      </Table.Td>
      <Table.Td>
        <Group gap="xs"><IconMail size={14} /><Text size="xs">{customer.email}</Text></Group>
      </Table.Td>
      <Table.Td>
        <Group gap="xs"><IconPhone size={14} /><Text size="xs">{customer.phone}</Text></Group>
      </Table.Td>
      <Table.Td>
        <Text size="xs" c="dimmed" truncate>{customer.address}</Text>
      </Table.Td>
      <Table.Td>
        <ActionIcon
          variant="subtle"
          color="red"
          aria-label={`Delete ${customer.name}`}
          onClick={() => handleDeleteCustomer(customer)}
        >
          <IconTrash size={16} />
        </ActionIcon>
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <Group justify="space-between" mb="xl">
        <Title order={2} style={{ fontFamily: 'Playfair Display' }}>Client Registry</Title>
        <Button leftSection={<IconPlus size={18} />} color="dark" radius="xl" onClick={() => setOpened(true)}>
          Add Customer
        </Button>
      </Group>

      {error && <Text c="red" size="sm" mb="md">{error}</Text>}
      <Paper p="md" radius="lg" withBorder style={{ background: 'rgba(255,255,255,0.5)', backdropFilter: 'blur(10px)' }}>
        <TextInput
          placeholder="Search by name, email or phone..."
          mb="md"
          leftSection={<IconSearch size={16} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          radius="md"
        />

        <ScrollArea>
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Email</Table.Th>
                <Table.Th>Phone</Table.Th>
                <Table.Th>Address</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>{rows}</Table.Tbody>
          </Table>
        </ScrollArea>
      </Paper>

      {/* Add Customer Modal */}
      <Modal opened={opened} onClose={() => setOpened(false)} title="Register New Client" centered radius="lg">
        <form onSubmit={handleAddCustomer}>
          <Stack>
            <TextInput label="Full Name" required value={formData.name} onChange={(e)=>setFormData({...formData, name: e.target.value})} />
            <TextInput label="Email" required value={formData.email} onChange={(e)=>setFormData({...formData, email: e.target.value})} />
            <TextInput label="Phone" required value={formData.phone} onChange={(e)=>setFormData({...formData, phone: e.target.value})} />
            <TextInput label="Address" value={formData.address} onChange={(e)=>setFormData({...formData, address: e.target.value})} />
            <Button type="submit" color="yellow" fullWidth loading={loading} mt="md">Save Customer</Button>
          </Stack>
        </form>
      </Modal>
    </motion.div>
  );
};

export default Customers;