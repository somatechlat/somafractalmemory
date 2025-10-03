# Custom Redpanda image with sysctl support
FROM redpandadata/redpanda:latest

# Switch to root to install packages
USER root

# Install procps to provide sysctl binary for adjusting kernel parameters
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# Switch back to default user (if needed)
# USER redpanda
