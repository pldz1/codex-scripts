# Technology Selection Reference

Use this when a meaningful choice is being made between technologies, libraries, frameworks, architecture patterns, storage systems, or infrastructure components.

## Selection frame

### 1. Problem
What outcome is required? Avoid naming a technology in the problem statement.

### 2. Workload
What are the relevant shapes of usage?

- request/event volume
- read/write ratio
- data size and growth
- latency sensitivity
- burstiness
- concurrency
- access/query patterns

### 3. Correctness constraints

- consistency
- ordering
- durability
- idempotency
- transactions
- data loss tolerance
- stale data tolerance

### 4. Organizational constraints

- team size
- existing expertise
- time to ship
- operational maturity
- ownership model
- on-call burden
- budget
- vendor constraints

### 5. Candidate set

Prefer a small set of realistic candidates.
Include the simplest plausible solution.
Do not manufacture weak alternatives just to make the preferred option look good.

### 6. Trade-off matrix

Compare only dimensions that materially affect this problem.
Common dimensions:

- complexity
- performance
- consistency
- reliability
- operability
- ecosystem
- portability
- development speed
- maintenance cost
- migration cost
- failure characteristics

### 7. Decision

State:

- chosen option
- decisive constraints
- accepted downside
- why the next-best option loses

### 8. Reversal condition

Ask:

> What specific change would make the runner-up become the better choice?

This is strong evidence that the user understands the decision boundary.

## Anti-pattern checks

Challenge these shortcuts:

- "Redis is fast, so use Redis."
- "Kafka is scalable, so use Kafka."
- "Microservices are best practice."
- "NoSQL scales better."
- "GraphQL is better for frontend."
- "Kubernetes is production-grade."
- "Elasticsearch is for search."

Replace category-to-technology mapping with requirement-to-trade-off reasoning.

## Example: background work

Question: How should a small web app process emails asynchronously?

Potential candidates:

- database-backed job table
- Redis-backed queue
- managed queue service
- Kafka

A good choice depends on volume, delivery semantics, operational maturity, latency, retry needs, and existing infrastructure.

The learning target is not "which queue is best" but "which constraints make each option appropriate."
