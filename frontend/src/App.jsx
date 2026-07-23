import GoogleLoginButton from "./components/GoogleLoginButton";
import { useAuth } from "./contexts/AuthContext";

export default function App() {
  const { isAuthLoading, isAuthenticated, logout, user } = useAuth();

  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Milestone 1 · ExamLens AI</p>
        <h1>Question-paper ingestion, ready for review.</h1>
        <p className="lede">
          Sign in to access the authenticated upload and exam-management API.
          Interactive API documentation is available at port 8000.
        </p>
        {isAuthLoading ? (
          <div className="session">
            <div>
              <strong>Restoring session</strong>
              <span>Please wait</span>
            </div>
          </div>
        ) : isAuthenticated ? (
          <div className="session">
            {user?.avatar_url && (
              <img
                className="avatar"
                src={user.avatar_url}
                alt=""
                referrerPolicy="no-referrer"
              />
            )}
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
