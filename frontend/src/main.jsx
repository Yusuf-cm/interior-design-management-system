import React from 'react'
import ReactDOM from 'react-dom/client'
import { MantineProvider, createTheme } from '@mantine/core';
import '@mantine/core/styles.css'; // This is the core CSS
import App from './App.jsx'

const theme = createTheme({
  primaryColor: 'gold',
  colors: {
    // Custom luxury gold palette
    gold: [
      '#fcf8ec', '#f4eed7', '#e9ddae', '#decb81', '#d5bc5b', 
      '#cfb244', '#ccad37', '#b4982a', '#a08722', '#8b7416'
    ],
  },
  fontFamily: 'Inter, sans-serif',
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <MantineProvider theme={theme}>
      <App />
    </MantineProvider>
  </React.StrictMode>,
)