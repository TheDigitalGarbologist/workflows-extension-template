-- Step 1: Create the output table dynamically
EXECUTE IMMEDIATE '''
  CREATE OR REPLACE TABLE ''' || output_table || '''
  OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
  AS 
  SELECT 
      r.* EXCEPT (geom),  
      CAST(NULL AS INT64) AS segmentid,            -- segmented line identifier
      CAST(NULL AS STRING) AS segment_wkt,         -- segmented line as WKT
      CAST(NULL AS GEOGRAPHY) AS geom,             -- new geometry (GEOGRAPHY type)
      CAST(NULL AS FLOAT64) AS segment_length_km   -- length in km
  FROM ''' || input_table || ''' r
  WHERE 1 = 0;
  ''';


-- Step 2: Define the JavaScript UDF for splitting road segments at intersections
CREATE TEMP FUNCTION splitLineAtPoints(
  line_wkt STRING, pts_wkt ARRAY<STRING>, tolerance FLOAT64
) RETURNS ARRAY<STRUCT<segmentid INT64, segment_wkt STRING>> 
LANGUAGE js AS """
function parsePoint(wkt) {
  try {
    var inner = wkt.replace(/^POINT\\(/, "").replace(/\\)$/, "");
    var parts = inner.split(" ");
    return { x: parseFloat(parts[0]), y: parseFloat(parts[1]) };
  } catch (err) {
    return null;
  }
}

function parseLine(wkt) {
  var inner = wkt.replace(/^LINESTRING\\(/, "").replace(/\\)$/, "");
  var parts = inner.split(",");
  return parts.map(function(part) {
    var coords = part.trim().split(" ");
    return { x: parseFloat(coords[0]), y: parseFloat(coords[1]) };
  });
}

function lineWKT(points) {
  return "LINESTRING(" + points.map(pt => pt.x + " " + pt.y).join(", ") + ")";
}

function distance(a, b) {
  var dx = b.x - a.x, dy = b.y - a.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function interpolatePoint(line, d) {
  var cum = 0;
  for (var i = 0; i < line.length - 1; i++) {
    var a = line[i], b = line[i+1];
    var segLen = distance(a, b);
    if (cum + segLen >= d) {
      var t = (d - cum) / segLen;
      return { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) };
    }
    cum += segLen;
  }
  return line[line.length - 1];
}

function cumulativeDistances(line) {
  var cum = [0];
  for (var i = 1; i < line.length; i++) {
    cum.push(cum[i - 1] + distance(line[i - 1], line[i]));
  }
  return cum;
}

function splitLineAtPoints(line_wkt, pts_wkt, tolerance) {
  tolerance = tolerance || 1e-6;
  var line = parseLine(line_wkt);
  var cum = cumulativeDistances(line);
  var totalLength = cum[cum.length - 1];
  var projections = [];

  pts_wkt.forEach(function(ptWKT) {
    var pt = parsePoint(ptWKT);
    if (pt === null) return;
    var bestProj = null;
    var bestError = 1e9;
    for (var i = 0; i < line.length - 1; i++) {
      var a = line[i], b = line[i+1];
      var segLen = distance(a, b);
      if (segLen === 0) continue;

      var t = ((pt.x - a.x) * (b.x - a.x) + (pt.y - a.y) * (b.y - a.y)) / (segLen * segLen);
      t = Math.max(0, Math.min(1, t));
      var proj = { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) };
      var err = distance(pt, proj);
      
      if (err < bestError) {
        bestError = err;
        bestProj = cum[i] + t * segLen;
      }
    }
    if (bestProj !== null) {
      projections.push(bestProj);
    }
  });

  projections.push(0);
  projections.push(totalLength);
  projections.sort((a, b) => a - b);

  var unique = projections.filter((d, i) => i === 0 || Math.abs(d - projections[i - 1]) > tolerance);
  var segments = [];
  for (var i = 0; i < unique.length - 1; i++) {
    var d_start = unique[i];
    var d_end = unique[i+1];
    var segPoints = [interpolatePoint(line, d_start)];

    for (var j = 0; j < cum.length; j++) {
      if (cum[j] > d_start && cum[j] < d_end) {
        segPoints.push(line[j]);
      }
    }

    segPoints.push(interpolatePoint(line, d_end));
    segments.push({ segmentid: i, segment_wkt: lineWKT(segPoints) });
  }

  return segments;
}

return splitLineAtPoints(line_wkt, pts_wkt, tolerance);
""";

-- Step 3: Insert split road segments into output_table
EXECUTE IMMEDIATE '''
INSERT INTO ''' || output_table || '''
SELECT * FROM (
  WITH intersections AS (
    SELECT
      r.''' || user_column || ''' AS rid,  -- Dynamically use user-defined column
      ARRAY_AGG(ST_ASTEXT(ST_INTERSECTION(r.geom, other.geom)) IGNORE NULLS) AS inter_pts
    FROM ''' || input_table || ''' r
    JOIN ''' || input_table || ''' other
      ON r.''' || user_column || ''' <> other.''' || user_column || '''
         AND ST_INTERSECTS(r.geom, other.geom)
    GROUP BY r.''' || user_column || '''
  )
  SELECT
    r.* EXCEPT (geom),
    seg.segmentid,
    seg.segment_wkt,
    ST_GEOGFROMTEXT(seg.segment_wkt) AS geom,
    ST_LENGTH(ST_GEOGFROMTEXT(seg.segment_wkt)) / 1000 AS segment_length_km
  FROM ''' || input_table || ''' r
  LEFT JOIN intersections i
    ON r.''' || user_column || ''' = i.rid
  CROSS JOIN UNNEST(
    splitLineAtPoints(
      ST_ASTEXT(r.geom),
      IFNULL(i.inter_pts, []),
      ''' || tolerance || '''  -- Inject tolerance from metadata.json
    )
  ) AS seg
  WHERE ST_LENGTH(ST_GEOGFROMTEXT(seg.segment_wkt)) > 0
);
''';