# Audit Question Bank

Use sparingly. Select the smallest number of questions that reveals actual reasoning.

## Understanding

- What problem is this solving?
- Why does this concept exist?
- What would happen if we removed it?
- Explain it without using the technology's name.
- What assumption does this design rely on?

## Placement

- Who should own this responsibility?
- Why does it belong here rather than one layer above or below?
- What belongs on the client, and what must be enforced on the server?
- Is this state local UI state, shared client state, or server state?
- Is this concern business logic, transport logic, or persistence logic?

## Technology selection

- What are the decisive requirements?
- What is the simplest plausible alternative?
- Why not use the existing database?
- What is the next-best option?
- Which downside are you accepting?
- What change would reverse your decision?

## System design

- What are the core invariants?
- Where is state stored and who owns it?
- What is synchronous and what is asynchronous?
- Which component fails first under 100x load?
- Where can duplicate work occur?
- Which boundary needs idempotency?

## Failure reasoning

- What happens if this request is retried?
- What happens if the dependency times out after completing the work?
- What happens if the cache disappears?
- What happens if the queue is delayed for an hour?
- How does the system recover from partial success?
- How would you detect this failure before users report it?

## Frontend

- Who owns this state?
- Is this state canonical or derived?
- Why is this a component boundary?
- What causes this component to rerender?
- Is this abstraction solving current repeated complexity or imagined future complexity?
- What changes on mobile?

## Backend/API

- What is the transaction boundary?
- Where is validation enforced?
- What happens if this endpoint is called twice?
- Why is this operation synchronous?
- Who is responsible for retrying?
- What are the API's error semantics?

## Data

- What are the dominant query patterns?
- Which index supports that access pattern?
- What consistency does the product actually require?
- What data owns the relationship?
- What happens during migration?

## UI/UX

- What is the user's actual task?
- Do they know the exact value they want?
- Do they need to compare choices at the same time?
- What is the cost of a mistake?
- Is the action reversible?
- Can it be completed efficiently with a keyboard?
- How does the user know it worked?

## Transfer

- Where else would this principle apply?
- Give one case where this same solution would be wrong.
- If scale dropped by 100x, what would you remove?
- If the team shrank to three engineers, what would you simplify?
- If the action became irreversible, how would the UI change?
