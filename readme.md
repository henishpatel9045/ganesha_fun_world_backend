# Ganesha Fun World Management System

## Pre-requisites

- Docker
- Docker Compose

## Installation

1. Clone the repository

Clone for production

```bash
mkdir production_api
```

```bash
cd production_api
```

```bash
git clone GANESHA_MANAGEMENT_REPO .
```

Clone for testing

```bash
mkdir test_api
```

```bash
cd test_api
```

```bash
git clone GANESHA_MANAGEMENT_REPO .
git checkout release/dev
```

For server configuration

```bash
mkdir server_config
```

```bash
cd server_config
```

```bash
git clone SERVER_CONFIG_REPO .
```

2. Upload env files

- Upload .env file to production_api folder
- Upload .env.test file to test_api folder

3. Start applications

Create external network

```bash
docker network create prod_network
docker network create test_network
```

Create external volume

```bash
docker volume create static_volume
docker volume create test_static_volume
```

For Production

```bash
cd production_api
```

```bash
docker-compose -f docker-compose-prod.yml up --build -d
```

For Testing

```bash
cd test_api
```

```bash
docker-compose -f docker-compose-test.yml up --build -d
```

For Server Configuration

```bash
cd server_config
```

```bash
docker-compose up --build -d
```
