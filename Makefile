GIT_DESCRIBE ?= $(shell git describe --always --dirty --tags)
DOCKER_TAG ?= travisci/gesund:$(GIT_DESCRIBE)

DOCKER ?= docker

.PHONY: help
help:
	@echo Perhaps you would like:
	@echo - deps
	@echo - docker-build
	@echo - docker-login
	@echo - docker-push
	@echo - lint

.PHONY: deps
deps:
	pip install -r requirements.txt

.PHONY: lint
lint:
	yapf -vv -i gesund.py

.PHONY: docker-build
docker-build:
	$(DOCKER) build -t="$(DOCKER_TAG)" .

.PHONY: docker-login
docker-login:
	@echo "$(DOCKER_LOGIN_PASSWORD)" | \
		$(DOCKER) login --username "$(DOCKER_LOGIN_USERNAME)" --password-stdin

.PHONY: docker-push
docker-push:
	$(DOCKER) push "$(DOCKER_TAG)"
