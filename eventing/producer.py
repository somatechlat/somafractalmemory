import json
import uuid
from typing import Dict

from jsonschema import ValidationError, validate

# Minimal JSON Schema for memory events (sync with schemas/memory.event.json)
MEMORY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["event_id", "id", "namespace", "type", "timestamp", "payload"],
}


def build_memory_event(namespace: str, payload: Dict) -> Dict:
    event = {
        "event_id": str(uuid.uuid4()),
        "id": str(uuid.uuid4()),
        "namespace": namespace,
        "type": "created",
        "timestamp": __import__("time").time(),
        "payload": payload,
    }
    try:
        validate(instance=event, schema=MEMORY_SCHEMA)
    except ValidationError as e:
        # Chain the original ValidationError for better traceability
        raise ValueError(f"Event does not conform to schema: {e}") from e
    return event


# Placeholder produce function — in future will use confluent-kafka or aiokafka
def produce_event(event: Dict, topic: str = "memory.events") -> bool:
    # For local development this can be implemented by a simple HTTP call or
    # by using librdkafka via confluent-kafka library. For now we just write
    # the event to stdout so examples can be integrated via `docker-compose`.
    print(json.dumps(event))
    return True
