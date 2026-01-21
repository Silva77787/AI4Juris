# AI4Juris

Stack:
- Backend: Django 5 + DRF + Postgres
- Frontend: React (Vite)
- Container orchestration: Docker Compose

## Pre-requisitos
- Docker e Docker Compose instalados

## Como correr (tudo em Docker)
Na raiz do repositório:
```sh
docker compose up -d --build
```
Serviços e portas:
- Backend: http://localhost:7777 (runserver)
- Frontend: http://localhost:3333 (serve build)
- Postgres: localhost:11111 (user: admin, password: admin123, db: ai4jurisdb)

Parar:
```sh
docker compose stop
```
Parar e remover containers/rede:
```sh
docker compose down
```
Parar e remover volumes (perde dados da base):
```sh
docker compose down -v
```

## Admin do Django
- URL: http://localhost:7777/admin
- Credenciais: user `admin`, password `1234`

## Desenvolvimento rápido (só frontend)
```sh
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Notas
- As migrações da base correm automaticamente no arranque via entrypoint do backend.
- O frontend chama o backend em `http://localhost:7777`.
- BD internal URL : postgresql://admin:JBWFFVleFw6C4OpQh0pM7i3rfOsyP762@dpg-d54piieuk2gs73bgob7g-a/ai4jurisdb
	keyID: 003704170a20ebd0000000001
	keyName: ai4juris
	applicationKey: K00339UMxStLm7GHO3Asc/GfNDnY65s