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
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">FL</span>
          <div>
            <strong>FantaLab</strong>
            <span>Asta 26/27</span>
          </div>
        </div>
        <nav aria-label="Navigazione principale">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link--active" : ""}`
              }
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
