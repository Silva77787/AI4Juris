import React, { useState } from "react";
import LoginPage from "./LoginPage.jsx";
import RegisterPage from "./RegisterPage.jsx";
import DynamicToast from "../components/DynamicToast.jsx";

function AuthPage() {
  const [type, setType] = useState("signIn");
  const [toasts, setToasts] = useState([]);

  const handleOnClick = (text) => {
    if (text !== type) setType(text);
  };

  const containerClass = "container " + (type === "signUp" ? "right-panel-active" : "");

  const showToast = (message, type = "success") => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((prev) => {
      const next = [...prev, { id, message, type }];
      return next.slice(-5);
    });
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  };

  return (
    <div className="login-page">
      <div className={containerClass} id="container">
        <LoginPage showToast={showToast} />
        <RegisterPage showToast={showToast} />

        <div className="overlay-container">
          <div className="overlay">
            <div className="overlay-panel overlay-left">
              <h1>Bem-vindo de volta!</h1>
              <button className="ghost" id="signIn" onClick={() => handleOnClick("signIn")}>
                Iniciar sessao
              </button>
            </div>
            <div className="overlay-panel overlay-right">
              <h1>Ola, bem-vindo ao AI4Juris</h1>
              <button className="ghost" id="signUp" onClick={() => handleOnClick("signUp")}>
                Criar conta
              </button>
            </div>
          </div>
        </div>
      </div>

      <DynamicToast
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((toast) => toast.id !== id))}
      />
    </div>
  );
}

export default AuthPage;
