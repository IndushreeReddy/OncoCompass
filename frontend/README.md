# OncoCompass Frontend

React SPA for the OncoCompass precision oncology platform.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Copy `.env.example` to `.env` and set your backend API URL:
```bash
cp .env.example .env
# Edit .env and set VITE_API_URL=http://localhost:8000 (or your backend URL)
```

3. Start development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

## Build

```bash
npm run build
```

The built files will be in the `dist/` directory.
