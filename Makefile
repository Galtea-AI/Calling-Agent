.PHONY: help install run run-dev run-simulator docker-build docker-run docker-compose-up docker-compose-down docker-logs setup-env setup-ngrok dev-setup health clean clean-docker

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development setup
install: ## Install dependencies using uv
	uv sync

# Local development
run: ## Run the application locally
	uv run uvicorn agent_twilio:app --host 0.0.0.0 --port 8001

run-dev: ## Run the application in development mode with auto-reload
	uv run uvicorn agent_twilio:app --host 0.0.0.0 --port 8001 --reload

run-simulator: ## Run the talk.py simulator
	uv run python talk.py

# Docker deployment (optional)
docker-build: ## Build Docker image
	docker build -t calling-agent:latest .

docker-run: ## Run application in Docker container
	docker run -p 8001:8001 --env-file .env -v $(PWD)/config.yaml:/app/config.yaml:ro calling-agent:latest

docker-compose-up: ## Start services with docker compose (V2)
	docker compose up -d

docker-compose-down: ## Stop docker compose services
	docker compose down

docker-logs: ## Show docker compose logs
	docker compose logs -f calling-agent

# Utility commands
health: ## Check application health
	curl -f http://localhost:8001/health || echo "Health check failed"

clean: ## Clean up temporary files and caches
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -delete

clean-docker: ## Clean up Docker containers and images
	docker compose down --rmi all --volumes --remove-orphans
	docker system prune -f

# Environment setup helpers
setup-env: ## Create .env file template
	@if [ ! -f .env ]; then \
		echo "Creating .env template..."; \
		echo "TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > .env; \
		echo "TWILIO_AUTH_TOKEN=your_twilio_auth_token" >> .env; \
		echo "ELEVENLABS_API_KEY_GAL=your_elevenlabs_api_key" >> .env; \
		echo "API_KEY=your_internal_api_key_for_generate" >> .env; \
		echo "GALTEA_API_KEY_DEV=your_galtea_api_key" >> .env; \
		echo ".env file created. Please fill in your actual credentials."; \
	else \
		echo ".env file already exists."; \
	fi

setup-ngrok: ## Install ngrok (system-wide)
	@echo "Installing ngrok..."
	@if command -v brew >/dev/null 2>&1; then \
		echo "Installing via Homebrew..."; \
		brew install ngrok; \
	elif command -v apt >/dev/null 2>&1; then \
		echo "Installing via apt (Linux)..."; \
		curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null; \
		echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list; \
		sudo apt update && sudo apt install ngrok; \
	else \
		echo "Please install ngrok manually from https://ngrok.com/download"; \
	fi
	@echo "After installation, sign up at ngrok.com and run: ngrok config add-authtoken <your-token>"

# Complete development setup
dev-setup: setup-env install ## Complete development setup
	@echo "Development setup complete!"
	@echo ""
	@echo "🚀 Next steps:"
	@echo "1. Edit .env file with your actual credentials"
	@echo "2. Install ngrok if not installed: make setup-ngrok"
	@echo ""
	@echo "📱 Local Development:"
	@echo "3. Run 'make run-dev' to start the development server"
	@echo "4. In another terminal, start ngrok: ngrok http 8001"
	@echo "5. Update Twilio webhook and config.yaml with ngrok URL"
	@echo "6. Run 'make run-simulator' to test with a phone call"
	@echo ""
	@echo "🐳 Docker Deployment (alternative):"
	@echo "3. Run 'make docker-compose-up' to start with Docker"
	@echo "4. Check logs with 'make docker-logs'"
