#!/bin/bash

# Deploy script for testing the ezloPi integration in Home Assistant.
#
# Copies the custom_components/ezlopi component into the Home Assistant pod and
# restarts Home Assistant so the updated integration is picked up. Mirrors the
# deploy flow used by the other Home Assistant integrations (adsb, moultrie,
# nexgrill, starlink).

set -euo pipefail

CONTEXT="mini"
NAMESPACE="homeassistant"
POD="homeassistant-home-assistant-0"
STATEFULSET="homeassistant-home-assistant"
DOMAIN="ezlopi"
SRC="custom_components/${DOMAIN}"
DEST="/config/custom_components/${DOMAIN}"

K="kubectl --context ${CONTEXT} --namespace ${NAMESPACE}"

echo "Deploying ezloPi integration to Home Assistant..."

# Create the custom_components/ezlopi directory (incl. translations) if missing.
echo "Creating directory structure..."
$K exec "${POD}" -- mkdir -p "${DEST}/translations"

# Copy all Python files
echo "Copying integration files..."
for file in "${SRC}"/*.py; do
    filename=$(basename "$file")
    echo "  Copying $filename..."
    $K cp "$file" "${POD}:${DEST}/$filename"
done

# Copy JSON files (manifest.json, strings.json, icons.json, ...)
for file in "${SRC}"/*.json; do
    filename=$(basename "$file")
    echo "  Copying $filename..."
    $K cp "$file" "${POD}:${DEST}/$filename"
done

# Copy YAML files if they exist
for file in "${SRC}"/*.yaml "${SRC}"/*.yml; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "  Copying $filename..."
        $K cp "$file" "${POD}:${DEST}/$filename"
    fi
done

# Copy translations
echo "  Copying translations..."
$K cp "${SRC}/translations/en.json" "${POD}:${DEST}/translations/en.json"

echo "Files copied successfully."

# Restart Home Assistant
echo "Restarting Home Assistant..."
$K rollout restart statefulset "${STATEFULSET}"

# Wait for rollout to complete
echo "Waiting for Home Assistant to restart..."
$K rollout status statefulset "${STATEFULSET}"

echo "Deployment complete! Home Assistant has been restarted with the updated integration."
echo ""
echo "You can check the logs with:"
echo "kubectl --context ${CONTEXT} --namespace ${NAMESPACE} logs ${POD} | grep -i ${DOMAIN}"
