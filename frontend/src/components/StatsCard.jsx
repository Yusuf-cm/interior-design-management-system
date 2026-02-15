import { Paper, Text, Group, Box, ThemeIcon } from '@mantine/core';
import { motion } from 'framer-motion';

const StatsCard = ({ title, value, icon: Icon, color, delay }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: delay }}
      whileHover={{ scale: 1.03, rotate: 1 }}
    >
      <Paper
        p="xl"
        radius="lg"
        style={{
          background: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.3)',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.07)',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {/* Subtle Decorative Background Circle */}
        <Box
          style={{
            position: 'absolute',
            top: -10,
            right: -10,
            width: 80,
            height: 80,
            background: `var(--mantine-color-${color}-light)`,
            borderRadius: '50%',
            opacity: 0.4,
            filter: 'blur(20px)'
          }}
        />

        <Group justify="space-between" align="flex-start">
          <div>
            <Text size="xs" fw={700} c="dimmed" tt="uppercase" lts={1.5}>
              {title}
            </Text>
            <Text size="32px" fw={800} mt={5} style={{ fontFamily: 'Playfair Display, serif' }}>
              {value}
            </Text>
          </div>
          <ThemeIcon size={48} radius="md" variant="gradient" gradient={{ from: color, to: 'gray', deg: 45 }}>
            <Icon size="1.5rem" stroke={1.5} />
          </ThemeIcon>
        </Group>
      </Paper>
    </motion.div>
  );
};

export default StatsCard;