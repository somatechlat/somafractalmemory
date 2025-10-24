---
title: "API Reference"
purpose: "OpenAPI specification for SomaFractalMemory API."
audience:
  - "Developers"
  - "Integrators"
last_updated: "2025-10-24"
---

```yaml
openapi: 3.0.3
info:
  title: SomaFractalMemory API
  version: "1.0.0"
paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: Service is healthy
  /memories:
    post:
      summary: Store a memory
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                coord:
                  type: string
                memory_type:
                  type: string
                payload:
                  type: object
      responses:
        '200':
          description: Memory stored
  /memories/{coord}:
    get:
      summary: Retrieve a memory
      parameters:
        - name: coord
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Memory retrieved
    delete:
      summary: Delete a memory
      parameters:
        - name: coord
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Memory deleted
  /memories/search:
    post:
      summary: Search memories
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                top_k:
                  type: integer
                filters:
                  type: object
      responses:
        '200':
          description: Search results
```
