import React, { useEffect, useState } from "react";

function Toast({ message, type = "success", duration = 3000, onClose }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(true);

    const timer = setTimeout(() => {
      setVisible(false);
      if (onClose) onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!message) return null;

  const bgColor = type === "success" ? "green" : "red";

  return (
    <div
      style={{
        position: "fixed",
        top: "20px",
        left: "50%",
        transform: "translateX(-50%)",
        padding: "15px 20px",
        backgroundColor: bgColor,
        color: "white",
        borderRadius: "5px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
        fontWeight: "bold",
        minWidth: "250px",
        textAlign: "center",
        opacity: visible ? 1 : 0,
        transition: "opacity 0.3s ease-in-out",
        zIndex: 1000,
      }}
    >
      {message}
    </div>
  );
}

export default Toast;
