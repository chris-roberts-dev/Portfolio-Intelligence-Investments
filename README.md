# Portfolio Intelligence

Portfolio Intelligence is an investment analytics and decision-support platform built with Django, Django REST Framework, PostgreSQL, a framework-independent Python quantitative engine, and a React/TypeScript frontend.

Development follows the phased engineering plan in [`docs/dev-guide.md`](docs/dev-guide.md). The local-development workflow is Docker-first, while deterministic host-side quality and market-data evidence commands use the committed backend and frontend lockfiles.

## Local development

See [`docs/setup.md`](docs/setup.md) for the complete clean-clone setup and validation workflow.

A typical local start is:

```text
make bootstrap-env
make up-build
