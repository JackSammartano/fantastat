import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { IS_STATIC } from "../api/client";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/current-list", label: "Listone 26/27" },
  { to: "/compare", label: "Confronto" },
  { to: "/rankings", label: "Classifiche" },
  ...(!IS_STATIC ? [{ to: "/mappings", label: "Revisioni" }] : [])
];

export function AppShell() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="app-shell">
      <aside className={`sidebar${isMobileMenuOpen ? " sidebar--open" : ""}`}>
        <button
          type="button"
          className="brand"
          aria-label={isMobileMenuOpen ? "Chiudi menu" : "Apri menu"}
          aria-expanded={isMobileMenuOpen}
          aria-controls="main-navigation"
          onClick={() => setIsMobileMenuOpen((isOpen) => !isOpen)}
        >
          <span className="brand__mark">FL</span>
          <span className="brand__text">
            <strong>FantaLab</strong>
            <span>Asta 26/27</span>
          </span>
        </button>
        <nav id="main-navigation" aria-label="Navigazione principale">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link--active" : ""}`
              }
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__footer">
          <span className="status-dot" />
          Dati locali
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
