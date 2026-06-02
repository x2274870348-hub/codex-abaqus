"""Template script for reading ODB field output.

This script is executed by `abaqus python` and outputs JSON to stdout.
Expected environment variables:
    ODB_PATH: path to the .odb file
    FIELD_OUTPUT: comma-separated list of variable names (e.g., "S,U")
    STEP_INDEX: which step to read (0-based, default 0)
    FRAME_INDEX: which frame to read (-1 for last, default -1)
    NODE_LABELS: comma-separated node labels to filter (optional)
    ELEMENT_LABELS: comma-separated element labels to filter (optional)
"""

import os
import sys
import json
import traceback

try:
    from odbAccess import openOdb

    odb_path = os.environ.get("ODB_PATH")
    field_names = os.environ.get("FIELD_OUTPUT", "").split(",")
    field_names = [f.strip() for f in field_names if f.strip()]
    step_idx = int(os.environ.get("STEP_INDEX", "0"))
    frame_idx = int(os.environ.get("FRAME_INDEX", "-1"))
    node_filter = os.environ.get("NODE_LABELS", "")
    elem_filter = os.environ.get("ELEMENT_LABELS", "")
    max_per_field = int(os.environ.get("MAX_PER_FIELD", "500"))

    if not odb_path:
        print(json.dumps({"error": "ODB_PATH not set"}))
        sys.exit(1)

    odb = openOdb(path=odb_path, readOnly=True)

    steps = list(odb.steps.keys())
    if step_idx >= len(steps):
        print(json.dumps({"error": f"Step index {step_idx} out of range (0-{len(steps)-1})", "available_steps": steps}))
        odb.close()
        sys.exit(1)

    step_name = steps[step_idx]
    step = odb.steps[step_name]

    frames = list(step.frames)
    if not frames:
        print(json.dumps({"error": f"No frames in step '{step_name}'"}))
        odb.close()
        sys.exit(1)

    frame = frames[frame_idx]
    frame_value = frame.frameValue

    result = {
        "odb_path": odb_path,
        "step": step_name,
        "step_index": step_idx,
        "frame_index": frame_idx if frame_idx >= 0 else len(frames) + frame_idx,
        "frame_value": frame_value,
        "available_steps": steps,
        "available_frame_values": [f.frameValue for f in frames],
        "fields": {},
    }

    if not field_names:
        # List available field outputs
        available = {}
        for fo in frame.fieldOutputs.keys():
            available[fo] = {
                "description": frame.fieldOutputs[fo].description,
                "type": str(frame.fieldOutputs[fo].type),
            }
        result["available_fields"] = available
    else:
        for fname in field_names:
            if fname not in frame.fieldOutputs:
                result["fields"][fname] = {"error": f"Field '{fname}' not found", "available": list(frame.fieldOutputs.keys())}
                continue

            fo = frame.fieldOutputs[fname]
            loc = fo.locations[0] if fo.locations else None
            loc_str = str(loc) if loc else "unknown"

            values = []
            count = 0
            node_labels = [int(n) for n in node_filter.split(",") if n.strip()] if node_filter else None
            elem_labels = [int(e) for e in elem_filter.split(",") if e.strip()] if elem_filter else None

            for val in fo.values:
                if max_per_field and count >= max_per_field:
                    break

                label = val.nodeLabel if hasattr(val, "nodeLabel") else (val.elementLabel if hasattr(val, "elementLabel") else None)
                
                if node_labels and label not in node_labels:
                    continue
                if elem_labels and label not in elem_labels:
                    continue

                entry = {}
                if hasattr(val, "nodeLabel"):
                    entry["node"] = val.nodeLabel
                if hasattr(val, "elementLabel"):
                    entry["element"] = val.elementLabel
                if hasattr(val, "integrationPoint"):
                    entry["integration_point"] = val.integrationPoint
                if hasattr(val, "sectionPoint"):
                    entry["sectionPoint"] = val.sectionPoint

                # Handle data (scalar, vector, tensor)
                if hasattr(val, "data"):
                    d = val.data
                    if hasattr(d, "tolist"):
                        entry["value"] = d.tolist()
                    elif isinstance(d, (int, float)):
                        entry["value"] = d
                    else:
                        entry["value"] = str(d)

                if hasattr(val, "magnitude"):
                    entry["magnitude"] = val.magnitude

                values.append(entry)
                count += 1

            result["fields"][fname] = {
                "location": loc_str,
                "type": str(fo.type),
                "componentLabels": list(fo.componentLabels) if fo.componentLabels else [],
                "value_count": len(values),
                "truncated": count >= max_per_field if max_per_field else False,
                "values": values,
            }

    odb.close()
    print(json.dumps(result, default=str))

except Exception as e:
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}, default=str))
    sys.exit(1)
