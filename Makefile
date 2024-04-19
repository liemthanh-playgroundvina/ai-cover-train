download_model:
	curl -o ./models/ai_cover_pretrained_model.zip https://aiservices-bucket.s3.ap-southeast-1.amazonaws.com/ai_model/ai-cover/ai_cover_pretrained_model.zip
	unzip ./models/ai_cover_pretrained_model.zip -d ./models
	rm -rf ./models/ai_cover_pretrained_model.zip

config:
	cp ./configs/env.example ./configs/.env
	# And add params ...

build:
	docker pull python:3.9-slim
	docker build -t ai-cover-train -f Dockerfile .

start:
	docker compose -f docker-compose.yml down
	docker compose -f docker-compose.yml up -d

start-prod:
	docker compose -f docker-compose-prod.yml down
	docker compose -f docker-compose-prod.yml up -d

stop:
	docker compose -f docker-compose.yml down

stop-prod:
	docker compose -f docker-compose-prod.yml down

# Checker
cmd-image:
	docker run -it --gpus all --rm ai-cover-train /bin/bash

cmd-worker:
	docker compose exec worker-ai-cover-train /bin/bash