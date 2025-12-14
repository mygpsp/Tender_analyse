import { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Button,
} from '@mui/material'
import AssessmentIcon from '@mui/icons-material/Assessment'
import ListIcon from '@mui/icons-material/List'
import DashboardIcon from '@mui/icons-material/Dashboard'
import VisibilityIcon from '@mui/icons-material/Visibility'
import BusinessIcon from '@mui/icons-material/Business'
import DataUsageIcon from '@mui/icons-material/DataUsage'
import RateReviewIcon from '@mui/icons-material/RateReview'
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
    { path: '/tenders', label: 'Tenders', icon: <ListIcon /> },
    { path: '/analytics', label: 'Analytics', icon: <AssessmentIcon /> },
    { path: '/suppliers', label: 'Suppliers', icon: <BusinessIcon /> },
    { path: '/coverage', label: 'Coverage', icon: <DataUsageIcon /> },
    { path: '/data-review', label: 'Data Review', icon: <RateReviewIcon /> },
    { path: '/con-tenders', label: 'CON Tenders', icon: <DirectionsCarIcon /> },
    { path: '/market-analysis', label: 'Market Analysis', icon: <AssessmentIcon /> },
    { path: '/system-health', label: 'System Health', icon: <AssessmentIcon /> },
    { path: '/tender-viewer', label: 'Field Viewer', icon: <VisibilityIcon /> },
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Tender Analysis
          </Typography>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              sx={{
                ml: 1,
                backgroundColor:
                  location.pathname === item.path ? 'rgba(255,255,255,0.2)' : 'transparent',
              }}
            >
              {item.label}
            </Button>
          ))}
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flex: 1 }}>
        {children}
      </Container>
    </Box>
  )
}

