clean:
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf .ruff_cache
	@rm -rf pytest-coverage.txt
	@rm -rf pytest.xml
	@rm -rf htmlcov
	@find . | grep -E "(/__pycache__$$|\.pyc$$|\.pyo$$)" | xargs rm -rf