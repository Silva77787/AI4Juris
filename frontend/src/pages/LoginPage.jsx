import React from "react";
import { useNavigate } from "react-router-dom";
import { config } from "../utils/config";
function LoginPage({ showToast }) {
  const navigate = useNavigate();
  const [state, setState] = React.useState({ email: "", password: "" });

  const handleChange = (evt) => {
    setState({ ...state, [evt.target.name]: evt.target.value });
  };

  const setPendingToast = (message, type = "success") => {
    localStorage.setItem("pendingToast", JSON.stringify({ message, type, ts: Date.now() }));
  };

  const handleOnSubmit = async (evt) => {
    evt.preventDefault();

    if (!state.email || !state.password) {
      showToast("Email e password sao obrigatorios", "error");
      return;
    }

    try {
      const response = await fetch(`${config.apiUrl}/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });

      const data = await response.json();

      if (!response.ok) {
        showToast(data.error || "Credenciais invalidas", "error");
        return;
      }

      localStorage.setItem("accessToken", data.tokens.access);
      localStorage.setItem("refreshToken", data.tokens.refresh);

      setPendingToast("Login efetuado com sucesso!", "success");
      setState({ email: "", password: "" });
      navigate("/home");
    } catch (err) {
      console.error(err);
      showToast("Erro ao fazer login", "error");
    }
  };

  return (
    <div className="form-container sign-in-container">
      <form onSubmit={handleOnSubmit}>
        <h1>Entrar</h1>
        <p className="login-subtitle">Acede a plataforma AI4Juris</p>
        <input type="email" name="email" value={state.email} onChange={handleChange} placeholder="Email" />
        <input type="password" name="password" value={state.password} onChange={handleChange} placeholder="Palavra-passe" />
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}

export default LoginPage;
