import { Outlet } from "react-router-dom";
import { Sidebar } from "./ui/Sidebar";

export function Layout() {
  return (
    <div className="shell">
      <Sidebar />
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
