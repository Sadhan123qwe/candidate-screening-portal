import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate, type Location } from "react-router-dom";
import { useLogin } from "../api/auth";
import { getToken } from "../api/client";
import { ErrorNotice, Field } from "../components/FormParts";
import { validateEmail, withoutEmptyErrors, type FieldErrors } from "../lib/validation";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [clientErrors, setClientErrors] = useState<FieldErrors>({});

  // Return the user to the page they originally asked for.
  const destination = (location.state as { from?: Location } | null)?.from?.pathname ?? "/applications";

  if (getToken() && !login.isPending) {
    return <Navigate to={destination} replace />;
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const errors = withoutEmptyErrors({
      email: validateEmail(email),
      password: password ? undefined : "Password is required.",
    });
    setClientErrors(errors);
    if (Object.keys(errors).length > 0) return;

    login.mutate({ email, password }, { onSuccess: () => navigate(destination, { replace: true }) });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="card w-full max-w-sm p-6">
        <h1 className="text-lg font-semibold text-gray-900">Candidate Screening Portal</h1>
        <p className="mb-5 mt-1 text-sm text-gray-600">Sign in to review applications.</p>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <Field id="login-email" label="Email" error={clientErrors.email}>
            <input id="login-email" type="email" autoComplete="username" className="input" value={email} onChange={(event) => setEmail(event.target.value)} />
          </Field>
          <Field id="login-password" label="Password" error={clientErrors.password}>
            <input id="login-password" type="password" autoComplete="current-password" className="input" value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
          <ErrorNotice message={login.error?.message} />
          <button type="submit" className="btn-primary w-full" disabled={login.isPending}>
            {login.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
