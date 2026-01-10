# Fastapi template

Boilerplate for project with fastapi, docker, github actions


---
## Local development

## Setting-up the local development environment
Prerequisites
- Docker and Docker-compose
- Pycharm Professional Edition (Docker integration is only available on this edition)


To run the app locally, use the docker compose file in the root dir

1. Create `.env` file using the template `.env.sample` on the project root directory
2. Run docker-compose to spin up the containers
```bash
docker-compose up
```
**Note:** The .env file is loaded by default. So there is no need to use `--env-file` flag for pointing the env file.
3. When the containers are running double check if the app is being served on your local by visiting this URL:

    http://localhost:8000/healthy
![Healthy status](https://user-images.githubusercontent.com/12617804/144807933-879cbc3a-dee5-460f-a001-77c98583dfa8.png)

---

4. Setup Pycharm to use the interpreter inside the running containers

5. `Preferences -> Python Interpreter -> (Cog icon) Add -> Docker-compose`
![Screenshot 2021-12-06 at 08 58 43](https://user-images.githubusercontent.com/12617804/144808865-fa030564-3e70-4be3-b0f5-e27a53cd80da.png)

6. Add the path mappings as project working directory in local pointing to the /app/ folder
7. Run a test to check if the configurations are working properly.

---




#### For running server + migrations + requirements
```bash
make start
```

#### Running migrations
```bash
make migrations
```

#### Install requirements
```bash
make requirements
```

#### Starting server
```bash
make main
```

#### Running scrapers
```bash
make scrape
```

#### Running analyser
```bash
make analyse
```

#### Running Code Quality checks
```bash
make check
```

### add pre commit hook for formatting
pre-commit install
