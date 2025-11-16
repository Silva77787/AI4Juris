import React from "react";
import { useNavigate } from "react-router-dom";

function RegisterPage({ showToast }) {
  const navigate = useNavigate();
  const [state, setState] = React.useState({ name: "", email: "", password: "" });

  const handleChange = (evt) => {
    setState({ ...state, [evt.target.name]: evt.target.value });
  };

  const handleOnSubmit = async (evt) => {
    evt.preventDefault();

    if (!state.name || !state.email || !state.password) {
      showToast("Todos os campos são obrigatórios", "error");
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/register/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });

      const data = await response.json();

      if (!response.ok) {
        showToast(data.error || "Erro ao criar conta", "error");
        return;
      }

      // Guardar tokens
      localStorage.setItem("accessToken", data.tokens.access);
      localStorage.setItem("refreshToken", data.tokens.refresh);

      setState({ name: "", email: "", password: "" });
      showToast("Conta criada com sucesso!", "success");

      setTimeout(() => navigate("/home"), 1000);
    } catch (err) {
      console.error(err);
      showToast("Erro ao registrar utilizador", "error");
    }
  };

  return (
    <div className="form-container sign-up-container">
      <form onSubmit={handleOnSubmit}>
        <h1>Criar conta</h1>
        <p className="login-subtitle">Crie o seu acesso ao AI4Juris</p>
        <input type="text" name="name" value={state.name} onChange={handleChange} placeholder="Nome" />
        <input type="email" name="email" value={state.email} onChange={handleChange} placeholder="Email" />
        <input type="password" name="password" value={state.password} onChange={handleChange} placeholder="Palavra-passe" />
        <button type="submit">Criar conta</button>
      </form>
    </div>
  );
}

export default RegisterPage;
