import { Routes, Route, NavLink } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import SetupGuidePage from "./pages/SetupGuidePage";
import ArchitecturePage from "./pages/ArchitecturePage";

function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? "bg-copilot-600 text-white"
        : "text-gray-600 hover:bg-gray-200"
    }`;

  return (
    <header className="bg-white border-b shadow-sm">
      <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🤖</span>
          <h1 className="text-lg font-bold text-gray-800">
            Ask HR{" "}
            <span className="text-copilot-600">Copilot Studio</span>
          </h1>
          <span className="text-xs bg-copilot-100 text-copilot-700 px-2 py-0.5 rounded-full font-medium">
            Agent
          </span>
        </div>
        <nav className="flex gap-2">
          <NavLink to="/" className={linkClass}>
            Chat
          </NavLink>
          <NavLink to="/setup" className={linkClass}>
            Setup Guide
          </NavLink>
          <NavLink to="/architecture" className={linkClass}>
            Architecture
          </NavLink>
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/setup" element={<SetupGuidePage />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
        </Routes>
      </main>
    </div>
  );
}
