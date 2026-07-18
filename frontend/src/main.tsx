import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import CreateRoomPage from './pages/CreateRoomPage'
import DraftRoomPage from './pages/DraftRoomPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CreateRoomPage />} />
        <Route path="/room/:token" element={<DraftRoomPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
