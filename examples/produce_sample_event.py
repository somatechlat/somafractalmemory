from eventing.producer import build_memory_event, produce_event


def main():
    ev = build_memory_event("local_dev", {"task": "sample"})
    produce_event(ev)


if __name__ == "__main__":
    main()
