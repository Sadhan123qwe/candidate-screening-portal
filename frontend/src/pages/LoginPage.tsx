import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate, type Location } from "react-router-dom";
import { useLogin } from "../api/auth";
import { ApiError, getToken } from "../api/client";
import { useStats } from "../api/stats";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Controls";
import { GlassCard } from "../components/ui/GlassCard";
import { Brand } from "../components/ui/Sidebar";
import { validateEmail, withoutEmptyErrors, type FieldErrors } from "../lib/validation";

const WRONG_CREDENTIALS_MESSAGE = "Wrong email or password. Check them and try again.";

function loginErrorMessage(error: Error | null): string | undefined {
  if (!error) return undefined;
  return error instanceof ApiError && error.code === "INVALID_CREDENTIALS" ? WRONG_CREDENTIALS_MESSAGE : error.message;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();
  const stats = useStats();
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
    <div className="login-page">
      <GlassCard padding="none" className="login-card">
        <section className="login-intro">
          <Brand />
          <div className="login-pitch">
            <p className="login-headline">Review applications. See the model's hint. Make the call.</p>
            <p className="login-support">
              Every application gets a Potential Match or Needs Review prediction from a trained model. Shortlisting and
              rejecting stay with you.
            </p>
          </div>
          <p className="login-stats">
            {stats.data && (
              <>
                <span>
                  <b className="num">{stats.data.jobs}</b> jobs
                </span>
                <span>
                  <b className="num">{stats.data.candidates}</b> candidates
                </span>
                <span>
                  <b className="num">{stats.data.applications}</b> applications
                </span>
              </>
            )}
          </p>
        </section>

        <section className="login-panel">
          <h1 className="page-title">Log in</h1>
          <p className="page-subtitle">Use your recruiter account.</p>
          <form onSubmit={handleSubmit} noValidate className="login-form">
            <Input
              id="login-email"
              label="Email"
              type="email"
              autoComplete="username"
              value={email}
              error={clientErrors.email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Input
              id="login-password"
              label="Password"
              type="password"
              autoComplete="current-password"
              value={password}
              error={clientErrors.password ?? loginErrorMessage(login.error)}
              onChange={(event) => setPassword(event.target.value)}
            />
            <Button type="submit" variant="primary" className="w-full" disabled={login.isPending}>
              {login.isPending ? "Logging in..." : "Log in"}
            </Button>
          </form>
          <div className="demo-box">
            <p className="text-muted">Demo account</p>
            <p className="num mt-0.5">recruiter@demo.com &middot; Demo@12345</p>
          </div>
        </section>
      </GlassCard>
    </div>
  );
}
