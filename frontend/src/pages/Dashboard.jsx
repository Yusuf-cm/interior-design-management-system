import React from 'react';
import { Group, Title, Text, Button, SimpleGrid, Box, Stack, Paper } from '@mantine/core';
import { IconPlus, IconUsers, IconBriefcase, IconCurrencyDollar } from '@tabler/icons-react';
import { motion } from 'framer-motion';
import StatsCard from '../components/StatsCard';

const Dashboard = ({ data, onNewProject }) => {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <Group justify="space-between" mb={30} align="flex-end">
        <div>
          <Title order={1} style={{ fontFamily: 'Playfair Display', fontSize: 'clamp(24px, 5vw, 40px)' }}>
            Overview
          </Title>
          <Text c="dimmed" size="sm">Operational intelligence for your studio.</Text>
        </div>
        <Button 
          leftSection={<IconPlus size={18} />} 
          variant="filled" 
          color="dark" 
          radius="xl"
          onClick={onNewProject} // This now triggers the function in App.jsx
        >
          New Project
        </Button>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
        <StatsCard title="Clients" value={data?.metrics?.total_customers || 0} icon={IconUsers} color="blue" delay={0.1} />
        <StatsCard title="Active Jobs" value={data?.metrics?.active_jobs || 0} icon={IconBriefcase} color="orange" delay={0.2} />
        <StatsCard title="Revenue" value={`$${data?.financials?.total_revenue || 0}`} icon={IconCurrencyDollar} color="green" delay={0.3} />
      </SimpleGrid>

      <Box mt={40}>
        <Title order={3} mb="lg" style={{ fontFamily: 'Playfair Display' }}>Recent Activity</Title>
        <Stack spacing="sm">
          {data?.recent_activity?.length > 0 ? (
            data.recent_activity.map((job) => (
              <motion.div key={job.id} whileHover={{ x: 5 }}>
                <Paper p="md" radius="md" withBorder style={{ background: 'rgba(255,255,255,0.5)' }}>
                  <Group justify="space-between" wrap="nowrap">
                    <Box style={{ overflow: 'hidden' }}>
                      <Text fw={700} truncate>{job.title}</Text>
                      <Text size="xs" c="dimmed">{job.customer}</Text>
                    </Box>
                    <Box style={{ textAlign: 'right', minWidth: '80px' }}>
                      <Text size="xs" fw={700} c={job.status === 'ACTIVE' ? 'orange' : 'green'}>{job.status}</Text>
                      <Text size="xs" c="dimmed" visibleFrom="xs">{new Date(job.created_at).toLocaleDateString()}</Text>
                    </Box>
                  </Group>
                </Paper>
              </motion.div>
            ))
          ) : (
            <Text c="dimmed" ta="center" py="xl">No recent project activity found.</Text>
          )}
        </Stack>
      </Box>
    </motion.div>
  );
};

export default Dashboard;