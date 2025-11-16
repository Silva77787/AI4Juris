import React, { useState } from "react";
import LoginPage from "./LoginPage.jsx";
import RegisterPage from "./RegisterPage.jsx";
import Toast from "../components/Toast.jsx";

function AuthPage() {
  const [type, setType] = useState("signIn");
  const [toast, setToast] = useState(null);

  const handleOnClick = (text) => {
    if (text !== type) setType(text);
  };

  const containerClass = "container " + (type === "signUp" ? "right-panel-active" : "");

  const showToast = (message, type = "success") => setToast({ message, type });

  return (
    <div className="login-page">
      <div className={containerClass} id="container">
        <LoginPage showToast={showToast} />
        <RegisterPage showToast={showToast} />

        <div className="overlay-container">
          <div className="overlay">
            <div className="overlay-panel overlay-left">
              <h1>Bem-vindo de volta!</h1>
              <button className="ghost" id="signIn" onClick={() => handleOnClick("signIn")}>Iniciar sessão</button>
            </div>
            <div className="overlay-panel overlay-right">
              <h1>Olá, bem-vindo ao AI4Juris</h1>
              <button className="ghost" id="signUp" onClick={() => handleOnClick("signUp")}>Criar conta</button>
            </div>
          </div>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

export default AuthPage;
