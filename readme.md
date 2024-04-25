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

2. Start applications

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
