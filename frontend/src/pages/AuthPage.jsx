import { useState } from "react";
import LoginPage from "./LoginPage";
import RegisterPage from "./RegisterPage";

function AuthPage({ onLogin }) {
  const [type, setType] = useState("signIn");

  const handleOnClick = (text) => {
    if (text !== type) {
      setType(text);
    }
  };

  const containerClass =
    "container " + (type === "signUp" ? "right-panel-active" : "");

  return (
    <div className="login-page">
      <div className={containerClass} id="container">
        <LoginPage onLogin={onLogin} />
        <RegisterPage onLogin={onLogin} />

        <div className="overlay-container">
          <div className="overlay">
            <div className="overlay-panel overlay-left">
              <h1>Bem-vindo de volta!</h1>
              <p>
                Para manter-se conectado connosco, por favor inicie sessão com
                as suas credenciais AI4Juris.
              </p>
              <button
                className="ghost"
                id="signIn"
                onClick={() => handleOnClick("signIn")}
              >
                Iniciar sessão
              </button>
            </div>
            <div className="overlay-panel overlay-right">
              <h1>Olá, bem-vindo ao AI4Juris</h1>
              <p>
                Carregue acórdãos e outros documentos legais e obtenha
                classificações automáticas e explicações compreensíveis,
                suportadas por IA.
              </p>
              <button
                className="ghost"
                id="signUp"
                onClick={() => handleOnClick("signUp")}
              >
                Criar conta
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="login-footer-tagline">
          Projeto de Gestão de Projetos — AI4Juris · DEI · FCTUC · 2025
      </div>
    </div>
  );
}

export default AuthPage;
