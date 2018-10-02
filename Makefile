GIT_DESCRIBE ?= $(shell git describe --always --dirty --tags)
DOCKER_TAG ?= travisci/gesund:$(GIT_DESCRIBE)

DOCKER ?= docker

.PHONY: test
test: fmt
	pytest -vv --cov=gesund

.PHONY: coverage
coverage: htmlcov/index.html

htmlcov/index.html: .coverage
	coverage html

.PHONY: deps
deps:
	pip install -r requirements.txt

.PHONY: fmt
fmt:
	yapf -vv -i $(shell git ls-files '*.py')

.PHONY: lint
lint:
	flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics

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
