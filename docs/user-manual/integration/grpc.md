---
title: "gRPC Integration Guide"
purpose: "Guide users on integrating with the gRPC interface"
audience: "Developers and integrators"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# gRPC Integration Guide

## Overview
SomaFractalMemory provides a high-performance gRPC interface for service-to-service communication. This guide covers protobuf definitions, service methods, and integration patterns.

## Service Definition

### Proto Files
```protobuf
syntax = "proto3";

package somafractalmemory.v1;

service MemoryService {
  rpc StoreMemory(StoreMemoryRequest) returns (Memory);
  rpc GetMemory(GetMemoryRequest) returns (Memory);
  rpc SearchVector(SearchVectorRequest) returns (SearchVectorResponse);
  rpc StreamMemories(StreamMemoriesRequest) returns (stream Memory);
}

message Memory {
  string id = 1;
  string content = 2;
  map<string, string> metadata = 3;
  repeated float vector = 4;
  string created_at = 5;
}
```

## Service Methods

### Memory Operations

#### Store Memory
```protobuf
message StoreMemoryRequest {
  string content = 1;
  map<string, string> metadata = 2;
  repeated float vector = 3;
}
```

#### Get Memory
```protobuf
message GetMemoryRequest {
  string id = 1;
}
```

### Vector Operations

#### Search Vector
```protobuf
message SearchVectorRequest {
  repeated float vector = 1;
  int32 limit = 2;
  float threshold = 3;
}

message SearchVectorResponse {
  repeated Memory memories = 1;
  repeated float scores = 2;
}
```

### Streaming

#### Stream Memories
```protobuf
message StreamMemoriesRequest {
  string query = 1;
  map<string, string> filters = 2;
}
```

## Client Examples

### Python
```python
import grpc
from somafractalmemory.v1 import memory_pb2, memory_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50051')
stub = memory_pb2_grpc.MemoryServiceStub(channel)

# Store memory
request = memory_pb2.StoreMemoryRequest(
    content="Example content",
    metadata={"type": "note"},
    vector=[0.1, 0.2, 0.3]
)
memory = stub.StoreMemory(request)

# Search vectors
search_request = memory_pb2.SearchVectorRequest(
    vector=[0.1, 0.2, 0.3],
    limit=5
)
results = stub.SearchVector(search_request)
```

### Go
```go
package main

import (
    "context"
    pb "somafractalmemory/v1"
    "google.golang.org/grpc"
)

func main() {
    conn, err := grpc.Dial("localhost:50051", grpc.WithInsecure())
    if err != nil {
        log.Fatalf("Failed to connect: %v", err)
    }
    defer conn.Close()

    client := pb.NewMemoryServiceClient(conn)

    // Store memory
    memory, err := client.StoreMemory(context.Background(), &pb.StoreMemoryRequest{
        Content: "Example content",
        Metadata: map[string]string{"type": "note"},
        Vector: []float32{0.1, 0.2, 0.3},
    })
}
```

## Authentication

### SSL/TLS
```python
# Create credentials
credentials = grpc.ssl_channel_credentials(root_certificates=None)

# Create secure channel
channel = grpc.secure_channel('api.somafractalmemory.com:443', credentials)
```

### Token Authentication
```python
# Create credentials with token
metadata = [('authorization', f'Bearer {token}')]
auth_creds = grpc.metadata_call_credentials(lambda context, callback: callback(metadata, None))

# Combine with SSL
channel_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)
```

## Error Handling

### Status Codes
| Code | Description | Example |
|------|-------------|---------|
| OK | Success | Operation completed |
| INVALID_ARGUMENT | Bad request | Invalid vector dimension |
| UNAUTHENTICATED | Auth failed | Invalid token |
| NOT_FOUND | Resource missing | Memory not found |
| INTERNAL | Server error | Database error |

### Error Handling Example
```python
try:
    memory = stub.GetMemory(request)
except grpc.RpcError as e:
    status_code = e.code()
    if status_code == grpc.StatusCode.NOT_FOUND:
        print("Memory not found")
    elif status_code == grpc.StatusCode.UNAUTHENTICATED:
        print("Authentication failed")
```

## Streaming Examples

### Server Streaming
```python
# Stream memories
request = memory_pb2.StreamMemoriesRequest(
    query="example",
    filters={"type": "note"}
)

for memory in stub.StreamMemories(request):
    print(f"Received memory: {memory.id}")
```

### Client Streaming
```python
# Batch store memories
def memory_generator():
    for content in contents:
        yield memory_pb2.StoreMemoryRequest(
            content=content,
            metadata={"type": "note"}
        )

responses = stub.BatchStoreMemories(memory_generator())
```

## Performance Optimization

### Connection Management
```python
# Connection pooling
pool = grpc.channel_pool([
    grpc.insecure_channel('localhost:50051')
    for _ in range(10)
])
```

### Compression
```python
# Enable compression
options = [('grpc.default_compression_algorithm', grpc.Compression.Gzip)]
channel = grpc.insecure_channel('localhost:50051', options=options)
```

## Best Practices

1. **Connection Management**
   - Use connection pooling
   - Implement retry logic
   - Handle disconnects

2. **Performance**
   - Use streaming for large datasets
   - Enable compression
   - Batch operations

3. **Error Handling**
   - Implement retries
   - Handle timeouts
   - Log errors

## Monitoring

### Health Checking
```python
# Health check
health_stub = health_pb2_grpc.HealthStub(channel)
response = health_stub.Check(health_pb2.HealthCheckRequest())
```

### Metrics
```python
# Get service metrics
metrics_stub = metrics_pb2_grpc.MetricsStub(channel)
metrics = metrics_stub.GetMetrics(metrics_pb2.GetMetricsRequest())
```

## Further Reading
- [Protocol Buffers Guide](../../development-manual/protobuf.md)
- [gRPC Best Practices](../../development-manual/grpc-practices.md)
- [Authentication Guide](authentication.md)
- [Performance Guide](../../technical-manual/performance.md)
