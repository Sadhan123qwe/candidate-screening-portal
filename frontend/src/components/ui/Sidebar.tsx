import { useQueryClient } from "@tanstack/react-query";
import { NavLink, useNavigate } from "react-router-dom";
import { useCurrentUser } from "../../api/auth";
import { clearToken } from "../../api/client";
import { GlassCard } from "./GlassCard";
import { ApplicationsIcon, CandidatesIcon, JobsIcon, ModelIcon } from "./icons";

const NAV_LINKS = [
  { to: "/applications", label: "Applications", icon: <ApplicationsIcon /> },
  { to: "/jobs", label: "Jobs", icon: <JobsIcon /> },
  { to: "/candidates", label: "Candidates", icon: <CandidatesIcon /> },
  { to: "/model", label: "Model", icon: <ModelIcon /> },
];

export function Brand() {
  return (
    <div className="brand">
      <span aria-hidden="true" className="brand-tile">
        CS
      </span>
      Screening Portal
    </div>
  );
}

export function Sidebar() {
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
    <GlassCard as="aside" padding="none" className="sidebar">
      <div className="pl-2 max-[899.98px]:pl-0">
        <Brand />
      </div>
      <nav aria-label="Main" className="nav-list">
        {NAV_LINKS.map((link) => (
          <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-item ${isActive ? "nav-item-active" : ""}`}>
            {link.icon}
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <p className="sidebar-footer-name font-medium">{user.data?.full_name}</p>
        <p className="sidebar-footer-email text-muted">{user.data?.email}</p>
        <button type="button" className="link mt-3 font-normal max-[899.98px]:mt-0" onClick={logOut}>
          Log out
        </button>
      </div>
    </GlassCard>
  );
}
