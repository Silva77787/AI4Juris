import React from "react";
import { useNavigate } from "react-router-dom";

function LoginPage({ showToast }) {
  const navigate = useNavigate();
  const [state, setState] = React.useState({ email: "", password: "" });

  const handleChange = (evt) => {
    setState({ ...state, [evt.target.name]: evt.target.value });
  };

  const handleOnSubmit = async (evt) => {
    evt.preventDefault();

    if (!state.email || !state.password) {
      showToast("Email e password são obrigatórios", "error");
      return;
    }

    try {
      const response = await fetch("http://localhost:7777/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });

      const data = await response.json();

      if (!response.ok) {
        showToast(data.error || "Credenciais inválidas", "error");
        return;
      }

      // Guardar tokens
      localStorage.setItem("accessToken", data.tokens.access);
      localStorage.setItem("refreshToken", data.tokens.refresh);

      showToast("Login efetuado com sucesso!", "success");

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
        <p className="login-subtitle">Aceda à plataforma AI4Juris</p>
        <input type="email" name="email" value={state.email} onChange={handleChange} placeholder="Email" />
        <input type="password" name="password" value={state.password} onChange={handleChange} placeholder="Palavra-passe" />
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}

export default LoginPage;
