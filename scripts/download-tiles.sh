#!/usr/bin/env bash
# ============================================================
# FLIP v3.0 — Download OSM Liberty Map Tiles for Local Dev
# Downloads: district-level MBTiles for target region
# Output: apps/web/public/tiles/
# ============================================================
set -euo pipefail

TILES_DIR="apps/web/public/tiles"
mkdir -p "$TILES_DIR"

# Target: Karnataka/Maharashtra border district (example bbox for dev)
# Adjust these coordinates for your actual target district
BBOX_WEST=76.8
BBOX_SOUTH=12.1
BBOX_EAST=77.5
BBOX_NORTH=12.7
MAX_ZOOM=14

log() { echo -e "\033[0;32m[TILES]\033[0m $*"; }

log "Downloading OSM tiles for district bbox: $BBOX_WEST,$BBOX_SOUTH,$BBOX_EAST,$BBOX_NORTH"

# Option 1: Use Planetiler to generate PMTiles from OSM data
if command -v docker &>/dev/null; then
    log "Using Planetiler via Docker to generate PMTiles..."
    docker run --rm \
        -v "$(pwd)/$TILES_DIR:/output" \
        -e JAVA_TOOL_OPTIONS=-Xmx4g \
        ghcr.io/onthegomap/planetiler:latest \
        --download \
        --area=india \
        --bounds="$BBOX_WEST,$BBOX_SOUTH,$BBOX_EAST,$BBOX_NORTH" \
        --maxzoom=$MAX_ZOOM \
        --output=/output/india_district.pmtiles 2>/dev/null || true
fi

# Option 2: Download pre-built tiles from MapTiler (free tier)
# Requires MAPTILER_API_KEY env var
if [[ -n "${MAPTILER_API_KEY:-}" ]]; then
    log "Downloading from MapTiler API..."
    curl -L -o "$TILES_DIR/base.mbtiles" \
        "https://api.maptiler.com/tiles/v3-openmaptiles/{z}/{x}/{y}.pbf?key=$MAPTILER_API_KEY" \
        --create-dirs || true
fi

# Option 3: Download from Protomaps public CDN (free for OSM Liberty style)
log "Downloading OSM Liberty PMTiles from Protomaps CDN (free)..."
PMTILES_URL="https://build.protomaps.com/20240614.pmtiles"
REGION_FILE="$TILES_DIR/fliplocal.pmtiles"

if [[ ! -f "$REGION_FILE" ]]; then
    log "Downloading full PMTiles (will extract region using pmtiles CLI)..."
    if command -v pmtiles &>/dev/null; then
        pmtiles extract "$PMTILES_URL" "$REGION_FILE" \
            --bbox="$BBOX_WEST,$BBOX_SOUTH,$BBOX_EAST,$BBOX_NORTH" \
            --maxzoom=$MAX_ZOOM
        log "Extracted region PMTiles: $REGION_FILE"
    else
        log "pmtiles CLI not found. Installing via npm..."
        npm install -g pmtiles 2>/dev/null || true
        if command -v pmtiles &>/dev/null; then
            pmtiles extract "$PMTILES_URL" "$REGION_FILE" \
                --bbox="$BBOX_WEST,$BBOX_SOUTH,$BBOX_EAST,$BBOX_NORTH" \
                --maxzoom=$MAX_ZOOM
            log "Extracted region PMTiles: $REGION_FILE"
        else
            log "Skipping PMTiles extraction — install pmtiles CLI manually:"
            log "  npm install -g pmtiles"
            log "  pmtiles extract $PMTILES_URL $REGION_FILE --bbox='$BBOX_WEST,$BBOX_SOUTH,$BBOX_EAST,$BBOX_NORTH'"
        fi
    fi
else
    log "Tile file already exists: $REGION_FILE"
fi

# Download OSM Liberty Map Style JSON
STYLE_URL="https://raw.githubusercontent.com/maputnik/osm-liberty/gh-pages/style.json"
log "Downloading OSM Liberty style.json..."
curl -L -o "$TILES_DIR/style.json" "$STYLE_URL" 2>/dev/null || \
    log "Warning: Could not download style.json — add manually."

log "✅ Tiles ready in $TILES_DIR/"
ls -lh "$TILES_DIR/" 2>/dev/null || true
