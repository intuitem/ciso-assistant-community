#!/bin/sh
# Usage: ./add-jitter.sh <jitter_ms>

TOXIPROXY_API="http://localhost:8474"
PROXY_NAME="pg"
TOXIC_NAME="jitter"

JITTER_MS="$1"
[ -z "$JITTER_MS" ] && { echo "Usage: $0 <jitter_ms>"; exit 1; }

if [ "$JITTER_MS" -eq 0 ]; then
  echo "Suppression du toxic '$TOXIC_NAME'..."
  curl -sf -X DELETE "$TOXIPROXY_API/proxies/$PROXY_NAME/toxics/$TOXIC_NAME" && echo "OK" || echo "Déjà absent"
else
  echo "Ajout du jitter ${JITTER_MS}ms sur proxy '$PROXY_NAME'..."
  # 1) Tente mise à jour si le toxic existe déjà
  if curl -sf "$TOXIPROXY_API/proxies/$PROXY_NAME/toxics" | grep -q "\"name\":\"$TOXIC_NAME\""; then
    curl -sf -X POST "$TOXIPROXY_API/proxies/$PROXY_NAME/toxics/$TOXIC_NAME" \
      -H "Content-Type: application/json" \
      -d "{\"attributes\":{\"latency\":0,\"jitter\":$JITTER_MS}}" && echo "OK (mis à jour)"
  else
    # 2) Sinon création (route /toxics sans <name>)
    curl -sf -X POST "$TOXIPROXY_API/proxies/$PROXY_NAME/toxics" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"$TOXIC_NAME\",\"type\":\"latency\",\"stream\":\"downstream\",\"attributes\":{\"latency\":0,\"jitter\":$JITTER_MS}}" \
      && echo "OK (créé)"
  fi
fi
