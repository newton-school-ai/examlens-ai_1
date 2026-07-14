import { useState } from "react";
import { useGoogleLogin } from "@react-oauth/google";

import { useAuth } from "../contexts/AuthContext";

export default function GoogleLoginButton() {
  const { login } = useAuth();
  const [error, setError] = useState("");
  const googleLogin = useGoogleLogin({
    flow: "auth-code",
    onSuccess: async ({ code }) => {
      try {
        setError("");
        await login(code);
      } catch (loginError) {
        setError(loginError.message);
      }
    },
    onError: () => setError("Google sign-in was cancelled or failed"),
  });

  return (
    <div>
      <button type="button" onClick={() => googleLogin()}>
        Sign in with Google
      </button>
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
