---
name: fastapi-tdd
description: "Build and change FastAPI APIs test-first. Use for pytest API tests, Pydantic request/response schemas, routers, dependency injection, SQLAlchemy async sessions, and transactional database writes."
---

# FastAPI TDD

## When to Use
- Adding or changing FastAPI endpoints, dependencies, validation, or error responses.
- Defining Pydantic schemas or SQLAlchemy-backed services.
- Fixing backend behavior with regression tests.

## Procedure
1. Inspect the existing router, schema, service, session dependency, and nearby tests. Follow the project's layering and conventions.
2. Write a focused pytest that captures the required behavior, including the success response and relevant invalid-input or failure cases.
3. Run the focused test and confirm it fails for the expected reason.
4. Define explicit Pydantic input and output schemas. Constrain user-controlled fields with appropriate types, bounds, and validators; never expose ORM objects or secrets directly.
5. Implement the endpoint in the API layer and keep business logic in a service. Inject the database session through the existing dependency rather than opening a second engine or session.
6. Wrap every database write in an explicit SQLAlchemy transaction, for example:

   ```python
   async with session.begin():
       session.add(record)
   ```

   Keep transaction ownership clear: do not commit inside a service when its caller owns the transaction, and do not swallow failures or return success-shaped fallbacks.
7. Run the focused test, then the backend test suite and configured linter/type checks for affected files. Add a regression test for each fixed bug.

## API and Test Expectations
- Assert status code and response shape, not only that a request does not raise.
- Test schema validation, missing resources, and authorization boundaries when relevant.
- Use dependency overrides or isolated test fixtures for external services and database access.
- Keep error responses explicit and consistent with existing API conventions.
