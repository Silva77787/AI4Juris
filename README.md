# AI4Juris – Interface Web
Plataforma web para classificação automática de documentos jurídicos em português, com suporte a técnicas de IA Explicável (XAI).  
Este repositório contém o **frontend** desenvolvido em **React + Vite**.

---

## 🚀 Tecnologias utilizadas

- **React 18**
- **Vite**
- **JavaScript / JSX**
- **React Router**
- **Axios**
- **CSS / Styled Components (quando aplicável)**
- **Node.js + npm**

---

## 📦 Pré-requisitos

Antes de iniciar, certifique-se de que tem instalado:

- **Node.js** (>= 16)
- **npm**

---

## 🔧 Instalação

Clone o repositório:

```bash
git clone https://github.com/<teu-username>/<teu-repo>.git
```

Entre no diretório:

```bash
cd ai4juris-frontend
```

Instale as dependências:

```bash
npm install
```

---

## ▶️ Executar em modo de desenvolvimento

```bash
npm run dev
```

A aplicação ficará disponível em:

```
http://localhost:5173/
```

---

## 🏗️ Build para produção

```bash
npm run build
```

Os ficheiros finais serão gerados na pasta:

```
dist/
```

---

## 🧪 Pré-visualizar a build

```bash
npm run preview
```

---

## 📁 Estrutura principal do projeto

```
src/
 ├─ pages/
 │   ├─ LoginPage.jsx
 │   ├─ RegisterPage.jsx
 │   ├─ Dashboard.jsx
 │   └─ ...
 ├─ components/
 ├─ api/
 │   └─ api.js
 ├─ App.jsx
 ├─ main.jsx
 └─ styles.css
```
## 🐳 Executar o Projeto com Docker (Backend + Base de Dados)

O backend do AI4Juris (Django + PostgreSQL) pode ser executado completamente via **Docker**.

## ▶️ 1. Pré-requisitos

Certifique-se de que tem instalado:

- **Docker Desktop** (Windows / macOS) — *e que está ligado*

---

## ▶️ 2. Iniciar todos os serviços

No diretório onde está o `docker-compose.yml` (AI4Juris\backend) execute:

```bash
docker compose up --build
```

Este comando irá:

 - Iniciar o container django_app

 - Iniciar o container postgres_db

 - Criar volumes para guardar o estado da base de dados

 - Expor as portas necessárias para acesso ao backend e base dados
---

Quando quiserem terminar de trabalhar devem fazer ***docker compose down***


## ▶️ 3. Fazer migrações no Docker

Devem fazer migrações sempre que for alterado alguma coisa nos modelos para a base de dados (em models.py).
As migrações do Django **devem ser executadas dentro do container do Docker**, usando o nome do serviço definido no `docker-compose.yml`, que neste projeto é **web**.
Depois de fazerem **docker compose up --build** já podem fazer as migrações

### Entrar no container Django:

```bash
docker compose exec web bash
```

Depois sim fazem as migrações: ***python manage.py makemigrations*** e depois ***python manage.py migrate***
Para sairem da bash é so fazer exit.

No entanto se quiserem fazer alterações diretamente na base de dados ou apenas visualizar a base de dados diretamente podem fazer o seguinte:

### Entrar no container PostgreSQL:

```bash
docker compose exec bd bash
```

E depois sim podem entrar através de PSQL na base de dados: ***psql -U admin -d ai4jurisdb***
Têm aqui um link com comandos muito basicos caso necessitem:
https://medium.com/permalink-univesp/postgresql-na-linha-de-comandos-ff6300b80709

## Acesso ao Backend e Base de dados
Para aceder aos endpoints do backend devem utilizar o base URL: http://localhost:8000/
Segue em um exemplo:
```bash
     const response = await fetch("http://localhost:8000/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });
```




## 🤝 Créditos e enquadramento

Projeto desenvolvido no âmbito de:

- **AI4Juris – Classificação Automática de Documentos Jurídicos**
- **DEI – Departamento de Engenharia Informática**
- **FCTUC – Universidade de Coimbra**
- **CISUC – Centre for Informatics and Systems of the University of Coimbra**
- Em colaboração com **DataJuris** e **Instituto Pedro Nunes (IPN)**

---

## 📄 Licença

Projeto de uso académico associado ao AI4Juris.
