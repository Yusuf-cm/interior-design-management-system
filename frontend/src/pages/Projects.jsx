import React, { useState, useEffect } from 'react';
import { 
  Table, Badge, Group, Text, ActionIcon, Paper, Title, Button, 
  Modal, TextInput, Select, NumberInput, Stack, Progress, Box, Center, Loader
} from '@mantine/core';
import { IconPlus, IconPencil, IconBriefcase, IconCurrencyDollar, IconAlertCircle } from '@tabler/icons-react';
import { motion } from 'framer-motion';
import api from '../api';

const Projects = () => {
  const [projects, setProjects] = useState([]);
  const [customers, setCustomers] = useState([]); 
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  
  // Track if we are in "Edit" mode or "Create" mode
  const [isEditing, setIsEditing] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    id: null, 
    title: '',
    customer: '',
    status: 'PENDING',
    estimated_cost: 0,
    actual_payment_received: 0,
  });

  const fetchData = async () => {
    setFetching(true);
    try {
      // Fetch both Jobs and Customers (Customers needed for the dropdown)
      const [jobsRes, custRes] = await Promise.all([
        api.get('jobs/'),
        api.get('customers/')
      ]);
      setProjects(jobsRes.data);
      // Format customers for the Mantine Select component
      setCustomers(custRes.data.map(c => ({ value: c.id.toString(), label: c.name })));
    } catch (err) { 
      console.error("Error fetching project data:", err); 
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Handle Create (POST) vs Update (PUT)
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isEditing) {
        // UPDATE existing record
        await api.put(`jobs/${formData.id}/`, formData);
      } else {
        // CREATE new record
        await api.post('jobs/', formData);
      }
      setOpened(false);
      fetchData(); // Refresh the list
    } catch (err) { 
        console.error("Submission failed:", err); 
    } finally { 
        setLoading(false); 
    }
  };

  // Prepare Modal for Editing (Locks Title & Client)
  const openEditModal = (project) => {
    setIsEditing(true);
    setFormData({
      id: project.id,
      title: project.title,
      customer: project.customer.toString(),
      status: project.status,
      estimated_cost: parseFloat(project.estimated_cost),
      actual_payment_received: parseFloat(project.actual_payment_received),
    });
    setOpened(true);
  };

  // Prepare Modal for Creating (Clean form)
  const openCreateModal = () => {
    setIsEditing(false);
    setFormData({
      id: null,
      title: '',
      customer: '',
      status: 'PENDING',
      estimated_cost: 0,
      actual_payment_received: 0,
    });
    setOpened(true);
  };

  const getStatusColor = (status) => {
    const colors = {
      'ACTIVE': 'orange',
      'COMPLETED': 'green',
      'CANCELLED': 'red',
      'PENDING': 'gray'
    };
    return colors[status] || 'gray';
  };

  if (fetching) return <Center h={400}><Loader color="yellow" type="dots" /></Center>;

  const rows = projects.map((project) => {
    // Calculate progress percentage
    const progress = project.estimated_cost > 0 
      ? (project.actual_payment_received / project.estimated_cost) * 100 
      : 0;
    
    return (
      <Table.Tr key={project.id}>
        <Table.Td>
          <Box>
            <Text fw={700} size="sm">{project.title}</Text>
            <Text size="xs" c="dimmed">{project.customer_name}</Text>
          </Box>
        </Table.Td>
        <Table.Td>
          <Badge color={getStatusColor(project.status)} variant="light" radius="sm">
            {project.status}
          </Badge>
        </Table.Td>
        <Table.Td style={{ minWidth: '180px' }}>
          <Group justify="space-between" mb={5}>
            <Text size="xs" fw={700}>${project.actual_payment_received} / ${project.estimated_cost}</Text>
            <Text size="xs" c="dimmed">{Math.round(progress)}%</Text>
          </Group>
          <Progress 
            value={progress} 
            color={progress >= 100 ? 'green' : 'yellow'} 
            size="sm" 
            radius="xl" 
            animated={project.status === 'ACTIVE'}
          />
        </Table.Td>
        <Table.Td>
          <Text size="xs" fw={700} c={project.remaining_balance > 0 ? 'red.7' : 'green.7'}>
            {project.remaining_balance > 0 ? `Owed: $${project.remaining_balance}` : 'Settled'}
          </Text>
        </Table.Td>
        <Table.Td>
          <ActionIcon variant="subtle" color="blue" onClick={() => openEditModal(project)}>
            <IconPencil size={18} /> 
          </ActionIcon>
        </Table.Td>
      </Table.Tr>
    );
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <Group justify="space-between" mb="xl">
        <Title order={2} style={{ fontFamily: 'Playfair Display' }}>Project Ledger</Title>
        <Button 
          leftSection={<IconPlus size={18} />} 
          color="dark" 
          radius="xl" 
          onClick={openCreateModal}
        >
          Launch Project
        </Button>
      </Group>

      <Paper p="md" radius="lg" withBorder style={{ background: 'rgba(255,255,255,0.5)', backdropFilter: 'blur(10px)' }}>
        {projects.length > 0 ? (
          <Table verticalSpacing="md" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Project & Client</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Financial Progress</Table.Th>
                <Table.Th>Balance</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>{rows}</Table.Tbody>
          </Table>
        ) : (
          <Center py={50}>
            <Stack align="center" gap="xs">
              <IconBriefcase size={40} color="gray" />
              <Text c="dimmed">No projects recorded yet. Launch your first one!</Text>
            </Stack>
          </Center>
        )}
      </Paper>

      <Modal 
        opened={opened} 
        onClose={() => setOpened(false)} 
        title={isEditing ? "Update Project Progress" : "New Project Specification"} 
        centered 
        radius="lg"
        overlayProps={{ backgroundOpacity: 0.55, blur: 3 }}
      >
        <form onSubmit={handleSubmit}>
          <Stack>
            {/* Title: Permanent after creation */}
            <TextInput 
              label="Project Title" 
              placeholder="e.g. Modern Villa Interior" 
              required 
              value={formData.title} 
              disabled={isEditing} 
              onChange={(e) => setFormData({...formData, title: e.target.value})} 
            />
            
            {/* Client: Permanent after creation */}
            <Select 
              label="Assign Client" 
              placeholder="Select from registry" 
              data={customers} 
              required
              value={formData.customer}
              disabled={isEditing} 
              onChange={(val) => setFormData({...formData, customer: val})} 
            />
            
            <Select 
              label="Workflow Status" 
              data={['PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED']} 
              value={formData.status}
              onChange={(val) => setFormData({...formData, status: val})} 
            />
            
            <Group grow>
              <NumberInput 
                label="Contract Value ($)" 
                hideControls 
                min={0}
                value={formData.estimated_cost}
                onChange={(val) => setFormData({...formData, estimated_cost: val})} 
              />
              <NumberInput 
                label={isEditing ? "Payments to Date ($)" : "Initial Deposit ($)"}
                hideControls 
                min={0}
                value={formData.actual_payment_received}
                onChange={(val) => setFormData({...formData, actual_payment_received: val})} 
              />
            </Group>

            {isEditing && (
                <Group gap="xs" p="xs" style={{ background: '#f8f9fa', borderRadius: '8px' }}>
                    <IconAlertCircle size={14} color="gray" />
                    <Text size="xs" c="dimmed">Title and Client are locked to maintain record integrity.</Text>
                </Group>
            )}

            <Button type="submit" color="yellow" fullWidth loading={loading} mt="md">
              {isEditing ? "Save Progress" : "Start Project"}
            </Button>
          </Stack>
        </form>
      </Modal>
    </motion.div>
  );
};

export default Projects;