import React from "react";
import { useNavigate } from "react-router-dom";

function RegisterPage({ onLogin }) {
  const navigate = useNavigate();
  const [state, setState] = React.useState({
    name: "",
    email: "",
    password: ""
  });

  const handleChange = (evt) => {
    const value = evt.target.value;
    setState({
      ...state,
      [evt.target.name]: value
    });
  };

  const handleOnSubmit = (evt) => {
    evt.preventDefault();

    // FRONTEND ONLY: registo “fake”, sem chamar API
    console.log("Register submit (frontend only):", state);

    if (onLogin) {
      onLogin("fake-token");
    }

    // se não quiseres ir para o dashboard, remove esta linha
    navigate("/dashboard");

    setState({ name: "", email: "", password: "" });
  };

  return (
    <div className="form-container sign-up-container">
      <form onSubmit={handleOnSubmit}>
        <h1>Criar conta</h1>
        <p className="login-subtitle">Crie o seu acesso ao AI4Juris</p>
        <input
          type="text"
          name="name"
          value={state.name}
          onChange={handleChange}
          placeholder="Nome"
        />
        <input
          type="email"
          name="email"
          value={state.email}
          onChange={handleChange}
          placeholder="Email"
        />
        <input
          type="password"
          name="password"
          value={state.password}
          onChange={handleChange}
          placeholder="Palavra-passe"
        />
        <button type="submit">Criar conta</button>
      </form>
    </div>
  );
}

export default RegisterPage;
