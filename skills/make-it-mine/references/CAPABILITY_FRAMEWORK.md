# Full-Stack Product Engineering Capability Framework

Use this reference when evaluating capability gaps, assigning maturity evidence, or suggesting what to develop next.

Do not treat this as a curriculum that must be completed. It is a map for interpreting evidence from real work.

## 1. Product reasoning

- problem framing
- requirement clarification
- user goals and jobs-to-be-done
- constraints
- success metrics
- scope and MVP decisions
- prioritization
- product trade-offs
- edge cases
- user workflows

Key evidence: can distinguish the underlying problem from the requested implementation.

## 2. UX and interaction judgment

- user flows
- information architecture
- interaction cost
- cognitive load
- discoverability
- affordance
- feedback
- progressive disclosure
- error prevention and recovery
- accessibility
- keyboard behavior
- mobile/responsive behavior

Key evidence: can choose interaction patterns based on user task rather than fashion.

## 3. Visual UI judgment

- hierarchy
- density
- spacing and rhythm
- grouping
- typography
- emphasis
- contrast
- consistency
- scanability
- action priority
- responsive layout
- content priority

Key evidence: can explain why a visual decision helps comprehension or action.

## 4. Frontend engineering

- component boundaries
- composition
- state ownership
- local/global/server state
- derived state
- controlled/uncontrolled components
- rendering model
- data fetching
- client caching
- optimistic UI
- forms
- routing
- loading/error/empty states
- performance
- accessibility
- frontend security
- reusable abstractions
- design systems

Key evidence: can explain who owns state, why a boundary exists, and when abstraction is justified.

## 5. Backend engineering

- domain modeling
- service/module boundaries
- API design
- validation
- authentication
- authorization
- transactions
- concurrency
- idempotency
- jobs and queues
- caching
- retries
- rate limiting
- error semantics
- asynchronous workflows

Key evidence: can separate architectural responsibility from implementation convenience.

## 6. Data and storage

- relational modeling
- normalization/denormalization
- indexes
- query patterns
- transactions
- consistency and isolation
- locking
- migrations
- pagination
- search
- caching
- analytics storage
- retention
- data ownership

Key evidence: selects structures and storage based on access patterns, consistency, lifecycle, and operational constraints.

## 7. Systems and distributed systems

- decomposition and boundaries
- dependencies
- sync vs async communication
- scaling
- messaging
- distributed state
- replication
- partitioning
- backpressure
- retries
- idempotency
- fault tolerance
- failure domains
- graceful degradation
- recovery

Key evidence: reasons about partial failure and avoids unnecessary distributed complexity.

## 8. Infrastructure and production

- deployment
- containers
- CI/CD
- cloud architecture
- networking and DNS
- load balancing
- secrets/configuration
- logs, metrics, traces
- alerts
- rollback
- database migrations
- capacity planning
- incident response
- SLO/SLA thinking

Key evidence: can answer "how do we know it is broken, and how do we recover?"

## 9. Security

- authentication
- authorization
- session management
- permissions
- secrets
- trust boundaries
- XSS
- CSRF
- SSRF
- injection
- rate limiting
- abuse prevention
- data exposure
- threat modeling

Key evidence: reasons about hostile clients and trust boundaries, not only happy-path validation.

## 10. Engineering practice

- debugging methodology
- testing strategy
- code review
- refactoring
- technical debt
- abstraction
- maintainability
- naming and APIs
- architecture evolution
- codebase navigation
- performance investigation
- incident analysis

Key evidence: can investigate unknown behavior systematically before guessing.

## Capability maturity evidence

### OBSERVED
Evidence: recognizes the term or has encountered the pattern.

### EXPLAINABLE
Evidence: explains purpose and mechanism in own words without copying the original answer.

### USABLE
Evidence: applies it successfully to a concrete implementation or design.

### PLACEABLE
Evidence: identifies the correct owner/layer/boundary and explains why adjacent layers should not own all of the responsibility.

### SELECTABLE
Evidence: compares realistic options against stated requirements and constraints.

### DEFENDABLE
Evidence: withstands reasonable challenge and can name downsides of the chosen option.

### ADAPTABLE
Evidence: changes or abandons the original approach when constraints change.

### TEACHABLE
Evidence: communicates a compact mental model that another engineer could reuse.

## Gap prioritization

Rank possible growth areas by:

1. frequency in actual work
2. leverage across domains
3. foundational dependency
4. risk of mistakes
5. repeated reasoning dependency on AI

Do not prioritize a topic merely because it is advanced or fashionable.
