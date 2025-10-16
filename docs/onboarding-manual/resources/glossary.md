# Glossary

## Core Concepts

### Vector Memory

- **Vector**: A high-dimensional numerical representation of data.
- **Embedding**: The process of converting data into vectors.
- **Similarity**: A measure of how close two vectors are in the vector space.
- **Dimension**: The number of components in a vector (e.g., 768 for BERT).

### Temporal Decay

- **Decay Rate**: The speed at which memory importance diminishes over time.
- **Importance**: A numerical measure of a memory's significance.
- **Access Pattern**: How frequently and recently a memory is used.
- **Consolidation**: The process of strengthening important memories.

### Graph Relations

- **Node**: A vertex in the graph representing a memory.
- **Edge**: A connection between two memories.
- **Path**: A sequence of edges connecting two nodes.
- **Weight**: The strength or importance of a connection.

## Technical Terms

### Storage

- **HNSW**: Hierarchical Navigable Small World (vector search index).
- **Vector Store**: Database specialized for vector storage and retrieval.
- **Cache**: Fast temporary storage for frequently accessed data.
- **Index**: Data structure for efficient vector search.

### API

- **Endpoint**: A specific URL where an API can be accessed.
- **gRPC**: High-performance RPC framework.
- **REST**: Representational State Transfer API style.
- **WebSocket**: Protocol for real-time bidirectional communication.

### Infrastructure

- **Container**: Isolated environment for running applications.
- **Docker**: Platform for building and running containers.
- **Kubernetes**: Container orchestration platform.
- **Helm**: Package manager for Kubernetes.

## Development Terms

### Tools

- **Git**: Version control system.
- **GitHub**: Code hosting and collaboration platform.
- **CI/CD**: Continuous Integration/Continuous Deployment.
- **pytest**: Python testing framework.

### Code Quality

- **Linter**: Tool for checking code style.
- **Type Hint**: Python type annotations.
- **Coverage**: Measure of code tested.
- **Benchmark**: Performance measurement.

### Process

- **PR**: Pull Request for code review.
- **Issue**: Bug report or feature request.
- **Release**: Version of software.
- **Tag**: Named version marker.

## Monitoring Terms

### Metrics

- **Latency**: Time taken to complete operation.
- **Throughput**: Operations per second.
- **Error Rate**: Percentage of failed operations.
- **Saturation**: Resource utilization level.

### Observability

- **Log**: Record of system events.
- **Trace**: Path of request through system.
- **Alert**: Notification of system issue.
- **Dashboard**: Visual display of metrics.

### Performance

- **QPS**: Queries per second.
- **P95**: 95th percentile latency.
- **SLA**: Service Level Agreement.
- **SLO**: Service Level Objective.

## Database Terms

### Operations

- **Query**: Request for data.
- **Index**: Data structure for fast lookup.
- **Transaction**: Atomic set of operations.
- **Migration**: Database schema change.

### Types

- **PostgreSQL**: Relational database.
- **Redis**: In-memory data store.
- **Hybrid**: Combined storage approach.
- **Sharding**: Data partitioning.

## Project-Specific

### Features

- **Memory Manager**: Core vector storage system.
- **Graph Engine**: Relationship management system.
- **Decay Service**: Temporal importance calculator.
- **Query Optimizer**: Search performance improver.

### Components

- **API Service**: Main application interface.
- **Vector Store**: Vector data storage.
- **Cache Layer**: Fast retrieval layer.
- **Index Service**: Search optimization.

### Configuration

- **Environment**: Development context.
- **Settings**: Application configuration.
- **Profile**: Performance settings.
- **Policy**: System rules.

## Cloud Terms

### Services

- **Load Balancer**: Traffic distributor.
- **Auto Scaling**: Automatic resource adjustment.
- **CDN**: Content Delivery Network.
- **VPC**: Virtual Private Cloud.

### Resources

- **Node**: Computing instance.
- **Pod**: Kubernetes unit.
- **Volume**: Persistent storage.
- **Network**: Communication path.

## Security Terms

### Access Control

- **Authentication**: Identity verification.
- **Authorization**: Permission checking.
- **Token**: Security credential.
- **RBAC**: Role-Based Access Control.

### Data Protection

- **Encryption**: Data scrambling.
- **TLS**: Transport Layer Security.
- **Backup**: Data copy.
- **Recovery**: Data restoration.

## Testing Terms

### Types

- **Unit**: Individual component test.
- **Integration**: Component interaction test.
- **E2E**: End-to-end system test.
- **Load**: Performance capacity test.

### Tools

- **Fixture**: Test data setup.
- **Mock**: Test double.
- **Assert**: Test verification.
- **Coverage**: Test measurement.

## Common Acronyms

- **API**: Application Programming Interface
- **CPU**: Central Processing Unit
- **RAM**: Random Access Memory
- **I/O**: Input/Output
- **URL**: Uniform Resource Locator
- **JSON**: JavaScript Object Notation
- **HTTP**: Hypertext Transfer Protocol
- **SSL**: Secure Sockets Layer
- **DNS**: Domain Name System
- **TCP**: Transmission Control Protocol
