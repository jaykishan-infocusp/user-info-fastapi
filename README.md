# User Info

## 🛠 Requirements
- [Docker](https://docs.docker.com/get-docker/) (≥ 20.x)
- [Docker Compose](https://docs.docker.com/compose/install/)

## ⚡ Getting Started

### 1️⃣ Clone the repository
```bash
git clone https://github.com/jaykishan-infocusp/user-info-fastapi.git
cd user-info-fastapi
```

### 2️⃣ Set up environment variables

Create a `.env` file in the project root:
```bash
cp example.env .env
```
- Update all the values in .env

### 3️⃣ Build and start the app

```bash
docker compose up --build
```

This will start:

* `web` → FastAPI backend ([http://localhost:8000](http://localhost:8000))
* `db` → PostgreSQL (port 5432, persistent volume)


---

## 📚 Usage

### API Docs

Once running, open:

* Swagger UI → [http://localhost:8000](http://localhost:8000)
* ReDoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Database

Connect to Postgres locally:

```bash
psql -h localhost -U postgres -d <DB_NAME>
```
- Note: Update as per the database name given in .env file

### Run Alembic migrations

```bash
docker compose exec web alembic upgrade head
```

---