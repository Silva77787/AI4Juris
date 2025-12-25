import React from "react";
import { useNavigate } from "react-router-dom";
import { config } from "../utils/config";
function RegisterPage({ showToast }) {
  const navigate = useNavigate();
  const [state, setState] = React.useState({ name: "", email: "", password: "", confirmPassword: "" });

  const handleChange = (evt) => {
    setState({ ...state, [evt.target.name]: evt.target.value });
  };

  const setPendingToast = (message, type = "success") => {
    localStorage.setItem("pendingToast", JSON.stringify({ message, type, ts: Date.now() }));
  };

  const handleOnSubmit = async (evt) => {
    evt.preventDefault();

    if (!state.name || !state.email || !state.password || !state.confirmPassword) {
      showToast("Todos os campos sao obrigatorios", "error");
      return;
    }

    if (state.password !== state.confirmPassword) {
      showToast("As passwords nao coincidem", "error");
      return;
    }

    try {
      const response = await fetch(`${config.apiUrl}/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: state.name,
          email: state.email,
          password: state.password,
          confirm_password: state.confirmPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showToast(data.error || "Erro ao criar conta", "error");
        return;
      }

      localStorage.setItem("accessToken", data.tokens.access);
      localStorage.setItem("refreshToken", data.tokens.refresh);

      setState({ name: "", email: "", password: "", confirmPassword: "" });
      setPendingToast("Conta criada com sucesso!", "success");
      navigate("/home");
    } catch (err) {
      console.error(err);
      showToast("Erro ao registar utilizador", "error");
    }
  };

  return (
    <div className="form-container sign-up-container">
      <form onSubmit={handleOnSubmit}>
        <h1>Criar conta</h1>
        <p className="login-subtitle">Cria o teu acesso ao AI4Juris</p>
        <input type="text" name="name" value={state.name} onChange={handleChange} placeholder="Nome" />
        <input type="email" name="email" value={state.email} onChange={handleChange} placeholder="Email" />
        <input type="password" name="password" value={state.password} onChange={handleChange} placeholder="Palavra-passe" />
        <input
          type="password"
          name="confirmPassword"
          value={state.confirmPassword}
          onChange={handleChange}
          placeholder="Repetir palavra-passe"
        />
        <button type="submit">Criar conta</button>
      </form>
    </div>
  );
}

export default RegisterPage;
