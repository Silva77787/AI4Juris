import React from "react";
import { useNavigate } from "react-router-dom";

function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [state, setState] = React.useState({
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

    // FRONTEND ONLY: login “fake”, sem chamar API
    console.log("Login submit (frontend only):", state);

    if (onLogin) {
      onLogin("fake-token");
    }

    // se quiseres só o ecrã, podes remover esta linha
    navigate("/dashboard");

    setState({
      email: "",
      password: ""
    });
  };

  return (
    <div className="form-container sign-in-container">
      <form onSubmit={handleOnSubmit}>
        <h1>Entrar</h1>
        <p className="login-subtitle">Aceda à plataforma AI4Juris</p>
        <input
          type="email"
          placeholder="Email"
          name="email"
          value={state.email}
          onChange={handleChange}
        />
        <input
          type="password"
          name="password"
          placeholder="Palavra-passe"
          value={state.password}
          onChange={handleChange}
        />
        <a href="#">Esqueceu-se da palavra-passe?</a>
        <button type="submit">Entrar</button>
      </form>
    </div>
    
  );
}

export default LoginPage;
