import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getToken } from "../api/client";

/** Wraps protected routes. An expired token is handled by the 401 check in api/client.ts. */
export function RequireAuth() {
  const location = useLocation();
  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
