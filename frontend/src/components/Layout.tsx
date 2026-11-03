import { useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCurrentUser } from "../api/auth";
import { clearToken } from "../api/client";

const NAV_LINKS = [
  { to: "/applications", label: "Applications" },
  { to: "/jobs", label: "Jobs" },
  { to: "/candidates", label: "Candidates" },
  { to: "/model", label: "Model" },
];

export function Layout() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  function logOut() {
    clearToken();
    // The next user on this browser must not see this user's cached data.
    queryClient.clear();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <div className="flex flex-wrap items-center gap-6">
            <span className="font-semibold text-gray-900">Candidate Screening</span>
            <nav className="flex flex-wrap gap-1">
              {NAV_LINKS.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-1.5 text-sm font-medium ${
                      isActive ? "bg-accent-50 text-accent-700" : "text-gray-600 hover:bg-gray-100"
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span>{user.data?.full_name}</span>
            <button type="button" className="btn-secondary py-1" onClick={logOut}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
