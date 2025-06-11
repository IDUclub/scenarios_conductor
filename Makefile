CODE := scenarios_conductor
TEST := tests

lint:
	poetry run pylint $(CODE)

lint-tests:
	poetry run pylint $(TEST)

format:
	poetry run isort $(CODE)
	poetry run black $(CODE)
	poetry run isort $(TEST)
	poetry run black $(TEST)

run-app:
	CONFIG_PATH=config.yaml poetry run launch_app

install:
	pip install .

install-dev:
	poetry install --with dev

install-dev-pip:
	pip install -e . --config-settings editable_mode=strict

clean:
	rm -rf ./dist

build:
	poetry build

install-from-build:
	python -m wheel install dist/scenarios_conductor-*.whl

test:
	poetry run pytest --verbose tests/

test-with-cov:
	poetry run pytest --verbose tests/ --cov scenarios_conductor