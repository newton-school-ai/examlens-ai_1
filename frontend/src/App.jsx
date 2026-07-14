import GoogleLoginButton from "./components/GoogleLoginButton";
import { useAuth } from "./contexts/AuthContext";

export default function App() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Milestone 1 · ExamLens AI</p>
        <h1>Question-paper ingestion, ready for review.</h1>
        <p className="lede">
          Sign in to access the authenticated upload and exam-management API.
          Interactive API documentation is available at port 8000.
        </p>
        {isAuthenticated ? (
          <div className="session">
            <div>
              <strong>{user?.full_name || user?.email}</strong>
              <span>{user?.role}</span>
            </div>
            <button type="button" onClick={logout}>Sign out</button>
          </div>
        ) : (
          <GoogleLoginButton />
        )}
        <a className="docs" href="http://localhost:8000/docs">
          Open FastAPI documentation →
        </a>
      </section>
    </main>
  );
}
