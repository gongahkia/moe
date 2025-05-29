.PHONY: all build up down clean logs test help env

all: build up

DOCKER_COMPOSE := docker-compose
SERVICE_NAME := bot  
BUILD_ARGS := --no-cache --pull
PYTHON := python3

config:.pre-commit-config.yaml
	@echo "installing precommit hooks..."
	pip install pre-commit
	pre-commit install
	pre-commit run --all-files
	@echo "precommit hooks have been installed!"

build:
	@echo "building containers..."
	@$(DOCKER_COMPOSE) build $(BUILD_ARGS)

up:
	@echo "starting services..."
	@$(DOCKER_COMPOSE) up -d --remove-orphans

down:
	@echo "stopping services..."
	@$(DOCKER_COMPOSE) down --remove-orphans

clean: down
	@echo "cleaning system..."
	@docker system prune -a --volumes -f
	@rm -rf .build

logs:
	@$(DOCKER_COMPOSE) logs -f --tail=100 $(SERVICE_NAME)

test:
	@echo "Running tests..."
	@$(DOCKER_COMPOSE) exec $(SERVICE_NAME) $(PYTHON) -m pytest tests/

env:
	@if [ ! -f .env ]; then \
		echo "Creating .env file"; \
		echo "DISCORD_TOKEN=your_token_here" > .env; \
		echo "STEAM_API_KEY=your_key_here" >> .env; \
		echo "REDIS_URL=redis://redis:6379/0" >> .env; \
	fi

help:
	@echo "Available targets:"
	@echo "  all       - Build and start containers (default)"
	@echo "  build     - Build containers"
	@echo "  up        - Start containers"
	@echo "  down      - Stop and remove containers"
	@echo "  clean     - Remove all Docker artifacts"
	@echo "  logs      - View container logs"
	@echo "  test      - Run tests"
	@echo "  env       - Create .env template"
	@echo "  help      - Show this help"

.DEFAULT_GOAL := help