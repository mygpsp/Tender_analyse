# Tender Analysis Frontend

React + TypeScript frontend application for visualizing and analyzing tender data.

## Setup

cd frontend

1. Install dependencies:

```bash
npm install
```

2. Create a `.env` file (optional):

```
VITE_API_URL=http://localhost:8000
```

## Running

### Development

```bash
npm run dev
```

The application will be available at http://localhost:3000

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Features

- **Dashboard**: Overview statistics and recent tenders
- **Tenders List**: Browse all tenders with search and pagination
- **Analytics**: Visual charts and statistics
  - Tenders by buyer (bar chart)
  - Tenders by category (pie chart)
  - Timeline analysis (line chart)

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable components
│   │   └── Layout.tsx
│   ├── pages/          # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Tenders.tsx
│   │   └── Analytics.tsx
│   ├── services/       # API services
│   │   └── api.ts
│   ├── App.tsx         # Main app component
│   └── main.tsx        # Entry point
├── public/
├── package.json
└── vite.config.ts
```

## Technologies

- React 18
- TypeScript
- Material-UI (MUI)
- Recharts
- React Router
- Axios
- Vite
